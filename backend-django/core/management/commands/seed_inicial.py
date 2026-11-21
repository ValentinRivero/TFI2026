import os
from datetime import time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import (
    AlcanceExcepcion,
    Cancha,
    Cobertura,
    Complejo,
    ComplejoServicio,
    Deporte,
    DiaSemana,
    DuracionTurno,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    ExcepcionHoraria,
    HorarioApertura,
    Iluminacion,
    Permiso,
    Reserva,
    Rol,
    RolPermiso,
    Servicio,
    TipoMotivoExcepcion,
    TipoOcupacion,
    TipoSuperficie,
    TurnoFijo,
    Usuario,
)
from core.services import calcular_monto_sena

ROLES = {
    'SUPERADMIN': 'Administrador de la plataforma (Bombo Devs). Hereda las acciones de cualquier complejo.',
    'DUENO_COMPLEJO': 'Responsable del complejo: configuración, canchas, precios, agenda y reportes.',
    'OPERADOR_COMPLEJO': 'Personal del complejo: agenda diaria, reservas manuales, turnos fijos y excepciones.',
    'JUGADOR': 'Usuario final que consulta disponibilidad y reserva turnos.',
}

# codigo: (nombre, modulo)
PERMISOS = {
    'ver_perfil_propio': ('Ver el perfil propio', 'perfil'),
    'editar_perfil_propio': ('Editar los datos del perfil propio', 'perfil'),
    'desactivar_perfil_propio': ('Dar de baja la cuenta propia', 'perfil'),
    'reservar_turno': ('Reservar un turno como jugador', 'reservas'),
    'ver_reservas_propias': ('Consultar las reservas propias', 'reservas'),
    'cancelar_reserva_propia': ('Cancelar una reserva propia dentro del margen horario', 'reservas'),
    'ver_panel_complejo': ('Acceder al panel del complejo y ver su perfil', 'complejos'),
    'configurar_complejo': ('Editar el perfil y los servicios del complejo', 'complejos'),
    'ver_canchas': ('Ver las canchas, horarios y precios del complejo', 'canchas'),
    'administrar_canchas': ('Alta, modificación y baja lógica de canchas', 'canchas'),
    'administrar_horarios': ('Configurar los horarios de apertura', 'canchas'),
    'administrar_precios': ('Configurar el precio base y los precios diferenciados', 'canchas'),
    'ver_agenda': ('Ver la agenda de reservas del complejo', 'agenda'),
    'gestionar_agenda': ('Registrar reservas manuales y cambiar su estado', 'agenda'),
    'cancelar_reserva_complejo': ('Cancelar reservas del complejo sin restricción horaria', 'agenda'),
    'gestionar_turnos_fijos': ('Registrar, pausar y dar de baja turnos fijos', 'agenda'),
    'ver_excepciones': ('Ver las excepciones horarias del complejo', 'excepciones'),
    'gestionar_excepciones': ('Registrar y anular excepciones horarias', 'excepciones'),
    'ver_operadores': ('Ver los operadores del complejo', 'personal'),
    'gestionar_operadores': ('Asignar y quitar operadores del complejo', 'personal'),
    'ver_reportes': ('Consultar el dashboard y los reportes', 'reportes'),
    'ver_panel_sistema': ('Acceder al panel del sistema', 'sistema'),
    'ver_contratos': ('Ver los contratos de los complejos', 'sistema'),
    'administrar_contratos': ('Administrar los contratos de los complejos', 'sistema'),
    'ver_usuarios': ('Ver los perfiles de otros usuarios', 'sistema'),
    'editar_usuarios': ('Editar los perfiles de otros usuarios', 'sistema'),
    'desactivar_usuarios': ('Suspender o dar de baja a otros usuarios', 'sistema'),
    'administrar_catalogos': ('Administrar los catálogos de deportes y servicios', 'sistema'),
    'administrar_roles': ('Administrar los roles personalizados y consultar el catálogo de permisos', 'sistema'),
    'auditar_seguridad': ('Consultar la auditoría global del sistema', 'sistema'),
}

PERMISOS_PERFIL = [
    'ver_perfil_propio',
    'editar_perfil_propio',
    'desactivar_perfil_propio',
]

PERMISOS_JUGADOR = PERMISOS_PERFIL + [
    'reservar_turno',
    'ver_reservas_propias',
    'cancelar_reserva_propia',
]

PERMISOS_OPERADOR = PERMISOS_PERFIL + [
    'ver_panel_complejo',
    'ver_canchas',
    'ver_agenda',
    'gestionar_agenda',
    'cancelar_reserva_complejo',
    'gestionar_turnos_fijos',
    'ver_excepciones',
    'gestionar_excepciones',
]

