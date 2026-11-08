import hashlib
import ipaddress
import logging
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied, ValidationError
from rest_framework.settings import api_settings as drf_settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .exceptions import ServicioNoDisponible
from .models import (
    AlcanceExcepcion,
    EstadoCancha,
    EstadoContrato,
    EstadoRegistro,
    EstadoUsuario,
    TipoEventoAuditoria,
    TipoMotivoExcepcion,
)
from .repositories import (
    ESTADOS_RESERVA_OCUPANTES,
    AuditoriaRepository,
    CanchaRepository,
    CatalogoRepository,
    ComplejoRepository,
    ComplejoServicioRepository,
    ExcepcionHorariaRepository,
    GrillaRepository,
    HorarioAperturaRepository,
    PermisoRepository,
    RolRepository,
    SesionRepository,
    UsuarioRepository,
)

logger_seguridad = logging.getLogger('seguridad')

ROL_SUPERADMIN = 'SUPERADMIN'
ROL_DUENO = 'DUENO_COMPLEJO'
ROL_OPERADOR = 'OPERADOR_COMPLEJO'
ROL_JUGADOR = 'JUGADOR'

# Soporte delegado: el superadmin conserva cualquier permiso de los roles de complejo aunque no lo tenga asignado.
ROLES_HEREDADOS_POR_SUPERADMIN = (ROL_DUENO, ROL_OPERADOR)


def _esta_autenticado(usuario):
    return usuario is not None and getattr(usuario, 'is_authenticated', False)


class RbacService:
    @staticmethod
    def nombre_rol_activo(usuario):
        if not _esta_autenticado(usuario) or usuario.rol_id is None:
            return None
        rol = usuario.rol
        return rol.nombre if rol.estado == EstadoRegistro.ACTIVO else None

    @staticmethod
    def es_superadmin(usuario):
        return (
            _esta_autenticado(usuario)
            and usuario.estado == EstadoUsuario.ACTIVO
            and RbacService.nombre_rol_activo(usuario) == ROL_SUPERADMIN
        )

    @staticmethod
    def permisos_de(usuario):
        if not _esta_autenticado(usuario):
            return frozenset()

        # El usuario autenticado es un objeto nuevo por petición: la caché dura lo que dura la request.
        codigos = getattr(usuario, '_permisos_rbac', None)
        if codigos is None:
            encontrados = PermisoRepository.codigos_activos_de_usuario(usuario.pk)
            if RbacService.es_superadmin(usuario):
                encontrados |= PermisoRepository.codigos_activos_de_roles(ROLES_HEREDADOS_POR_SUPERADMIN)
            codigos = frozenset(encontrados)
            usuario._permisos_rbac = codigos
        return codigos

    @staticmethod
    def tiene_permiso(usuario, codigo):
        return codigo in RbacService.permisos_de(usuario)

    @staticmethod
    def tiene_permisos(usuario, codigos):
        return set(codigos).issubset(RbacService.permisos_de(usuario))


class AccesoComplejoService:
    """Único punto que decide qué complejos administra un usuario."""

    @staticmethod
    def _rol(usuario):
        if not _esta_autenticado(usuario) or usuario.estado != EstadoUsuario.ACTIVO:
            return None
        return RbacService.nombre_rol_activo(usuario)

    @staticmethod
    def puede_administrar(usuario, complejo_id):
        try:
            complejo_id = int(complejo_id)
        except (TypeError, ValueError):
            return False

        rol = AccesoComplejoService._rol(usuario)
        if rol == ROL_SUPERADMIN:
            return ComplejoRepository.existe(complejo_id)
        if rol == ROL_DUENO:
            return ComplejoRepository.es_propietario(complejo_id, usuario.pk)
        if rol == ROL_OPERADOR:
            return usuario.complejo_operado_id == complejo_id and ComplejoRepository.existe(complejo_id)
        return False

    @staticmethod
    def filtrar_queryset(queryset, usuario, campo_complejo='complejo'):
        rol = AccesoComplejoService._rol(usuario)
        if rol == ROL_SUPERADMIN:
            return queryset
        if rol == ROL_DUENO:
            return ComplejoRepository.restringir_queryset(queryset, campo_complejo, {'propietario_id': usuario.pk})
        if rol == ROL_OPERADOR and usuario.complejo_operado_id:
            return ComplejoRepository.restringir_queryset(queryset, campo_complejo, {'id': usuario.complejo_operado_id})
        return queryset.none()

    @staticmethod
    def validar_operacion(usuario, complejo_id):
        if not AccesoComplejoService.puede_administrar(usuario, complejo_id):
            raise PermissionDenied('No podés operar sobre recursos de este complejo.')


CLAVES_SENSIBLES = ('password', 'contrasena', 'contraseña', 'token', 'access', 'refresh', 'authorization', 'secret')
PATRON_JWT = re.compile(r'eyJ[\w-]+\.[\w-]+\.[\w-]*')
PATRON_CLAVE_VALOR = re.compile(
    r'(?i)\b(password|contrase(?:ñ|n)a|token|access|refresh|authorization|secret)\b(\s*[:=]\s*)\S+'
)
LARGO_MAXIMO_DETALLE = 2000
VENTANA_AUDITORIA_429 = 60

NIVEL_POR_EVENTO = {
    TipoEventoAuditoria.LOGIN_FALLIDO: logging.WARNING,
    TipoEventoAuditoria.ACCESO_DENEGADO: logging.WARNING,
    TipoEventoAuditoria.LIMITE_PETICIONES: logging.WARNING,
}


