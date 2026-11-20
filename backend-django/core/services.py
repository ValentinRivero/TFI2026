import asyncio
import calendar
import hashlib
import ipaddress
import logging
import re
import threading
import time as time_module
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied, ValidationError
from rest_framework.settings import api_settings as drf_settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from . import node_client
from .exceptions import ConflictoConConfirmacion, ConflictoNegocio, ServicioNoDisponible
from .models import (
    LARGO_ACCION_AUDITORIA,
    AlcanceExcepcion,
    DiaSemana,
    EstadoCancha,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    EstadoTurnoFijo,
    EstadoUsuario,
    TipoEventoAuditoria,
    TipoMotivoExcepcion,
    TipoOcupacion,
)
from .repositories import (
    ESTADOS_RESERVA_A_RESOLVER,
    ESTADOS_RESERVA_OCUPANTES,
    AuditoriaRepository,
    CanchaRepository,
    CatalogoRepository,
    ComplejoRepository,
    ComplejoServicioRepository,
    DeporteRepository,
    ExcepcionHorariaRepository,
    GrillaRepository,
    HorarioAperturaRepository,
    PermisoRepository,
    ReporteRepository,
    ReservaRepository,
    RolAdminRepository,
    RolRepository,
    ServicioRepository,
    SesionRepository,
    TurnoFijoRepository,
    UsuarioRepository,
)

logger_seguridad = logging.getLogger('seguridad')

ROL_SUPERADMIN = 'SUPERADMIN'
ROL_DUENO = 'DUENO_COMPLEJO'
ROL_OPERADOR = 'OPERADOR_COMPLEJO'
ROL_JUGADOR = 'JUGADOR'
# Roles que carga seed_inicial: el código decide el acceso por su nombre y el seed reescribe sus permisos en cada despliegue.
ROLES_BASE = (ROL_SUPERADMIN, ROL_DUENO, ROL_OPERADOR, ROL_JUGADOR)
# Los permisos de estos módulos gobiernan la plataforma entera: solo los tiene el superadministrador y un rol
# personalizado nunca los recibe, para que crear un rol no sea una vía de escalación de privilegios.
MODULOS_EXCLUSIVOS_DE_PLATAFORMA = frozenset({'sistema'})

CATEGORIA_AVISO_RESERVAS = 1
CATEGORIA_AVISO_CUENTAS = 2
CATEGORIA_AVISO_OPERATORIA = 3
CATEGORIA_AVISO_SISTEMA = 4
# Tipo de la colección `eventos` de backend-node que solo emite Django: las visitas y consultas llegan del frontend.
TIPO_EVENTO_RESERVA_REALIZADA = 3
PRIORIDAD_AVISO_NORMAL = 1
PRIORIDAD_AVISO_URGENTE = 2

# Permisos que definen quién ve cada tipo de aviso: el operativo llega a quien opera la agenda o las excepciones, y el
# comercial o de titularidad, solo a quien administra el complejo.
PERMISO_AVISO_AGENDA = 'ver_agenda'
PERMISO_AVISO_EXCEPCIONES = 'ver_excepciones'
PERMISO_AVISO_CONFIGURACION = 'configurar_complejo'
PERMISO_AVISO_PRECIOS = 'administrar_precios'
PERMISO_AVISO_OPERADORES = 'ver_operadores'