# configurar_complejo edita parámetros comerciales (info_sena, horas_limite_cancelacion): no es del operador.
PERMISOS_DUENO = PERMISOS_OPERADOR + [
    'configurar_complejo',
    'administrar_canchas',
    'administrar_horarios',
    'administrar_precios',
    'ver_operadores',
    'gestionar_operadores',
    'ver_reportes',
]

ASIGNACIONES = {
    'SUPERADMIN': list(PERMISOS.keys()),
    'DUENO_COMPLEJO': PERMISOS_DUENO,
    'OPERADOR_COMPLEJO': PERMISOS_OPERADOR,
    'JUGADOR': PERMISOS_JUGADOR,
}

DEPORTES = ['Fútbol 5', 'Fútbol 7', 'Pádel', 'Vóley', 'Básquet', 'Tenis']

SERVICIOS = [
    'Estacionamiento',
    'Vestuarios',
    'Duchas',
    'Buffet',
    'Wi-Fi',
    'Parrilleros',
    'Alquiler de equipamiento',
    'Accesibilidad',
]

USUARIOS = [
    {'email': 'superadmin@demo.talibre.test', 'nombre_completo': 'Bombo Devs',
     'telefono': '3777 000100', 'rol': 'SUPERADMIN'},
    {'email': 'aurelio.quintana@demo.talibre.test', 'nombre_completo': 'Aurelio Quintana',
     'telefono': '3777 000201', 'rol': 'DUENO_COMPLEJO'},
    {'email': 'elias.mendieta@demo.talibre.test', 'nombre_completo': 'Elías Mendieta',
     'telefono': '3777 000202', 'rol': 'OPERADOR_COMPLEJO', 'complejo_operado': 'Complejo El Yacaré'},
    {'email': 'brenda.saucedo@demo.talibre.test', 'nombre_completo': 'Brenda Saucedo',
     'telefono': '3777 000203', 'rol': 'DUENO_COMPLEJO'},
    {'email': 'ciro.valdez@demo.talibre.test', 'nombre_completo': 'Ciro Valdez',
     'telefono': '3777 000204', 'rol': 'DUENO_COMPLEJO'},
    {'email': 'delfina.paredes@demo.talibre.test', 'nombre_completo': 'Delfina Paredes',
     'telefono': '3777 000205', 'rol': 'DUENO_COMPLEJO'},
    {'email': 'fabricio.medina@demo.talibre.test', 'nombre_completo': 'Fabricio Medina',
     'telefono': '3777 000206', 'rol': 'JUGADOR'},
    {'email': 'gisela.barrios@demo.talibre.test', 'nombre_completo': 'Gisela Barrios',
     'telefono': '3777 000207', 'rol': 'JUGADOR'},
    {'email': 'hugo.caceres@demo.talibre.test', 'nombre_completo': 'Hugo Cáceres',
     'telefono': '3777 000208', 'rol': 'JUGADOR'},
]

FIN_DE_SEMANA = (DiaSemana.SABADO, DiaSemana.DOMINGO)