class AuditoriaService:
    @staticmethod
    def _es_sensible(clave):
        clave = str(clave).lower()
        return any(sensible in clave for sensible in CLAVES_SENSIBLES)

    @staticmethod
    def depurar(valor):
        """Quita credenciales y saltos de línea antes de persistir o loguear (evita fugas e inyección en el log)."""
        if isinstance(valor, dict):
            valor = ', '.join(
                f'{clave}=[OCULTO]' if AuditoriaService._es_sensible(clave) else f'{clave}={dato}'
                for clave, dato in valor.items()
            )
        texto = PATRON_JWT.sub('[TOKEN OCULTO]', str(valor or ''))
        texto = PATRON_CLAVE_VALOR.sub(r'\1\2[OCULTO]', texto)
        texto = ' '.join(texto.split())
        return texto[:LARGO_MAXIMO_DETALLE]

    @staticmethod
    def ip_de_request(request):
        """Replica el criterio de DRF para identificar la IP (respeta NUM_PROXIES) y descarta valores inválidos."""
        remota = request.META.get('REMOTE_ADDR')
        reenviada = request.META.get('HTTP_X_FORWARDED_FOR')
        proxies = drf_settings.NUM_PROXIES
        candidata = remota
        if proxies is not None and reenviada and proxies > 0:
            direcciones = reenviada.split(',')
            candidata = direcciones[-min(proxies, len(direcciones))].strip()
        try:
            return str(ipaddress.ip_address(candidata))
        except ValueError:
            return None

    @staticmethod
    def registrar(tipo_evento, accion, *, detalle='', usuario=None, complejo=None, ip_origen=None):
        tipo_evento = TipoEventoAuditoria(tipo_evento)
        usuario_id = getattr(usuario, 'pk', usuario)
        complejo_id = getattr(complejo, 'pk', complejo)
        accion = AuditoriaService.depurar(accion)[:120]
        detalle = AuditoriaService.depurar(detalle)

        logger_seguridad.log(
            NIVEL_POR_EVENTO.get(tipo_evento, logging.INFO),
            'evento=%s accion="%s" usuario=%s complejo=%s ip=%s detalle="%s"',
            tipo_evento.name, accion, usuario_id, complejo_id, ip_origen, detalle,
        )

        try:
            # El savepoint evita que una falla de auditoría invalide la transacción del llamador.
            with transaction.atomic():
                return AuditoriaRepository.crear(tipo_evento, accion, detalle, usuario_id, complejo_id, ip_origen)
        except DatabaseError:
            logger_seguridad.exception('No se pudo guardar el evento %s en logs_auditoria', tipo_evento.name)
            return None

    @staticmethod
    def _usuario_de_request(request):
        usuario = getattr(request, 'user', None)
        return usuario if _esta_autenticado(usuario) else None

    @staticmethod
    def registrar_acceso_denegado(request, detalle=''):
        return AuditoriaService.registrar(
            TipoEventoAuditoria.ACCESO_DENEGADO,
            f'{request.method} {request.path}',
            detalle=detalle,
            usuario=AuditoriaService._usuario_de_request(request),
            ip_origen=AuditoriaService.ip_de_request(request),
        )

    @staticmethod
    def registrar_limite_peticiones(request, detalle=''):
        """
        Un ataque de fuerza bruta genera miles de 429: se persiste el primero de cada ventana por IP,
        usuario y ruta, que alcanza para saber quién fue rechazado, dónde y por qué, sin amplificar escrituras.
        """
        usuario = AuditoriaService._usuario_de_request(request)
        ip_origen = AuditoriaService.ip_de_request(request)
        accion = f'{request.method} {request.path}'
        huella = hashlib.sha256(f'{ip_origen}|{getattr(usuario, "pk", None)}|{accion}'.encode()).hexdigest()
        if not cache.add(f'auditoria:429:{huella}', 1, timeout=VENTANA_AUDITORIA_429):
            return None
        return AuditoriaService.registrar(
            TipoEventoAuditoria.LIMITE_PETICIONES,
            accion,
            detalle=detalle or 'Se superó el límite de solicitudes permitido.',
            usuario=usuario,
            ip_origen=ip_origen,
        )

    @staticmethod
    def listar(tipo_evento=None, usuario=None, complejo=None, ip_origen=None, fecha_desde=None, fecha_hasta=None):
        zona = timezone.get_current_timezone()
        desde = datetime.combine(fecha_desde, time.min, tzinfo=zona) if fecha_desde else None
        hasta = datetime.combine(fecha_hasta + timedelta(days=1), time.min, tzinfo=zona) if fecha_hasta else None
        return AuditoriaRepository.listar(
            tipo_evento=tipo_evento,
            usuario_id=usuario,
            complejo_id=complejo,
            ip_origen=ip_origen,
            desde=desde,
            hasta=hasta,
        )


MENSAJE_CREDENCIALES_INVALIDAS = 'Email o contraseña incorrectos.'
MENSAJE_ULTIMO_SUPERADMIN_PROPIO = (
    'No podés dar de baja la única cuenta de superadministrador activa. '
    'Asigná otro superadministrador antes de hacerlo.'
)
MENSAJE_ULTIMO_SUPERADMIN_ADMINISTRATIVO = (
    'No se puede suspender, dar de baja ni cambiar el rol de la única cuenta de superadministrador activa. '
    'Asigná otro superadministrador antes de hacerlo.'
)


