from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class EstadoRegistro(models.IntegerChoices):
    BAJA = 0, 'Baja lógica'
    ACTIVO = 1, 'Activo'


class ModeloBase(models.Model):
    estado = models.SmallIntegerField(
        choices=EstadoRegistro.choices,
        default=EstadoRegistro.ACTIVO,
        db_index=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_index=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def desactivar(self):
        self.estado = EstadoRegistro.BAJA
        self.save(update_fields=['estado', 'fecha_modificacion'])


class EstadoUsuario(models.IntegerChoices):
    BAJA = 0, 'Baja lógica'
    ACTIVO = 1, 'Activo'
    SUSPENDIDO = 2, 'Suspendido'


class EstadoCancha(models.IntegerChoices):
    BAJA = 0, 'Baja lógica'
    ACTIVA = 1, 'Activa'
    EN_MANTENIMIENTO = 2, 'En mantenimiento'


class EstadoTurnoFijo(models.IntegerChoices):
    BAJA = 0, 'Baja lógica'
    VIGENTE = 1, 'Vigente'
    PAUSADO = 2, 'Pausado'


class AlcanceExcepcion(models.IntegerChoices):
    FRANJA_HORARIA = 0, 'Franja horaria'
    DIA_COMPLETO = 1, 'Día completo'


class EstadoContrato(models.IntegerChoices):
    BAJA = 0, 'Baja'
    PENDIENTE = 1, 'Pendiente'
    ACTIVO = 2, 'Activo'
    SUSPENDIDO = 3, 'Suspendido'


class TipoSuperficie(models.IntegerChoices):
    CESPED_SINTETICO = 1, 'Césped sintético'
    CESPED_NATURAL = 2, 'Césped natural'
    CEMENTO = 3, 'Cemento'
    PARQUET = 4, 'Parquet'
    POLVO_LADRILLO = 5, 'Polvo de ladrillo'
    ARENA = 6, 'Arena'


class Cobertura(models.IntegerChoices):
    DESCUBIERTA = 1, 'Descubierta'
    TECHADA = 2, 'Techada'
    SEMICUBIERTA = 3, 'Semicubierta'


class Iluminacion(models.IntegerChoices):
    SIN_ILUMINACION = 1, 'Sin iluminación'
    HALOGENA = 2, 'Halógena'
    LED = 3, 'LED'


class DuracionTurno(models.IntegerChoices):
    SESENTA = 60, '60 minutos'
    NOVENTA = 90, '90 minutos'
    CIENTO_VEINTE = 120, '120 minutos'


class DiaSemana(models.IntegerChoices):
    LUNES = 0, 'Lunes'
    MARTES = 1, 'Martes'
    MIERCOLES = 2, 'Miércoles'
    JUEVES = 3, 'Jueves'
    VIERNES = 4, 'Viernes'
    SABADO = 5, 'Sábado'
    DOMINGO = 6, 'Domingo'


class TipoMotivoExcepcion(models.IntegerChoices):
    MANTENIMIENTO = 1, 'Mantenimiento'
    CLIMA = 2, 'Condiciones climáticas'
    FERIADO = 3, 'Feriado'
    EVENTO_PRIVADO = 4, 'Evento privado'
    CORTE_SERVICIO = 5, 'Corte de servicio'
    OTRO = 6, 'Otro'


class EstadoReserva(models.IntegerChoices):
    BAJA = 0, 'Baja lógica'
    PENDIENTE = 1, 'Pendiente Seña'
    CONFIRMADA = 2, 'Confirmada'
    SENADA = 3, 'Señada/Pagada'
    CANCELADA_JUGADOR = 4, 'Cancelada por el jugador'
    CANCELADA_COMPLEJO = 5, 'Cancelada por el complejo'
    AUSENTE = 6, 'Ausente'
    COMPLETADA = 7, 'Completada'


class TipoOcupacion(models.IntegerChoices):
    WEB = 1, 'Reserva web del jugador'
    MANUAL = 2, 'Reserva manual (telefónica o presencial)'
    TURNO_FIJO = 3, 'Turno fijo'


class TipoEventoAuditoria(models.IntegerChoices):
    LOGIN_EXITOSO = 1, 'Inicio de sesión exitoso'
    LOGIN_FALLIDO = 2, 'Inicio de sesión fallido'
    LOGOUT = 3, 'Cierre de sesión'
    ACCESO_DENEGADO = 4, 'Acceso denegado (403)'
    LIMITE_PETICIONES = 5, 'Límite de peticiones superado (429)'
    REGISTRO_USUARIO = 6, 'Registro de usuario'
    BAJA_USUARIO = 7, 'Baja lógica de usuario'
    CAMBIO_CONTRATO = 8, 'Cambio de contrato de complejo'
    ALTA_EXCEPCION = 9, 'Alta de excepción horaria'
    BAJA_EXCEPCION = 10, 'Baja de excepción horaria'
    RESERVA_CREADA = 11, 'Reserva creada'
    RESERVA_CANCELADA = 12, 'Reserva cancelada'
    RESERVA_CAMBIO_ESTADO = 13, 'Cambio de estado de reserva'
    CAMBIO_CONFIGURACION = 14, 'Cambio de configuración del complejo'


class Rol(ModeloBase):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'rol'
        verbose_name_plural = 'roles'
        ordering = ['id']

    def __str__(self):
        return self.nombre


class Permiso(ModeloBase):
    codigo = models.CharField(max_length=60, unique=True)
    nombre = models.CharField(max_length=100)
    modulo = models.CharField(max_length=50)

    class Meta:
        db_table = 'permisos'
        verbose_name = 'permiso'
        verbose_name_plural = 'permisos'
        ordering = ['modulo', 'codigo']
        indexes = [
            models.Index(fields=['modulo', 'estado'], name='idx_permiso_modulo_estado'),
        ]

    def __str__(self):
        return self.codigo


class RolPermiso(ModeloBase):
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name='asignaciones')
    permiso = models.ForeignKey(Permiso, on_delete=models.PROTECT, related_name='asignaciones')

    class Meta:
        db_table = 'roles_permisos'
        verbose_name = 'asignación de permiso'
        verbose_name_plural = 'asignaciones de permisos'
        constraints = [
            models.UniqueConstraint(fields=['rol', 'permiso'], name='uq_rol_permiso'),
        ]
        indexes = [
            models.Index(fields=['rol', 'estado'], name='idx_rolperm_rol_estado'),
        ]

    def __str__(self):
        return f'{self.rol} -> {self.permiso}'


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, email, password, rol, **campos):
        if not email:
            raise ValueError('El email es obligatorio.')
        usuario = self.model(email=self.normalize_email(email).lower(), rol=rol, **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, rol=None, **campos):
        if rol is None:
            rol, _ = Rol.objects.get_or_create(nombre='JUGADOR')
        return self._crear(email, password, rol, **campos)

    def create_superuser(self, email, password=None, **campos):
        rol, _ = Rol.objects.get_or_create(nombre='SUPERADMIN')
        return self._crear(email, password, rol, **campos)