COMPLEJOS = [
    {
        'nombre': 'Complejo El Yacaré',
        'propietario': 'aurelio.quintana@demo.talibre.test',
        'direccion': 'Av. del Ombú 1250, Goya, Corrientes',
        'latitud': Decimal('-29.145000'),
        'longitud': Decimal('-59.272500'),
        'telefono_contacto': '3777 000101',
        'horas_limite_cancelacion': 4,
        'info_sena': 'La seña se transfiere al alias del complejo y se descuenta del total.',
        'porcentaje_sena': 30,
        'alias_transferencia': 'YACARE.DEMO.SENA',
        'titular_transferencia': 'Yacaré Deportes S.R.L.',
        'estado_contrato': EstadoContrato.ACTIVO,
        'servicios': ['Estacionamiento', 'Vestuarios', 'Duchas', 'Buffet', 'Parrilleros'],
        'canchas': [
            {'nombre': 'Cancha 1', 'deporte': 'Fútbol 5', 'tipo_superficie': TipoSuperficie.CESPED_SINTETICO,
             'cobertura': Cobertura.DESCUBIERTA, 'iluminacion': Iluminacion.LED,
             'duracion_turno_min': DuracionTurno.SESENTA, 'precio_base': '38000.00',
             'apertura': time(14, 0), 'cierre': time(23, 0), 'precio_finde': '42000.00'},
            {'nombre': 'Cancha 2', 'deporte': 'Fútbol 5', 'tipo_superficie': TipoSuperficie.CESPED_SINTETICO,
             'cobertura': Cobertura.TECHADA, 'iluminacion': Iluminacion.LED,
             'duracion_turno_min': DuracionTurno.SESENTA, 'precio_base': '42000.00',
             'apertura': time(14, 0), 'cierre': time(23, 0), 'precio_finde': '46000.00'},
            {'nombre': 'Cancha 7', 'deporte': 'Fútbol 7', 'tipo_superficie': TipoSuperficie.CESPED_SINTETICO,
             'cobertura': Cobertura.DESCUBIERTA, 'iluminacion': Iluminacion.HALOGENA,
             'duracion_turno_min': DuracionTurno.SESENTA, 'precio_base': '56000.00',
             'apertura': time(16, 0), 'cierre': time(23, 0), 'precio_finde': None},
        ],
    },
    {
        'nombre': 'Pádel Ñandubay',
        'propietario': 'brenda.saucedo@demo.talibre.test',
        'direccion': 'Calle Los Aromos 860, Goya, Corrientes',
        'latitud': Decimal('-29.137500'),
        'longitud': Decimal('-59.258000'),
        'telefono_contacto': '3777 000102',
        'horas_limite_cancelacion': 12,
        'info_sena': 'Se reintegra cancelando con 12 horas de anticipación.',
        'porcentaje_sena': 50,
        'alias_transferencia': 'PADEL.NANDUBAY.DEMO',
        'titular_transferencia': 'Ñandubay Pádel',
        'estado_contrato': EstadoContrato.ACTIVO,
        'servicios': ['Estacionamiento', 'Vestuarios', 'Buffet', 'Wi-Fi', 'Alquiler de equipamiento'],
        'canchas': [
            {'nombre': f'Pádel {numero}', 'deporte': 'Pádel', 'tipo_superficie': TipoSuperficie.CESPED_SINTETICO,
             'cobertura': Cobertura.TECHADA if numero <= 2 else Cobertura.DESCUBIERTA,
             'iluminacion': Iluminacion.LED, 'duracion_turno_min': DuracionTurno.NOVENTA,
             'precio_base': '30000.00', 'apertura': time(8, 0), 'cierre': time(23, 0),
             'precio_finde': '34000.00'}
            for numero in range(1, 5)
        ],
    },
    {
        'nombre': 'Polideportivo Los Timbós',
        'propietario': 'ciro.valdez@demo.talibre.test',
        'direccion': 'Pasaje Los Jacarandaes 1540, Goya, Corrientes',
        'latitud': Decimal('-29.153500'),
        'longitud': Decimal('-59.265000'),
        'telefono_contacto': '3777 000103',
        'horas_limite_cancelacion': 4,
        'info_sena': '',
        'porcentaje_sena': 0,
        'alias_transferencia': '',
        'titular_transferencia': '',
        'estado_contrato': EstadoContrato.ACTIVO,
        'servicios': ['Vestuarios', 'Duchas', 'Accesibilidad', 'Wi-Fi'],
        'canchas': [
            {'nombre': 'Estadio Cubierto', 'deporte': 'Básquet', 'tipo_superficie': TipoSuperficie.PARQUET,
             'cobertura': Cobertura.TECHADA, 'iluminacion': Iluminacion.LED,
             'duracion_turno_min': DuracionTurno.CIENTO_VEINTE, 'precio_base': '45000.00',
             'apertura': time(9, 0), 'cierre': time(23, 0), 'precio_finde': None},
            {'nombre': 'Vóley Playa', 'deporte': 'Vóley', 'tipo_superficie': TipoSuperficie.ARENA,
             'cobertura': Cobertura.DESCUBIERTA, 'iluminacion': Iluminacion.HALOGENA,
             'duracion_turno_min': DuracionTurno.SESENTA, 'precio_base': '15000.00',
             'apertura': time(9, 0), 'cierre': time(22, 0), 'precio_finde': None},
        ],
    },
    {
        'nombre': 'Club Mburucuyá',
        'propietario': 'delfina.paredes@demo.talibre.test',
        'direccion': 'Av. de los Tarumás 2100, Goya, Corrientes',
        'latitud': Decimal('-29.161000'),
        'longitud': Decimal('-59.280000'),
        'telefono_contacto': '3777 000104',
        'horas_limite_cancelacion': 4,
        'info_sena': '',
        'porcentaje_sena': 0,
        'alias_transferencia': '',
        'titular_transferencia': '',
        'estado_contrato': EstadoContrato.PENDIENTE,
        'servicios': ['Estacionamiento', 'Vestuarios'],
        'canchas': [
            {'nombre': 'Tenis 1', 'deporte': 'Tenis', 'tipo_superficie': TipoSuperficie.POLVO_LADRILLO,
             'cobertura': Cobertura.DESCUBIERTA, 'iluminacion': Iluminacion.SIN_ILUMINACION,
             'duracion_turno_min': DuracionTurno.SESENTA, 'precio_base': '18000.00',
             'apertura': time(8, 0), 'cierre': time(20, 0), 'precio_finde': None},
        ],
    },
]