class SesionService:
    @staticmethod
    def autenticar(email, password, ip_origen):
        usuario = UsuarioRepository.obtener_por_email(email)

        # La auditoría identifica al titular solo por FK: el email tipeado no se guarda, porque puede ser
        # de un tercero sin cuenta (minimización de datos personales).
        if usuario is None:
            # Hashear igual que con un usuario real impide distinguir emails registrados por tiempo de respuesta.
            get_user_model()().set_password(password)
            AuditoriaService.registrar(
                TipoEventoAuditoria.LOGIN_FALLIDO, 'Inicio de sesión fallido',
                detalle='Email no registrado.', ip_origen=ip_origen,
            )
            raise AuthenticationFailed(MENSAJE_CREDENCIALES_INVALIDAS)

        if not usuario.check_password(password):
            AuditoriaService.registrar(
                TipoEventoAuditoria.LOGIN_FALLIDO, 'Inicio de sesión fallido',
                detalle='Contraseña incorrecta.', usuario=usuario, ip_origen=ip_origen,
            )
            raise AuthenticationFailed(MENSAJE_CREDENCIALES_INVALIDAS)

        if usuario.estado != EstadoUsuario.ACTIVO:
            AuditoriaService.registrar(
                TipoEventoAuditoria.LOGIN_FALLIDO, 'Inicio de sesión rechazado',
                detalle=f'Cuenta no activa ({usuario.get_estado_display()}).',
                usuario=usuario, ip_origen=ip_origen,
            )
            raise AuthenticationFailed('La cuenta no está activa.')

        AuditoriaService.registrar(
            TipoEventoAuditoria.LOGIN_EXITOSO, 'Inicio de sesión', usuario=usuario, ip_origen=ip_origen,
        )
        return usuario

    @staticmethod
    def emitir_refresh(usuario):
        from .serializers_auth import TokenConRolSerializer

        return TokenConRolSerializer.get_token(usuario)

    @staticmethod
    def _leer_refresh(token):
        if not token:
            raise AuthenticationFailed('No hay una sesión activa.')
        try:
            return RefreshToken(token)
        except TokenError:
            raise AuthenticationFailed('La sesión expiró o no es válida. Iniciá sesión nuevamente.')

    @staticmethod
    def rotar_refresh(token):
        refresh = SesionService._leer_refresh(token)
        usuario = UsuarioRepository.obtener_activo_por_id(refresh.payload.get(jwt_settings.USER_ID_CLAIM))
        if usuario is None:
            raise AuthenticationFailed('La cuenta no está activa.')
        refresh.blacklist()
        # El token nuevo se arma desde la base, así el claim rol refleja cambios hechos durante la sesión.
        return SesionService.emitir_refresh(usuario)

    @staticmethod
    def cerrar_sesion(token, ip_origen):
        if not token:
            raise AuthenticationFailed('No hay una sesión activa.')
        try:
            refresh = RefreshToken(token)
        except TokenError:
            # Un refresh vencido o ya revocado no abre sesión: el cierre es idempotente.
            return
        refresh.blacklist()
        AuditoriaService.registrar(
            TipoEventoAuditoria.LOGOUT, 'Cierre de sesión',
            usuario=refresh.payload.get(jwt_settings.USER_ID_CLAIM), ip_origen=ip_origen,
        )


class UsuarioService:
    @staticmethod
    def _constancia_de_consentimiento():
        return {
            'version_politica_aceptada': settings.POLITICA_PRIVACIDAD_VERSION,
            'fecha_aceptacion_politica': timezone.now(),
        }

    @staticmethod
    def registrar_jugador(datos, ip_origen):
        rol = RolRepository.obtener_activo_por_nombre(ROL_JUGADOR)
        if rol is None:
            raise ServicioNoDisponible('El registro no está disponible: falta configurar el rol de jugador.')

        usuario = UsuarioRepository.crear(
            email=datos['email'],
            password=datos['password'],
            rol=rol,
            nombre_completo=datos['nombre_completo'],
            telefono=datos.get('telefono', ''),
            **UsuarioService._constancia_de_consentimiento(),
        )
        AuditoriaService.registrar(
            TipoEventoAuditoria.REGISTRO_USUARIO, 'Registro de jugador',
            detalle=f'Alta pública con rol de jugador. Política de privacidad {usuario.version_politica_aceptada} aceptada.',
            usuario=usuario, ip_origen=ip_origen,
        )
        return usuario

    @staticmethod
    def actualizar_perfil(usuario, datos, ip_origen):
        campos = {campo: datos[campo] for campo in ('nombre_completo', 'telefono') if campo in datos}
        acepta_politica = datos.get('acepta_politica_privacidad', False)
        if acepta_politica:
            campos.update(UsuarioService._constancia_de_consentimiento())
        if not campos:
            return usuario

        UsuarioRepository.actualizar(usuario, **campos)
        if acepta_politica:
            AuditoriaService.registrar(
                TipoEventoAuditoria.ACEPTACION_POLITICA, 'Aceptación de la política de privacidad',
                detalle=f'Versión {usuario.version_politica_aceptada}.', usuario=usuario, ip_origen=ip_origen,
            )
        return usuario

    @staticmethod
    def _validar_continuidad_superadmin(usuario, mensaje=MENSAJE_ULTIMO_SUPERADMIN_PROPIO):
        """
        La plataforma no puede quedar sin superadministrador activo. Se bloquean todas las filas de superadmins
        activos (incluida la propia) para que dos bajas simultáneas no pasen la validación a la vez.
        """
        if not RbacService.es_superadmin(usuario):
            return
        activos = UsuarioRepository.bloquear_activos_con_rol(ROL_SUPERADMIN)
        if not [usuario_id for usuario_id in activos if usuario_id != usuario.pk]:
            raise ValidationError(mensaje)

    @staticmethod
    def _validar_complejos_sin_responsable(usuario):
        # Un complejo con contrato vigente no puede quedar sin titular identificable.
        if ComplejoRepository.tiene_contratos_vigentes(usuario.pk):
            raise ValidationError(
                'Tenés complejos con contrato vigente. Pedí la baja del contrato al superadministrador '
                'antes de dar de baja tu cuenta.'
            )

    @staticmethod
    def desactivar_cuenta_propia(usuario, ip_origen):
        """Atiende el derecho de supresión: baja lógica, anonimización de datos personales y cierre de sesiones."""
        with transaction.atomic():
            UsuarioService._validar_continuidad_superadmin(usuario)
            UsuarioService._validar_complejos_sin_responsable(usuario)
            UsuarioRepository.anonimizar(usuario)
            usuario.desactivar()
            SesionRepository.revocar_refresh_de_usuario(usuario.pk)
        AuditoriaService.registrar(
            TipoEventoAuditoria.BAJA_USUARIO, 'Baja lógica de la cuenta propia',
            detalle='Baja solicitada por el titular: datos personales anonimizados y sesiones revocadas.',
            usuario=usuario, ip_origen=ip_origen,
        )