class Usuario(AbstractBaseUser, ModeloBase):
    estado = models.SmallIntegerField(
        choices=EstadoUsuario.choices,
        default=EstadoUsuario.ACTIVO,
        db_index=True,
    )
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name='usuarios')
    nombre_completo = models.CharField(max_length=120)
    email = models.EmailField(max_length=120, unique=True)
    telefono = models.CharField(max_length=30, blank=True)
    complejo_operado = models.ForeignKey(
        'Complejo',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='operadores',
    )

    last_login = None

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        indexes = [
            models.Index(fields=['rol', 'estado'], name='idx_usuario_rol_estado'),
            models.Index(fields=['complejo_operado', 'estado'], name='idx_usuario_complejo_operado'),
        ]

    def __str__(self):
        return f'{self.nombre_completo} <{self.email}>'

    @property
    def is_active(self):
        return self.estado == EstadoUsuario.ACTIVO

    @property
    def es_superadmin(self):
        return self.rol_id is not None and self.rol.nombre == 'SUPERADMIN'

    @property
    def is_staff(self):
        return self.es_superadmin

    @property
    def is_superuser(self):
        return self.es_superadmin

    def has_perm(self, perm, obj=None):
        return self.is_active and self.es_superadmin

    def has_module_perms(self, app_label):
        return self.is_active and self.es_superadmin

    def get_full_name(self):
        return self.nombre_completo

    def get_short_name(self):
        return self.nombre_completo.split(' ')[0]