def _proximo_dia_semana(desde, dia_semana):
    """Primera fecha igual o posterior a `desde` que cae en `dia_semana` (0 = lunes, igual que `date.weekday()`)."""
    return desde + timedelta(days=(dia_semana - desde.weekday()) % 7)


# La agenda de demostración se calcula respecto de la fecha de la carga, así la base siempre muestra turnos próximos.
# Los cierres por excepción caen después de todas las reservas y turnos fijos del mismo complejo, para que la
# agenda de muestra no tenga turnos dentro de un día cerrado.
def _excepciones(hoy):
    return [
        {'complejo': 'Complejo El Yacaré', 'cancha': None, 'creado_por': 'aurelio.quintana@demo.talibre.test',
         'fecha_inicio': hoy + timedelta(days=25), 'fecha_fin': hoy + timedelta(days=25),
         'es_dia_completo': AlcanceExcepcion.DIA_COMPLETO, 'hora_inicio': None, 'hora_fin': None,
         'tipo_motivo': TipoMotivoExcepcion.FERIADO, 'descripcion': 'Cierre por jornada feriada'},
        {'complejo': 'Complejo El Yacaré', 'cancha': 'Cancha 2', 'creado_por': 'elias.mendieta@demo.talibre.test',
         'fecha_inicio': hoy + timedelta(days=1), 'fecha_fin': hoy + timedelta(days=1),
         'es_dia_completo': AlcanceExcepcion.FRANJA_HORARIA, 'hora_inicio': time(14, 0), 'hora_fin': time(17, 0),
         'tipo_motivo': TipoMotivoExcepcion.MANTENIMIENTO, 'descripcion': 'Recambio de red y cepillado del césped'},
        {'complejo': 'Pádel Ñandubay', 'cancha': None, 'creado_por': 'brenda.saucedo@demo.talibre.test',
         'fecha_inicio': hoy + timedelta(days=15), 'fecha_fin': hoy + timedelta(days=16),
         'es_dia_completo': AlcanceExcepcion.DIA_COMPLETO, 'hora_inicio': None, 'hora_fin': None,
         'tipo_motivo': TipoMotivoExcepcion.FERIADO, 'descripcion': 'Cierre por festividades'},
        {'complejo': 'Polideportivo Los Timbós', 'cancha': 'Estadio Cubierto',
         'creado_por': 'ciro.valdez@demo.talibre.test', 'fecha_inicio': hoy + timedelta(days=4),
         'fecha_fin': hoy + timedelta(days=4), 'es_dia_completo': AlcanceExcepcion.FRANJA_HORARIA,
         'hora_inicio': time(9, 0), 'hora_fin': time(15, 0), 'tipo_motivo': TipoMotivoExcepcion.EVENTO_PRIVADO,
         'descripcion': 'Encuentro escolar de minibásquet'},
    ]


def _turnos_fijos(hoy):
    primer_martes = _proximo_dia_semana(hoy, DiaSemana.MARTES)
    primer_jueves = _proximo_dia_semana(hoy, DiaSemana.JUEVES)
    return [
        {'complejo': 'Complejo El Yacaré', 'cancha': 'Cancha 1', 'usuario': None,
         'creado_por': 'elias.mendieta@demo.talibre.test',
         'nombre_cliente_manual': 'Los del Martes (Ignacio Ferreyra)', 'telefono_cliente_manual': '3777 000301',
         'dia_semana': DiaSemana.MARTES, 'hora_inicio': time(21, 0), 'hora_fin': time(22, 0),
         'fecha_inicio_vigencia': primer_martes, 'fecha_fin_vigencia': primer_martes + timedelta(days=28),
         'reservas': [primer_martes + timedelta(days=7 * semana) for semana in range(3)]},
        {'complejo': 'Pádel Ñandubay', 'cancha': 'Pádel 2', 'usuario': 'gisela.barrios@demo.talibre.test',
         'creado_por': 'brenda.saucedo@demo.talibre.test', 'nombre_cliente_manual': '',
         'telefono_cliente_manual': '', 'dia_semana': DiaSemana.JUEVES, 'hora_inicio': time(20, 0),
         'hora_fin': time(21, 30), 'fecha_inicio_vigencia': primer_jueves, 'fecha_fin_vigencia': None,
         'reservas': [primer_jueves + timedelta(days=7 * semana) for semana in range(2)]},
    ]