def _campos_modificados(instancia, datos):
    return {campo: valor for campo, valor in datos.items() if getattr(instancia, campo) != valor}


class UsuarioAdminService:
    """Gestión de cuentas por el superadministrador. La baja administrativa no anonimiza: es una medida de seguridad."""

    @staticmethod
    def listar():
        return UsuarioRepository.listar()

    @staticmethod
    def _validar_cambio(usuario, rol_nuevo, estado_nuevo, datos):
        if usuario.estado == EstadoUsuario.BAJA and not usuario.has_usable_password():
            raise ValidationError(
                'La cuenta fue dada de baja por su titular y sus datos personales se anonimizaron: no admite cambios.'
            )

        sigue_siendo_superadmin = estado_nuevo == EstadoUsuario.ACTIVO and rol_nuevo.nombre == ROL_SUPERADMIN
        if not sigue_siendo_superadmin:
            UsuarioService._validar_continuidad_superadmin(usuario, MENSAJE_ULTIMO_SUPERADMIN_ADMINISTRATIVO)

        deja_de_ser_dueno = usuario.rol.nombre == ROL_DUENO and rol_nuevo.nombre != ROL_DUENO
        if deja_de_ser_dueno and ComplejoRepository.tiene_contratos_vigentes(usuario.pk):
            raise ValidationError({
                'rol': 'El usuario es titular de complejos con contrato vigente: '
                       'dá de baja esos contratos antes de cambiarle el rol.',
            })

        if rol_nuevo.nombre != ROL_OPERADOR and datos.get('complejo_operado') is not None:
            raise ValidationError({
                'complejo_operado': 'Solo un usuario con rol de operador puede tener un complejo asignado.',
            })

    @staticmethod
    def _describir_cambios(usuario, campos, estado_anterior, rol_anterior, sesiones_revocadas):
        # Solo nombres de campos e ids: la auditoría no replica datos personales.
        partes = [f'Usuario afectado: id {usuario.pk}.']
        if 'estado' in campos:
            partes.append(
                f'Estado: {EstadoUsuario(estado_anterior).label} -> {EstadoUsuario(usuario.estado).label}.'
            )
        if 'rol' in campos:
            partes.append(f'Rol: {rol_anterior.nombre} -> {usuario.rol.nombre}.')
        if 'complejo_operado' in campos:
            partes.append(f'Complejo operado: {usuario.complejo_operado_id or "ninguno"}.')
        editados = sorted(set(campos) & {'nombre_completo', 'telefono'})
        if editados:
            partes.append(f'Campos editados: {", ".join(editados)}.')
        if sesiones_revocadas:
            partes.append('Sesiones revocadas.')
        return ' '.join(partes)

    @staticmethod
    def actualizar(usuario_id, datos, actor, ip_origen):
        with transaction.atomic():
            if 'estado' in datos or 'rol' in datos:
                # Mismo orden de bloqueo que la baja propia (superadmins primero, por id): evita deadlocks
                # entre dos operaciones concurrentes sobre superadministradores.
                UsuarioRepository.bloquear_activos_con_rol(ROL_SUPERADMIN)
            usuario = UsuarioRepository.bloquear_por_id(usuario_id)
            if usuario is None:
                raise NotFound()

            rol_nuevo = datos.get('rol', usuario.rol)
            estado_nuevo = datos.get('estado', usuario.estado)
            UsuarioAdminService._validar_cambio(usuario, rol_nuevo, estado_nuevo, datos)

            if rol_nuevo.nombre != ROL_OPERADOR:
                datos = {**datos, 'complejo_operado': None}
            campos = _campos_modificados(usuario, datos)
            if not campos:
                return usuario

            estado_anterior, rol_anterior = usuario.estado, usuario.rol
            UsuarioRepository.actualizar(usuario, **campos)
            sesiones_revocadas = 'estado' in campos and usuario.estado != EstadoUsuario.ACTIVO
            if sesiones_revocadas:
                SesionRepository.revocar_refresh_de_usuario(usuario.pk)

        es_baja = 'estado' in campos and usuario.estado == EstadoUsuario.BAJA
        AuditoriaService.registrar(
            TipoEventoAuditoria.BAJA_USUARIO if es_baja else TipoEventoAuditoria.CAMBIO_USUARIO,
            'Baja administrativa de usuario' if es_baja else 'Cambio administrativo de usuario',
            detalle=UsuarioAdminService._describir_cambios(
                usuario, campos, estado_anterior, rol_anterior, sesiones_revocadas,
            ),
            usuario=actor, ip_origen=ip_origen,
        )
        return usuario


