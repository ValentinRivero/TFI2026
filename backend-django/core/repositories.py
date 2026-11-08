from django.db.models import Exists, Min, OuterRef, Prefetch, Q, Subquery
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import (
    Cancha,
    Complejo,
    ComplejoServicio,
    Deporte,
    EstadoCancha,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    EstadoTurnoFijo,
    EstadoUsuario,
    HorarioApertura,
    LogAuditoria,
    Reserva,
    Rol,
    RolPermiso,
    Servicio,
    TurnoFijo,
    Usuario,
)

ESTADOS_RESERVA_OCUPANTES = (
    EstadoReserva.PENDIENTE,
    EstadoReserva.CONFIRMADA,
    EstadoReserva.SENADA,
    EstadoReserva.COMPLETADA,
)


class UsuarioRepository:
    @staticmethod
    def existe_email(email):
        return Usuario.objects.filter(email__iexact=email).exists()

    @staticmethod
    def obtener_por_email(email):
        return Usuario.objects.select_related('rol').filter(email__iexact=email).first()

    @staticmethod
    def obtener_activo_por_id(usuario_id):
        return (
            Usuario.objects.select_related('rol')
            .filter(id=usuario_id, estado=EstadoUsuario.ACTIVO)
            .first()
        )

    @staticmethod
    def bloquear_activos_con_rol(nombre_rol):
        """Bloquea (FOR UPDATE, solo la tabla usuarios) a los usuarios activos de un rol activo y devuelve sus ids."""
        return list(
            Usuario.objects.select_for_update(of=('self',))
            .filter(rol__nombre=nombre_rol, rol__estado=EstadoRegistro.ACTIVO, estado=EstadoUsuario.ACTIVO)
            .order_by('id')
            .values_list('id', flat=True)
        )

    @staticmethod
    def bloquear_por_id(usuario_id):
        return Usuario.objects.select_for_update(of=('self',)).select_related('rol').filter(id=usuario_id).first()

    @staticmethod
    def bloquear_por_email(email):
        return (
            Usuario.objects.select_for_update(of=('self',)).select_related('rol')
            .filter(email__iexact=email).first()
        )

    @staticmethod
    def listar():
        return Usuario.objects.select_related('rol', 'complejo_operado').order_by('id')

    @staticmethod
    def duenos_activos():
        return Usuario.objects.filter(
            rol__nombre='DUENO_COMPLEJO', rol__estado=EstadoRegistro.ACTIVO, estado=EstadoUsuario.ACTIVO,
        )

    @staticmethod
    def operadores_de(complejo_id):
        return (
            Usuario.objects.filter(complejo_operado_id=complejo_id, rol__nombre='OPERADOR_COMPLEJO')
            .exclude(estado=EstadoUsuario.BAJA)
            .order_by('nombre_completo', 'id')
        )

    @staticmethod
    def crear(email, password, rol, **campos):
        return Usuario.objects.create_user(email=email, password=password, rol=rol, **campos)

    @staticmethod
    def anonimizar(usuario):
        """
        Supresión de datos personales sin borrado físico: la fila queda para la integridad de reservas,
        reportes y auditoría, pero ya no identifica a nadie. `.invalid` es un dominio reservado (RFC 2606).
        """
        usuario.nombre_completo = 'Usuario dado de baja'
        usuario.email = f'baja-{usuario.pk}@talibre.invalid'
        usuario.telefono = ''
        usuario.complejo_operado = None
        usuario.set_unusable_password()
        usuario.save(update_fields=[
            'nombre_completo', 'email', 'telefono', 'complejo_operado', 'password', 'fecha_modificacion',
        ])
        return usuario

    @staticmethod
    def actualizar(usuario, **campos):
        for campo, valor in campos.items():
            setattr(usuario, campo, valor)
        usuario.save(update_fields=[*campos, 'fecha_modificacion'])
        return usuario


class RolRepository:
    @staticmethod
    def obtener_activo_por_nombre(nombre):
        return Rol.objects.filter(nombre=nombre, estado=EstadoRegistro.ACTIVO).first()

    @staticmethod
    def activos():
        return Rol.objects.filter(estado=EstadoRegistro.ACTIVO)


class PermisoRepository:
    @staticmethod
    def _asignaciones_activas():
        return RolPermiso.objects.filter(
            estado=EstadoRegistro.ACTIVO,
            rol__estado=EstadoRegistro.ACTIVO,
            permiso__estado=EstadoRegistro.ACTIVO,
        )

    @staticmethod
    def codigos_activos_de_usuario(usuario_id):
        codigos = PermisoRepository._asignaciones_activas().filter(
            rol__usuarios__id=usuario_id,
            rol__usuarios__estado=EstadoUsuario.ACTIVO,
        ).values_list('permiso__codigo', flat=True)
        return set(codigos)

    @staticmethod
    def codigos_activos_de_roles(nombres_roles):
        codigos = PermisoRepository._asignaciones_activas().filter(
            rol__nombre__in=nombres_roles,
        ).values_list('permiso__codigo', flat=True)
        return set(codigos)