# Ninguna reserva suelta de la cancha 1 usa el turno de las 21:00: lo ocupa el turno fijo de los martes.
def _reservas(hoy):
    return [
        {'complejo': 'Complejo El Yacaré', 'cancha': 'Cancha 1', 'fecha_turno': hoy + timedelta(days=3),
         'hora_inicio': time(20, 0), 'hora_fin': time(21, 0), 'usuario': 'fabricio.medina@demo.talibre.test',
         'creado_por': 'fabricio.medina@demo.talibre.test', 'tipo_ocupacion': TipoOcupacion.WEB,
         'estado': EstadoReserva.CONFIRMADA, 'precio_acordado': '38000.00'},
        {'complejo': 'Complejo El Yacaré', 'cancha': 'Cancha 1', 'fecha_turno': hoy + timedelta(days=3),
         'hora_inicio': time(19, 0), 'hora_fin': time(20, 0), 'usuario': None,
         'creado_por': 'elias.mendieta@demo.talibre.test', 'nombre_cliente_manual': 'Julián Ríos',
         'telefono_cliente_manual': '3777 000302', 'tipo_ocupacion': TipoOcupacion.MANUAL,
         'estado': EstadoReserva.SENADA, 'precio_acordado': '38000.00', 'pago': 'sena',
         'observaciones': 'Seña de $11.400 recibida por transferencia'},
        {'complejo': 'Complejo El Yacaré', 'cancha': 'Cancha 2', 'fecha_turno': hoy + timedelta(days=2),
         'hora_inicio': time(19, 0), 'hora_fin': time(20, 0), 'usuario': 'gisela.barrios@demo.talibre.test',
         'creado_por': 'gisela.barrios@demo.talibre.test', 'tipo_ocupacion': TipoOcupacion.WEB,
         'estado': EstadoReserva.CANCELADA_JUGADOR, 'precio_acordado': '42000.00'},
        {'complejo': 'Complejo El Yacaré', 'cancha': 'Cancha 7', 'fecha_turno': hoy - timedelta(days=4),
         'hora_inicio': time(21, 0), 'hora_fin': time(22, 0), 'usuario': 'hugo.caceres@demo.talibre.test',
         'creado_por': 'hugo.caceres@demo.talibre.test', 'tipo_ocupacion': TipoOcupacion.WEB,
         'estado': EstadoReserva.COMPLETADA, 'precio_acordado': '56000.00', 'pago': 'total'},
        {'complejo': 'Complejo El Yacaré', 'cancha': 'Cancha 7', 'fecha_turno': hoy - timedelta(days=3),
         'hora_inicio': time(20, 0), 'hora_fin': time(21, 0), 'usuario': 'fabricio.medina@demo.talibre.test',
         'creado_por': 'fabricio.medina@demo.talibre.test', 'tipo_ocupacion': TipoOcupacion.WEB,
         'estado': EstadoReserva.AUSENTE, 'precio_acordado': '56000.00'},
        {'complejo': 'Pádel Ñandubay', 'cancha': 'Pádel 1', 'fecha_turno': hoy + timedelta(days=3),
         'hora_inicio': time(18, 30), 'hora_fin': time(20, 0), 'usuario': 'gisela.barrios@demo.talibre.test',
         'creado_por': 'gisela.barrios@demo.talibre.test', 'tipo_ocupacion': TipoOcupacion.WEB,
         'estado': EstadoReserva.SENADA, 'precio_acordado': '30000.00', 'pago': 'sena'},
        {'complejo': 'Pádel Ñandubay', 'cancha': 'Pádel 3', 'fecha_turno': hoy + timedelta(days=4),
         'hora_inicio': time(9, 30), 'hora_fin': time(11, 0), 'usuario': None,
         'creado_por': 'brenda.saucedo@demo.talibre.test', 'nombre_cliente_manual': 'Karina Molina',
         'telefono_cliente_manual': '3777 000303', 'tipo_ocupacion': TipoOcupacion.MANUAL,
         'estado': EstadoReserva.PENDIENTE, 'precio_acordado': '34000.00'},
        {'complejo': 'Polideportivo Los Timbós', 'cancha': 'Estadio Cubierto', 'fecha_turno': hoy + timedelta(days=5),
         'hora_inicio': time(17, 0), 'hora_fin': time(19, 0), 'usuario': 'hugo.caceres@demo.talibre.test',
         'creado_por': 'hugo.caceres@demo.talibre.test', 'tipo_ocupacion': TipoOcupacion.WEB,
         'estado': EstadoReserva.CONFIRMADA, 'precio_acordado': '45000.00'},
    ]