class ContratoService:
    @staticmethod
    def listar():
        return ComplejoRepository.contratos()

    @staticmethod
    def crear(datos, actor, ip_origen):
        complejo = ComplejoRepository.crear(**datos)
        AuditoriaService.registrar(
            TipoEventoAuditoria.CAMBIO_CONTRATO, 'Alta de contrato de complejo',
            detalle=f'Estado inicial: {complejo.get_estado_contrato_display()}. '
                    f'Propietario: id {complejo.propietario_id}.',
            usuario=actor, complejo=complejo, ip_origen=ip_origen,
        )
        return complejo

    @staticmethod
    def cambiar_estado(complejo_id, estado_nuevo, actor, ip_origen):
        """
        El catálogo público solo muestra contratos activos: pasar a Suspendido o Baja oculta el complejo al
        instante sin tocar sus canchas, reservas ni auditoría, y el titular conserva el acceso a su historial.
        """
        with transaction.atomic():
            complejo = ComplejoRepository.bloquear(complejo_id)
            estado_anterior = complejo.estado_contrato
            if estado_anterior == estado_nuevo:
                return complejo
            if estado_nuevo == EstadoContrato.ACTIVO:
                propietario = complejo.propietario
                es_dueno_activo = (
                    propietario.estado == EstadoUsuario.ACTIVO
                    and RbacService.nombre_rol_activo(propietario) == ROL_DUENO
                )
                if not es_dueno_activo:
                    raise ValidationError({
                        'estado_contrato': 'No se puede activar el contrato: el propietario no es un dueño de '
                                           'complejo activo.',
                    })
            ComplejoRepository.actualizar(complejo, estado_contrato=estado_nuevo)

        AuditoriaService.registrar(
            TipoEventoAuditoria.CAMBIO_CONTRATO, 'Cambio de estado de contrato',
            detalle=f'{EstadoContrato(estado_anterior).label} -> {EstadoContrato(estado_nuevo).label}.',
            usuario=actor, complejo=complejo, ip_origen=ip_origen,
        )
        return complejo


class CatalogoService:
    @staticmethod
    def deportes():
        return CatalogoRepository.deportes_activos()

    @staticmethod
    def servicios():
        return CatalogoRepository.servicios_activos()

    @staticmethod
    def complejos_publicos():
        return ComplejoRepository.catalogo_publico()


class ComplejoService:
    @staticmethod
    def listar_administrables(usuario):
        return AccesoComplejoService.filtrar_queryset(
            ComplejoRepository.administrables(), usuario, campo_complejo='',
        )

    @staticmethod
    def actualizar_configuracion(complejo, datos, actor, ip_origen):
        campos = _campos_modificados(complejo, datos)
        if not campos:
            return complejo
        ComplejoRepository.actualizar(complejo, **campos)
        AuditoriaService.registrar(
            TipoEventoAuditoria.CAMBIO_CONFIGURACION, 'Cambio de configuración del complejo',
            detalle=f'Campos modificados: {", ".join(sorted(campos))}.',
            usuario=actor, complejo=complejo, ip_origen=ip_origen,
        )
        return complejo

    @staticmethod
    def sincronizar_servicios(complejo, servicios, actor, ip_origen):
        """
        Deja activos exactamente los servicios pedidos. Las asignaciones quitadas pasan a baja lógica y las
        que vuelven a pedirse se reactivan, sin duplicar filas (uq_complejo_servicio).
        """
        pedidos = {servicio.pk for servicio in servicios}
        agregados, quitados = [], []
        with transaction.atomic():
            ComplejoRepository.bloquear(complejo.pk)
            existentes = {asignacion.servicio_id: asignacion for asignacion in
                          ComplejoServicioRepository.de_complejo(complejo.pk)}
            for servicio_id in sorted(pedidos):
                asignacion = existentes.get(servicio_id)
                if asignacion is None:
                    ComplejoServicioRepository.crear(complejo.pk, servicio_id)
                    agregados.append(servicio_id)
                elif asignacion.estado != EstadoRegistro.ACTIVO:
                    ComplejoServicioRepository.reactivar(asignacion)
                    agregados.append(servicio_id)
            for servicio_id, asignacion in sorted(existentes.items()):
                if servicio_id not in pedidos and asignacion.estado == EstadoRegistro.ACTIVO:
                    asignacion.desactivar()
                    quitados.append(servicio_id)

        if agregados or quitados:
            AuditoriaService.registrar(
                TipoEventoAuditoria.CAMBIO_CONFIGURACION, 'Cambio de servicios del complejo',
                detalle=f'Servicios agregados: {agregados or "ninguno"}. Servicios quitados: {quitados or "ninguno"}.',
                usuario=actor, complejo=complejo, ip_origen=ip_origen,
            )
        return ComplejoServicioRepository.servicios_activos_de(complejo.pk)


MENSAJE_OPERADOR_NO_DISPONIBLE = 'El email no corresponde a un operador activo disponible para asignar.'