class Complejo(ModeloBase):
    propietario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='complejos_propios')
    nombre = models.CharField(max_length=120)
    direccion = models.CharField(max_length=160)
    latitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    telefono_contacto = models.CharField(max_length=30, blank=True)
    horas_limite_cancelacion = models.SmallIntegerField(default=4)
    info_sena = models.CharField(max_length=200, blank=True)
    estado_contrato = models.SmallIntegerField(
        choices=EstadoContrato.choices,
        default=EstadoContrato.PENDIENTE,
    )

    class Meta:
        db_table = 'complejos'
        verbose_name = 'complejo'
        verbose_name_plural = 'complejos'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['estado', 'estado_contrato'], name='idx_complejo_estados'),
            models.Index(fields=['propietario', 'estado'], name='idx_complejo_propietario'),
            models.Index(fields=['nombre'], name='idx_complejo_nombre'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(horas_limite_cancelacion__gte=0),
                name='ck_complejo_horas_limite',
            ),
        ]

    def __str__(self):
        return self.nombre


class Servicio(ModeloBase):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        db_table = 'servicios'
        verbose_name = 'servicio'
        verbose_name_plural = 'servicios'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ComplejoServicio(ModeloBase):
    complejo = models.ForeignKey(Complejo, on_delete=models.PROTECT, related_name='servicios_ofrecidos')
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='ofrecido_en')

    class Meta:
        db_table = 'complejos_servicios'
        verbose_name = 'servicio del complejo'
        verbose_name_plural = 'servicios de complejos'
        constraints = [
            models.UniqueConstraint(fields=['complejo', 'servicio'], name='uq_complejo_servicio'),
        ]
        indexes = [
            models.Index(fields=['servicio', 'estado'], name='idx_cs_servicio_estado'),
        ]

    def __str__(self):
        return f'{self.complejo} - {self.servicio}'


class Deporte(ModeloBase):
    nombre = models.CharField(max_length=60, unique=True)

    class Meta:
        db_table = 'deportes'
        verbose_name = 'deporte'
        verbose_name_plural = 'deportes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Cancha(ModeloBase):
    estado = models.SmallIntegerField(
        choices=EstadoCancha.choices,
        default=EstadoCancha.ACTIVA,
        db_index=True,
    )
    complejo = models.ForeignKey(Complejo, on_delete=models.PROTECT, related_name='canchas')
    deporte = models.ForeignKey(Deporte, on_delete=models.PROTECT, related_name='canchas')
    nombre = models.CharField(max_length=80)
    tipo_superficie = models.SmallIntegerField(choices=TipoSuperficie.choices)
    cobertura = models.SmallIntegerField(choices=Cobertura.choices)
    iluminacion = models.SmallIntegerField(choices=Iluminacion.choices)
    duracion_turno_min = models.SmallIntegerField(
        choices=DuracionTurno.choices,
        default=DuracionTurno.SESENTA,
    )
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'canchas'
        verbose_name = 'cancha'
        verbose_name_plural = 'canchas'
        ordering = ['complejo_id', 'nombre']
        indexes = [
            models.Index(fields=['complejo', 'estado'], name='idx_cancha_complejo_estado'),
            models.Index(fields=['deporte', 'estado'], name='idx_cancha_deporte_estado'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['complejo', 'nombre'],
                condition=~Q(estado=0),
                name='uq_cancha_nombre_activa',
            ),
            models.CheckConstraint(condition=Q(precio_base__gte=0), name='ck_cancha_precio_base'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.complejo})'