class Command(BaseCommand):
    help = (
        'Carga roles, permisos RBAC, deportes, servicios y datos de demostración de Goya. Es idempotente: la agenda '
        'de muestra (excepciones, turnos fijos y reservas) solo se crea junto con su complejo, así que repetir el '
        'comando nunca duplica turnos ni pisa los que se cargaron después.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--sin-demo',
            action='store_true',
            help='Carga solo los catálogos base (roles, permisos, deportes y servicios).',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help=(
                'Da de baja lógica la agenda de los complejos de demostración (excepciones, turnos fijos y reservas, '
                'también las cargadas después) y la vuelve a generar con fechas relativas a hoy.'
            ),
        )
        parser.add_argument(
            '--actualizar-claves',
            action='store_true',
            help=(
                'Reemplaza por SEED_PASSWORD_DEMO la clave de las cuentas de demostración que ya existen. '
                'Sin esta opción, una cuenta existente conserva la suya.'
            ),
        )

    def handle(self, *args, **opciones):
        if opciones['sin_demo'] and (opciones['reset'] or opciones['actualizar_claves']):
            raise CommandError('--reset y --actualizar-claves operan sobre los datos de demostración: no se combinan con --sin-demo.')

        hoy = timezone.localdate()
        with transaction.atomic():
            roles = self._cargar_roles()
            permisos = self._cargar_permisos()
            self._asignar_permisos(roles, permisos)
            deportes = self._cargar_deportes()
            servicios = self._cargar_servicios()

            if not opciones['sin_demo']:
                password = os.environ.get('SEED_PASSWORD_DEMO')
                if not password:
                    raise CommandError(
                        'Definí SEED_PASSWORD_DEMO en el .env para crear los usuarios de demostración '
                        'o ejecutá el comando con --sin-demo.'
                    )
                usuarios = self._cargar_usuarios(roles, password, opciones['actualizar_claves'])
                canchas, complejos_nuevos = self._cargar_complejos(usuarios, deportes, servicios)
                self._vincular_operadores(usuarios)
                if opciones['reset']:
                    self._dar_de_baja_agenda()
                    complejos_nuevos = {datos['nombre'] for datos in COMPLEJOS}
                self._cargar_excepciones(canchas, usuarios, hoy, complejos_nuevos)
                self._cargar_turnos_fijos(canchas, usuarios, hoy, complejos_nuevos)
                self._cargar_reservas(canchas, usuarios, hoy, complejos_nuevos)

        self._resumen()

    def _cargar_roles(self):
        roles = {}
        for nombre, descripcion in ROLES.items():
            rol, _ = Rol.objects.update_or_create(nombre=nombre, defaults={'descripcion': descripcion})
            roles[nombre] = rol
        return roles

    def _cargar_permisos(self):
        permisos = {}
        for codigo, (nombre, modulo) in PERMISOS.items():
            permiso, _ = Permiso.objects.update_or_create(
                codigo=codigo,
                defaults={'nombre': nombre, 'modulo': modulo},
            )
            permisos[codigo] = permiso
        return permisos

    def _asignar_permisos(self, roles, permisos):
        for nombre_rol, codigos in ASIGNACIONES.items():
            rol = roles[nombre_rol]
            for codigo in codigos:
                asignacion, _ = RolPermiso.objects.get_or_create(rol=rol, permiso=permisos[codigo])
                if asignacion.estado != EstadoRegistro.ACTIVO:
                    asignacion.estado = EstadoRegistro.ACTIVO
                    asignacion.save(update_fields=['estado', 'fecha_modificacion'])

            # Sincroniza bases donde ya se había corrido el seed: lo que ya no corresponde queda con baja lógica.
            sobrantes = RolPermiso.objects.filter(rol=rol, estado=EstadoRegistro.ACTIVO).exclude(
                permiso__codigo__in=codigos
            )
            for asignacion in sobrantes:
                asignacion.desactivar()

    def _cargar_deportes(self):
        return {nombre: Deporte.objects.get_or_create(nombre=nombre)[0] for nombre in DEPORTES}

    def _cargar_servicios(self):
        return {nombre: Servicio.objects.get_or_create(nombre=nombre)[0] for nombre in SERVICIOS}

    def _cargar_usuarios(self, roles, password, actualizar_claves=False):
        usuarios = {}
        for datos in USUARIOS:
            usuario = Usuario.objects.filter(email=datos['email']).first()
            if usuario is None:
                usuario = Usuario.objects.create_user(
                    email=datos['email'],
                    password=password,
                    rol=roles[datos['rol']],
                    nombre_completo=datos['nombre_completo'],
                    telefono=datos['telefono'],
                )
            elif actualizar_claves:
                usuario.set_password(password)
                usuario.save(update_fields=['password', 'fecha_modificacion'])
            usuarios[usuario.email] = usuario
        return usuarios

    def _cargar_complejos(self, usuarios, deportes, servicios):
        canchas = {}
        complejos_nuevos = set()
        campos_complejo = (
            'direccion', 'latitud', 'longitud', 'telefono_contacto',
            'horas_limite_cancelacion', 'info_sena', 'porcentaje_sena', 'alias_transferencia',
            'titular_transferencia', 'estado_contrato',
        )

        for datos in COMPLEJOS:
            complejo, creado = Complejo.objects.get_or_create(
                nombre=datos['nombre'],
                defaults={
                    'propietario': usuarios[datos['propietario']],
                    **{campo: datos[campo] for campo in campos_complejo},
                },
            )

            if creado:
                complejos_nuevos.add(complejo.nombre)
            elif datos['porcentaje_sena'] and not complejo.porcentaje_sena and not complejo.alias_transferencia:
                # Complejo de una carga anterior a las señas por transferencia: solo se completa si nadie lo configuró.
                for campo in ('porcentaje_sena', 'alias_transferencia', 'titular_transferencia'):
                    setattr(complejo, campo, datos[campo])
                complejo.save(update_fields=[
                    'porcentaje_sena', 'alias_transferencia', 'titular_transferencia', 'fecha_modificacion',
                ])

            for nombre_servicio in datos['servicios']:
                ComplejoServicio.objects.get_or_create(complejo=complejo, servicio=servicios[nombre_servicio])

            for datos_cancha in datos['canchas']:
                cancha, _ = Cancha.objects.get_or_create(
                    complejo=complejo,
                    nombre=datos_cancha['nombre'],
                    defaults={
                        'deporte': deportes[datos_cancha['deporte']],
                        'tipo_superficie': datos_cancha['tipo_superficie'],
                        'cobertura': datos_cancha['cobertura'],
                        'iluminacion': datos_cancha['iluminacion'],
                        'duracion_turno_min': datos_cancha['duracion_turno_min'],
                        'precio_base': Decimal(datos_cancha['precio_base']),
                    },
                )
                canchas[(complejo.nombre, cancha.nombre)] = cancha

                for dia in DiaSemana.values:
                    precio_finde = datos_cancha['precio_finde']
                    HorarioApertura.objects.get_or_create(
                        cancha=cancha,
                        dia_semana=dia,
                        hora_apertura=datos_cancha['apertura'],
                        estado=EstadoRegistro.ACTIVO,
                        defaults={
                            'hora_cierre': datos_cancha['cierre'],
                            'precio_diferenciado': (
                                Decimal(precio_finde) if precio_finde and dia in FIN_DE_SEMANA else None
                            ),
                        },
                    )

        return canchas, complejos_nuevos

    def _dar_de_baja_agenda(self):
        nombres = [datos['nombre'] for datos in COMPLEJOS]
        for modelo, filtro in (
            (Reserva, 'cancha__complejo__nombre__in'),
            (TurnoFijo, 'cancha__complejo__nombre__in'),
            (ExcepcionHoraria, 'complejo__nombre__in'),
        ):
            for registro in modelo.objects.filter(**{filtro: nombres}).exclude(estado=EstadoRegistro.BAJA):
                registro.desactivar()

    def _vincular_operadores(self, usuarios):
        for datos in USUARIOS:
            nombre_complejo = datos.get('complejo_operado')
            if not nombre_complejo:
                continue
            usuario = usuarios[datos['email']]
            if usuario.complejo_operado_id is None:
                usuario.complejo_operado = Complejo.objects.get(nombre=nombre_complejo)
                usuario.save(update_fields=['complejo_operado', 'fecha_modificacion'])

    def _cargar_excepciones(self, canchas, usuarios, hoy, complejos_nuevos):
        for datos in _excepciones(hoy):
            if datos['complejo'] not in complejos_nuevos:
                continue
            complejo = Complejo.objects.get(nombre=datos['complejo'])
            ExcepcionHoraria.objects.create(
                complejo=complejo,
                cancha=canchas[(complejo.nombre, datos['cancha'])] if datos['cancha'] else None,
                creado_por=usuarios[datos['creado_por']],
                fecha_inicio=datos['fecha_inicio'],
                fecha_fin=datos['fecha_fin'],
                es_dia_completo=datos['es_dia_completo'],
                hora_inicio=datos['hora_inicio'],
                hora_fin=datos['hora_fin'],
                tipo_motivo=datos['tipo_motivo'],
                descripcion=datos['descripcion'],
            )

    def _cargar_turnos_fijos(self, canchas, usuarios, hoy, complejos_nuevos):
        for datos in _turnos_fijos(hoy):
            if datos['complejo'] not in complejos_nuevos:
                continue
            cancha = canchas[(datos['complejo'], datos['cancha'])]
            usuario = usuarios[datos['usuario']] if datos['usuario'] else None
            turno = TurnoFijo.objects.create(
                cancha=cancha,
                usuario=usuario,
                creado_por=usuarios[datos['creado_por']],
                nombre_cliente_manual=datos['nombre_cliente_manual'],
                telefono_cliente_manual=datos['telefono_cliente_manual'],
                dia_semana=datos['dia_semana'],
                hora_inicio=datos['hora_inicio'],
                hora_fin=datos['hora_fin'],
                fecha_inicio_vigencia=datos['fecha_inicio_vigencia'],
                fecha_fin_vigencia=datos['fecha_fin_vigencia'],
            )

            for fecha in datos['reservas']:
                # El día puede tener varios rangos: se usa el que contiene al turno.
                horario = cancha.horarios.get(
                    dia_semana=fecha.weekday(),
                    estado=EstadoRegistro.ACTIVO,
                    hora_apertura__lte=turno.hora_inicio,
                    hora_cierre__gte=turno.hora_fin,
                )
                Reserva.objects.create(
                    cancha=cancha,
                    fecha_turno=fecha,
                    hora_inicio=turno.hora_inicio,
                    hora_fin=turno.hora_fin,
                    usuario=usuario,
                    turno_fijo=turno,
                    creado_por=turno.creado_por,
                    nombre_cliente_manual=turno.nombre_cliente_manual,
                    telefono_cliente_manual=turno.telefono_cliente_manual,
                    precio_acordado=horario.precio_diferenciado or cancha.precio_base,
                    tipo_ocupacion=TipoOcupacion.TURNO_FIJO,
                    estado=EstadoReserva.CONFIRMADA,
                )

    def _cargar_reservas(self, canchas, usuarios, hoy, complejos_nuevos):
        for datos in _reservas(hoy):
            if datos['complejo'] not in complejos_nuevos:
                continue
            cancha = canchas[(datos['complejo'], datos['cancha'])]
            precio = Decimal(datos['precio_acordado'])
            monto_sena = calcular_monto_sena(precio, cancha.complejo.porcentaje_sena)
            pago = datos.get('pago')
            Reserva.objects.create(
                cancha=cancha,
                fecha_turno=datos['fecha_turno'],
                hora_inicio=datos['hora_inicio'],
                hora_fin=datos['hora_fin'],
                usuario=usuarios[datos['usuario']] if datos['usuario'] else None,
                creado_por=usuarios[datos['creado_por']],
                nombre_cliente_manual=datos.get('nombre_cliente_manual', ''),
                telefono_cliente_manual=datos.get('telefono_cliente_manual', ''),
                precio_acordado=precio,
                monto_sena=monto_sena,
                monto_pagado=precio if pago == 'total' else monto_sena if pago == 'sena' else Decimal('0'),
                tipo_ocupacion=datos['tipo_ocupacion'],
                estado=datos['estado'],
                observaciones=datos.get('observaciones', ''),
            )

    def _resumen(self):
        conteos = [
            ('Roles', Rol.objects.count()),
            ('Permisos', Permiso.objects.count()),
            ('Asignaciones rol-permiso activas', RolPermiso.objects.filter(estado=EstadoRegistro.ACTIVO).count()),
            ('Deportes', Deporte.objects.count()),
            ('Servicios', Servicio.objects.count()),
            ('Usuarios', Usuario.objects.count()),
            ('Complejos', Complejo.objects.count()),
            ('Servicios por complejo', ComplejoServicio.objects.count()),
            ('Canchas', Cancha.objects.count()),
            ('Horarios de apertura', HorarioApertura.objects.count()),
            ('Excepciones horarias', ExcepcionHoraria.objects.count()),
            ('Turnos fijos', TurnoFijo.objects.count()),
            ('Reservas', Reserva.objects.count()),
        ]
        self.stdout.write(self.style.SUCCESS('seed_inicial ejecutado correctamente.'))
        for etiqueta, cantidad in conteos:
            self.stdout.write(f'  {etiqueta}: {cantidad}')