class OperadorService:
    @staticmethod
    def listar(complejo):
        return UsuarioRepository.operadores_de(complejo.pk)

    @staticmethod
    def vincular(complejo, email, actor, ip_origen):
        """
        Se vincula por email exacto, que el dueño conoce porque es su personal: con un id bastaría
        recorrer números para encontrar operadores libres y ver sus datos de contacto.
        """
        with transaction.atomic():
            usuario = UsuarioRepository.bloquear_por_email(email)
            # Un único mensaje para inexistente, otro rol o asignado a otro complejo: no se revela nada de cuentas ajenas.
            disponible = (
                usuario is not None
                and usuario.estado == EstadoUsuario.ACTIVO
                and RbacService.nombre_rol_activo(usuario) == ROL_OPERADOR
            )
            if not disponible:
                raise ValidationError({'email': MENSAJE_OPERADOR_NO_DISPONIBLE})
            if usuario.complejo_operado_id == complejo.pk:
                raise ValidationError({'email': 'El usuario ya opera este complejo.'})
            if usuario.complejo_operado_id is not None:
                raise ValidationError({'email': MENSAJE_OPERADOR_NO_DISPONIBLE})
            UsuarioRepository.actualizar(usuario, complejo_operado=complejo)

        AuditoriaService.registrar(
            TipoEventoAuditoria.CAMBIO_CONFIGURACION, 'Alta de operador del complejo',
            detalle=f'Operador: id {usuario.pk}.', usuario=actor, complejo=complejo, ip_origen=ip_origen,
        )
        return usuario

    @staticmethod
    def desvincular(complejo, usuario_id, actor, ip_origen):
        with transaction.atomic():
            usuario = UsuarioRepository.bloquear_por_id(usuario_id)
            if usuario is None or usuario.complejo_operado_id != complejo.pk:
                raise NotFound()
            UsuarioRepository.actualizar(usuario, complejo_operado=None)

        AuditoriaService.registrar(
            TipoEventoAuditoria.CAMBIO_CONFIGURACION, 'Baja de operador del complejo',
            detalle=f'Operador: id {usuario.pk}.', usuario=actor, complejo=complejo, ip_origen=ip_origen,
        )


MENSAJE_NOMBRE_CANCHA_REPETIDO = 'Ya existe una cancha con ese nombre en el complejo.'


class CanchaService:
    @staticmethod
    def listar():
        return CanchaRepository.vigentes()

    @staticmethod
    def es_visible_para(usuario, cancha_id):
        return AccesoComplejoService.filtrar_queryset(CanchaRepository.vigentes(), usuario).filter(id=cancha_id).exists()

    @staticmethod
    def _validar_nombre(complejo_id, nombre, excluir_id=None):
        if CanchaRepository.existe_nombre(complejo_id, nombre, excluir_id):
            raise ValidationError({'nombre': MENSAJE_NOMBRE_CANCHA_REPETIDO})

    @staticmethod
    def crear(datos):
        CanchaService._validar_nombre(datos['complejo'].pk, datos['nombre'])
        try:
            with transaction.atomic():
                return CanchaRepository.crear(**datos)
        except IntegrityError:
            # Alta simultánea con el mismo nombre: la restricción uq_cancha_nombre_activa decide.
            raise ValidationError({'nombre': MENSAJE_NOMBRE_CANCHA_REPETIDO})

    @staticmethod
    def actualizar(cancha, datos):
        campos = _campos_modificados(cancha, datos)
        if not campos:
            return cancha
        if 'nombre' in campos:
            CanchaService._validar_nombre(cancha.complejo_id, campos['nombre'], excluir_id=cancha.pk)
        try:
            with transaction.atomic():
                return CanchaRepository.actualizar(cancha, **campos)
        except IntegrityError:
            raise ValidationError({'nombre': MENSAJE_NOMBRE_CANCHA_REPETIDO})

    @staticmethod
    def dar_de_baja(cancha):
        with transaction.atomic():
            CanchaRepository.bloquear(cancha.pk)
            if CanchaRepository.tiene_ocupacion_futura(cancha.pk, timezone.localdate()):
                raise ValidationError(
                    'La cancha tiene reservas o turnos fijos vigentes desde hoy en adelante. '
                    'Cancelalos antes de darla de baja.'
                )
            cancha.desactivar()


class HorarioAperturaService:
    @staticmethod
    def listar():
        return HorarioAperturaRepository.vigentes()

    @staticmethod
    def _validar_rango_libre(cancha_id, dia_semana, apertura, cierre, excluir_id=None):
        """
        Un día admite varios rangos (por ejemplo, 08:00 a 12:00 y 16:00 a 23:00), cada uno con su precio,
        siempre que no se superpongan entre sí.
        """
        existente = HorarioAperturaRepository.solapado(cancha_id, dia_semana, apertura, cierre, excluir_id)
        if existente is not None:
            rango = f'{existente.hora_apertura:%H:%M} a {existente.hora_cierre:%H:%M}'
            raise ValidationError({
                'hora_apertura': f'El rango se solapa con otro horario activo de ese día ({rango}).',
            })

    @staticmethod
    def _guardar(cancha_id, dia_semana, apertura, cierre, excluir_id, operacion):
        with transaction.atomic():
            # Bloquear la cancha serializa altas y ediciones simultáneas de sus horarios: dos rangos
            # superpuestos no pueden pasar la validación a la vez.
            CanchaRepository.bloquear(cancha_id)
            HorarioAperturaService._validar_rango_libre(cancha_id, dia_semana, apertura, cierre, excluir_id)
            return operacion()

    @staticmethod
    def crear(datos):
        return HorarioAperturaService._guardar(
            datos['cancha'].pk, datos['dia_semana'], datos['hora_apertura'], datos['hora_cierre'], None,
            lambda: HorarioAperturaRepository.crear(**datos),
        )

    @staticmethod
    def actualizar(horario, datos):
        campos = _campos_modificados(horario, datos)
        if not campos:
            return horario
        return HorarioAperturaService._guardar(
            horario.cancha_id,
            campos.get('dia_semana', horario.dia_semana),
            campos.get('hora_apertura', horario.hora_apertura),
            campos.get('hora_cierre', horario.hora_cierre),
            horario.pk,
            lambda: HorarioAperturaRepository.actualizar(horario, **campos),
        )

    @staticmethod
    def dar_de_baja(horario):
        horario.desactivar()