# Alcance de una entrada del registro del complejo: el operador no ve lo comercial ni lo de titularidad.
AMBITO_REGISTRO_OPERATIVO = 1
AMBITO_REGISTRO_COMERCIAL = 2

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
        accion = AuditoriaService.depurar(accion)[:LARGO_ACCION_AUDITORIA]
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
        registro = AuditoriaService.registrar(
            TipoEventoAuditoria.LIMITE_PETICIONES,
            accion,
            detalle=detalle or 'Se superó el límite de solicitudes permitido.',
            usuario=usuario,
            ip_origen=ip_origen,
        )
        AuditoriaService._alertar_limite(accion)
        return registro

    @staticmethod
    def _alertar_limite(accion):
        """
        Un aviso de seguridad a los superadministradores por ruta y ventana, no por cada IP: un ataque distribuido no
        llena sus bandejas. El aviso nombra la ruta y no la IP ni el usuario; el detalle está en la auditoría.
        """
        ventana = settings.ALERTA_LIMITE_VENTANA_SEGUNDOS
        huella = hashlib.sha256(accion.encode()).hexdigest()[:16]
        if not cache.add(f'alerta:429:{huella}', 1, timeout=ventana):
            return
        try:
            AvisoComplejoService.a_superadmins(
                CATEGORIA_AVISO_SISTEMA, PRIORIDAD_AVISO_URGENTE,
                f'Alerta de seguridad: se bloquearon solicitudes por exceso de intentos en {accion}. '
                'Revisá la auditoría de seguridad.',
                clave_unica=f'limite-peticiones-{huella}-{int(time_module.time() // ventana)}',
            )
        except DatabaseError:
            # El rechazo 429 ya se auditó: una falla al avisar no puede convertirlo en un error del servidor.
            logger_seguridad.exception('No se pudo avisar a los superadministradores del límite de peticiones')

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

    @staticmethod
    def anonimizar_ips_vencidas():
        """
        Retención de la IP de origen: pasados `AUDITORIA_RETENCION_MESES` meses calendario se anonimiza. Una segunda
        corrida no encuentra nada que cambiar. Devuelve la cantidad de registros anonimizados.
        """
        corte = _sumar_meses(timezone.localdate(), -settings.AUDITORIA_RETENCION_MESES)
        limite = datetime.combine(corte, time.min, tzinfo=timezone.get_current_timezone())
        return AuditoriaRepository.anonimizar_ips_anteriores_a(limite)


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
    def impedimento_de_baja(usuario):
        """Motivo por el que hoy se rechazaría la baja propia, o None: la vista previa lo informa antes de confirmar."""
        try:
            with transaction.atomic():
                UsuarioService._validar_continuidad_superadmin(usuario)
                UsuarioService._validar_complejos_sin_responsable(usuario)
        except ValidationError as error:
            return str(error.detail[0])
        return None

    @staticmethod
    def _avisar_baja_propia(usuario, conteos):
        senadas = conteos['senadas']
        AvisoComplejoService.a_superadmins(
            CATEGORIA_AVISO_CUENTAS, PRIORIDAD_AVISO_URGENTE if senadas else PRIORIDAD_AVISO_NORMAL,
            f'El usuario id {usuario.pk} ({usuario.rol.nombre}) dio de baja su cuenta. '
            f'Reservas canceladas: {conteos["canceladas"]}. '
            + (f'Reservas señadas retenidas: {senadas}, a resolver con el complejo. ' if senadas else 'Sin reservas señadas retenidas. ')
            + f'Turnos fijos dados de baja: {conteos["turnos_fijos"]}.',
            {'usuario': usuario.pk}, actor=usuario,
        )

    @staticmethod
    def desactivar_cuenta_propia(usuario, ip_origen):
        """
        Atiende el derecho de supresión: resuelve las reservas y turnos fijos del titular, anonimiza sus datos
        personales, hace la baja lógica y cierra sus sesiones, todo en una única transacción.
        """
        with transaction.atomic():
            UsuarioService._validar_continuidad_superadmin(usuario)
            UsuarioService._validar_complejos_sin_responsable(usuario)
            # Antes de anonimizar: las reservas señadas necesitan una copia del nombre y el teléfono.
            canceladas, resumen, conteos = BajaDeCuentaService.resolver_ocupaciones(usuario)
            UsuarioRepository.anonimizar(usuario)
            usuario.desactivar()
            SesionRepository.revocar_refresh_de_usuario(usuario.pk)
            UsuarioService._avisar_baja_propia(usuario, conteos)
        for reserva, estado_anterior in canceladas:
            ReservaService._auditar(
                TipoEventoAuditoria.RESERVA_CANCELADA, 'Cancelación por baja de la cuenta del titular',
                reserva, usuario, ip_origen, f' Estado: {estado_anterior} -> {reserva.get_estado_display()}.',
            )
        AuditoriaService.registrar(
            TipoEventoAuditoria.BAJA_USUARIO, 'Baja lógica de la cuenta propia',
            detalle=f'Baja solicitada por el titular: datos personales anonimizados y sesiones revocadas. {resumen}',
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
        detalle = UsuarioAdminService._describir_cambios(usuario, campos, estado_anterior, rol_anterior, sesiones_revocadas)
        AuditoriaService.registrar(
            TipoEventoAuditoria.BAJA_USUARIO if es_baja else TipoEventoAuditoria.CAMBIO_USUARIO,
            'Baja administrativa de usuario' if es_baja else 'Cambio administrativo de usuario',
            detalle=detalle, usuario=actor, ip_origen=ip_origen,
        )
        if {'estado', 'rol'} & set(campos):
            AvisoComplejoService.a_superadmins(
                CATEGORIA_AVISO_CUENTAS,
                PRIORIDAD_AVISO_URGENTE if sesiones_revocadas else PRIORIDAD_AVISO_NORMAL,
                f'Cambio de cuenta hecho por el superadministrador id {actor.pk}. {detalle}',
                {'usuario': usuario.pk}, actor=actor,
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
        AvisoComplejoService.a_superadmins(
            CATEGORIA_AVISO_SISTEMA, PRIORIDAD_AVISO_NORMAL,
            f'Alta de contrato: «{complejo.nombre}» (complejo id {complejo.pk}) quedó en estado '
            f'{complejo.get_estado_contrato_display()}.',
            {'complejo': complejo.pk}, actor=actor,
        )
        AvisoComplejoService.al_dueno(
            complejo, PERMISO_AVISO_CONFIGURACION, CATEGORIA_AVISO_CUENTAS, PRIORIDAD_AVISO_NORMAL,
            f'se dio de alta el contrato de tu complejo. Estado: {complejo.get_estado_contrato_display()}.',
            {'complejo': complejo.pk}, actor=actor,
        )
        return complejo

    @staticmethod
    def _avisar_cambio_de_estado(complejo, estado_anterior, estado_nuevo, actor):
        # Suspender o dar de baja oculta el complejo del catálogo: es lo que más le importa a su titular.
        urgente = estado_nuevo in (EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA)
        prioridad = PRIORIDAD_AVISO_URGENTE if urgente else PRIORIDAD_AVISO_NORMAL
        cambio = f'{EstadoContrato(estado_anterior).label} -> {EstadoContrato(estado_nuevo).label}'
        AvisoComplejoService.a_superadmins(
            CATEGORIA_AVISO_SISTEMA, prioridad,
            f'Cambio de contrato de «{complejo.nombre}» (complejo id {complejo.pk}): {cambio}.',
            {'complejo': complejo.pk}, actor=actor,
        )
        AvisoComplejoService.al_dueno(
            complejo, PERMISO_AVISO_CONFIGURACION, CATEGORIA_AVISO_CUENTAS, prioridad,
            f'cambió el estado del contrato de tu complejo: {cambio}.', {'complejo': complejo.pk}, actor=actor,
        )

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
            if estado_nuevo == EstadoContrato.ACTIVO:
                DifusionGrillaService.programar_operatoria(complejo.pk)
            else:
                DifusionGrillaService.programar_cierre(complejo.pk)
            ContratoService._avisar_cambio_de_estado(complejo, estado_anterior, estado_nuevo, actor)

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

    @staticmethod
    def marcadores_publicos():
        return ComplejoRepository.marcadores_publicos()


class CatalogoMaestroService:
    """
    Administración de un catálogo maestro (deportes, servicios) por el superadministrador. La baja es lógica y se
    rechaza mientras el registro esté en uso, para no dejar canchas o complejos apuntando a algo que el catálogo
    público ya no muestra. Las subclases declaran el repositorio y cómo se describe el uso.
    """

    repositorio = None
    etiqueta = ''

    @classmethod
    def _describir_uso(cls, usos):
        raise NotImplementedError

    @classmethod
    def _al_renombrar(cls, registro):
        """Gancho para invalidar lo que guarda una copia del nombre. Corre dentro de la transacción."""

    @classmethod
    def listar(cls):
        return cls.repositorio.listar()

    @classmethod
    def listar_usos(cls, registro_id):
        """Dónde está en uso el registro (lo que impide su baja). 404 si no existe."""
        if cls.repositorio.obtener(registro_id) is None:
            raise NotFound()
        return cls.repositorio.detalle_de_usos(registro_id)

    @classmethod
    def _validar_nombre(cls, nombre, excluir_id=None):
        existente = cls.repositorio.con_nombre(nombre, excluir_id)
        if existente is None:
            return
        if existente.estado == EstadoRegistro.BAJA:
            mensaje = f'Ya existe un {cls.etiqueta} con ese nombre dado de baja. Reactivalo en lugar de crear otro.'
        else:
            mensaje = f'Ya existe un {cls.etiqueta} con ese nombre.'
        raise ValidationError({'nombre': mensaje})

    @classmethod
    def _auditar(cls, accion, registro, actor, ip_origen, extra=''):
        AuditoriaService.registrar(
            TipoEventoAuditoria.CAMBIO_CATALOGO, f'{accion} de {cls.etiqueta}',
            detalle=f'{cls.etiqueta.capitalize()} id {registro.pk}: «{registro.nombre}».{extra}',
            usuario=actor, ip_origen=ip_origen,
        )

    @classmethod
    def crear(cls, datos, actor, ip_origen):
        try:
            with transaction.atomic():
                cls._validar_nombre(datos['nombre'])
                registro = cls.repositorio.crear(datos['nombre'])
        except IntegrityError:
            # Alta simultánea con el mismo nombre: la unicidad de la tabla decide.
            raise ValidationError({'nombre': f'Ya existe un {cls.etiqueta} con ese nombre.'})
        cls._auditar('Alta', registro, actor, ip_origen)
        return cls.repositorio.obtener(registro.pk)

    @classmethod
    def actualizar(cls, registro_id, datos, actor, ip_origen):
        try:
            with transaction.atomic():
                registro = cls.repositorio.bloquear(registro_id)
                if registro is None:
                    raise NotFound()
                campos = _campos_modificados(registro, datos)
                if not campos:
                    return cls.repositorio.obtener(registro_id)
                nombre_anterior = registro.nombre
                if 'nombre' in campos:
                    cls._validar_nombre(campos['nombre'], excluir_id=registro.pk)
                cls.repositorio.actualizar(registro, **campos)
                if 'nombre' in campos:
                    cls._al_renombrar(registro)
        except IntegrityError:
            raise ValidationError({'nombre': f'Ya existe un {cls.etiqueta} con ese nombre.'})

        cambios = []
        if 'nombre' in campos:
            cambios.append(f' Antes: «{nombre_anterior}».')
        if 'estado' in campos:
            cambios.append(' Reactivado.')
        cls._auditar('Modificación', registro, actor, ip_origen, ''.join(cambios))
        return cls.repositorio.obtener(registro_id)

    @classmethod
    def dar_de_baja(cls, registro_id, actor, ip_origen):
        with transaction.atomic():
            registro = cls.repositorio.bloquear(registro_id)
            if registro is None:
                raise NotFound()
            if registro.estado == EstadoRegistro.BAJA:
                raise ValidationError(f'El {cls.etiqueta} ya está dado de baja.')
            usos = cls.repositorio.contar_usos(registro.pk)
            if usos:
                raise ValidationError(
                    f'No se puede dar de baja el {cls.etiqueta} «{registro.nombre}»: está en uso en '
                    f'{cls._describir_uso(usos)}. Quitalo de ahí antes de darlo de baja.'
                )
            registro.desactivar()
        cls._auditar('Baja', registro, actor, ip_origen)


class DeporteService(CatalogoMaestroService):
    repositorio = DeporteRepository
    etiqueta = 'deporte'

    @classmethod
    def _describir_uso(cls, usos):
        return f'{usos} cancha' if usos == 1 else f'{usos} canchas'

    @classmethod
    def _al_renombrar(cls, registro):
        # La grilla pública cacheada lleva el nombre del deporte: se invalida la de cada complejo que lo usa.
        for complejo_id in DeporteRepository.complejos_con_canchas(registro.pk):
            transaction.on_commit(lambda complejo_id=complejo_id: CacheGrillaService.invalidar(complejo_id))


class ServicioService(CatalogoMaestroService):
    repositorio = ServicioRepository
    etiqueta = 'servicio'

    @classmethod
    def _describir_uso(cls, usos):
        return f'{usos} complejo' if usos == 1 else f'{usos} complejos'


class RolAdminService:
    """
    Administración de roles por el superadministrador. Los roles base (`ROLES_BASE`) son de solo lectura: el acceso
    por complejo se decide por su nombre y `seed_inicial` reescribe sus permisos en cada despliegue, así que una
    edición se perdería o dejaría la matriz de permisos distinta de la documentada. Un rol personalizado solo recibe
    permisos fuera de `MODULOS_EXCLUSIVOS_DE_PLATAFORMA` y no se da de baja mientras lo usen cuentas vigentes.
    """

    @staticmethod
    def listar():
        return RolAdminRepository.listar()

    @staticmethod
    def permisos():
        return PermisoRepository.activos()

    @staticmethod
    def listar_usos(rol_id):
        """Cuentas vigentes con el rol (lo que impide su baja). 404 si no existe."""
        if RolAdminRepository.obtener(rol_id) is None:
            raise NotFound()
        return RolAdminRepository.detalle_de_usos(rol_id)

    @staticmethod
    def es_asignable(permiso):
        return permiso.modulo not in MODULOS_EXCLUSIVOS_DE_PLATAFORMA

    @staticmethod
    def _clave(nombre):
        """Forma comparable de un nombre: sin mayúsculas, espacios ni guiones bajos ("Encargado Turno" = "ENCARGADO_TURNO")."""
        return re.sub(r'[\s_]+', '', nombre).casefold()

    @staticmethod
    def _validar_nombre(nombre, excluir_id=None):
        clave = RolAdminService._clave(nombre)
        for rol_id, existente, estado in RolAdminRepository.nombres():
            if rol_id == excluir_id or RolAdminService._clave(existente) != clave:
                continue
            if estado == EstadoRegistro.BAJA:
                mensaje = 'Ya existe un rol con ese nombre dado de baja. Reactivalo en lugar de crear otro.'
            else:
                mensaje = 'Ya existe un rol con ese nombre.'
            raise ValidationError({'nombre': mensaje})

    @staticmethod
    def _exigir_rol_personalizado(rol, operacion):
        if rol.nombre in ROLES_BASE:
            raise ValidationError(
                f'«{rol.nombre}» es un rol base del sistema: no se puede {operacion}. '
                'Su nombre y sus permisos se definen en la carga inicial.'
            )

    @staticmethod
    def _resolver_permisos(permiso_ids):
        permisos = PermisoRepository.activos_por_ids(permiso_ids)
        inexistentes = sorted(set(permiso_ids) - {permiso.pk for permiso in permisos})
        if inexistentes:
            raise ValidationError({'permisos': f'No existen estos permisos: {", ".join(map(str, inexistentes))}.'})
        reservados = sorted(permiso.codigo for permiso in permisos if not RolAdminService.es_asignable(permiso))
        if reservados:
            raise ValidationError({
                'permisos': 'Un rol personalizado no puede tener permisos exclusivos de la plataforma: '
                            f'{", ".join(reservados)}.',
            })
        return permisos

    @staticmethod
    def _sincronizar_permisos(rol, permisos):
        """Deja asignados exactamente `permisos`: reactiva las bajas, desactiva las sobrantes y devuelve los cambios."""
        actuales = {asignacion.permiso_id: asignacion for asignacion in RolAdminRepository.asignaciones(rol.pk)}
        deseados = {permiso.pk: permiso for permiso in permisos}
        agregados, quitados = [], []
        for permiso_id, permiso in deseados.items():
            asignacion = actuales.get(permiso_id)
            if asignacion is None:
                RolAdminRepository.asignar(rol, permiso)
                agregados.append(permiso.codigo)
            elif asignacion.estado != EstadoRegistro.ACTIVO:
                RolAdminRepository.reactivar(asignacion)
                agregados.append(permiso.codigo)
        for permiso_id, asignacion in actuales.items():
            if permiso_id not in deseados and asignacion.estado == EstadoRegistro.ACTIVO:
                asignacion.desactivar()
                quitados.append(asignacion.permiso.codigo)
        return sorted(agregados), sorted(quitados)

    @staticmethod
    def _describir_permisos(agregados, quitados):
        partes = []
        if agregados:
            partes.append(f' Permisos agregados: {", ".join(agregados)}.')
        if quitados:
            partes.append(f' Permisos quitados: {", ".join(quitados)}.')
        return ''.join(partes)

    @staticmethod
    def _auditar(accion, rol, actor, ip_origen, extra=''):
        AuditoriaService.registrar(
            TipoEventoAuditoria.CAMBIO_CATALOGO, f'{accion} de rol',
            detalle=f'Rol id {rol.pk}: «{rol.nombre}».{extra}',
            usuario=actor, ip_origen=ip_origen,
        )

    @staticmethod
    def crear(datos, actor, ip_origen):
        try:
            with transaction.atomic():
                RolAdminService._validar_nombre(datos['nombre'])
                permisos = RolAdminService._resolver_permisos(datos.get('permisos', []))
                rol = RolAdminRepository.crear(datos['nombre'], datos.get('descripcion', ''))
                agregados, _ = RolAdminService._sincronizar_permisos(rol, permisos)
        except IntegrityError:
            # Alta simultánea con el mismo nombre: la unicidad de la tabla decide.
            raise ValidationError({'nombre': 'Ya existe un rol con ese nombre.'})
        RolAdminService._auditar('Alta', rol, actor, ip_origen, RolAdminService._describir_permisos(agregados, []))
        return RolAdminRepository.obtener(rol.pk)

    @staticmethod
    def actualizar(rol_id, datos, actor, ip_origen):
        try:
            with transaction.atomic():
                rol = RolAdminRepository.bloquear(rol_id)
                if rol is None:
                    raise NotFound()
                RolAdminService._exigir_rol_personalizado(rol, 'modificar')
                campos = _campos_modificados(rol, {c: datos[c] for c in ('nombre', 'descripcion', 'estado') if c in datos})
                nombre_anterior = rol.nombre
                if 'nombre' in campos:
                    RolAdminService._validar_nombre(campos['nombre'], excluir_id=rol.pk)
                permisos = RolAdminService._resolver_permisos(datos['permisos']) if 'permisos' in datos else None
                if campos:
                    RolAdminRepository.actualizar(rol, **campos)
                agregados, quitados = (
                    RolAdminService._sincronizar_permisos(rol, permisos) if permisos is not None else ([], [])
                )
        except IntegrityError:
            raise ValidationError({'nombre': 'Ya existe un rol con ese nombre.'})

        if not (campos or agregados or quitados):
            return RolAdminRepository.obtener(rol_id)
        cambios = []
        if 'nombre' in campos:
            cambios.append(f' Antes: «{nombre_anterior}».')
        if 'descripcion' in campos:
            cambios.append(' Descripción modificada.')
        if 'estado' in campos:
            cambios.append(' Reactivado.')
        cambios.append(RolAdminService._describir_permisos(agregados, quitados))
        RolAdminService._auditar('Modificación', rol, actor, ip_origen, ''.join(cambios))
        return RolAdminRepository.obtener(rol_id)

    @staticmethod
    def dar_de_baja(rol_id, actor, ip_origen):
        with transaction.atomic():
            rol = RolAdminRepository.bloquear(rol_id)
            if rol is None:
                raise NotFound()
            RolAdminService._exigir_rol_personalizado(rol, 'dar de baja')
            if rol.estado == EstadoRegistro.BAJA:
                raise ValidationError('El rol ya está dado de baja.')
            usos = RolAdminRepository.contar_usos(rol.pk)
            if usos:
                uso = 'lo usa 1 usuario' if usos == 1 else f'lo usan {usos} usuarios'
                raise ValidationError(
                    f'No se puede dar de baja el rol «{rol.nombre}»: {uso}. '
                    'Reasigná el rol de esas cuentas antes de darlo de baja.'
                )
            rol.desactivar()
        RolAdminService._auditar('Baja', rol, actor, ip_origen)


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
        AvisoComplejoService.al_dueno(
            complejo, PERMISO_AVISO_CONFIGURACION, CATEGORIA_AVISO_OPERATORIA, PRIORIDAD_AVISO_NORMAL,
            f'se modificó la configuración del complejo (campos: {", ".join(sorted(campos))}).',
            {'complejo': complejo.pk}, actor=actor,
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
        AvisoComplejoService.al_dueno(
            complejo, PERMISO_AVISO_OPERADORES, CATEGORIA_AVISO_CUENTAS, PRIORIDAD_AVISO_NORMAL,
            f'se vinculó al usuario id {usuario.pk} como operador del complejo.', {'operador': usuario.pk}, actor=actor,
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
        AvisoComplejoService.al_dueno(
            complejo, PERMISO_AVISO_OPERADORES, CATEGORIA_AVISO_CUENTAS, PRIORIDAD_AVISO_NORMAL,
            f'se desvinculó al usuario id {usuario.pk} como operador del complejo.', {'operador': usuario.pk},
            actor=actor,
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
                cancha = CanchaRepository.crear(**datos)
                DifusionGrillaService.programar_operatoria(cancha.complejo_id, cancha.pk)
                return cancha
        except IntegrityError:
            # Alta simultánea con el mismo nombre: la restricción uq_cancha_nombre_activa decide.
            raise ValidationError({'nombre': MENSAJE_NOMBRE_CANCHA_REPETIDO})

    @staticmethod
    def actualizar(cancha, datos, confirmar=False, actor=None, ip_origen=None):
        campos = _campos_modificados(cancha, datos)
        if not campos:
            return cancha
        if 'nombre' in campos:
            CanchaService._validar_nombre(cancha.complejo_id, campos['nombre'], excluir_id=cancha.pk)
        precio_anterior = cancha.precio_base
        try:
            with transaction.atomic():
                bloqueada = CanchaRepository.bloquear(cancha.pk)
                if {'duracion_turno_min', 'estado'} & set(campos):
                    ConflictoOperatoriaService.validar_cambio(
                        bloqueada, confirmar, actor, ip_origen,
                        duracion=campos.get('duracion_turno_min', bloqueada.duracion_turno_min),
                        estado=campos.get('estado', bloqueada.estado),
                        descripcion=f'edición de la cancha ({", ".join(sorted(campos))})',
                    )
                cancha = CanchaRepository.actualizar(cancha, **campos)
                DifusionGrillaService.programar_operatoria(cancha.complejo_id, cancha.pk)
                if 'precio_base' in campos:
                    AvisoComplejoService.al_dueno(
                        cancha.complejo, PERMISO_AVISO_PRECIOS, CATEGORIA_AVISO_OPERATORIA, PRIORIDAD_AVISO_NORMAL,
                        f'se modificó el precio base de la cancha «{cancha.nombre}»: de ${precio_anterior} a '
                        f'${cancha.precio_base}.',
                        {'cancha': cancha.pk}, actor=actor,
                    )
                return cancha
        except IntegrityError:
            raise ValidationError({'nombre': MENSAJE_NOMBRE_CANCHA_REPETIDO})

    @staticmethod
    def dar_de_baja(cancha):
        """Sin confirmación posible: una cancha con ocupación futura primero se libera desde la agenda."""
        with transaction.atomic():
            CanchaRepository.bloquear(cancha.pk)
            if CanchaRepository.tiene_ocupacion_futura(cancha.pk, timezone.localdate()):
                raise ValidationError(
                    'La cancha tiene reservas o turnos fijos vigentes desde hoy en adelante. '
                    'Cancelalos antes de darla de baja.'
                )
            cancha.desactivar()
            DifusionGrillaService.programar_operatoria(cancha.complejo_id, cancha.pk)


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
            cancha = CanchaRepository.bloquear(cancha_id)
            HorarioAperturaService._validar_rango_libre(cancha_id, dia_semana, apertura, cierre, excluir_id)
            resultado = operacion(cancha)
            DifusionGrillaService.programar_operatoria(cancha.complejo_id, cancha.pk)
            return resultado

    @staticmethod
    def _avisar_precio_diferenciado(horario, actor):
        cancha = horario.cancha
        AvisoComplejoService.al_dueno(
            cancha.complejo, PERMISO_AVISO_PRECIOS, CATEGORIA_AVISO_OPERATORIA, PRIORIDAD_AVISO_NORMAL,
            f'se modificó el precio diferenciado de «{cancha.nombre}» para el horario de '
            f'{horario.hora_apertura:%H:%M} a {horario.hora_cierre:%H:%M}.',
            {'cancha': cancha.pk, 'horario': horario.pk}, actor=actor,
        )

    @staticmethod
    def crear(datos, actor=None):
        # Un rango nuevo solo agrega turnos: no puede dejar reservas fuera de la grilla.
        horario = HorarioAperturaService._guardar(
            datos['cancha'].pk, datos['dia_semana'], datos['hora_apertura'], datos['hora_cierre'], None,
            lambda cancha: HorarioAperturaRepository.crear(**datos),
        )
        if datos.get('precio_diferenciado') is not None:
            HorarioAperturaService._avisar_precio_diferenciado(horario, actor)
        return horario

    @staticmethod
    def actualizar(horario, datos, confirmar=False, actor=None, ip_origen=None):
        campos = _campos_modificados(horario, datos)
        if not campos:
            return horario
        dia = campos.get('dia_semana', horario.dia_semana)
        apertura = campos.get('hora_apertura', horario.hora_apertura)
        cierre = campos.get('hora_cierre', horario.hora_cierre)

        def operar(cancha):
            if {'dia_semana', 'hora_apertura', 'hora_cierre'} & set(campos):
                horarios = [
                    rango for rango in HorarioAperturaRepository.activos_de_cancha(cancha.pk) if rango[0] != horario.pk
                ] + [(horario.pk, dia, apertura, cierre)]
                ConflictoOperatoriaService.validar_cambio(
                    cancha, confirmar, actor, ip_origen, horarios=horarios,
                    descripcion=f'edición del horario id {horario.pk}',
                )
            return HorarioAperturaRepository.actualizar(horario, **campos)

        horario = HorarioAperturaService._guardar(horario.cancha_id, dia, apertura, cierre, horario.pk, operar)
        if 'precio_diferenciado' in campos:
            HorarioAperturaService._avisar_precio_diferenciado(horario, actor)
        return horario

    @staticmethod
    def dar_de_baja(horario, confirmar=False, actor=None, ip_origen=None):
        with transaction.atomic():
            cancha = CanchaRepository.bloquear(horario.cancha_id)
            horarios = [rango for rango in HorarioAperturaRepository.activos_de_cancha(cancha.pk) if rango[0] != horario.pk]
            ConflictoOperatoriaService.validar_cambio(
                cancha, confirmar, actor, ip_origen, horarios=horarios, descripcion=f'baja del horario id {horario.pk}',
            )
            horario.desactivar()
            DifusionGrillaService.programar_operatoria(cancha.complejo_id, cancha.pk)


EVENTO_GRILLA_ACTUALIZADA = 'grilla_actualizada'
# Nombres de los handlers del consumer: Channels traduce el punto del tipo a guion bajo (grilla_actualizada).
TIPO_MENSAJE_GRILLA = 'grilla.actualizada'
TIPO_MENSAJE_CIERRE = 'complejo.no_disponible'

logger_difusion = logging.getLogger('core.difusion')


def grupo_de_complejo(complejo_id):
    return f'complejo_{int(complejo_id)}'


# Referencias a los envíos agendados desde código asíncrono: sin ellas el recolector podría cortarlos a mitad.
_ENVIOS_EN_CURSO = set()


def _cerrar_envio(tarea, complejo_id):
    _ENVIOS_EN_CURSO.discard(tarea)
    if not tarea.cancelled() and tarea.exception() is not None:
        logger_difusion.error(
            'No se pudo difundir la grilla del complejo %s', complejo_id, exc_info=tarea.exception(),
        )


class DifusionGrillaService:
    """
    Punto único de aviso a las grillas abiertas de un complejo. El evento se programa con
    transaction.on_commit, nunca dentro del bloque atómico: un rollback no puede anunciar un cambio que no
    ocurrió. Solo lleva ids, fechas y horarios, sin datos personales.
    """

    @staticmethod
    def admite_suscripcion(complejo_id):
        """Solo publican su grilla los complejos con estado = 1 y contrato activo, como el catálogo."""
        return ComplejoRepository.publico_por_id(complejo_id) is not None

    @staticmethod
    def programar(complejo_id, **cambio):
        evento = {'event': EVENTO_GRILLA_ACTUALIZADA, **cambio}
        transaction.on_commit(lambda: DifusionGrillaService._confirmado(complejo_id, evento))

    @staticmethod
    def _confirmado(complejo_id, evento):
        # Primero se invalida la caché: cuando los clientes reciban el evento y pidan la grilla, ya está fresca.
        CacheGrillaService.invalidar(complejo_id)
        DifusionGrillaService.publicar(complejo_id, evento)

    @staticmethod
    def programar_operatoria(complejo_id, cancha_id=None):
        """
        Cambió la operatoria de una cancha (horarios, duración, estado, precio) o de todo el complejo si
        cancha_id es nulo: rige desde hoy, sin fecha de fin y para el día completo.
        """
        DifusionGrillaService.programar(
            complejo_id, cancha_id=cancha_id, fecha_desde=timezone.localdate().isoformat(), fecha_hasta=None,
            hora_inicio=None, hora_fin=None,
        )

    @staticmethod
    def programar_cierre(complejo_id):
        """El complejo dejó de publicar su grilla: las conexiones abiertas se cierran después del commit."""
        def cerrar():
            CacheGrillaService.invalidar(complejo_id)
            DifusionGrillaService._enviar(complejo_id, {'type': TIPO_MENSAJE_CIERRE})

        transaction.on_commit(cerrar)

    @staticmethod
    def publicar(complejo_id, evento):
        DifusionGrillaService._enviar(complejo_id, {'type': TIPO_MENSAJE_GRILLA, 'evento': evento})

    @staticmethod
    def _enviar(complejo_id, mensaje):
        """
        Envía el mensaje al grupo complejo_<id>. Corre después del commit: si el channel layer falla (Redis caído,
        por ejemplo) se registra y se sigue, porque la operación ya quedó confirmada y las grillas abiertas se
        resincronizan por REST al reconectar.
        Sirve desde código sincrónico (vistas de DRF, que Daphne ejecuta en un hilo) y desde código asíncrono
        (consumers o vistas async): ahí no se puede bloquear el loop, así que el envío se agenda como tarea.
        """
        grupo = grupo_de_complejo(complejo_id)
        try:
            capa = get_channel_layer()
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                async_to_sync(capa.group_send)(grupo, mensaje)
                return
            tarea = loop.create_task(capa.group_send(grupo, mensaje))
            _ENVIOS_EN_CURSO.add(tarea)
            tarea.add_done_callback(lambda terminada: _cerrar_envio(terminada, complejo_id))
        except Exception:
            logger_difusion.exception('No se pudo difundir la grilla del complejo %s', complejo_id)


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
        if (datos['fecha_fin'] - datos['fecha_inicio']).days >= settings.RANGO_MAXIMO_DIAS:
            raise ValidationError({
                'fecha_fin': f'Una excepción abarca como máximo {settings.RANGO_MAXIMO_DIAS} días.',
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
    def _alcance(excepcion):
        if excepcion.cancha_id:
            return f'la cancha «{excepcion.cancha.nombre}»'
        return 'todo el complejo'

    @staticmethod
    def _periodo(excepcion):
        if excepcion.fecha_inicio == excepcion.fecha_fin:
            return f'el {excepcion.fecha_inicio:%d/%m/%Y}'
        return f'del {excepcion.fecha_inicio:%d/%m/%Y} al {excepcion.fecha_fin:%d/%m/%Y}'

    @staticmethod
    def _avisar_alta(excepcion, actor):
        """
        Al personal, que hay una excepción nueva (urgente si deja reservas sin cancha) y, a cada jugador con una
        reserva futura dentro del cierre, que su turno quedó afectado. El texto libre de la excepción no se replica.
        """
        hoy = timezone.localdate()
        afectadas = [
            reserva for reserva in ReservaRepository.afectadas_por_excepcion(excepcion, hoy)
            if not _ya_comenzo(reserva['fecha_turno'], reserva['hora_inicio'])
        ]
        complejo = excepcion.complejo
        motivo = TipoMotivoExcepcion(excepcion.tipo_motivo).label
        descripcion = (
            f'{ExcepcionHorariaService._alcance(excepcion)} {ExcepcionHorariaService._periodo(excepcion)} '
            f'(«{motivo}»)'
        )
        ids = [reserva['id'] for reserva in afectadas]
        AvisoComplejoService.al_personal(
            complejo, PERMISO_AVISO_EXCEPCIONES, CATEGORIA_AVISO_OPERATORIA,
            PRIORIDAD_AVISO_URGENTE if ids else PRIORIDAD_AVISO_NORMAL,
            f'se registró la excepción id {excepcion.pk}: cierre de {descripcion}.'
            + (f' Afecta {_plural(len(ids), "reserva", "reservas")} (ids {_lista_de_ids(ids)}).' if ids else ''),
            {'excepcion': excepcion.pk, 'reservas': ids, **({'cancha': excepcion.cancha_id} if excepcion.cancha_id else {})},
            actor=actor,
        )
        _avisar_titulares_afectados(
            afectadas,
            lambda propias: (
                f'{complejo.nombre} cerrará {descripcion} y {_frase_de_reservas(propias)} queda afectada. '
                'El complejo se comunicará para reprogramarla o cancelarla.'
            ),
            lambda propias: {'excepcion': excepcion.pk, 'reservas': propias},
        )

    @staticmethod
    def crear(datos, actor, ip_origen):
        ExcepcionHorariaService._validar_alta(datos)
        with transaction.atomic():
            excepcion = ExcepcionHorariaRepository.crear(creado_por=actor, **datos)
            ExcepcionHorariaService._difundir(excepcion)
            TurnoFijoService.avisar_fechas_en_espera(excepcion)
            ExcepcionHorariaService._avisar_alta(excepcion, actor)

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
            AvisoComplejoService.al_personal(
                excepcion.complejo, PERMISO_AVISO_EXCEPCIONES, CATEGORIA_AVISO_OPERATORIA, PRIORIDAD_AVISO_NORMAL,
                f'se dio de baja la excepción id {excepcion.pk}: el cierre de {ExcepcionHorariaService._alcance(excepcion)} '
                f'{ExcepcionHorariaService._periodo(excepcion)} dejó de regir.',
                {'excepcion': excepcion.pk}, actor=actor,
            )

        AuditoriaService.registrar(
            TipoEventoAuditoria.BAJA_EXCEPCION, 'Baja de excepción horaria',
            detalle=ExcepcionHorariaService._describir(excepcion),
            usuario=actor, complejo=excepcion.complejo_id, ip_origen=ip_origen,
        )


BLOQUE_LIBRE = 'LIBRE'
BLOQUE_OCUPADO = 'OCUPADO'
BLOQUE_CERRADO_EXCEPCION = 'CERRADO_EXCEPCION'
BLOQUE_NO_DISPONIBLE = 'NO_DISPONIBLE'

# Fecha arbitraria para operar con horas: ningún rango cruza la medianoche (ck_horario_apertura_cierre).
_FECHA_DE_REFERENCIA = date(2000, 1, 1)


def _se_superponen(inicio_a, fin_a, inicio_b, fin_b):
    """Intervalos semiabiertos [inicio, fin): los contiguos (14 a 15 y 15 a 16) no se superponen."""
    return inicio_a < fin_b and fin_a > inicio_b


def _excepcion_cubre(excepcion, inicio, fin):
    return excepcion['es_dia_completo'] == AlcanceExcepcion.DIA_COMPLETO or _se_superponen(
        inicio, fin, excepcion['hora_inicio'], excepcion['hora_fin'],
    )


def _inicio_del_turno(fecha, hora):
    return timezone.make_aware(datetime.combine(fecha, hora))


def _ya_comenzo(fecha, hora):
    return _inicio_del_turno(fecha, hora) <= timezone.now()


def _primera_fecha_del_dia(desde, hasta, dia_semana):
    """Primera fecha de [desde, hasta] que cae en ese día de la semana, o None; hasta nulo es sin fin."""
    fecha = desde + timedelta(days=(dia_semana - desde.weekday()) % 7)
    return fecha if hasta is None or fecha <= hasta else None


def _sumar_meses(fecha, meses):
    """Mismo día del mes destino o, si no existe (31 de enero más un mes), el último día de ese mes."""
    total = fecha.month - 1 + meses
    anio, mes = fecha.year + total // 12, total % 12 + 1
    return fecha.replace(year=anio, month=mes, day=min(fecha.day, calendar.monthrange(anio, mes)[1]))


def fecha_maxima_de_reserva():
    """Último día que se puede reservar: hoy más el máximo de anticipación, en meses calendario."""
    return _sumar_meses(timezone.localdate(), settings.RESERVA_MESES_ANTICIPACION)


def _menor_fecha(a, b):
    """La menor de dos fechas de fin, donde None significa sin fin."""
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


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
            if _excepcion_cubre(excepcion, inicio, fin):
                return BLOQUE_CERRADO_EXCEPCION, TipoMotivoExcepcion(excepcion['tipo_motivo']).label
        return BLOQUE_LIBRE, None

    @staticmethod
    def _calcular_desde_la_base(complejo_id, fecha):
        """
        Parte cacheable de la grilla: canchas, bloques, precios y estados según reservas, turnos fijos y
        excepciones. Seis consultas fijas, sin importar canchas ni reservas. None si el complejo no es público.
        """
        complejo = ComplejoRepository.publico_por_id(complejo_id)
        if complejo is None:
            return None

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
                'deporte': {'id': cancha.deporte_id, 'nombre': cancha.deporte.nombre},
                'duracion_turno_min': cancha.duracion_turno_min,
                'bloques': bloques,
            })

        return {
            'complejo': {'id': complejo.pk, 'nombre': complejo.nombre},
            'fecha': fecha,
            'dia_semana': dia_semana,
            'canchas': resultado,
        }

    @staticmethod
    def calcular(complejo_id, fecha):
        """
        Grilla pública de un día: los bloques de cada rango horario activo de las canchas activas, con su
        precio y su estado. La parte que sale de la base se cachea (CacheGrillaService) y las marcas que dependen
        del reloj se aplican en cada pedido: un bloque libre que el motor de reservas rechazaría (hoy, ya
        iniciado; o más allá de la anticipación máxima) se informa NO_DISPONIBLE.
        """
        hoy = timezone.localdate()
        if fecha < hoy:
            raise ValidationError({'fecha': 'La grilla se consulta desde hoy en adelante.'})
        grilla = CacheGrillaService.obtener(
            complejo_id, fecha, lambda: GrillaService._calcular_desde_la_base(complejo_id, fecha),
        )
        if grilla is None:
            raise NotFound()

        hora_actual = timezone.localtime().time() if fecha == hoy else None
        fuera_de_anticipacion = fecha > fecha_maxima_de_reserva()
        if hora_actual is not None or fuera_de_anticipacion:
            for cancha in grilla['canchas']:
                for bloque in cancha['bloques']:
                    ya_iniciado = hora_actual is not None and bloque['hora_inicio'] <= hora_actual
                    if bloque['estado'] == BLOQUE_LIBRE and (ya_iniciado or fuera_de_anticipacion):
                        bloque['estado'] = BLOQUE_NO_DISPONIBLE
        return grilla


class CacheGrillaService:
    """
    Caché de la grilla pública por complejo y fecha. Cada evento grilla_actualizada hace que todas las grillas
    abiertas del complejo vuelvan a pedirla: sin caché, N clientes son N cálculos por evento.
    La clave lleva una versión por complejo que DifusionGrillaService incrementa después de cada commit, así un
    cambio confirmado nunca se sirve viejo. La versión se lee antes de calcular: un cálculo concurrente queda
    guardado bajo la versión anterior y no se vuelve a servir. El TTL corto cubre los cambios que no pasan por la
    difusión (por ejemplo, el admin de Django). Si la caché falla, la grilla se calcula directo de la base.
    """

    @staticmethod
    def _clave_version(complejo_id):
        return f'grilla_version:{int(complejo_id)}'

    @staticmethod
    def obtener(complejo_id, fecha, calcular):
        try:
            cache.add(CacheGrillaService._clave_version(complejo_id), 1, timeout=None)
            version = cache.get(CacheGrillaService._clave_version(complejo_id), 1)
            clave = f'grilla:{int(complejo_id)}:{fecha.isoformat()}:v{version}'
            guardada = cache.get(clave)
        except Exception:
            logger_difusion.exception('Caché de la grilla no disponible; se calcula sin caché')
            return calcular()
        if guardada is not None:
            return guardada['grilla']
        grilla = calcular()
        try:
            # Se envuelve para poder cachear también "complejo no público" (None) sin confundirlo con un fallo.
            cache.set(clave, {'grilla': grilla}, settings.GRILLA_CACHE_SEGUNDOS)
        except Exception:
            logger_difusion.exception('No se pudo guardar la grilla en caché')
        return grilla

    @staticmethod
    def invalidar(complejo_id):
        clave = CacheGrillaService._clave_version(complejo_id)
        try:
            cache.add(clave, 1, timeout=None)
            cache.incr(clave)
        except Exception:
            logger_difusion.exception('No se pudo invalidar la grilla del complejo %s', complejo_id)


class DisponibilidadService:
    """
    Reglas que comparten la grilla, las reservas y los turnos fijos: un turno se toma solo si coincide con un
    bloque de la grilla y en esa fecha no lo ocupa una reserva ni un turno fijo, ni lo cierra una excepción.
    """

    @staticmethod
    def validar_cancha_reservable(cancha):
        complejo = cancha.complejo
        if complejo.estado != EstadoRegistro.ACTIVO or complejo.estado_contrato != EstadoContrato.ACTIVO:
            raise ValidationError({'cancha': 'El complejo no está habilitado para tomar reservas.'})
        if cancha.estado != EstadoCancha.ACTIVA or cancha.deporte.estado != EstadoRegistro.ACTIVO:
            raise ValidationError({'cancha': 'La cancha no está disponible para reservas.'})

    @staticmethod
    def bloque(cancha, dia_semana, hora_inicio):
        """Fin y precio del bloque de la grilla que empieza a esa hora, o None si ningún rango activo lo genera."""
        for horario in GrillaRepository.horarios_del_dia([cancha.pk], dia_semana):
            bloques = GrillaService.generar_bloques(
                horario['hora_apertura'], horario['hora_cierre'], cancha.duracion_turno_min,
            )
            for inicio, fin in bloques:
                if inicio == hora_inicio:
                    precio = horario['precio_diferenciado']
                    return fin, cancha.precio_base if precio is None else precio
        return None

    @staticmethod
    def precio_vigente(cancha, dia_semana, inicio, fin):
        """Precio del rango que contiene al turno; sin rango que lo contenga rige el precio_base."""
        for horario in GrillaRepository.horarios_del_dia([cancha.pk], dia_semana):
            if horario['hora_apertura'] <= inicio and fin <= horario['hora_cierre']:
                if horario['precio_diferenciado'] is not None:
                    return horario['precio_diferenciado']
                break
        return cancha.precio_base

    @staticmethod
    def validar_fecha_libre(cancha, fecha, inicio, fin):
        """Misma convención que la grilla: un turno fijo deja de ocupar la fecha que ya tiene su reserva generada."""
        reservas = GrillaRepository.reservas_de_fecha([cancha.pk], fecha)
        for reserva in reservas:
            ocupa = reserva['estado'] in ESTADOS_RESERVA_OCUPANTES
            if ocupa and _se_superponen(inicio, fin, reserva['hora_inicio'], reserva['hora_fin']):
                raise ConflictoNegocio('El turno ya está reservado.')

        con_fecha_generada = {reserva['turno_fijo_id'] for reserva in reservas if reserva['turno_fijo_id']}
        for turno in GrillaRepository.turnos_fijos_vigentes([cancha.pk], fecha.weekday(), fecha):
            if turno['id'] not in con_fecha_generada and _se_superponen(
                inicio, fin, turno['hora_inicio'], turno['hora_fin'],
            ):
                raise ConflictoNegocio('El horario está tomado por un turno fijo.')

        for excepcion in ExcepcionHorariaRepository.activas_en_fecha(cancha.complejo_id, fecha):
            if excepcion['cancha_id'] in (None, cancha.pk) and _excepcion_cubre(excepcion, inicio, fin):
                motivo = TipoMotivoExcepcion(excepcion['tipo_motivo']).label
                raise ConflictoNegocio(f'La cancha está cerrada en ese horario por una excepción ({motivo}).')


ESTADOS_RESERVA_CANCELABLES = (EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA)

# Ausente y Completada se pueden corregir entre sí; las canceladas no vuelven atrás.
TRANSICIONES_AGENDA = {
    EstadoReserva.PENDIENTE: {
        EstadoReserva.CONFIRMADA, EstadoReserva.SENADA, EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA,
    },
    EstadoReserva.CONFIRMADA: {EstadoReserva.SENADA, EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA},
    EstadoReserva.SENADA: {EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA},
    EstadoReserva.AUSENTE: {EstadoReserva.COMPLETADA},
    EstadoReserva.COMPLETADA: {EstadoReserva.AUSENTE},
}
ESTADOS_QUE_REQUIEREN_TURNO_INICIADO = (EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA)

MENSAJE_TURNO_YA_RESERVADO = 'El turno ya está reservado.'
ESTADOS_RESERVA_CANCELADAS = (EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO)
ACCION_MANTENER_FECHA = 'mantener'
ACCION_CANCELAR_FECHA = 'cancelar'


def _horas(cantidad):
    return f'{cantidad} hora' if cantidad == 1 else f'{cantidad} horas'


class ReservaService:
    @staticmethod
    def propias(usuario):
        return ReservaRepository.de_usuario(usuario.pk)

    @staticmethod
    def agenda():
        return ReservaRepository.agenda()

    @staticmethod
    def limite_de_cancelacion(reserva):
        """Momento hasta el que el jugador puede cancelar: el inicio del turno menos el margen del complejo."""
        horas = reserva.cancha.complejo.horas_limite_cancelacion
        return _inicio_del_turno(reserva.fecha_turno, reserva.hora_inicio) - timedelta(hours=horas)

    @staticmethod
    def _describir(reserva):
        # Solo ids, fechas y horarios: ni nombres ni teléfonos de clientes, ni las observaciones del personal.
        return (
            f'Reserva id {reserva.pk}. Cancha id {reserva.cancha_id}. '
            f'Turno: {reserva.fecha_turno.isoformat()} de {reserva.hora_inicio:%H:%M} a {reserva.hora_fin:%H:%M}. '
            f'Origen: {TipoOcupacion(reserva.tipo_ocupacion).label}.'
        )

    @staticmethod
    def _difundir(reserva):
        fecha = reserva.fecha_turno.isoformat()
        DifusionGrillaService.programar(
            reserva.cancha.complejo_id,
            cancha_id=reserva.cancha_id,
            fecha_desde=fecha,
            fecha_hasta=fecha,
            hora_inicio=_hora_iso(reserva.hora_inicio),
            hora_fin=_hora_iso(reserva.hora_fin),
        )

    @staticmethod
    def _turno(reserva):
        return (
            f'{reserva.cancha.nombre}, el {reserva.fecha_turno:%d/%m/%Y} '
            f'de {reserva.hora_inicio:%H:%M} a {reserva.hora_fin:%H:%M}'
        )

    @staticmethod
    def _al_titular(reserva, mensaje, prioridad=PRIORIDAD_AVISO_NORMAL):
        """Aviso a la bandeja del titular. Una reserva manual no tiene cuenta y una cuenta dada de baja ya no tiene bandeja."""
        AvisoComplejoService.al_usuario(
            reserva.usuario, CATEGORIA_AVISO_RESERVAS, prioridad, mensaje, {'reserva': reserva.pk},
        )

    @staticmethod
    def _al_personal(reserva, mensaje, prioridad=PRIORIDAD_AVISO_NORMAL, *, actor=None, evento=None):
        """Aviso operativo al dueño y a los operadores del complejo, menos a quien hizo el cambio."""
        referencias = {'reserva': reserva.pk, 'cancha': reserva.cancha_id}
        if reserva.usuario_id is not None:
            referencias['titular'] = reserva.usuario_id
        if reserva.turno_fijo_id is not None:
            referencias['turno_fijo'] = reserva.turno_fijo_id
        AvisoComplejoService.al_personal(
            reserva.cancha.complejo, PERMISO_AVISO_AGENDA, CATEGORIA_AVISO_RESERVAS, prioridad, mensaje,
            referencias, actor=actor, evento=evento,
        )

    @staticmethod
    def _complejo(reserva):
        return reserva.cancha.complejo.nombre

    @staticmethod
    def _avisar_reserva_realizada(reserva):
        """
        Una reserva web registra el evento "reserva realizada" en backend-node y avisa al personal del complejo. El
        mensaje identifica el turno, no al jugador: su id viaja solo en el evento, que el panel no expone. El jugador
        recibe en su bandeja la constancia de que quedó registrada.
        """
        ReservaService._al_personal(
            reserva, f'nueva reserva web id {reserva.pk}: {ReservaService._turno(reserva)}. Pendiente de seña.',
            evento={
                'tipo_evento': TIPO_EVENTO_RESERVA_REALIZADA,
                'usuario_id': reserva.usuario_id,
                'metadata': {
                    'reserva_id': reserva.pk, 'cancha_id': reserva.cancha_id,
                    'fecha_turno': reserva.fecha_turno.isoformat(), 'hora_inicio': f'{reserva.hora_inicio:%H:%M}',
                },
            },
        )
        ReservaService._al_titular(
            reserva,
            f'Tu reserva id {reserva.pk} en {ReservaService._complejo(reserva)} quedó registrada: '
            f'{ReservaService._turno(reserva)}. Está pendiente de seña.',
        )

    @staticmethod
    def _avisar_reserva_manual(reserva, actor):
        ReservaService._al_personal(
            reserva, f'se cargó la reserva manual id {reserva.pk}: {ReservaService._turno(reserva)}.', actor=actor,
        )

    @staticmethod
    def _avisar_reserva_confirmada(reserva):
        ReservaService._al_titular(
            reserva, f'{ReservaService._complejo(reserva)} confirmó tu reserva id {reserva.pk} '
                     f'({ReservaService._turno(reserva)}).',
        )

    @staticmethod
    def _avisar_reserva_senada(reserva):
        ReservaService._al_titular(
            reserva, f'{ReservaService._complejo(reserva)} registró la seña de tu reserva id {reserva.pk} '
                     f'({ReservaService._turno(reserva)}). Tu turno quedó señado.',
        )

    @staticmethod
    def _avisar_reserva_pagada(reserva):
        """
        Aviso propio de la reserva pagada. Hoy el estado «Señada/Pagada» es uno solo y se avisa como señada; cuando se
        separe en dos estados, alcanza con registrar este método en `_avisar_estado_al_titular`.
        """
        ReservaService._al_titular(
            reserva, f'{ReservaService._complejo(reserva)} registró el pago de tu reserva id {reserva.pk} '
                     f'({ReservaService._turno(reserva)}). Tu turno quedó pagado.',
        )

    @staticmethod
    def _avisar_reserva_completada(reserva):
        ReservaService._al_titular(
            reserva, f'Tu reserva id {reserva.pk} en {ReservaService._complejo(reserva)} '
                     f'({ReservaService._turno(reserva)}) figura como completada. Gracias por jugar.',
        )

    @staticmethod
    def _avisar_reserva_ausente(reserva):
        ReservaService._al_titular(
            reserva, f'Tu reserva id {reserva.pk} en {ReservaService._complejo(reserva)} '
                     f'({ReservaService._turno(reserva)}) figura como ausente. Si es un error, comunicate con el complejo.',
        )

    @staticmethod
    def _avisar_estado_al_titular(reserva):
        avisar = {
            EstadoReserva.CONFIRMADA: ReservaService._avisar_reserva_confirmada,
            EstadoReserva.SENADA: ReservaService._avisar_reserva_senada,
            EstadoReserva.COMPLETADA: ReservaService._avisar_reserva_completada,
            EstadoReserva.AUSENTE: ReservaService._avisar_reserva_ausente,
        }.get(reserva.estado)
        if avisar is not None:
            avisar(reserva)

    @staticmethod
    def _avisar_cambio_de_estado(reserva, estado_anterior, actor):
        ReservaService._al_personal(
            reserva,
            f'la reserva id {reserva.pk} ({ReservaService._turno(reserva)}) pasó de «{EstadoReserva(estado_anterior).label}» '
            f'a «{reserva.get_estado_display()}».',
            actor=actor,
        )
        ReservaService._avisar_estado_al_titular(reserva)

    @staticmethod
    def _avisar_cancelacion_por_jugador(reserva, estado_anterior, actor):
        """Constancia al propio jugador y aviso al personal; urgente si había una seña que resolver."""
        ReservaService._al_titular(
            reserva,
            f'Procesamos la cancelación de tu reserva id {reserva.pk} en {ReservaService._complejo(reserva)} '
            f'({ReservaService._turno(reserva)}). El turno quedó libre.',
        )
        senada = estado_anterior == EstadoReserva.SENADA
        ReservaService._al_personal(
            reserva,
            f'el titular canceló la reserva id {reserva.pk} ({ReservaService._turno(reserva)})'
            + (': tenía una seña, resolvela con el jugador.' if senada else '.'),
            PRIORIDAD_AVISO_URGENTE if senada else PRIORIDAD_AVISO_NORMAL,
            actor=actor,
        )

    @staticmethod
    def _avisar_cancelacion_por_complejo(reserva, actor):
        """
        El titular de una reserva cancelada por el complejo recibe un aviso urgente en su bandeja propia, y el resto
        del personal se entera de la cancelación.
        """
        ReservaService._al_titular(
            reserva,
            f'{ReservaService._complejo(reserva)} canceló tu reserva id {reserva.pk} ({ReservaService._turno(reserva)}). '
            'Si habías pagado una seña, comunicate con el complejo.',
            PRIORIDAD_AVISO_URGENTE,
        )
        ReservaService._al_personal(
            reserva, f'se canceló la reserva id {reserva.pk} ({ReservaService._turno(reserva)}).', actor=actor,
        )

    @staticmethod
    def _avisar_reapertura(reserva, estado_anterior, actor):
        ReservaService._al_titular(
            reserva,
            f'{ReservaService._complejo(reserva)} reabrió tu reserva id {reserva.pk} ({ReservaService._turno(reserva)}). '
            f'Quedó en estado «{reserva.get_estado_display()}».',
        )
        ReservaService._al_personal(
            reserva,
            f'se reabrió la reserva id {reserva.pk} ({ReservaService._turno(reserva)}): de «{estado_anterior}» a '
            f'«{reserva.get_estado_display()}».',
            actor=actor,
        )

    @staticmethod
    def _avisar_fecha_de_turno_fijo(reserva, turno, cancelada, actor):
        if cancelada:
            ReservaService._avisar_cancelacion_por_complejo(reserva, actor)
            return
        ReservaService._al_titular(
            reserva,
            f'{ReservaService._complejo(reserva)} registró una fecha de tu turno fijo (reserva id {reserva.pk}): '
            f'{ReservaService._turno(reserva)}. Estado: {reserva.get_estado_display()}.',
        )
        ReservaService._al_personal(
            reserva,
            f'se llevó a la agenda la fecha del {reserva.fecha_turno:%d/%m/%Y} del turno fijo id {turno.pk} '
            f'(reserva id {reserva.pk}).',
            actor=actor,
        )

    @staticmethod
    def _guardar(operacion):
        try:
            with transaction.atomic():
                return operacion()
        except IntegrityError:
            # Última defensa: uq_reserva_cancha_turno_activa ante un alta simultánea del mismo turno.
            raise ConflictoNegocio(MENSAJE_TURNO_YA_RESERVADO)

    @staticmethod
    def _auditar(tipo_evento, accion, reserva, actor, ip_origen, extra=''):
        AuditoriaService.registrar(
            tipo_evento, accion,
            detalle=f'{ReservaService._describir(reserva)}{extra}',
            usuario=actor, complejo=reserva.cancha.complejo_id, ip_origen=ip_origen,
        )

    @staticmethod
    def crear_reserva(datos, actor, ip_origen, manual=False):
        """
        Motor anti-colisiones. Con la fila de la cancha bloqueada, las altas que compiten por ella se
        serializan: el turno debe ser un bloque válido de la grilla y estar libre en esa fecha. hora_fin y
        precio_acordado los fija el servidor a partir del horario.
        """
        fecha, hora_inicio = datos['fecha_turno'], datos['hora_inicio']
        if _ya_comenzo(fecha, hora_inicio):
            raise ValidationError({'hora_inicio': 'El turno ya comenzó o pasó: elegí un horario futuro.'})
        maxima = fecha_maxima_de_reserva()
        if fecha > maxima:
            raise ValidationError({
                'fecha_turno': f'Se reserva con hasta {settings.RESERVA_MESES_ANTICIPACION} meses de anticipación '
                               f'(hasta el {maxima:%d/%m/%Y}).',
            })

        if manual:
            cliente = {
                'usuario': None,
                'nombre_cliente_manual': datos['nombre_cliente_manual'],
                'telefono_cliente_manual': datos.get('telefono_cliente_manual', ''),
                'observaciones': datos.get('observaciones', ''),
                'tipo_ocupacion': TipoOcupacion.MANUAL,
            }
        else:
            cliente = {'usuario': actor, 'tipo_ocupacion': TipoOcupacion.WEB}

        with transaction.atomic():
            cancha = ReservaRepository.bloquear_cancha(datos['cancha'].pk)
            DisponibilidadService.validar_cancha_reservable(cancha)
            bloque = DisponibilidadService.bloque(cancha, fecha.weekday(), hora_inicio)
            if bloque is None:
                raise ValidationError({
                    'hora_inicio': 'El horario no corresponde a un turno de la cancha para esa fecha.',
                })
            hora_fin, precio = bloque
            DisponibilidadService.validar_fecha_libre(cancha, fecha, hora_inicio, hora_fin)
            reserva = ReservaService._guardar(lambda: ReservaRepository.crear(
                cancha=cancha, creado_por=actor, fecha_turno=fecha, hora_inicio=hora_inicio, hora_fin=hora_fin,
                precio_acordado=precio, estado=EstadoReserva.PENDIENTE, **cliente,
            ))
            ReservaService._difundir(reserva)
            if manual:
                ReservaService._avisar_reserva_manual(reserva, actor)
            else:
                ReservaService._avisar_reserva_realizada(reserva)

        ReservaService._auditar(TipoEventoAuditoria.RESERVA_CREADA, 'Alta de reserva', reserva, actor, ip_origen)
        return reserva

    @staticmethod
    def _validar_cancelable(reserva):
        if reserva.estado not in ESTADOS_RESERVA_CANCELABLES:
            raise ValidationError(f'Una reserva en estado «{reserva.get_estado_display()}» no se puede cancelar.')

    @staticmethod
    def _contacto_de_baja_a_liberar(reserva):
        """
        Una reserva señada de un titular que se dio de baja guarda una copia de su nombre y teléfono solo para
        resolver la seña (PROJECT.md §13.2): al resolverse (completada, ausente o cancelada) esa copia se borra.
        """
        usuario = reserva.usuario
        if usuario is None or usuario.estado != EstadoUsuario.BAJA:
            return {}
        if not reserva.nombre_cliente_manual and not reserva.telefono_cliente_manual:
            return {}
        return {'nombre_cliente_manual': '', 'telefono_cliente_manual': ''}

    @staticmethod
    def _cancelar(reserva, estado_nuevo):
        estado_anterior = reserva.get_estado_display()
        ReservaRepository.actualizar(
            reserva, estado=estado_nuevo, **ReservaService._contacto_de_baja_a_liberar(reserva),
        )
        ReservaService._difundir(reserva)
        return f' Estado: {estado_anterior} -> {reserva.get_estado_display()}.'

    @staticmethod
    def cancelar_por_jugador(reserva_id, jugador, ip_origen):
        with transaction.atomic():
            reserva = ReservaRepository.bloquear(reserva_id)
            if reserva is None or reserva.usuario_id != jugador.pk:
                raise NotFound()
            ReservaService._validar_cancelable(reserva)
            if _ya_comenzo(reserva.fecha_turno, reserva.hora_inicio):
                raise ValidationError('El turno ya comenzó: no se puede cancelar.')
            # Faltar exactamente el margen no alcanza: se exige que falten más horas que las fijadas por el complejo.
            if timezone.now() >= ReservaService.limite_de_cancelacion(reserva):
                horas = reserva.cancha.complejo.horas_limite_cancelacion
                raise ValidationError(
                    f'Solo podés cancelar con más de {_horas(horas)} de anticipación. Comunicate con el complejo.'
                )
            estado_anterior = reserva.estado
            cambio = ReservaService._cancelar(reserva, EstadoReserva.CANCELADA_JUGADOR)
            ReservaService._avisar_cancelacion_por_jugador(reserva, estado_anterior, jugador)

        ReservaService._auditar(
            TipoEventoAuditoria.RESERVA_CANCELADA, 'Cancelación de reserva por el jugador',
            reserva, jugador, ip_origen, cambio,
        )
        return reserva

    @staticmethod
    def cancelar_por_complejo(reserva_id, actor, ip_origen):
        with transaction.atomic():
            reserva = ReservaRepository.bloquear(reserva_id)
            if reserva is None:
                raise NotFound()
            ReservaService._validar_cancelable(reserva)
            cambio = ReservaService._cancelar(reserva, EstadoReserva.CANCELADA_COMPLEJO)
            ReservaService._avisar_cancelacion_por_complejo(reserva, actor)

        ReservaService._auditar(
            TipoEventoAuditoria.RESERVA_CANCELADA, 'Cancelación de reserva por el complejo',
            reserva, actor, ip_origen, cambio,
        )
        return reserva

    @staticmethod
    def _validar_transicion(reserva, estado_nuevo):
        if estado_nuevo not in TRANSICIONES_AGENDA.get(reserva.estado, ()):
            raise ValidationError({
                'estado': f'No se puede pasar de «{reserva.get_estado_display()}» a '
                          f'«{EstadoReserva(estado_nuevo).label}».',
            })
        if estado_nuevo in ESTADOS_QUE_REQUIEREN_TURNO_INICIADO and not _ya_comenzo(
            reserva.fecha_turno, reserva.hora_inicio,
        ):
            raise ValidationError({'estado': 'Solo se marca ausente o completada una vez iniciado el turno.'})

    @staticmethod
    def actualizar_en_agenda(reserva_id, datos, actor, ip_origen):
        with transaction.atomic():
            reserva = ReservaRepository.bloquear(reserva_id)
            if reserva is None:
                raise NotFound()
            campos = _campos_modificados(reserva, datos)
            if not campos:
                return reserva
            estado_anterior = reserva.estado
            if 'estado' in campos:
                ReservaService._validar_transicion(reserva, campos['estado'])
                if campos['estado'] in (EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA):
                    campos.update(ReservaService._contacto_de_baja_a_liberar(reserva))
            ReservaService._guardar(lambda: ReservaRepository.actualizar(reserva, **campos))
            cambia_ocupacion = (estado_anterior in ESTADOS_RESERVA_OCUPANTES) != (
                reserva.estado in ESTADOS_RESERVA_OCUPANTES
            )
            if cambia_ocupacion:
                ReservaService._difundir(reserva)
            if 'estado' in campos:
                ReservaService._avisar_cambio_de_estado(reserva, estado_anterior, actor)

        # Las observaciones son texto libre del personal: su edición no se replica en la auditoría.
        if 'estado' in campos:
            ReservaService._auditar(
                TipoEventoAuditoria.RESERVA_CAMBIO_ESTADO, 'Cambio de estado de reserva', reserva, actor, ip_origen,
                f' Estado: {EstadoReserva(estado_anterior).label} -> {reserva.get_estado_display()}.',
            )
        return reserva

    @staticmethod
    def registrar_fecha_de_turno_fijo(turno_fijo, fecha, actor, ip_origen, accion=ACCION_MANTENER_FECHA):
        """
        Lleva a la agenda una fecha puntual de un turno fijo para operarla (señarla, completarla o cancelarla).
        Desde ese momento manda el estado de la reserva generada: cancelarla libera el casillero, como en la grilla.
        `accion = cancelar` la registra ya cancelada por el complejo, en un solo paso: es la decisión típica ante
        una fecha en espera por una excepción (por ejemplo, un feriado).
        """
        with transaction.atomic():
            cancha, turno = TurnoFijoService.bloquear(turno_fijo)
            if turno.estado != EstadoTurnoFijo.VIGENTE:
                raise ValidationError('Solo se registran fechas de un turno fijo vigente.')
            fuera_de_vigencia = fecha < turno.fecha_inicio_vigencia or (
                turno.fecha_fin_vigencia is not None and fecha > turno.fecha_fin_vigencia
            )
            if fecha.weekday() != turno.dia_semana or fuera_de_vigencia:
                raise ValidationError({
                    'fecha_turno': 'La fecha no corresponde al día del turno fijo dentro de su vigencia.',
                })
            if ReservaRepository.existe_fecha_de_turno_fijo(turno.pk, fecha):
                raise ConflictoNegocio('Esa fecha del turno fijo ya figura en la agenda.')
            precio = DisponibilidadService.precio_vigente(cancha, turno.dia_semana, turno.hora_inicio, turno.hora_fin)
            cancelada = accion == ACCION_CANCELAR_FECHA
            reserva = ReservaService._guardar(lambda: ReservaRepository.crear(
                cancha=cancha, usuario_id=turno.usuario_id, turno_fijo=turno, creado_por=actor,
                nombre_cliente_manual=turno.nombre_cliente_manual,
                telefono_cliente_manual=turno.telefono_cliente_manual,
                fecha_turno=fecha, hora_inicio=turno.hora_inicio, hora_fin=turno.hora_fin, precio_acordado=precio,
                tipo_ocupacion=TipoOcupacion.TURNO_FIJO,
                estado=EstadoReserva.CANCELADA_COMPLEJO if cancelada else EstadoReserva.CONFIRMADA,
            ))
            ReservaService._difundir(reserva)
            ReservaService._avisar_fecha_de_turno_fijo(reserva, turno, cancelada, actor)

        if cancelada:
            ReservaService._auditar(
                TipoEventoAuditoria.RESERVA_CANCELADA, 'Fecha de turno fijo cancelada por el complejo', reserva, actor,
                ip_origen, f' Turno fijo id {turno.pk}.',
            )
        else:
            ReservaService._auditar(
                TipoEventoAuditoria.RESERVA_CREADA, 'Alta de fecha de turno fijo', reserva, actor, ip_origen,
                f' Turno fijo id {turno.pk}.',
            )
        return reserva

    @staticmethod
    def reabrir(reserva_cancelada, estado_nuevo, confirmar, actor, ip_origen):
        """
        Corrige una cancelación hecha por error. Antes de pedir la confirmación revalida el turno con la cancha
        bloqueada, igual que un alta: si mientras tanto lo tomó otra reserva o un turno fijo, lo cerró una
        excepción o ya no es un turno de la grilla, es un choque real (409) que no se puede forzar.
        """
        with transaction.atomic():
            cancha = ReservaRepository.bloquear_cancha(reserva_cancelada.cancha_id)
            reserva = ReservaRepository.bloquear(reserva_cancelada.pk)
            if reserva is None:
                raise NotFound()
            if reserva.estado not in ESTADOS_RESERVA_CANCELADAS:
                raise ValidationError({'estado': 'Solo se reabre una reserva cancelada.'})
            if reserva.usuario_id is not None and reserva.usuario.estado == EstadoUsuario.BAJA:
                raise ValidationError('La cuenta del titular se dio de baja: registrá una reserva manual nueva.')
            if _ya_comenzo(reserva.fecha_turno, reserva.hora_inicio):
                raise ValidationError('El turno ya comenzó: no se puede reabrir.')

            complejo = cancha.complejo
            publica = complejo.estado == EstadoRegistro.ACTIVO and complejo.estado_contrato == EstadoContrato.ACTIVO
            if not publica or cancha.estado != EstadoCancha.ACTIVA:
                raise ConflictoNegocio('La cancha o el complejo ya no están disponibles para reservas.')
            bloque = DisponibilidadService.bloque(cancha, reserva.fecha_turno.weekday(), reserva.hora_inicio)
            if bloque is None or bloque[0] != reserva.hora_fin:
                raise ConflictoNegocio('El turno ya no coincide con los horarios vigentes de la cancha.')
            DisponibilidadService.validar_fecha_libre(cancha, reserva.fecha_turno, reserva.hora_inicio, reserva.hora_fin)

            if not confirmar:
                raise ConflictoConConfirmacion(
                    f'La reserva pasa de «{reserva.get_estado_display()}» a «{EstadoReserva(estado_nuevo).label}» y '
                    'vuelve a ocupar su turno. Para aplicarlo, repetí la operación con "confirmar": true.',
                    vista_previa={
                        'id': reserva.pk, 'fecha_turno': reserva.fecha_turno.isoformat(),
                        'hora_inicio': _hora_iso(reserva.hora_inicio), 'hora_fin': _hora_iso(reserva.hora_fin),
                        'estado_actual': reserva.estado, 'estado_nuevo': estado_nuevo,
                    },
                )
            estado_anterior = reserva.get_estado_display()
            ReservaService._guardar(lambda: ReservaRepository.actualizar(reserva, estado=estado_nuevo))
            ReservaService._difundir(reserva)
            ReservaService._avisar_reapertura(reserva, estado_anterior, actor)

        ReservaService._auditar(
            TipoEventoAuditoria.RESERVA_CAMBIO_ESTADO, 'Reapertura de reserva cancelada', reserva, actor, ip_origen,
            f' Estado: {estado_anterior} -> {reserva.get_estado_display()}.',
        )
        return reserva


class TurnoFijoService:
    @staticmethod
    def listar():
        return TurnoFijoRepository.vigentes()

    @staticmethod
    def bloquear(turno_fijo):
        """Siempre la cancha antes que el turno fijo, el mismo orden que las altas: evita deadlocks."""
        cancha = ReservaRepository.bloquear_cancha(turno_fijo.cancha_id)
        turno = TurnoFijoRepository.bloquear(turno_fijo.pk)
        if turno is None:
            raise NotFound()
        return cancha, turno

    @staticmethod
    def validar_vigencia(fecha_inicio, fecha_fin, dia_semana):
        if fecha_fin is not None and fecha_fin < fecha_inicio:
            raise ValidationError({'fecha_fin_vigencia': 'Debe ser igual o posterior a fecha_inicio_vigencia.'})
        if _primera_fecha_del_dia(fecha_inicio, fecha_fin, dia_semana) is None:
            raise ValidationError({
                'fecha_fin_vigencia': f'La vigencia no incluye ningún {DiaSemana(dia_semana).label.lower()}.',
            })

    @staticmethod
    def _validar_periodo_libre(cancha, dia_semana, inicio, fin, desde, hasta, excluir_id=None):
        """
        El turno fijo no puede chocar, en ninguna fecha de ese día de la semana dentro de [desde, hasta], con otro
        turno fijo vigente ni con una reserva activa. Las fechas pasadas no se revisan. Una excepción no lo
        impide: las fechas que cubre quedan en espera de una decisión del complejo (`fechas_en_espera`).
        """
        desde = max(desde, timezone.localdate())
        if hasta is not None and hasta < desde:
            return

        for otro in TurnoFijoRepository.solapados(cancha.pk, dia_semana, inicio, fin, desde, hasta, excluir_id):
            comun_desde = max(desde, otro['fecha_inicio_vigencia'])
            comun_hasta = _menor_fecha(hasta, otro['fecha_fin_vigencia'])
            if _primera_fecha_del_dia(comun_desde, comun_hasta, dia_semana) is not None:
                raise ConflictoNegocio(
                    f'Se superpone con otro turno fijo vigente de la cancha ({DiaSemana(dia_semana).label} de '
                    f'{otro["hora_inicio"]:%H:%M} a {otro["hora_fin"]:%H:%M}).'
                )

        reserva = ReservaRepository.primera_ocupante_en_dia_de_semana(
            cancha.pk, dia_semana, inicio, fin, desde, hasta, excluir_turno_fijo_id=excluir_id,
        )
        if reserva is not None:
            raise ConflictoNegocio(
                f'Se superpone con una reserva activa del {reserva["fecha_turno"]:%d/%m/%Y} '
                f'a las {reserva["hora_inicio"]:%H:%M}.'
            )

    @staticmethod
    def fechas_en_espera(turnos, excepciones=None):
        """
        {turno_id: [{'fecha', 'motivo'}]}: fechas desde hoy de turnos fijos vigentes que cubre una excepción activa y
        que el complejo todavía no decidió (no tienen reserva generada). Siguen ocupando la grilla mientras esperan.
        Dos consultas para toda la página, sin importar cuántos turnos fijos haya; con `excepciones` dadas, una.
        """
        vigentes = [turno for turno in turnos if turno.estado == EstadoTurnoFijo.VIGENTE]
        if not vigentes:
            return {}
        hoy = timezone.localdate()
        if excepciones is None:
            excepciones = ExcepcionHorariaRepository.activas_desde({turno.cancha.complejo_id for turno in vigentes}, hoy)
        generadas = ReservaRepository.fechas_generadas([turno.pk for turno in vigentes], hoy)

        resultado = {}
        for turno in vigentes:
            fechas = {}
            for excepcion in excepciones:
                misma_cancha = excepcion['cancha_id'] in (None, turno.cancha_id)
                if excepcion['complejo_id'] != turno.cancha.complejo_id or not misma_cancha:
                    continue
                if not _excepcion_cubre(excepcion, turno.hora_inicio, turno.hora_fin):
                    continue
                hasta = _menor_fecha(excepcion['fecha_fin'], turno.fecha_fin_vigencia)
                fecha = _primera_fecha_del_dia(
                    max(hoy, excepcion['fecha_inicio'], turno.fecha_inicio_vigencia), hasta, turno.dia_semana,
                )
                while fecha is not None and fecha <= hasta:
                    if (turno.pk, fecha) not in generadas:
                        fechas.setdefault(fecha, TipoMotivoExcepcion(excepcion['tipo_motivo']).label)
                    fecha += timedelta(days=7)
            if fechas:
                resultado[turno.pk] = [
                    {'fecha': fecha.isoformat(), 'motivo': motivo} for fecha, motivo in sorted(fechas.items())
                ]
        return resultado

    @staticmethod
    def filtrar_en_espera(queryset, en_espera):
        """Solo los candidatos que deja el prefiltro en SQL pasan por el cálculo exacto en Python."""
        candidatos = TurnoFijoRepository.con_excepcion_que_los_alcanza(queryset, timezone.localdate())
        con_fechas = set(TurnoFijoService.fechas_en_espera(list(candidatos)))
        return queryset.filter(pk__in=con_fechas) if en_espera else queryset.exclude(pk__in=con_fechas)

    @staticmethod
    def avisar_fechas_en_espera(excepcion):
        """Una excepción nueva que deja fechas de turnos fijos sin decidir genera un aviso urgente al complejo."""
        # Solo esta excepción y solo los turnos que puede alcanzar: no se recalcula todo el complejo.
        propia = {
            'complejo_id': excepcion.complejo_id, 'cancha_id': excepcion.cancha_id,
            'fecha_inicio': excepcion.fecha_inicio, 'fecha_fin': excepcion.fecha_fin,
            'es_dia_completo': excepcion.es_dia_completo, 'hora_inicio': excepcion.hora_inicio,
            'hora_fin': excepcion.hora_fin, 'tipo_motivo': excepcion.tipo_motivo,
        }
        en_espera = TurnoFijoService.fechas_en_espera(TurnoFijoRepository.alcanzados_por(excepcion), [propia])
        afectados = sorted(en_espera)
        cantidad = sum(len(fechas) for fechas in en_espera.values())
        if afectados:
            # Pide una decisión: le llega también a quien cargó la excepción.
            AvisoComplejoService.al_personal(
                excepcion.complejo, PERMISO_AVISO_AGENDA, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_URGENTE,
                f'la excepción id {excepcion.pk} deja {_plural(cantidad, "fecha", "fechas")} de turnos fijos en espera '
                f'(turnos fijos {_lista_de_ids(afectados)}). Indicá desde la agenda si cada fecha se mantiene o se cancela.',
                {'excepcion': excepcion.pk, 'turnos_fijos': afectados},
            )

    @staticmethod
    def _difundir(turno, dia_completo=False):
        """Con `dia_completo` (cambio de horario) el aviso cubre el horario viejo y el nuevo a la vez."""
        DifusionGrillaService.programar(
            turno.cancha.complejo_id,
            cancha_id=turno.cancha_id,
            fecha_desde=turno.fecha_inicio_vigencia.isoformat(),
            fecha_hasta=turno.fecha_fin_vigencia.isoformat() if turno.fecha_fin_vigencia else None,
            hora_inicio=None if dia_completo else _hora_iso(turno.hora_inicio),
            hora_fin=None if dia_completo else _hora_iso(turno.hora_fin),
        )

    @staticmethod
    def _vista_previa_de_horario(turno, inicio_nuevo, fin_nuevo, fin_vigencia):
        hoy = timezone.localdate()
        rige_desde = _primera_fecha_del_dia(max(hoy, turno.fecha_inicio_vigencia), fin_vigencia, turno.dia_semana)
        return {
            'horario_actual': {'hora_inicio': _hora_iso(turno.hora_inicio), 'hora_fin': _hora_iso(turno.hora_fin)},
            'horario_nuevo': {'hora_inicio': _hora_iso(inicio_nuevo), 'hora_fin': _hora_iso(fin_nuevo)},
            'rige_desde': rige_desde.isoformat() if rige_desde else None,
            # Ya están en la agenda con el horario anterior: se resuelven desde ahí (mantener, reabrir o cancelar).
            'fechas_registradas': [
                {'id': reserva['id'], 'fecha_turno': reserva['fecha_turno'].isoformat(), 'estado': reserva['estado']}
                for reserva in ReservaRepository.fechas_a_resolver_de_turno_fijo(turno.pk, hoy)
            ],
        }

    @staticmethod
    def crear(datos, actor):
        if datos['fecha_inicio_vigencia'] < timezone.localdate():
            raise ValidationError({'fecha_inicio_vigencia': 'No puede ser anterior a hoy.'})
        TurnoFijoService.validar_vigencia(
            datos['fecha_inicio_vigencia'], datos.get('fecha_fin_vigencia'), datos['dia_semana'],
        )
        with transaction.atomic():
            cancha = ReservaRepository.bloquear_cancha(datos['cancha'].pk)
            DisponibilidadService.validar_cancha_reservable(cancha)
            bloque = DisponibilidadService.bloque(cancha, datos['dia_semana'], datos['hora_inicio'])
            if bloque is None:
                raise ValidationError({
                    'hora_inicio': 'El horario no corresponde a un turno de la cancha para ese día de la semana.',
                })
            hora_fin, _ = bloque
            TurnoFijoService._validar_periodo_libre(
                cancha, datos['dia_semana'], datos['hora_inicio'], hora_fin,
                datos['fecha_inicio_vigencia'], datos.get('fecha_fin_vigencia'),
            )
            turno = TurnoFijoRepository.crear(**{**datos, 'cancha': cancha}, hora_fin=hora_fin, creado_por=actor)
            TurnoFijoService._difundir(turno)
        return turno

    @staticmethod
    def actualizar(turno_fijo, datos, confirmar=False):
        """
        El día, la cancha y el inicio de la vigencia no se editan: un cambio así es otro turno fijo. El horario sí,
        hacia otro turno libre de la grilla y con confirmación explícita, porque cambia el acuerdo con el cliente.
        Reanudar o cambiar el horario revisa toda la vigencia; extender el fin, solo el tramo agregado.
        """
        with transaction.atomic():
            cancha, turno = TurnoFijoService.bloquear(turno_fijo)
            campos = _campos_modificados(turno, datos)
            if not campos:
                return turno

            fin_nuevo = campos.get('fecha_fin_vigencia', turno.fecha_fin_vigencia)
            if 'fecha_fin_vigencia' in campos:
                if fin_nuevo is not None and fin_nuevo < timezone.localdate():
                    raise ValidationError({'fecha_fin_vigencia': 'No puede ser anterior a hoy.'})
                TurnoFijoService.validar_vigencia(turno.fecha_inicio_vigencia, fin_nuevo, turno.dia_semana)

            cambia_horario = 'hora_inicio' in campos
            inicio_nuevo, hora_fin_nueva = campos.get('hora_inicio', turno.hora_inicio), turno.hora_fin
            if cambia_horario:
                bloque = DisponibilidadService.bloque(cancha, turno.dia_semana, inicio_nuevo)
                if bloque is None:
                    raise ValidationError({
                        'hora_inicio': 'El horario no corresponde a un turno de la cancha para ese día de la semana.',
                    })
                hora_fin_nueva = bloque[0]
                campos['hora_fin'] = hora_fin_nueva

            if campos.get('estado', turno.estado) == EstadoTurnoFijo.VIGENTE:
                if turno.estado == EstadoTurnoFijo.PAUSADO or cambia_horario:
                    desde = turno.fecha_inicio_vigencia
                elif 'fecha_fin_vigencia' in campos and turno.fecha_fin_vigencia is not None and (
                    fin_nuevo is None or fin_nuevo > turno.fecha_fin_vigencia
                ):
                    desde = turno.fecha_fin_vigencia + timedelta(days=1)
                else:
                    desde = None
                if desde is not None:
                    TurnoFijoService._validar_periodo_libre(
                        cancha, turno.dia_semana, inicio_nuevo, hora_fin_nueva, desde, fin_nuevo,
                        excluir_id=turno.pk,
                    )

            # Primero los choques reales, que no se pueden confirmar; recién después se pide la confirmación.
            if cambia_horario and not confirmar:
                raise ConflictoConConfirmacion(
                    f'El turno fijo pasa de las {turno.hora_inicio:%H:%M} a las {inicio_nuevo:%H:%M}. Para aplicarlo, '
                    'repetí la operación con "confirmar": true. Las fechas ya registradas en la agenda conservan '
                    'el horario anterior.',
                    vista_previa=TurnoFijoService._vista_previa_de_horario(turno, inicio_nuevo, hora_fin_nueva, fin_nuevo),
                )

            TurnoFijoRepository.actualizar(turno, **campos)
            if cambia_horario or {'estado', 'fecha_fin_vigencia'} & set(campos):
                TurnoFijoService._difundir(turno, dia_completo=cambia_horario)
        return turno

    @staticmethod
    def dar_de_baja(turno_fijo):
        """Las fechas ya llevadas a la agenda siguen como reservas propias: se cancelan desde la agenda."""
        with transaction.atomic():
            _, turno = TurnoFijoService.bloquear(turno_fijo)
            turno.desactivar()
            TurnoFijoService._difundir(turno)


MOTIVO_CANCHA_EN_MANTENIMIENTO = 'La cancha está en mantenimiento.'
MOTIVO_FUERA_DE_LOS_TURNOS = 'El turno ya no coincide con los horarios ni con la duración vigentes de la cancha.'


class ConflictoOperatoriaService:
    """
    Reservas y turnos fijos que un cambio de horarios, de duración o de estado de una cancha deja fuera de su
    grilla. El cambio no los cancela: se informan (409) y, con confirmación, se aplica y quedan marcados en la
    agenda para que el complejo los reprograme o los cancele.
    """

    @staticmethod
    def _rangos(horarios):
        """Normaliza a (dia, apertura, cierre) tanto tuplas del repositorio como horarios precargados."""
        return [
            rango[1:] if isinstance(rango, tuple) else (rango.dia_semana, rango.hora_apertura, rango.hora_cierre)
            for rango in horarios
        ]

    @staticmethod
    def bloques_por_dia(rangos, duracion):
        """{dia_semana: {(inicio, fin)}}: los turnos válidos de la grilla, calculados una sola vez por configuración."""
        bloques = defaultdict(set)
        for dia, apertura, cierre in rangos:
            bloques[dia].update(GrillaService.generar_bloques(apertura, cierre, duracion))
        return bloques

    @staticmethod
    def motivo(estado_cancha, bloques, dia_semana, inicio, fin):
        """Por qué un turno quedó fuera de la grilla de su cancha, o None si sigue siendo un bloque válido."""
        if estado_cancha != EstadoCancha.ACTIVA:
            return MOTIVO_CANCHA_EN_MANTENIMIENTO
        if (inicio, fin) in bloques.get(dia_semana, ()):
            return None
        return MOTIVO_FUERA_DE_LOS_TURNOS

    @staticmethod
    def _bloques_de_cancha(cancha):
        horarios = getattr(cancha, 'horarios_activos', None)
        if horarios is None:
            horarios = HorarioAperturaRepository.activos_de_cancha(cancha.pk)
        return ConflictoOperatoriaService.bloques_por_dia(
            ConflictoOperatoriaService._rangos(horarios), cancha.duracion_turno_min,
        )

    @staticmethod
    def motivo_de_reserva(reserva):
        """Marca de la agenda: solo para reservas que todavía se van a jugar."""
        if reserva.estado not in ESTADOS_RESERVA_A_RESOLVER or _ya_comenzo(reserva.fecha_turno, reserva.hora_inicio):
            return None
        cancha = reserva.cancha
        return ConflictoOperatoriaService.motivo(
            cancha.estado, ConflictoOperatoriaService._bloques_de_cancha(cancha),
            reserva.fecha_turno.weekday(), reserva.hora_inicio, reserva.hora_fin,
        )

    @staticmethod
    def motivo_de_turno_fijo(turno_fijo):
        """Los listados de turnos fijos ya excluyen la baja lógica: solo resta ver si sigue en vigencia."""
        if turno_fijo.fecha_fin_vigencia is not None and turno_fijo.fecha_fin_vigencia < timezone.localdate():
            return None
        cancha = turno_fijo.cancha
        return ConflictoOperatoriaService.motivo(
            cancha.estado, ConflictoOperatoriaService._bloques_de_cancha(cancha),
            turno_fijo.dia_semana, turno_fijo.hora_inicio, turno_fijo.hora_fin,
        )

    @staticmethod
    def anotar(queryset):
        """Agrega `motivo_conflicto` calculado en SQL; se aplica por pedido porque depende de la fecha y la hora."""
        if 'motivo_conflicto' in queryset.query.annotations:
            return queryset
        ahora = timezone.localtime()
        return ReservaRepository.anotar_conflicto_operatoria(
            queryset, ahora.date(), ahora.time(), MOTIVO_CANCHA_EN_MANTENIMIENTO, MOTIVO_FUERA_DE_LOS_TURNOS,
        )

    @staticmethod
    def filtrar_reservas(queryset, con_conflicto):
        """Filtro de la agenda resuelto en SQL: no carga reservas en Python ni arma listas de ids."""
        return ConflictoOperatoriaService.anotar(queryset).filter(motivo_conflicto__isnull=not con_conflicto)

    @staticmethod
    def _afectados(reservas, turnos, bloques, estado):
        """Reservas y turnos fijos fuera de la grilla en una configuración, cada uno con su motivo. Sin consultas."""
        afectadas, afectados = [], []
        for reserva in reservas:
            motivo = ConflictoOperatoriaService.motivo(
                estado, bloques, reserva['fecha_turno'].weekday(), reserva['hora_inicio'], reserva['hora_fin'],
            )
            if motivo:
                afectadas.append({**reserva, 'motivo': motivo})
        for turno in turnos:
            motivo = ConflictoOperatoriaService.motivo(
                estado, bloques, turno['dia_semana'], turno['hora_inicio'], turno['hora_fin'],
            )
            if motivo:
                afectados.append({**turno, 'motivo': motivo})
        return afectadas, afectados

    @staticmethod
    def _con_impacto_nuevo(antes, despues):
        """Lo que el cambio afecta por primera vez o por otro motivo (por ejemplo, de fuera de turno a mantenimiento)."""
        motivos_previos = {item['id']: item['motivo'] for item in antes}
        return [item for item in despues if motivos_previos.get(item['id']) != item['motivo']]

    @staticmethod
    def _avisar(cancha, reservas, turnos, descripcion):
        """
        Un cambio confirmado con ocupaciones fuera de la grilla pide una decisión al personal y avisa a cada jugador con
        una reserva afectada. Los dos avisos son urgentes y no excluyen a quien confirmó: la decisión sigue pendiente.
        """
        complejo = cancha.complejo
        ids = [reserva['id'] for reserva in reservas]
        AvisoComplejoService.al_personal(
            complejo, PERMISO_AVISO_AGENDA, CATEGORIA_AVISO_OPERATORIA, PRIORIDAD_AVISO_URGENTE,
            f'el cambio de {descripcion} dejó fuera de la grilla {_plural(len(ids), "reserva futura", "reservas futuras")} '
            f'y {_plural(len(turnos), "turno fijo", "turnos fijos")}. Reprogramalos o cancelalos desde la agenda.',
            {'cancha': cancha.pk, 'reservas': ids, 'turnos_fijos': [turno['id'] for turno in turnos]},
        )
        _avisar_titulares_afectados(
            reservas,
            lambda propias: (
                f'{complejo.nombre} cambió la operatoria de {cancha.nombre} y {_frase_de_reservas(propias)} quedó '
                'fuera de la grilla. El complejo se comunicará para reprogramarla o cancelarla.'
            ),
            lambda propias: {'cancha': cancha.pk, 'reservas': propias},
        )

    @staticmethod
    def validar_cambio(cancha, confirmar, actor, ip_origen, *, horarios=None, duracion=None, estado=None,
                       descripcion=''):
        """
        Compara lo que queda fuera de la grilla antes y después del cambio. Pide confirmación por lo que el cambio
        afecta por primera vez o con un motivo distinto del que ya tenía; repetir el mismo aviso sobre lo ya marcado
        y sin novedades no aporta. Sin `confirmar` responde 409 con el detalle (sin datos personales); con
        `confirmar`, lo audita.
        """
        # Una sola lectura de reservas y turnos fijos; las dos configuraciones se evalúan en memoria.
        hoy = timezone.localdate()
        por_jugar = [
            reserva for reserva in ReservaRepository.a_resolver_de_cancha(cancha.pk, hoy)
            if not _ya_comenzo(reserva['fecha_turno'], reserva['hora_inicio'])
        ]
        turnos_activos = TurnoFijoRepository.activos_de_cancha(cancha.pk, hoy)
        actuales = ConflictoOperatoriaService._rangos(HorarioAperturaRepository.activos_de_cancha(cancha.pk))
        nuevos = actuales if horarios is None else ConflictoOperatoriaService._rangos(horarios)
        reservas_antes, turnos_antes = ConflictoOperatoriaService._afectados(
            por_jugar, turnos_activos,
            ConflictoOperatoriaService.bloques_por_dia(actuales, cancha.duracion_turno_min), cancha.estado,
        )
        reservas_despues, turnos_despues = ConflictoOperatoriaService._afectados(
            por_jugar, turnos_activos,
            ConflictoOperatoriaService.bloques_por_dia(nuevos, duracion or cancha.duracion_turno_min),
            cancha.estado if estado is None else estado,
        )
        reservas = ConflictoOperatoriaService._con_impacto_nuevo(reservas_antes, reservas_despues)
        turnos = ConflictoOperatoriaService._con_impacto_nuevo(turnos_antes, turnos_despues)
        if not reservas and not turnos:
            return

        conflictos = {
            'cantidad': len(reservas) + len(turnos),
            'reservas': [
                {'id': reserva['id'], 'fecha_turno': reserva['fecha_turno'].isoformat(),
                 'hora_inicio': _hora_iso(reserva['hora_inicio']), 'estado': reserva['estado'],
                 'motivo': reserva['motivo']}
                for reserva in reservas
            ],
            'turnos_fijos': [
                {'id': turno['id'], 'dia_semana': turno['dia_semana'], 'hora_inicio': _hora_iso(turno['hora_inicio']),
                 'motivo': turno['motivo']}
                for turno in turnos
            ],
        }
        if not confirmar:
            raise ConflictoConConfirmacion(
                f'El cambio deja fuera de la grilla {len(reservas)} reserva(s) futura(s) y {len(turnos)} turno(s) '
                'fijo(s). Para aplicarlo igual, repetí la operación con "confirmar": true: no se cancelan y quedan '
                'marcados en la agenda para reprogramarlos o cancelarlos.',
                conflictos,
            )
        AuditoriaService.registrar(
            TipoEventoAuditoria.CAMBIO_CONFIGURACION, 'Cambio de operatoria confirmado con ocupaciones afectadas',
            detalle=f'Cancha id {cancha.pk}: {descripcion}. '
                    f'Reservas afectadas: {[reserva["id"] for reserva in reservas] or "ninguna"}. '
                    f'Turnos fijos afectados: {[turno["id"] for turno in turnos] or "ninguno"}.',
            usuario=actor, complejo=cancha.complejo_id, ip_origen=ip_origen,
        )
        ConflictoOperatoriaService._avisar(cancha, reservas, turnos, descripcion)


logger_avisos = logging.getLogger('core.avisos')


MAXIMO_MENSAJE_AVISO = 280
MAXIMO_IDS_EN_AVISO = 10
CAMPOS_DEL_AVISO_PARA_NODE = (
    'complejo_id', 'usuario_id', 'usuarios_ids', 'categoria', 'prioridad', 'mensaje', 'evento', 'clave_unica',
    'registro',
)


def _lista_de_ids(ids):
    """Ids para el texto de un aviso: los primeros diez y la cantidad restante, para no superar el largo de Node."""
    if len(ids) <= MAXIMO_IDS_EN_AVISO:
        return str(list(ids))
    visibles = ', '.join(str(identificador) for identificador in ids[:MAXIMO_IDS_EN_AVISO])
    return f'[{visibles}, …] y {len(ids) - MAXIMO_IDS_EN_AVISO} más'


def _destino(aviso):
    if aviso.get('usuarios_ids'):
        return f'los usuarios {_lista_de_ids(aviso["usuarios_ids"])}'
    if aviso.get('usuario_id') is not None:
        return f'el usuario {aviso["usuario_id"]}'
    return f'el complejo {aviso["complejo_id"]}'


def _sin_usuario(ids, excluir):
    excluido = getattr(excluir, 'pk', excluir)
    return [identificador for identificador in ids if identificador != excluido]


class DestinatariosService:
    """
    Quién recibe cada aviso en su bandeja personal. Se resuelve por la identificación con el complejo (su
    propietario y los operadores que lo operan) y por el permiso del rol, nunca por el rol a secas: un usuario
    suspendido, dado de baja o sin el permiso no recibe nada. `excluir` es quien realizó la acción, que no se avisa
    a sí mismo.
    """

    @staticmethod
    def superadmins(excluir=None):
        return _sin_usuario(UsuarioRepository.ids_activos_con_rol(ROL_SUPERADMIN), excluir)

    @staticmethod
    def personal(complejo, permiso, excluir=None):
        candidatos = {complejo.propietario_id, *UsuarioRepository.ids_de_operadores_activos(complejo.pk)}
        return _sin_usuario(sorted(PermisoRepository.usuarios_con_permiso(candidatos, permiso)), excluir)

    @staticmethod
    def dueno(complejo, permiso, excluir=None):
        return _sin_usuario(sorted(PermisoRepository.usuarios_con_permiso({complejo.propietario_id}, permiso)), excluir)


class AvisoComplejoService:
    """
    Avisos de servidor con la categoría y la prioridad de la colección `notificaciones` de backend-node. Llegan a la
    bandeja personal de cada destinatario (`al_usuario`, `al_personal`, `al_dueno` y `a_superadmins`); la bandeja
    general de un complejo (`programar` sin usuarios) queda solo para el evento que no tiene a quién avisar. Pueden
    llevar el evento que los originó (una reserva realizada) y una clave de idempotencia (`clave_unica`) con la que
    backend-node descarta un aviso repetido. Se entregan después del commit y nunca revierten la operación que los
    originó. El mensaje no lleva datos personales: solo cantidades, ids, nombres de complejos, horarios y turnos.
    """

    @staticmethod
    def _armar(complejo_id, categoria, prioridad, mensaje, referencias, usuario_id, usuarios_ids, evento, clave_unica,
               registro=None):
        if complejo_id is None and usuario_id is None and not usuarios_ids:
            raise ValueError('Un aviso necesita un complejo o un usuario destinatario.')
        if len(mensaje) > MAXIMO_MENSAJE_AVISO:
            mensaje = f'{mensaje[:MAXIMO_MENSAJE_AVISO - 1]}…'
        return {
            'complejo_id': complejo_id, 'usuario_id': usuario_id, 'usuarios_ids': list(usuarios_ids or []) or None,
            'categoria': categoria, 'prioridad': prioridad, 'mensaje': mensaje, 'referencias': referencias or {},
            'evento': evento, 'clave_unica': clave_unica, 'registro': registro,
        }

    @staticmethod
    def programar(complejo_id, categoria, prioridad, mensaje, referencias=None, *, usuario_id=None, usuarios_ids=None,
                  evento=None, clave_unica=None, registro=None):
        aviso = AvisoComplejoService._armar(
            complejo_id, categoria, prioridad, mensaje, referencias, usuario_id, usuarios_ids, evento, clave_unica,
            registro,
        )
        # robust: una falla al entregar se registra y no convierte en error una operación ya confirmada.
        transaction.on_commit(lambda: AvisoComplejoService.entregar(aviso), robust=True)

    @staticmethod
    def al_usuario(usuario, categoria, prioridad, mensaje, referencias=None, *, clave_unica=None):
        """Aviso a la bandeja de un usuario. Una cuenta dada de baja ya no tiene bandeja y un titular manual no tiene cuenta."""
        if usuario is None or usuario.estado != EstadoUsuario.ACTIVO:
            return
        AvisoComplejoService.programar(
            None, categoria, prioridad, mensaje, referencias, usuario_id=usuario.pk, clave_unica=clave_unica,
        )

    @staticmethod
    def al_personal(complejo, permiso, categoria, prioridad, mensaje, referencias=None, *, actor=None, evento=None):
        """
        Aviso operativo: al dueño y a cada operador activo del complejo cuyo rol tenga el permiso, y una entrada de
        registro del complejo que ven los tres roles de complejo.
        """
        AvisoComplejoService._a_grupo(
            complejo, DestinatariosService.personal(complejo, permiso, actor), categoria, prioridad, mensaje,
            referencias, evento, AMBITO_REGISTRO_OPERATIVO, actor,
        )

    @staticmethod
    def al_dueno(complejo, permiso, categoria, prioridad, mensaje, referencias=None, *, actor=None):
        """
        Aviso comercial, financiero o de titularidad: solo al propietario del complejo, si su rol tiene el permiso, y
        una entrada de registro que el operador no ve.
        """
        AvisoComplejoService._a_grupo(
            complejo, DestinatariosService.dueno(complejo, permiso, actor), categoria, prioridad, mensaje,
            referencias, None, AMBITO_REGISTRO_COMERCIAL, actor,
        )

    @staticmethod
    def _texto_de_registro(texto, referencias, actor):
        """
        El texto del aviso más los ids que identifican lo ocurrido: la cancha, el titular de la reserva, el turno fijo y
        quien hizo el cambio. Son identificadores, no datos personales. Si no entra, se recorta el aviso y no los ids.
        """
        referencias = referencias or {}
        partes = []
        for clave, etiqueta in (('cancha', 'Cancha id'), ('titular', 'Titular: usuario id'), ('turno_fijo', 'Turno fijo id')):
            if isinstance(referencias.get(clave), int):
                partes.append(f'{etiqueta} {referencias[clave]}')
        if actor is not None:
            partes.append(f'Hecho por usuario id {getattr(actor, "pk", actor)}')
        if not partes:
            return texto
        sufijo = f' ({"; ".join(partes)})'
        if len(texto) + len(sufijo) > MAXIMO_MENSAJE_AVISO:
            texto = f'{texto[:MAXIMO_MENSAJE_AVISO - len(sufijo) - 1]}…'
        return f'{texto}{sufijo}'

    @staticmethod
    def _a_grupo(complejo, destinatarios, categoria, prioridad, mensaje, referencias, evento, ambito, actor):
        """
        Los avisos personales y la entrada del registro del complejo salen en un mismo pedido. Sin destinatarios queda
        solo el registro, que además conserva el evento de una reserva realizada para no perder la actividad.
        """
        texto = f'{complejo.nombre}: {mensaje}'
        AvisoComplejoService.programar(
            complejo.pk, categoria, prioridad, texto, referencias,
            usuarios_ids=destinatarios, evento=evento,
            registro={'ambito': ambito, 'mensaje': AvisoComplejoService._texto_de_registro(texto, referencias, actor)},
        )

    @staticmethod
    def a_superadmins(categoria, prioridad, mensaje, referencias=None, *, actor=None, clave_unica=None):
        destinatarios = DestinatariosService.superadmins(actor)
        if destinatarios:
            AvisoComplejoService.programar(
                None, categoria, prioridad, mensaje, referencias, usuarios_ids=destinatarios, clave_unica=clave_unica,
            )

    @staticmethod
    def entregar_en_segundo_plano(avisos):
        """Entrega sin hacer esperar a quien consulta: para los avisos que dispara una lectura y no una escritura."""
        threading.Thread(
            target=lambda: [AvisoComplejoService.entregar(aviso) for aviso in avisos], name='avisos', daemon=True,
        ).start()

    @staticmethod
    def entregar(aviso):
        """
        Un único intento por la ruta interna de backend-node, con tiempo máximo. Si no se entrega, el aviso completo
        queda en el log (`core.avisos`) para reenviarlo a mano: no tiene datos personales y la clave no se registra.
        """
        datos = {campo: aviso[campo] for campo in CAMPOS_DEL_AVISO_PARA_NODE if aviso.get(campo) is not None}
        try:
            node_client.enviar_notificacion(datos)
        except node_client.NodeNoConfigurado:
            logger_avisos.warning(
                'Aviso para %s sin entregar (backend-node no está configurado): categoría %s, prioridad %s. %s',
                _destino(aviso), aviso['categoria'], aviso['prioridad'], aviso['mensaje'],
            )
        except node_client.NodeNoDisponible as error:
            logger_avisos.error(
                'Aviso para %s sin entregar: backend-node %s. Categoría %s, prioridad %s. %s',
                _destino(aviso), error, aviso['categoria'], aviso['prioridad'], aviso['mensaje'],
            )


def _frase_de_reservas(ids):
    return f'tu reserva id {ids[0]}' if len(ids) == 1 else f'tus reservas (ids {_lista_de_ids(ids)})'


def _avisar_titulares_afectados(reservas, mensaje_de, referencias_de):
    """
    Un aviso urgente por titular con cuenta activa, con todas sus reservas afectadas. `mensaje_de(ids)` arma el
    texto y `referencias_de(ids)` las referencias; las reservas manuales no tienen a quién avisar.
    """
    por_titular = defaultdict(list)
    for reserva in reservas:
        if reserva['usuario_id'] is not None:
            por_titular[reserva['usuario_id']].append(reserva['id'])
    for usuario_id in UsuarioRepository.ids_activos_entre(por_titular):
        ids = por_titular[usuario_id]
        AvisoComplejoService.programar(
            None, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_URGENTE, mensaje_de(ids), referencias_de(ids),
            usuario_id=usuario_id,
        )


class RecordatorioService:
    """
    Recordatorio del turno próximo al titular de una reserva activa. Se emite desde el comando
    `emitir_recordatorios_reservas` (cron) y, además, cuando el propio jugador consulta sus reservas o una grilla, para
    que funcione igual sin tareas programadas. La repetición nunca duplica el aviso: viaja con una clave por reserva
    (`clave_unica`) y backend-node descarta la que ya emitió. La caché solo espacia las verificaciones del jugador.
    """

    @staticmethod
    def _pendientes(usuario_id=None):
        ahora = timezone.now()
        limite = ahora + timedelta(hours=settings.RECORDATORIO_HORAS_ANTICIPACION)
        reservas = ReservaRepository.proximas_a_recordar(
            timezone.localtime(ahora).date(), timezone.localtime(limite).date(), usuario_id,
        )
        return [
            reserva for reserva in reservas
            if ahora < _inicio_del_turno(reserva.fecha_turno, reserva.hora_inicio) <= limite
        ]

    @staticmethod
    def _cuando(reserva):
        dias = (reserva.fecha_turno - timezone.localdate()).days
        hora = f'{reserva.hora_inicio:%H:%M}'
        if dias == 0:
            return f'hoy a las {hora}'
        if dias == 1:
            return f'mañana a las {hora}'
        return f'el {reserva.fecha_turno:%d/%m/%Y} a las {hora}'

    @staticmethod
    def _armar(reserva):
        return AvisoComplejoService._armar(
            None, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL,
            f'Recordatorio: tenés turno {RecordatorioService._cuando(reserva)} en {reserva.cancha.complejo.nombre} '
            f'({reserva.cancha.nombre}, reserva id {reserva.pk}).',
            {'reserva': reserva.pk}, reserva.usuario_id, None, None, f'recordatorio-reserva-{reserva.pk}',
        )

    @staticmethod
    def emitir_pendientes(usuario_id=None, *, en_segundo_plano=False):
        """Emite el recordatorio de cada turno que empieza dentro de la ventana y devuelve cuántos pidió entregar."""
        avisos = [RecordatorioService._armar(reserva) for reserva in RecordatorioService._pendientes(usuario_id)]
        if en_segundo_plano and avisos:
            AvisoComplejoService.entregar_en_segundo_plano(avisos)
        else:
            for aviso in avisos:
                AvisoComplejoService.entregar(aviso)
        return len(avisos)

    @staticmethod
    def verificar_del_titular(usuario):
        """Verificación transparente de un jugador, como mucho una por intervalo y sin romper nunca la consulta."""
        if not _esta_autenticado(usuario):
            return 0
        if not cache.add(f'recordatorios:{usuario.pk}', 1, timeout=settings.RECORDATORIO_VERIFICACION_SEGUNDOS):
            return 0
        try:
            return RecordatorioService.emitir_pendientes(usuario.pk, en_segundo_plano=True)
        except Exception:
            logger_avisos.exception('No se pudieron verificar los recordatorios del usuario %s', usuario.pk)
            return 0


class EstadoSistemaService:
    """
    Reporte de estado y carga del servidor para los superadministradores. Mide la base de datos y la actividad de
    Django, consulta el estado que publica backend-node (memoria, latencia de MongoDB y fallas de servicios externos)
    y avisa a la bandeja personal de cada superadministrador: normal si todo está en orden, urgente si algo se degradó.
    backend-node no conoce a los usuarios, por eso el aviso lo emite Django.
    """

    @staticmethod
    def _latencia_bd_ms():
        inicio = time_module.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        return round((time_module.perf_counter() - inicio) * 1000)

    @staticmethod
    def _estado_de_node():
        try:
            return node_client.consultar_estado()
        except node_client.NodeNoConfigurado:
            return None
        except node_client.NodeNoDisponible as error:
            return {'estado': 'sin_respuesta', 'motivos': [f'backend-node {error}']}

    @staticmethod
    def medir():
        ahora = timezone.now()
        latencia = EstadoSistemaService._latencia_bd_ms()
        motivos = []
        if latencia > settings.REPORTE_LATENCIA_BD_MAXIMA_MS:
            motivos.append(f'la base de datos tarda {latencia} ms (máximo {settings.REPORTE_LATENCIA_BD_MAXIMA_MS} ms)')
        node = EstadoSistemaService._estado_de_node()
        if node is not None and node.get('estado') != 'ok':
            motivos.extend(str(motivo) for motivo in node.get('motivos') or ['backend-node degradado'])
        return {
            'latencia_bd_ms': latencia,
            'reservas_ultimas_24h': ReservaRepository.cantidad_creadas_desde(ahora - timedelta(hours=24)),
            'reservas_por_jugar': ReservaRepository.cantidad_por_jugar(timezone.localdate()),
            'usuarios_activos': UsuarioRepository.cantidad_activos(),
            'node': node,
            'motivos': motivos,
            'momento': ahora,
        }

    @staticmethod
    def _texto(reporte):
        partes = [
            'Estado del servidor: ' + ('degradado' if reporte['motivos'] else 'normal') + '.',
            f'Base de datos {reporte["latencia_bd_ms"]} ms, {reporte["reservas_ultimas_24h"]} reservas nuevas en 24 h, '
            f'{reporte["reservas_por_jugar"]} por jugar, {reporte["usuarios_activos"]} cuentas activas.',
        ]
        metricas = (reporte['node'] or {}).get('metricas')
        if reporte['node'] is None:
            partes.append('backend-node sin configurar.')
        elif metricas:
            latencia = metricas['latencia_mongo_ms']
            mongo = 'MongoDB sin conexión' if latencia is None else f'MongoDB {latencia} ms'
            partes.append(
                f'Node: memoria {metricas["memoria_rss_mb"]} MB, {mongo}, '
                f'{metricas["fallas_externas_recientes"]} fallas externas recientes.'
            )
        if reporte['motivos']:
            partes.append('Motivos: ' + '; '.join(reporte['motivos']) + '.')
        return ' '.join(partes)

    @staticmethod
    def emitir_reporte_estado_servidor(*, solo_si_degradado=False):
        """
        Avisa a los superadministradores. Con `solo_si_degradado` calla mientras todo esté normal, para correrlo seguido.
        Una clave por hora evita que dos corridas seguidas dupliquen el reporte. Devuelve el reporte o None.
        """
        reporte = EstadoSistemaService.medir()
        if solo_si_degradado and not reporte['motivos']:
            return None
        AvisoComplejoService.a_superadmins(
            CATEGORIA_AVISO_SISTEMA,
            PRIORIDAD_AVISO_URGENTE if reporte['motivos'] else PRIORIDAD_AVISO_NORMAL,
            EstadoSistemaService._texto(reporte),
            {'motivos': reporte['motivos']},
            clave_unica=f'estado-servidor-{timezone.localtime(reporte["momento"]):%Y%m%d%H}',
        )
        return reporte


def _plural(cantidad, singular, plural):
    return f'{cantidad} {singular if cantidad == 1 else plural}'


class BajaDeCuentaService:
    """
    Efectos de la baja de cuenta propia sobre sus ocupaciones (PROJECT.md §4.7 y §13.2): se cancelan las reservas
    futuras pendientes y confirmadas, se conservan las señadas o pagadas (hay dinero de por medio) y se dan de baja
    los turnos fijos. En las señadas se copia el nombre y el teléfono del titular antes de anonimizarlo, con la
    única finalidad de resolver la seña con el complejo.
    """

    @staticmethod
    def vista_previa(usuario):
        reservas = [
            reserva for reserva in ReservaRepository.a_resolver_de_titular(usuario.pk, timezone.localdate())
            if not _ya_comenzo(reserva['fecha_turno'], reserva['hora_inicio'])
        ]
        senadas = sum(1 for reserva in reservas if reserva['estado'] == EstadoReserva.SENADA)
        turnos_fijos = TurnoFijoRepository.cantidad_activos_de_titular(usuario.pk)
        avisos = []
        if senadas:
            avisos.append(
                f'{_plural(senadas, "reserva señada o pagada no se cancela", "reservas señadas o pagadas no se cancelan")}: '
                'el complejo decide si la mantiene, la reprograma o devuelve la seña. Para eso conservamos tu nombre y '
                'tu teléfono solo en esas reservas, hasta que se resuelvan o, como máximo, '
                f'{settings.CONTACTOS_BAJA_DIAS} días después de cada turno.'
            )
        return {
            'reservas_a_cancelar': len(reservas) - senadas,
            'reservas_senadas_conservadas': senadas,
            'turnos_fijos_a_dar_de_baja': turnos_fijos,
            'avisos': avisos,
            'impedimento': UsuarioService.impedimento_de_baja(usuario),
        }

    @staticmethod
    def resolver_ocupaciones(usuario):
        """
        Corre dentro de la transacción de la baja, antes de anonimizar. Devuelve las reservas canceladas para
        auditarlas después del commit, un resumen sin datos personales y los conteos para avisar a los superadministradores.
        """
        reservas = [
            reserva for reserva in ReservaRepository.bloquear_a_resolver_de_titular(usuario.pk, timezone.localdate())
            if not _ya_comenzo(reserva.fecha_turno, reserva.hora_inicio)
        ]
        canceladas, senadas_por_complejo, complejos = [], defaultdict(list), {}
        canceladas_por_complejo = defaultdict(list)
        for reserva in reservas:
            if reserva.estado == EstadoReserva.SENADA:
                ReservaRepository.actualizar(
                    reserva, nombre_cliente_manual=usuario.nombre_completo, telefono_cliente_manual=usuario.telefono,
                )
                senadas_por_complejo[reserva.cancha.complejo_id].append(reserva.pk)
                complejos[reserva.cancha.complejo_id] = reserva.cancha.complejo
            else:
                estado_anterior = reserva.get_estado_display()
                ReservaRepository.actualizar(reserva, estado=EstadoReserva.CANCELADA_JUGADOR)
                ReservaService._difundir(reserva)
                canceladas.append((reserva, estado_anterior))
                canceladas_por_complejo[reserva.cancha.complejo_id].append(reserva.pk)
                complejos[reserva.cancha.complejo_id] = reserva.cancha.complejo

        turnos_por_complejo = defaultdict(list)
        for turno in TurnoFijoRepository.bloquear_activos_de_titular(usuario.pk):
            turno.desactivar()
            TurnoFijoService._difundir(turno)
            turnos_por_complejo[turno.cancha.complejo_id].append(turno.pk)
            complejos[turno.cancha.complejo_id] = turno.cancha.complejo

        # La seña retenida es plata de por medio: la gestiona el dueño. Lo operativo le llega a todo el personal.
        for complejo_id, ids in senadas_por_complejo.items():
            AvisoComplejoService.al_dueno(
                complejos[complejo_id], PERMISO_AVISO_CONFIGURACION, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_URGENTE,
                f'un titular dio de baja su cuenta y conserva {_plural(len(ids), "reserva señada", "reservas señadas")} '
                f'(ids {_lista_de_ids(ids)}). Resolvé la seña desde la agenda: mantenerla, reprogramarla o cancelarla y devolverla.',
                {'reservas': ids},
            )
        for complejo_id, ids in canceladas_por_complejo.items():
            AvisoComplejoService.al_personal(
                complejos[complejo_id], PERMISO_AVISO_AGENDA, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL,
                f'un titular dio de baja su cuenta y se cancelaron {_plural(len(ids), "reserva", "reservas")} '
                f'(ids {_lista_de_ids(ids)}). Los horarios quedaron libres en la grilla.',
                {'reservas': ids},
            )
        for complejo_id, ids in turnos_por_complejo.items():
            AvisoComplejoService.al_personal(
                complejos[complejo_id], PERMISO_AVISO_AGENDA, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL,
                f'se dieron de baja {_plural(len(ids), "turno fijo", "turnos fijos")} (ids {_lista_de_ids(ids)}) porque su titular '
                'cerró la cuenta. El horario quedó libre en la grilla.',
                {'turnos_fijos': ids},
            )
        senadas = sum(len(ids) for ids in senadas_por_complejo.values())
        turnos = sum(len(ids) for ids in turnos_por_complejo.values())
        resumen = (
            f'Reservas canceladas: {len(canceladas)}. '
            f'Reservas señadas conservadas: {senadas}. '
            f'Turnos fijos dados de baja: {turnos}.'
        )
        return canceladas, resumen, {'canceladas': len(canceladas), 'senadas': senadas, 'turnos_fijos': turnos}

    @staticmethod
    def purgar_contactos_vencidos():
        """Plazo máximo de conservación (`CONTACTOS_BAJA_DIAS`) después del turno, aunque la reserva siga sin resolverse."""
        limite = timezone.localdate() - timedelta(days=settings.CONTACTOS_BAJA_DIAS)
        return ReservaRepository.limpiar_contactos_de_bajas_hasta(limite)


def _minutos(hora):
    return hora.hour * 60 + hora.minute


def _minutos_de_la_union(intervalos):
    """Minutos cubiertos por intervalos [inicio, fin) que pueden superponerse, contando una sola vez cada minuto."""
    total, fin_cubierto = 0, None
    for inicio, fin in sorted((_minutos(inicio), _minutos(fin)) for inicio, fin in intervalos):
        if fin_cubierto is not None and inicio < fin_cubierto:
            inicio = fin_cubierto
        if fin > inicio:
            total += fin - inicio
            fin_cubierto = fin
    return total


MAXIMO_HORARIOS_RANKING = 10
CRITERIO_REPORTE_POR_DEFECTO = 'fecha_turno'
CRITERIOS_REPORTE = ('fecha_turno', 'fecha_creacion', 'fecha_modificacion')
MENSAJE_CANCHA_AJENA_REPORTE = 'La cancha no pertenece al complejo.'


class ReporteService:
    """Dashboard comercial de un complejo, calculado sobre un rango de fechas acotado."""

    @staticmethod
    def validar_filtros(usuario, filtros):
        complejo_id = filtros['complejo']
        if not AccesoComplejoService.puede_administrar(usuario, complejo_id):
            raise NotFound()

        desde, hasta = filtros['fecha_desde'], filtros['fecha_hasta']
        if (hasta - desde).days >= settings.RANGO_MAXIMO_DIAS:
            raise ValidationError({
                'fecha_hasta': f'El rango del reporte abarca como máximo {settings.RANGO_MAXIMO_DIAS} días.',
            })

        cancha_id = filtros.get('cancha_id')
        # Mismo mensaje para una cancha ajena o inexistente, para no confirmar ids de otros complejos.
        if cancha_id is not None and not CanchaRepository.pertenece_a_complejo(cancha_id, complejo_id):
            raise ValidationError({'cancha_id': MENSAJE_CANCHA_AJENA_REPORTE})

        deporte_id = filtros.get('deporte_id')
        if deporte_id is not None and not CatalogoRepository.existe_deporte(deporte_id):
            raise ValidationError({'deporte_id': 'El deporte indicado no existe.'})

        return {
            'complejo': complejo_id,
            'fecha_desde': desde,
            'fecha_hasta': hasta,
            'criterio': filtros.get('criterio') or CRITERIO_REPORTE_POR_DEFECTO,
            'cancha_id': cancha_id,
            'deporte_id': deporte_id,
        }

    @staticmethod
    def _minutos_ofertables(bloques, excepciones, ocupados):
        """
        Turnos de la grilla que ninguna excepción cierra, unidos a los turnos tomados. Una reserva ocupa su horario
        aunque después se haya cargado un cierre o cambiado la grilla: ese tiempo se ofreció, y así el porcentaje
        nunca supera el 100 %.
        """
        abiertos = [
            (inicio, fin) for inicio, fin in bloques
            if not any(_excepcion_cubre(excepcion, inicio, fin) for excepcion in excepciones)
        ]
        return _minutos_de_la_union(abiertos + ocupados)

    @staticmethod
    def _fila_de_ocupacion(cancha, dias, horarios, excepciones, reservas):
        fila = {'cancha_id': cancha['id'], 'cancha': cancha['nombre']}
        ocupados = sum(
            _minutos(fin) - _minutos(inicio) for dia in dias for inicio, fin in reservas[(cancha['id'], dia)]
        )
        if cancha['estado'] != EstadoCancha.ACTIVA or cancha['deporte__estado'] != EstadoRegistro.ACTIVO:
            if not ocupados:
                return None
            return {**fila, 'minutos_ofertables': None, 'minutos_ocupados': ocupados, 'porcentaje': None}

        bloques_por_dia_semana = {
            dia_semana: [
                bloque
                for horario in horarios[(cancha['id'], dia_semana)]
                for bloque in GrillaService.generar_bloques(
                    horario['hora_apertura'], horario['hora_cierre'], cancha['duracion_turno_min'],
                )
            ]
            for dia_semana in DiaSemana.values
        }
        excepciones = [excepcion for excepcion in excepciones if excepcion['cancha_id'] in (None, cancha['id'])]
        ofertables = sum(
            ReporteService._minutos_ofertables(
                bloques_por_dia_semana[dia.weekday()],
                [excepcion for excepcion in excepciones if excepcion['fecha_inicio'] <= dia <= excepcion['fecha_fin']],
                reservas[(cancha['id'], dia)],
            )
            for dia in dias
        )
        return {
            **fila, 'minutos_ofertables': ofertables, 'minutos_ocupados': ocupados,
            'porcentaje': round(ocupados * 100 / ofertables, 2) if ofertables else None,
        }

    @staticmethod
    def ocupacion(filtros):
        """
        Minutos ocupados sobre minutos ofertables por cancha, día por día. Solo con el criterio de fecha de turno:
        con los otros el rango no describe días de juego. La oferta usa los horarios vigentes, porque no se guarda
        su historial; por eso una cancha inactiva no tiene oferta y aparece solo si tuvo reservas.
        """
        if filtros['criterio'] != CRITERIO_REPORTE_POR_DEFECTO:
            return None

        canchas = ReporteRepository.canchas(filtros)
        horarios = defaultdict(list)
        for horario in ReporteRepository.horarios_activos([cancha['id'] for cancha in canchas]):
            horarios[(horario['cancha_id'], horario['dia_semana'])].append(horario)
        reservas = defaultdict(list)
        for reserva in ReporteRepository.reservas_ocupantes(filtros):
            reservas[(reserva['cancha_id'], reserva['fecha_turno'])].append((reserva['hora_inicio'], reserva['hora_fin']))
        excepciones = ExcepcionHorariaRepository.activas_en_rango(
            filtros['complejo'], filtros['fecha_desde'], filtros['fecha_hasta'],
        )
        dias = [
            filtros['fecha_desde'] + timedelta(days=numero)
            for numero in range((filtros['fecha_hasta'] - filtros['fecha_desde']).days + 1)
        ]

        filas = (
            ReporteService._fila_de_ocupacion(cancha, dias, horarios, excepciones, reservas) for cancha in canchas
        )
        return [fila for fila in filas if fila is not None]

    @staticmethod
    def dashboard(usuario, filtros):
        filtros = ReporteService.validar_filtros(usuario, filtros)
        resumen = ReporteRepository.resumen(filtros)
        return {
            'filtros': filtros,
            'recaudacion': {clave: f'{monto:.2f}' for clave, monto in resumen['recaudacion'].items()},
            'conteos': resumen['conteos'],
            'ocupacion': ReporteService.ocupacion(filtros),
            'ranking_horarios': ReporteRepository.ranking_horarios(filtros, MAXIMO_HORARIOS_RANKING),
        }