class HorarioApertura(ModeloBase):
    cancha = models.ForeignKey(Cancha, on_delete=models.PROTECT, related_name='horarios')
    dia_semana = models.SmallIntegerField(choices=DiaSemana.choices)
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()
    # NULL indica que ese día se cobra el precio_base de la cancha.
    precio_diferenciado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'horarios_apertura'
        verbose_name = 'horario de apertura'
        verbose_name_plural = 'horarios de apertura'
        ordering = ['cancha_id', 'dia_semana']
        indexes = [
            models.Index(fields=['cancha', 'dia_semana', 'estado'], name='idx_horario_cancha_dia'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['cancha', 'dia_semana'],
                condition=~Q(estado=0),
                name='uq_horario_cancha_dia_activo',
            ),
            models.CheckConstraint(
                condition=Q(precio_diferenciado__isnull=True) | Q(precio_diferenciado__gte=0),
                name='ck_horario_precio_diferenciado',
            ),
            models.CheckConstraint(
                condition=Q(hora_cierre__gt=F('hora_apertura')),
                name='ck_horario_apertura_cierre',
            ),
        ]

    def __str__(self):
        return f'{self.cancha.nombre} {self.get_dia_semana_display()} {self.hora_apertura}-{self.hora_cierre}'


class ExcepcionHoraria(ModeloBase):
    complejo = models.ForeignKey(Complejo, on_delete=models.PROTECT, related_name='excepciones')
    # NULL indica una excepción global que afecta a todas las canchas del complejo.
    cancha = models.ForeignKey(
        Cancha,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='excepciones',
    )
    creado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='excepciones_creadas')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    es_dia_completo = models.SmallIntegerField(
        choices=AlcanceExcepcion.choices,
        default=AlcanceExcepcion.DIA_COMPLETO,
    )
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    tipo_motivo = models.SmallIntegerField(choices=TipoMotivoExcepcion.choices)
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'excepciones_horarias'
        verbose_name = 'excepción horaria'
        verbose_name_plural = 'excepciones horarias'
        ordering = ['fecha_inicio', 'hora_inicio']
        indexes = [
            models.Index(
                fields=['complejo', 'estado', 'fecha_inicio', 'fecha_fin'],
                name='idx_excepcion_complejo_rango',
            ),
            models.Index(
                fields=['cancha', 'estado', 'fecha_inicio', 'fecha_fin'],
                name='idx_excepcion_cancha_rango',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_fin__gte=F('fecha_inicio')),
                name='ck_excepcion_rango_fechas',
            ),
            models.CheckConstraint(
                condition=Q(es_dia_completo=AlcanceExcepcion.DIA_COMPLETO)
                | Q(hora_inicio__isnull=False, hora_fin__isnull=False, hora_fin__gt=F('hora_inicio')),
                name='ck_excepcion_franja_valida',
            ),
        ]

    def __str__(self):
        alcance = self.cancha.nombre if self.cancha_id else 'Todo el complejo'
        return f'{self.complejo} / {alcance}: {self.fecha_inicio} - {self.fecha_fin}'


class TurnoFijo(ModeloBase):
    estado = models.SmallIntegerField(
        choices=EstadoTurnoFijo.choices,
        default=EstadoTurnoFijo.VIGENTE,
        db_index=True,
    )
    cancha = models.ForeignKey(Cancha, on_delete=models.PROTECT, related_name='turnos_fijos')
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='turnos_fijos',
    )
    creado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='turnos_fijos_creados')
    nombre_cliente_manual = models.CharField(max_length=120, blank=True)
    telefono_cliente_manual = models.CharField(max_length=30, blank=True)
    dia_semana = models.SmallIntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    fecha_inicio_vigencia = models.DateField()
    # NULL indica un turno fijo sin fecha de finalización definida.
    fecha_fin_vigencia = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'turnos_fijos'
        verbose_name = 'turno fijo'
        verbose_name_plural = 'turnos fijos'
        ordering = ['cancha_id', 'dia_semana', 'hora_inicio']
        indexes = [
            models.Index(fields=['cancha', 'dia_semana', 'estado'], name='idx_turnofijo_cancha_dia'),
            models.Index(fields=['usuario', 'estado'], name='idx_turnofijo_usuario'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_fin_vigencia__isnull=True)
                | Q(fecha_fin_vigencia__gte=F('fecha_inicio_vigencia')),
                name='ck_turnofijo_vigencia',
            ),
            models.CheckConstraint(
                condition=Q(usuario__isnull=False) | ~Q(nombre_cliente_manual=''),
                name='ck_turnofijo_identifica_cliente',
            ),
            models.CheckConstraint(
                condition=Q(hora_fin__gt=F('hora_inicio')),
                name='ck_turnofijo_horario',
            ),
        ]

    def __str__(self):
        return f'{self.cancha} {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin}'