class ComplejoRepository:
    @staticmethod
    def _vigentes():
        return Complejo.objects.exclude(estado=EstadoRegistro.BAJA)

    @staticmethod
    def vigentes():
        return ComplejoRepository._vigentes().order_by('nombre', 'id')

    @staticmethod
    def contratos():
        return ComplejoRepository._vigentes().select_related('propietario').order_by('nombre', 'id')

    @staticmethod
    def _prefetch_servicios_activos():
        servicios = ComplejoServicio.objects.filter(
            estado=EstadoRegistro.ACTIVO, servicio__estado=EstadoRegistro.ACTIVO,
        ).select_related('servicio').order_by('servicio__nombre')
        return Prefetch('servicios_ofrecidos', queryset=servicios, to_attr='servicios_activos')

    @staticmethod
    def administrables():
        return ComplejoRepository._vigentes().prefetch_related(
            ComplejoRepository._prefetch_servicios_activos(),
        ).order_by('nombre', 'id')

    @staticmethod
    def catalogo_publico():
        """
        Solo complejos con contrato activo y sin baja lógica. Servicios y canchas activas se resuelven con
        un prefetch cada uno y el precio mínimo con una subconsulta: la cantidad de consultas no crece
        con la cantidad de complejos listados.
        """
        canchas = Cancha.objects.filter(
            estado=EstadoCancha.ACTIVA, deporte__estado=EstadoRegistro.ACTIVO,
        ).select_related('deporte').order_by('nombre', 'id')
        precio_minimo = (
            Cancha.objects.filter(complejo=OuterRef('pk'), estado=EstadoCancha.ACTIVA)
            .order_by()
            .values('complejo')
            .annotate(minimo=Min('precio_base'))
            .values('minimo')
        )
        return (
            Complejo.objects.filter(estado=EstadoRegistro.ACTIVO, estado_contrato=EstadoContrato.ACTIVO)
            .annotate(precio_desde=Subquery(precio_minimo))
            .prefetch_related(
                ComplejoRepository._prefetch_servicios_activos(),
                Prefetch('canchas', queryset=canchas, to_attr='canchas_activas'),
            )
            .order_by('nombre', 'id')
        )

    @staticmethod
    def filtrar_por_canchas(queryset, **condiciones):
        """Complejos con al menos una cancha activa que cumpla todas las condiciones a la vez."""
        canchas = Cancha.objects.filter(complejo=OuterRef('pk'), estado=EstadoCancha.ACTIVA, **condiciones)
        return queryset.filter(Exists(canchas))

    @staticmethod
    def filtrar_por_servicios(queryset, servicio_ids):
        """Complejos que ofrecen todos los servicios indicados."""
        for servicio_id in servicio_ids:
            ofrecido = ComplejoServicio.objects.filter(
                complejo=OuterRef('pk'), servicio_id=servicio_id, estado=EstadoRegistro.ACTIVO,
            )
            queryset = queryset.filter(Exists(ofrecido))
        return queryset

    @staticmethod
    def bloquear(complejo_id):
        return Complejo.objects.select_for_update(of=('self',)).get(id=complejo_id)

    @staticmethod
    def crear(**campos):
        return Complejo.objects.create(**campos)

    @staticmethod
    def actualizar(complejo, **campos):
        for campo, valor in campos.items():
            setattr(complejo, campo, valor)
        complejo.save(update_fields=[*campos, 'fecha_modificacion'])
        return complejo

    @staticmethod
    def existe(complejo_id):
        return ComplejoRepository._vigentes().filter(id=complejo_id).exists()

    @staticmethod
    def es_propietario(complejo_id, usuario_id):
        return ComplejoRepository._vigentes().filter(id=complejo_id, propietario_id=usuario_id).exists()

    @staticmethod
    def tiene_contratos_vigentes(propietario_id):
        return (
            ComplejoRepository._vigentes()
            .filter(propietario_id=propietario_id)
            .exclude(estado_contrato=EstadoContrato.BAJA)
            .exists()
        )

    @staticmethod
    def restringir_queryset(queryset, campo_complejo, condiciones):
        """Filtra un queryset por condiciones sobre su complejo; `campo_complejo` vacío indica que el modelo es Complejo."""
        prefijo = f'{campo_complejo}__' if campo_complejo else ''
        filtro = {f'{prefijo}{campo}': valor for campo, valor in condiciones.items()}
        return queryset.filter(**filtro).exclude(**{f'{prefijo}estado': EstadoRegistro.BAJA})


class CatalogoRepository:
    @staticmethod
    def deportes_activos():
        return Deporte.objects.filter(estado=EstadoRegistro.ACTIVO).order_by('nombre')

    @staticmethod
    def servicios_activos():
        return Servicio.objects.filter(estado=EstadoRegistro.ACTIVO).order_by('nombre')