EVENTO_GRILLA_ACTUALIZADA = 'grilla_actualizada'


class DifusionGrillaService:
    """
    Punto único de aviso a las grillas abiertas de un complejo. El evento se programa con
    transaction.on_commit, nunca dentro del bloque atómico: un rollback no puede anunciar un cambio que no
    ocurrió. Solo lleva ids, fechas y horarios, sin datos personales.
    """

    @staticmethod
    def programar(complejo_id, **cambio):
        evento = {'event': EVENTO_GRILLA_ACTUALIZADA, **cambio}
        transaction.on_commit(lambda: DifusionGrillaService.publicar(complejo_id, evento))

    @staticmethod
    def publicar(complejo_id, evento):
        """
        Envía el evento al grupo complejo_<id> del channel layer. Mientras no exista el consumer de
        disponibilidad no hay grillas suscriptas, así que todavía no hay a quién enviarlo.
        """
        return None


MAXIMO_DIAS_EXCEPCION = 366


def _hora_iso(valor):
    return valor.isoformat() if valor is not None else None


class ExcepcionHorariaService:
    @staticmethod
    def listar():
        return ExcepcionHorariaRepository.vigentes()

    @staticmethod
    def _validar_alta(datos):
        cancha = datos.get('cancha')
        if cancha is not None:
            if cancha.complejo_id != datos['complejo'].pk:
                raise ValidationError({'cancha': 'La cancha no pertenece al complejo indicado.'})
            if cancha.estado != EstadoCancha.ACTIVA:
                raise ValidationError({'cancha': 'Solo se registran excepciones sobre canchas activas.'})
        if datos['fecha_inicio'] < timezone.localdate():
            raise ValidationError({'fecha_inicio': 'No puede ser anterior a hoy.'})
        if (datos['fecha_fin'] - datos['fecha_inicio']).days >= MAXIMO_DIAS_EXCEPCION:
            raise ValidationError({
                'fecha_fin': f'Una excepción abarca como máximo {MAXIMO_DIAS_EXCEPCION} días.',
            })

    @staticmethod
    def _describir(excepcion):
        # La descripción es texto libre del personal y puede nombrar a terceros: no se replica en la auditoría.
        alcance = f'cancha id {excepcion.cancha_id}' if excepcion.cancha_id else 'todo el complejo'
        if excepcion.es_dia_completo == AlcanceExcepcion.DIA_COMPLETO:
            horario = 'día completo'
        else:
            horario = f'{excepcion.hora_inicio:%H:%M} a {excepcion.hora_fin:%H:%M}'
        return (
            f'Excepción id {excepcion.pk}. Alcance: {alcance}. '
            f'Fechas: {excepcion.fecha_inicio.isoformat()} a {excepcion.fecha_fin.isoformat()}. '
            f'Horario: {horario}. Motivo: {TipoMotivoExcepcion(excepcion.tipo_motivo).label}.'
        )

    @staticmethod
    def _difundir(excepcion):
        DifusionGrillaService.programar(
            excepcion.complejo_id,
            cancha_id=excepcion.cancha_id,
            fecha_desde=excepcion.fecha_inicio.isoformat(),
            fecha_hasta=excepcion.fecha_fin.isoformat(),
            hora_inicio=_hora_iso(excepcion.hora_inicio),
            hora_fin=_hora_iso(excepcion.hora_fin),
        )

    @staticmethod
    def crear(datos, actor, ip_origen):
        ExcepcionHorariaService._validar_alta(datos)
        with transaction.atomic():
            excepcion = ExcepcionHorariaRepository.crear(creado_por=actor, **datos)
            ExcepcionHorariaService._difundir(excepcion)

        AuditoriaService.registrar(
            TipoEventoAuditoria.ALTA_EXCEPCION, 'Alta de excepción horaria',
            detalle=ExcepcionHorariaService._describir(excepcion),
            usuario=actor, complejo=excepcion.complejo_id, ip_origen=ip_origen,
        )
        return excepcion

    @staticmethod
    def dar_de_baja(excepcion_id, actor, ip_origen):
        with transaction.atomic():
            # El bloqueo evita que dos bajas simultáneas de la misma excepción se registren dos veces.
            excepcion = ExcepcionHorariaRepository.bloquear(excepcion_id)
            if excepcion is None or excepcion.estado != EstadoRegistro.ACTIVO:
                raise NotFound()
            excepcion.desactivar()
            ExcepcionHorariaService._difundir(excepcion)

        AuditoriaService.registrar(
            TipoEventoAuditoria.BAJA_EXCEPCION, 'Baja de excepción horaria',
            detalle=ExcepcionHorariaService._describir(excepcion),
            usuario=actor, complejo=excepcion.complejo_id, ip_origen=ip_origen,
        )


BLOQUE_LIBRE = 'LIBRE'
BLOQUE_OCUPADO = 'OCUPADO'
BLOQUE_CERRADO_EXCEPCION = 'CERRADO_EXCEPCION'

# Fecha arbitraria para operar con horas: ningún rango cruza la medianoche (ck_horario_apertura_cierre).
_FECHA_DE_REFERENCIA = date(2000, 1, 1)