class Reserva(ModeloBase):
    estado = models.SmallIntegerField(
        choices=EstadoReserva.choices,
        default=EstadoReserva.PENDIENTE,
        db_index=True,
    )
    cancha = models.ForeignKey(Cancha, on_delete=models.PROTECT, related_name='reservas')
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reservas',
    )
    turno_fijo = models.ForeignKey(
        TurnoFijo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reservas',
    )
    creado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='reservas_creadas')
    nombre_cliente_manual = models.CharField(max_length=120, blank=True)
    telefono_cliente_manual = models.CharField(max_length=30, blank=True)
    fecha_turno = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    precio_acordado = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_ocupacion = models.SmallIntegerField(choices=TipoOcupacion.choices, default=TipoOcupacion.WEB)
    observaciones = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'reservas'
        verbose_name = 'reserva'
        verbose_name_plural = 'reservas'
        ordering = ['fecha_turno', 'hora_inicio']
        indexes = [
            models.Index(fields=['cancha', 'fecha_turno', 'estado'], name='idx_reserva_cancha_fecha'),
            models.Index(fields=['usuario', 'estado', 'fecha_turno'], name='idx_reserva_usuario'),
            models.Index(fields=['fecha_turno', 'estado'], name='idx_reserva_fecha_estado'),
            models.Index(fields=['fecha_modificacion'], name='idx_reserva_fecha_modif'),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(precio_acordado__gte=0), name='ck_reserva_precio'),
            models.CheckConstraint(
                condition=Q(usuario__isnull=False) | ~Q(nombre_cliente_manual=''),
                name='ck_reserva_identifica_cliente',
            ),
            models.CheckConstraint(
                condition=Q(hora_fin__gt=F('hora_inicio')),
                name='ck_reserva_horario',
            ),
            # Última defensa ante dos altas simultáneas del mismo turno; el solapamiento parcial lo valida el servicio.
            models.UniqueConstraint(
                fields=['cancha', 'fecha_turno', 'hora_inicio'],
                condition=Q(estado__in=[
                    EstadoReserva.PENDIENTE,
                    EstadoReserva.CONFIRMADA,
                    EstadoReserva.SENADA,
                    EstadoReserva.COMPLETADA,
                ]),
                name='uq_reserva_cancha_turno_activa',
            ),
        ]

    def __str__(self):
        return f'{self.cancha} {self.fecha_turno} {self.hora_inicio}-{self.hora_fin} [{self.get_estado_display()}]'


class LogAuditoria(ModeloBase):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='logs_auditoria',
    )
    complejo = models.ForeignKey(
        Complejo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='logs_auditoria',
    )
    tipo_evento = models.SmallIntegerField(choices=TipoEventoAuditoria.choices)
    accion = models.CharField(max_length=120)
    detalle = models.TextField(blank=True)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'logs_auditoria'
        verbose_name = 'log de auditoría'
        verbose_name_plural = 'logs de auditoría'
        # fecha_creacion es inmutable y marca el momento de la acción auditada.
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['tipo_evento', 'fecha_creacion'], name='idx_log_tipo_fecha'),
            models.Index(fields=['usuario', 'fecha_creacion'], name='idx_log_usuario_fecha'),
            models.Index(fields=['complejo', 'fecha_creacion'], name='idx_log_complejo_fecha'),
        ]

    def __str__(self):
        return f'[{self.get_tipo_evento_display()}] {self.accion}'