class ComplejoServicioRepository:
    @staticmethod
    def de_complejo(complejo_id):
        return list(ComplejoServicio.objects.filter(complejo_id=complejo_id))

    @staticmethod
    def crear(complejo_id, servicio_id):
        return ComplejoServicio.objects.create(complejo_id=complejo_id, servicio_id=servicio_id)

    @staticmethod
    def reactivar(asignacion):
        asignacion.estado = EstadoRegistro.ACTIVO
        asignacion.save(update_fields=['estado', 'fecha_modificacion'])

    @staticmethod
    def servicios_activos_de(complejo_id):
        return Servicio.objects.filter(
            estado=EstadoRegistro.ACTIVO,
            ofrecido_en__complejo_id=complejo_id,
            ofrecido_en__estado=EstadoRegistro.ACTIVO,
        ).order_by('nombre')


class CanchaRepository:
    @staticmethod
    def vigentes():
        return Cancha.objects.exclude(estado=EstadoCancha.BAJA).select_related('complejo', 'deporte')

    @staticmethod
    def bloquear(cancha_id):
        return Cancha.objects.select_for_update(of=('self',)).get(id=cancha_id)

    @staticmethod
    def existe_nombre(complejo_id, nombre, excluir_id=None):
        canchas = Cancha.objects.filter(complejo_id=complejo_id, nombre__iexact=nombre).exclude(
            estado=EstadoCancha.BAJA,
        )
        if excluir_id is not None:
            canchas = canchas.exclude(id=excluir_id)
        return canchas.exists()

    @staticmethod
    def tiene_ocupacion_futura(cancha_id, desde):
        reservas = Reserva.objects.filter(
            cancha_id=cancha_id, fecha_turno__gte=desde, estado__in=ESTADOS_RESERVA_OCUPANTES,
        )
        turnos_fijos = TurnoFijo.objects.filter(
            Q(fecha_fin_vigencia__isnull=True) | Q(fecha_fin_vigencia__gte=desde),
            cancha_id=cancha_id,
            estado__in=(EstadoTurnoFijo.VIGENTE, EstadoTurnoFijo.PAUSADO),
        )
        return reservas.exists() or turnos_fijos.exists()

    @staticmethod
    def crear(**campos):
        return Cancha.objects.create(**campos)

    @staticmethod
    def actualizar(cancha, **campos):
        for campo, valor in campos.items():
            setattr(cancha, campo, valor)
        cancha.save(update_fields=[*campos, 'fecha_modificacion'])
        return cancha


class HorarioAperturaRepository:
    @staticmethod
    def vigentes():
        return HorarioApertura.objects.filter(estado=EstadoRegistro.ACTIVO).select_related('cancha__complejo')

    @staticmethod
    def solapado(cancha_id, dia_semana, apertura, cierre, excluir_id=None):
        """Primer rango activo del mismo día que se superpone; rangos contiguos (12 a 16 y 16 a 20) no chocan."""
        horarios = HorarioApertura.objects.filter(
            cancha_id=cancha_id,
            dia_semana=dia_semana,
            estado=EstadoRegistro.ACTIVO,
            hora_apertura__lt=cierre,
            hora_cierre__gt=apertura,
        )
        if excluir_id is not None:
            horarios = horarios.exclude(id=excluir_id)
        return horarios.order_by('hora_apertura').first()

    @staticmethod
    def crear(**campos):
        return HorarioApertura.objects.create(**campos)

    @staticmethod
    def actualizar(horario, **campos):
        for campo, valor in campos.items():
            setattr(horario, campo, valor)
        horario.save(update_fields=[*campos, 'fecha_modificacion'])
        return horario


class SesionRepository:
    @staticmethod
    def revocar_refresh_de_usuario(usuario_id):
        vigentes = OutstandingToken.objects.filter(
            user_id=usuario_id,
            expires_at__gt=timezone.now(),
            blacklistedtoken__isnull=True,
        )
        BlacklistedToken.objects.bulk_create(
            [BlacklistedToken(token=token) for token in vigentes],
            ignore_conflicts=True,
        )


class AuditoriaRepository:
    @staticmethod
    def crear(tipo_evento, accion, detalle, usuario_id, complejo_id, ip_origen):
        return LogAuditoria.objects.create(
            tipo_evento=tipo_evento,
            accion=accion,
            detalle=detalle,
            usuario_id=usuario_id,
            complejo_id=complejo_id,
            ip_origen=ip_origen,
        )

    @staticmethod
    def listar(tipo_evento=None, usuario_id=None, complejo_id=None, ip_origen=None, desde=None, hasta=None):
        filtros = Q(estado=EstadoRegistro.ACTIVO)
        if tipo_evento is not None:
            filtros &= Q(tipo_evento=tipo_evento)
        if usuario_id is not None:
            filtros &= Q(usuario_id=usuario_id)
        if complejo_id is not None:
            filtros &= Q(complejo_id=complejo_id)
        if ip_origen:
            filtros &= Q(ip_origen=ip_origen)
        # Rango semiabierto [desde, hasta) sobre la columna indexada, sin convertir a fecha en SQL.
        if desde is not None:
            filtros &= Q(fecha_creacion__gte=desde)
        if hasta is not None:
            filtros &= Q(fecha_creacion__lt=hasta)
        return (
            LogAuditoria.objects.select_related('usuario', 'complejo')
            .filter(filtros)
            .order_by('-fecha_creacion', '-id')
        )
