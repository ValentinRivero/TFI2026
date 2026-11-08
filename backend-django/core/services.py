import hashlib
import ipaddress
import logging
import re
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.settings import api_settings as drf_settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .exceptions import ServicioNoDisponible
from .models import EstadoRegistro, EstadoUsuario, TipoEventoAuditoria
from .repositories import (
    AuditoriaRepository,
    ComplejoRepository,
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
    def _validar_continuidad_superadmin(usuario):
        """
        La plataforma no puede quedar sin superadministrador activo. Se bloquean todas las filas de superadmins
        activos (incluida la propia) para que dos bajas simultáneas no pasen la validación a la vez.
        """
        if not RbacService.es_superadmin(usuario):
            return
        activos = UsuarioRepository.bloquear_activos_con_rol(ROL_SUPERADMIN)
        if not [usuario_id for usuario_id in activos if usuario_id != usuario.pk]:
            raise ValidationError(
                'No podés dar de baja la única cuenta de superadministrador activa. '
                'Asigná otro superadministrador antes de hacerlo.'
            )

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
