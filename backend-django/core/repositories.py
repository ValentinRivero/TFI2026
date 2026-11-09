from datetime import date

from django.db.models import (
    Case,
    CharField,
    Exists,
    ExpressionWrapper,
    F,
    IntegerField,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, ExtractHour, ExtractIsoWeekDay, ExtractMinute, Mod
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import (
    AlcanceExcepcion,
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
    ExcepcionHoraria,
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
# Reservas que todavía se van a jugar y pueden necesitar una decisión del complejo o del titular.
ESTADOS_RESERVA_A_RESOLVER = (EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA)
ESTADOS_TURNO_FIJO_ACTIVOS = (EstadoTurnoFijo.VIGENTE, EstadoTurnoFijo.PAUSADO)


def _minutos_del_dia(campo):
    """Hora como minutos desde la medianoche, para operar en SQL igual en SQLite y en PostgreSQL."""
    return ExtractHour(campo) * 60 + ExtractMinute(campo)


def _entero_externo(anotacion):
    """Referencia a una anotación entera de la consulta externa, con tipo explícito para usarla en funciones."""
    return ExpressionWrapper(OuterRef(anotacion), output_field=IntegerField())


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
    def publico_por_id(complejo_id):
        """Mismo criterio que el catálogo: sin baja lógica y con contrato activo."""
        return (
            Complejo.objects.filter(id=complejo_id, estado=EstadoRegistro.ACTIVO, estado_contrato=EstadoContrato.ACTIVO)
            .only('id', 'nombre')
            .first()
        )

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

    @staticmethod
    def existe_deporte(deporte_id):
        # Incluye los dados de baja: sus reservas siguen formando parte del historial de los reportes.
        return Deporte.objects.filter(id=deporte_id).exists()


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
    def pertenece_a_complejo(cancha_id, complejo_id):
        # Incluye las dadas de baja: sus reservas siguen formando parte del historial de los reportes.
        return Cancha.objects.filter(id=cancha_id, complejo_id=complejo_id).exists()

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
    def activos_de_cancha(cancha_id):
        """(id, dia_semana, apertura, cierre) de los rangos activos: alcanza para recalcular los bloques."""
        return list(
            HorarioApertura.objects.filter(cancha_id=cancha_id, estado=EstadoRegistro.ACTIVO)
            .order_by('dia_semana', 'hora_apertura')
            .values_list('id', 'dia_semana', 'hora_apertura', 'hora_cierre')
        )

    @staticmethod
    def prefetch_activos(ruta_cancha):
        """Precarga, en `<ruta_cancha>.horarios_activos`, los rangos activos de cada cancha con una sola consulta."""
        return Prefetch(
            f'{ruta_cancha}horarios',
            queryset=HorarioApertura.objects.filter(estado=EstadoRegistro.ACTIVO).only(
                'id', 'cancha_id', 'dia_semana', 'hora_apertura', 'hora_cierre',
            ),
            to_attr='horarios_activos',
        )

    @staticmethod
    def crear(**campos):
        return HorarioApertura.objects.create(**campos)

    @staticmethod
    def actualizar(horario, **campos):
        for campo, valor in campos.items():
            setattr(horario, campo, valor)
        horario.save(update_fields=[*campos, 'fecha_modificacion'])
        return horario


class ExcepcionHorariaRepository:
    @staticmethod
    def vigentes():
        return (
            ExcepcionHoraria.objects.filter(estado=EstadoRegistro.ACTIVO)
            .select_related('complejo', 'cancha')
            .order_by('fecha_inicio', 'hora_inicio', 'id')
        )

    @staticmethod
    def que_afectan_a_cancha(queryset, cancha_id):
        """Las propias de la cancha y las globales de su complejo, que también la cierran."""
        complejo_de_la_cancha = Cancha.objects.filter(id=cancha_id).values('complejo_id')
        return queryset.filter(
            Q(cancha_id=cancha_id) | Q(cancha__isnull=True, complejo_id__in=complejo_de_la_cancha),
        )

    @staticmethod
    def que_cubren_fecha(queryset, fecha):
        return queryset.filter(fecha_inicio__lte=fecha, fecha_fin__gte=fecha)

    @staticmethod
    def activas_en_fecha(complejo_id, fecha):
        """Excepciones activas del complejo (globales y por cancha) vigentes en la fecha, sin texto libre."""
        return list(
            ExcepcionHoraria.objects.filter(
                complejo_id=complejo_id, estado=EstadoRegistro.ACTIVO, fecha_inicio__lte=fecha, fecha_fin__gte=fecha,
            ).values('cancha_id', 'es_dia_completo', 'hora_inicio', 'hora_fin', 'tipo_motivo')
        )

    @staticmethod
    def activas_desde(complejo_ids, hoy):
        """Excepciones activas de esos complejos que todavía no terminaron, sin texto libre."""
        return list(
            ExcepcionHoraria.objects.filter(complejo_id__in=complejo_ids, estado=EstadoRegistro.ACTIVO, fecha_fin__gte=hoy)
            .order_by('fecha_inicio', 'id')
            .values('complejo_id', 'cancha_id', 'fecha_inicio', 'fecha_fin', 'es_dia_completo', 'hora_inicio',
                    'hora_fin', 'tipo_motivo')
        )

    @staticmethod
    def crear(**campos):
        return ExcepcionHoraria.objects.create(**campos)

    @staticmethod
    def bloquear(excepcion_id):
        return ExcepcionHoraria.objects.select_for_update(of=('self',)).filter(id=excepcion_id).first()


class GrillaRepository:
    """
    Lecturas de la grilla pública. Las ocupaciones se leen con `values()` y solo con columnas de horario:
    los datos de clientes nunca salen de la base en esta consulta.
    """

    @staticmethod
    def canchas_activas(complejo_id):
        return list(
            Cancha.objects.filter(
                complejo_id=complejo_id, estado=EstadoCancha.ACTIVA, deporte__estado=EstadoRegistro.ACTIVO,
            ).select_related('deporte').order_by('nombre', 'id')
        )

    @staticmethod
    def horarios_del_dia(cancha_ids, dia_semana):
        return list(
            HorarioApertura.objects.filter(
                cancha_id__in=cancha_ids, dia_semana=dia_semana, estado=EstadoRegistro.ACTIVO,
            ).values('cancha_id', 'hora_apertura', 'hora_cierre', 'precio_diferenciado').order_by('hora_apertura')
        )

    @staticmethod
    def reservas_de_fecha(cancha_ids, fecha):
        """Reservas ocupantes, más las de turnos fijos en cualquier estado: indican si esa fecha ya se generó."""
        return list(
            Reserva.objects.filter(cancha_id__in=cancha_ids, fecha_turno=fecha)
            .exclude(estado=EstadoReserva.BAJA)
            .filter(Q(estado__in=ESTADOS_RESERVA_OCUPANTES) | Q(turno_fijo__isnull=False))
            .values('cancha_id', 'turno_fijo_id', 'hora_inicio', 'hora_fin', 'estado')
        )

    @staticmethod
    def turnos_fijos_vigentes(cancha_ids, dia_semana, fecha):
        return list(
            TurnoFijo.objects.filter(
                Q(fecha_fin_vigencia__isnull=True) | Q(fecha_fin_vigencia__gte=fecha),
                cancha_id__in=cancha_ids,
                dia_semana=dia_semana,
                estado=EstadoTurnoFijo.VIGENTE,
                fecha_inicio_vigencia__lte=fecha,
            ).values('id', 'cancha_id', 'hora_inicio', 'hora_fin')
        )


class ReservaRepository:
    @staticmethod
    def _vigentes():
        return Reserva.objects.exclude(estado=EstadoReserva.BAJA)

    @staticmethod
    def de_usuario(usuario_id):
        return (
            ReservaRepository._vigentes().filter(usuario_id=usuario_id)
            .select_related('cancha__complejo', 'cancha__deporte')
            .order_by('fecha_turno', 'hora_inicio', 'id')
        )

    @staticmethod
    def filtrar_por_vigencia(queryset, proximas, hoy, hora_actual):
        """Próxima hasta que termina el turno; un turno de hoy en curso sigue siendo próximo."""
        terminadas = Q(fecha_turno__lt=hoy) | Q(fecha_turno=hoy, hora_fin__lte=hora_actual)
        return queryset.exclude(terminadas) if proximas else queryset.filter(terminadas)

    @staticmethod
    def agenda():
        return (
            ReservaRepository._vigentes().select_related('cancha__complejo', 'usuario')
            .order_by('fecha_turno', 'hora_inicio', 'cancha__nombre', 'id')
        )

    @staticmethod
    def anotar_conflicto_operatoria(queryset, hoy, hora_actual, motivo_mantenimiento, motivo_fuera_de_turnos):
        """
        Anota `motivo_conflicto` en SQL con la misma regla que ConflictoOperatoriaService.motivo(): una reserva por
        jugar sigue en la grilla si su cancha está activa y algún rango activo de ese día la contiene alineada a la
        duración del turno. Así la agenda filtra y marca sin cargar filas en Python (paridad cubierta por tests).
        """
        # Las funciones no reciben OuterRef: el día y los minutos del turno se anotan antes en la consulta externa.
        queryset = queryset.annotate(
            dia_del_turno=ExtractIsoWeekDay('fecha_turno') - 1,
            minuto_de_inicio=_minutos_del_dia('hora_inicio'),
            minutos_de_turno=_minutos_del_dia('hora_fin') - _minutos_del_dia('hora_inicio'),
        )
        bloque_vigente = HorarioApertura.objects.filter(
            cancha_id=OuterRef('cancha_id'),
            estado=EstadoRegistro.ACTIVO,
            dia_semana=OuterRef('dia_del_turno'),
            hora_apertura__lte=OuterRef('hora_inicio'),
            hora_cierre__gte=OuterRef('hora_fin'),
        ).annotate(
            desfase=Mod(
                _entero_externo('minuto_de_inicio') - _minutos_del_dia('hora_apertura'),
                _entero_externo('minutos_de_turno'),
            ),
        ).filter(desfase=0)
        por_jugar = Q(fecha_turno__gt=hoy) | Q(fecha_turno=hoy, hora_inicio__gt=hora_actual)
        sin_motivo = Value(None, output_field=CharField())
        return queryset.annotate(
            en_bloque_vigente=Exists(bloque_vigente),
        ).annotate(
            motivo_conflicto=Case(
                When(~(Q(estado__in=ESTADOS_RESERVA_A_RESOLVER) & por_jugar), then=sin_motivo),
                When(~Q(cancha__estado=EstadoCancha.ACTIVA), then=Value(motivo_mantenimiento)),
                When(en_bloque_vigente=True, minutos_de_turno=F('cancha__duracion_turno_min'), then=sin_motivo),
                default=Value(motivo_fuera_de_turnos),
                output_field=CharField(),
            ),
        )

    @staticmethod
    def a_resolver_de_cancha(cancha_id, hoy):
        return list(
            Reserva.objects.filter(cancha_id=cancha_id, estado__in=ESTADOS_RESERVA_A_RESOLVER, fecha_turno__gte=hoy)
            .order_by('fecha_turno', 'hora_inicio', 'id')
            .values('id', 'fecha_turno', 'hora_inicio', 'hora_fin', 'estado')
        )

    @staticmethod
    def bloquear_a_resolver_de_titular(usuario_id, hoy):
        return list(
            Reserva.objects.select_for_update(of=('self',)).select_related('cancha', 'usuario')
            .filter(usuario_id=usuario_id, estado__in=ESTADOS_RESERVA_A_RESOLVER, fecha_turno__gte=hoy)
            .order_by('fecha_turno', 'hora_inicio', 'id')
        )

    @staticmethod
    def a_resolver_de_titular(usuario_id, hoy):
        return list(
            Reserva.objects.filter(usuario_id=usuario_id, estado__in=ESTADOS_RESERVA_A_RESOLVER, fecha_turno__gte=hoy)
            .values('fecha_turno', 'hora_inicio', 'estado')
        )

    @staticmethod
    def limpiar_contactos_de_bajas_hasta(fecha_limite):
        """
        Borra el nombre y el teléfono copiados de un titular dado de baja en reservas cuyo turno fue hace más de
        30 días (PROJECT.md §13.2). Es un UPDATE: la fila de la reserva se conserva.
        """
        return Reserva.objects.filter(
            usuario__estado=EstadoUsuario.BAJA, fecha_turno__lt=fecha_limite,
        ).exclude(nombre_cliente_manual='', telefono_cliente_manual='').update(
            nombre_cliente_manual='', telefono_cliente_manual='', fecha_modificacion=timezone.now(),
        )

    @staticmethod
    def bloquear_cancha(cancha_id):
        """FOR UPDATE solo sobre la cancha: serializa las altas de reservas y turnos fijos que compiten por ella."""
        return (
            Cancha.objects.select_for_update(of=('self',)).select_related('complejo', 'deporte')
            .filter(id=cancha_id).first()
        )

    @staticmethod
    def bloquear(reserva_id):
        return (
            Reserva.objects.select_for_update(of=('self',))
            .select_related('cancha__complejo', 'cancha__deporte', 'usuario')
            .filter(id=reserva_id).exclude(estado=EstadoReserva.BAJA).first()
        )

    @staticmethod
    def crear(**campos):
        return Reserva.objects.create(**campos)

    @staticmethod
    def actualizar(reserva, **campos):
        for campo, valor in campos.items():
            setattr(reserva, campo, valor)
        reserva.save(update_fields=[*campos, 'fecha_modificacion'])
        return reserva

    @staticmethod
    def existe_fecha_de_turno_fijo(turno_fijo_id, fecha):
        return ReservaRepository._vigentes().filter(turno_fijo_id=turno_fijo_id, fecha_turno=fecha).exists()

    @staticmethod
    def fechas_generadas(turno_fijo_ids, desde):
        """(turno_fijo_id, fecha) que ya tienen su reserva generada, en cualquier estado salvo la baja lógica."""
        return set(
            ReservaRepository._vigentes().filter(turno_fijo_id__in=turno_fijo_ids, fecha_turno__gte=desde)
            .values_list('turno_fijo_id', 'fecha_turno')
        )

    @staticmethod
    def fechas_a_resolver_de_turno_fijo(turno_fijo_id, desde):
        return list(
            Reserva.objects.filter(
                turno_fijo_id=turno_fijo_id, fecha_turno__gte=desde, estado__in=ESTADOS_RESERVA_A_RESOLVER,
            ).order_by('fecha_turno').values('id', 'fecha_turno', 'estado')
        )

    @staticmethod
    def primera_ocupante_en_dia_de_semana(cancha_id, dia_semana, inicio, fin, desde, hasta, excluir_turno_fijo_id=None):
        """Primera reserva ocupante de ese día de la semana y horario en [desde, hasta]; hasta nulo es sin fin."""
        reservas = Reserva.objects.filter(
            cancha_id=cancha_id,
            estado__in=ESTADOS_RESERVA_OCUPANTES,
            fecha_turno__gte=desde,
            fecha_turno__iso_week_day=dia_semana + 1,
            hora_inicio__lt=fin,
            hora_fin__gt=inicio,
        )
        if hasta is not None:
            reservas = reservas.filter(fecha_turno__lte=hasta)
        if excluir_turno_fijo_id is not None:
            reservas = reservas.exclude(turno_fijo_id=excluir_turno_fijo_id)
        return reservas.order_by('fecha_turno', 'hora_inicio').values('fecha_turno', 'hora_inicio').first()


class TurnoFijoRepository:
    @staticmethod
    def vigentes():
        return (
            TurnoFijo.objects.exclude(estado=EstadoTurnoFijo.BAJA)
            .select_related('cancha__complejo', 'usuario')
            .prefetch_related(HorarioAperturaRepository.prefetch_activos('cancha__'))
            .order_by('cancha_id', 'dia_semana', 'hora_inicio', 'id')
        )

    @staticmethod
    def activos_de_cancha(cancha_id, hoy):
        """Vigentes y pausados que siguen en vigencia: un pausado puede reanudarse."""
        return list(
            TurnoFijo.objects.filter(
                Q(fecha_fin_vigencia__isnull=True) | Q(fecha_fin_vigencia__gte=hoy),
                cancha_id=cancha_id, estado__in=ESTADOS_TURNO_FIJO_ACTIVOS,
            ).order_by('dia_semana', 'hora_inicio', 'id').values('id', 'dia_semana', 'hora_inicio', 'hora_fin')
        )

    @staticmethod
    def con_excepcion_que_los_alcanza(queryset, hoy):
        """
        Prefiltro en SQL de los turnos fijos que pueden tener fechas en espera: vigentes y con alguna excepción activa
        del complejo (global o de su cancha) que no terminó, se cruza con su vigencia y cubre su horario. El cálculo
        exacto (día de la semana dentro del cruce y fechas ya registradas) se hace en Python solo sobre estos.
        """
        alcanza = ExcepcionHoraria.objects.filter(
            Q(cancha__isnull=True) | Q(cancha_id=OuterRef('cancha_id')),
            Q(es_dia_completo=AlcanceExcepcion.DIA_COMPLETO)
            | Q(hora_inicio__lt=OuterRef('hora_fin'), hora_fin__gt=OuterRef('hora_inicio')),
            complejo_id=OuterRef('cancha__complejo_id'),
            estado=EstadoRegistro.ACTIVO,
            fecha_fin__gte=hoy,
            fecha_inicio__lte=OuterRef('fin_de_vigencia'),
        ).filter(fecha_fin__gte=OuterRef('fecha_inicio_vigencia'))
        return (
            queryset.filter(estado=EstadoTurnoFijo.VIGENTE)
            .annotate(fin_de_vigencia=Coalesce('fecha_fin_vigencia', Value(date.max)))
            .filter(Exists(alcanza))
        )

    @staticmethod
    def alcanzados_por(excepcion):
        """Turnos fijos vigentes que una excepción puede dejar en espera (mismo complejo, cancha, fechas y horario)."""
        turnos = TurnoFijo.objects.filter(
            Q(fecha_fin_vigencia__isnull=True) | Q(fecha_fin_vigencia__gte=excepcion.fecha_inicio),
            cancha__complejo_id=excepcion.complejo_id,
            estado=EstadoTurnoFijo.VIGENTE,
            fecha_inicio_vigencia__lte=excepcion.fecha_fin,
        )
        if excepcion.cancha_id is not None:
            turnos = turnos.filter(cancha_id=excepcion.cancha_id)
        if excepcion.es_dia_completo != AlcanceExcepcion.DIA_COMPLETO:
            turnos = turnos.filter(hora_inicio__lt=excepcion.hora_fin, hora_fin__gt=excepcion.hora_inicio)
        return list(turnos.select_related('cancha'))

    @staticmethod
    def bloquear_activos_de_titular(usuario_id):
        return list(
            TurnoFijo.objects.select_for_update(of=('self',)).select_related('cancha')
            .filter(usuario_id=usuario_id, estado__in=ESTADOS_TURNO_FIJO_ACTIVOS).order_by('id')
        )

    @staticmethod
    def cantidad_activos_de_titular(usuario_id):
        return TurnoFijo.objects.filter(usuario_id=usuario_id, estado__in=ESTADOS_TURNO_FIJO_ACTIVOS).count()

    @staticmethod
    def que_aplican_en(queryset, fecha):
        """Turnos fijos cuyo día de la semana y vigencia incluyen la fecha."""
        return queryset.filter(
            Q(fecha_fin_vigencia__isnull=True) | Q(fecha_fin_vigencia__gte=fecha),
            dia_semana=fecha.weekday(),
            fecha_inicio_vigencia__lte=fecha,
        )

    @staticmethod
    def bloquear(turno_fijo_id):
        return (
            TurnoFijo.objects.select_for_update(of=('self',)).select_related('cancha__complejo', 'usuario')
            .filter(id=turno_fijo_id).exclude(estado=EstadoTurnoFijo.BAJA).first()
        )

    @staticmethod
    def solapados(cancha_id, dia_semana, inicio, fin, desde, hasta, excluir_id=None):
        """Turnos fijos vigentes de la cancha, mismo día y horario superpuesto, cuya vigencia toca [desde, hasta]."""
        turnos = TurnoFijo.objects.filter(
            Q(fecha_fin_vigencia__isnull=True) | Q(fecha_fin_vigencia__gte=desde),
            cancha_id=cancha_id,
            dia_semana=dia_semana,
            estado=EstadoTurnoFijo.VIGENTE,
            hora_inicio__lt=fin,
            hora_fin__gt=inicio,
        )
        if hasta is not None:
            turnos = turnos.filter(fecha_inicio_vigencia__lte=hasta)
        if excluir_id is not None:
            turnos = turnos.exclude(id=excluir_id)
        return list(
            turnos.order_by('fecha_inicio_vigencia', 'id').values(
                'hora_inicio', 'hora_fin', 'fecha_inicio_vigencia', 'fecha_fin_vigencia',
            )
        )

    @staticmethod
    def crear(**campos):
        return TurnoFijo.objects.create(**campos)

    @staticmethod
    def actualizar(turno_fijo, **campos):
        for campo, valor in campos.items():
            setattr(turno_fijo, campo, valor)
        turno_fijo.save(update_fields=[*campos, 'fecha_modificacion'])
        return turno_fijo


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