def _se_superponen(inicio_a, fin_a, inicio_b, fin_b):
    """Intervalos semiabiertos [inicio, fin): los contiguos (14 a 15 y 15 a 16) no se superponen."""
    return inicio_a < fin_b and fin_a > inicio_b


class GrillaService:
    @staticmethod
    def generar_bloques(apertura, cierre, duracion_min):
        """Turnos consecutivos desde la apertura; un resto menor a un turno completo no se ofrece."""
        paso = timedelta(minutes=duracion_min)
        inicio = datetime.combine(_FECHA_DE_REFERENCIA, apertura)
        limite = datetime.combine(_FECHA_DE_REFERENCIA, cierre)
        bloques = []
        while inicio + paso <= limite:
            bloques.append((inicio.time(), (inicio + paso).time()))
            inicio += paso
        return bloques

    @staticmethod
    def _ocupaciones_por_cancha(reservas, turnos_fijos):
        """
        Una reserva ocupante bloquea su horario. Un turno fijo vigente ocupa el suyo salvo que esa fecha ya
        tenga una reserva generada por él: en ese caso manda el estado de la reserva, así cancelar una
        fecha puntual del turno fijo libera el casillero.
        """
        ocupaciones = defaultdict(list)
        turnos_con_reserva = set()
        for reserva in reservas:
            if reserva['turno_fijo_id'] is not None:
                turnos_con_reserva.add(reserva['turno_fijo_id'])
            if reserva['estado'] in ESTADOS_RESERVA_OCUPANTES:
                ocupaciones[reserva['cancha_id']].append((reserva['hora_inicio'], reserva['hora_fin']))
        for turno in turnos_fijos:
            if turno['id'] not in turnos_con_reserva:
                ocupaciones[turno['cancha_id']].append((turno['hora_inicio'], turno['hora_fin']))
        return ocupaciones

    @staticmethod
    def _excepciones_por_cancha(excepciones, cancha_ids):
        globales = [excepcion for excepcion in excepciones if excepcion['cancha_id'] is None]
        por_cancha = {cancha_id: list(globales) for cancha_id in cancha_ids}
        for excepcion in excepciones:
            if excepcion['cancha_id'] in por_cancha:
                por_cancha[excepcion['cancha_id']].append(excepcion)
        return por_cancha

    @staticmethod
    def _estado_del_bloque(inicio, fin, ocupaciones, excepciones):
        """
        La ocupación prevalece sobre la excepción: un turno ya tomado se informa ocupado aunque el complejo
        cierre después, y sigue a la vista en la agenda hasta que el complejo lo resuelva.
        """
        if any(_se_superponen(inicio, fin, desde, hasta) for desde, hasta in ocupaciones):
            return BLOQUE_OCUPADO, None
        for excepcion in excepciones:
            cubre_el_bloque = excepcion['es_dia_completo'] == AlcanceExcepcion.DIA_COMPLETO or _se_superponen(
                inicio, fin, excepcion['hora_inicio'], excepcion['hora_fin'],
            )
            if cubre_el_bloque:
                return BLOQUE_CERRADO_EXCEPCION, TipoMotivoExcepcion(excepcion['tipo_motivo']).label
        return BLOQUE_LIBRE, None

    @staticmethod
    def calcular(complejo_id, fecha):
        """
        Grilla pública de un día: los bloques de cada rango horario activo de las canchas activas, con su
        precio y su estado. La cantidad de consultas es fija, sin importar canchas ni reservas.
        """
        if fecha < timezone.localdate():
            raise ValidationError({'fecha': 'La grilla se consulta desde hoy en adelante.'})
        complejo = ComplejoRepository.publico_por_id(complejo_id)
        if complejo is None:
            raise NotFound()

        dia_semana = fecha.weekday()
        canchas = GrillaRepository.canchas_activas(complejo.pk)
        cancha_ids = [cancha.pk for cancha in canchas]

        horarios = defaultdict(list)
        for horario in GrillaRepository.horarios_del_dia(cancha_ids, dia_semana):
            horarios[horario['cancha_id']].append(horario)
        excepciones = GrillaService._excepciones_por_cancha(
            ExcepcionHorariaRepository.activas_en_fecha(complejo.pk, fecha), cancha_ids,
        )
        ocupaciones = GrillaService._ocupaciones_por_cancha(
            GrillaRepository.reservas_de_fecha(cancha_ids, fecha),
            GrillaRepository.turnos_fijos_vigentes(cancha_ids, dia_semana, fecha),
        )

        resultado = []
        for cancha in canchas:
            bloques = []
            for horario in horarios[cancha.pk]:
                precio = horario['precio_diferenciado']
                if precio is None:
                    precio = cancha.precio_base
                for inicio, fin in GrillaService.generar_bloques(
                    horario['hora_apertura'], horario['hora_cierre'], cancha.duracion_turno_min,
                ):
                    estado, motivo = GrillaService._estado_del_bloque(
                        inicio, fin, ocupaciones[cancha.pk], excepciones[cancha.pk],
                    )
                    bloques.append({
                        'hora_inicio': inicio, 'hora_fin': fin, 'precio': precio, 'estado': estado, 'motivo': motivo,
                    })
            resultado.append({
                'id': cancha.pk,
                'nombre': cancha.nombre,
                'deporte': cancha.deporte,
                'duracion_turno_min': cancha.duracion_turno_min,
                'bloques': bloques,
            })

        return {'complejo': complejo, 'fecha': fecha, 'dia_semana': dia_semana, 'canchas': resultado}
