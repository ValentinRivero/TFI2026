import os
from datetime import date, time
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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

ROLES = {
    'SUPERADMIN': 'Administrador de la plataforma (Bombo Devs). Hereda las acciones de cualquier complejo.',
    'DUENO_COMPLEJO': 'Responsable del complejo: configuración, canchas, precios, agenda y reportes.',
    'OPERADOR_COMPLEJO': 'Personal del complejo: perfil del complejo, agenda diaria, reservas manuales y excepciones.',
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
    'configurar_complejo',
    'ver_canchas',
    'ver_agenda',
    'gestionar_agenda',
    'cancelar_reserva_complejo',
    'gestionar_turnos_fijos',
    'ver_excepciones',
    'gestionar_excepciones',
]

PERMISOS_DUENO = PERMISOS_OPERADOR + [
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
    {'email': 'talibre@irracional.net', 'nombre_completo': 'Bombo Devs',
     'telefono': '3777 400000', 'rol': 'SUPERADMIN'},
    {'email': 'ramon.acosta@irracional.net', 'nombre_completo': 'Ramón Acosta',
     'telefono': '3777 412234', 'rol': 'DUENO_COMPLEJO'},
    {'email': 'lucas.benitez@irracional.net', 'nombre_completo': 'Lucas Benítez',
     'telefono': '3777 412235', 'rol': 'OPERADOR_COMPLEJO', 'complejo_operado': 'Complejo El Potrero'},
    {'email': 'carolina.insaurralde@irracional.net', 'nombre_completo': 'Carolina Insaurralde',
     'telefono': '3777 455679', 'rol': 'DUENO_COMPLEJO'},
    {'email': 'hector.romero@irracional.net', 'nombre_completo': 'Héctor Romero',
     'telefono': '3777 431091', 'rol': 'DUENO_COMPLEJO'},
    {'email': 'marta.fernandez@irracional.net', 'nombre_completo': 'Marta Fernández',
     'telefono': '3777 409877', 'rol': 'DUENO_COMPLEJO'},
    {'email': 'facundo.gomez@irracional.net', 'nombre_completo': 'Facundo Gómez',
     'telefono': '3777 501122', 'rol': 'JUGADOR'},
    {'email': 'valeria.sosa@irracional.net', 'nombre_completo': 'Valeria Sosa',
     'telefono': '3777 503344', 'rol': 'JUGADOR'},
    {'email': 'matias.ojeda@irracional.net', 'nombre_completo': 'Matías Ojeda',
     'telefono': '3777 505566', 'rol': 'JUGADOR'},
]

FIN_DE_SEMANA = (DiaSemana.SABADO, DiaSemana.DOMINGO)

COMPLEJOS = [
    {
        'nombre': 'Complejo El Potrero',
        'propietario': 'ramon.acosta@irracional.net',
        'direccion': 'Av. Neustadt 1250, Goya, Corrientes',
        'latitud': Decimal('-29.146820'),
        'longitud': Decimal('-59.271430'),
        'telefono_contacto': '3777 412233',
        'horas_limite_cancelacion': 4,
        'info_sena': 'Seña del 30% por transferencia al alias ELPOTRERO.GOYA. Se descuenta del total.',
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
        'nombre': 'Pádel Costa Goya',
        'propietario': 'carolina.insaurralde@irracional.net',
        'direccion': 'Av. Mazzanti 860, Goya, Corrientes',
        'latitud': Decimal('-29.138910'),
        'longitud': Decimal('-59.256780'),
        'telefono_contacto': '3777 455678',
        'horas_limite_cancelacion': 12,
        'info_sena': 'Seña del 50% para confirmar el turno. Se reintegra cancelando con 12 horas de anticipación.',
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
        'nombre': 'Polideportivo Santa Lucía',
        'propietario': 'hector.romero@irracional.net',
        'direccion': 'José Gómez 1540, Goya, Corrientes',
        'latitud': Decimal('-29.152340'),
        'longitud': Decimal('-59.264120'),
        'telefono_contacto': '3777 431090',
        'horas_limite_cancelacion': 4,
        'info_sena': '',
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
        'nombre': 'Complejo Los Lapachos',
        'propietario': 'marta.fernandez@irracional.net',
        'direccion': 'Av. Madariaga 2100, Goya, Corrientes',
        'latitud': Decimal('-29.160450'),
        'longitud': Decimal('-59.278900'),
        'telefono_contacto': '3777 409876',
        'horas_limite_cancelacion': 4,
        'info_sena': '',
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

EXCEPCIONES = [
    {'complejo': 'Complejo El Potrero', 'cancha': None, 'creado_por': 'ramon.acosta@irracional.net',
     'fecha_inicio': date(2026, 12, 8), 'fecha_fin': date(2026, 12, 8), 'es_dia_completo': AlcanceExcepcion.DIA_COMPLETO,
     'hora_inicio': None, 'hora_fin': None, 'tipo_motivo': TipoMotivoExcepcion.FERIADO,
     'descripcion': 'Feriado de la Inmaculada Concepción'},
    {'complejo': 'Complejo El Potrero', 'cancha': 'Cancha 2', 'creado_por': 'lucas.benitez@irracional.net',
     'fecha_inicio': date(2026, 11, 18), 'fecha_fin': date(2026, 11, 18), 'es_dia_completo': AlcanceExcepcion.FRANJA_HORARIA,
     'hora_inicio': time(14, 0), 'hora_fin': time(17, 0), 'tipo_motivo': TipoMotivoExcepcion.MANTENIMIENTO,
     'descripcion': 'Recambio de red y cepillado del césped'},
    {'complejo': 'Pádel Costa Goya', 'cancha': None, 'creado_por': 'carolina.insaurralde@irracional.net',
     'fecha_inicio': date(2026, 12, 24), 'fecha_fin': date(2026, 12, 25), 'es_dia_completo': AlcanceExcepcion.DIA_COMPLETO,
     'hora_inicio': None, 'hora_fin': None, 'tipo_motivo': TipoMotivoExcepcion.FERIADO,
     'descripcion': 'Cierre por Nochebuena y Navidad'},
    {'complejo': 'Polideportivo Santa Lucía', 'cancha': 'Estadio Cubierto',
     'creado_por': 'hector.romero@irracional.net', 'fecha_inicio': date(2026, 11, 21),
     'fecha_fin': date(2026, 11, 21), 'es_dia_completo': AlcanceExcepcion.FRANJA_HORARIA, 'hora_inicio': time(9, 0),
     'hora_fin': time(15, 0), 'tipo_motivo': TipoMotivoExcepcion.EVENTO_PRIVADO,
     'descripcion': 'Encuentro escolar de minibásquet'},
]

TURNOS_FIJOS = [
    {'complejo': 'Complejo El Potrero', 'cancha': 'Cancha 1', 'usuario': None,
     'creado_por': 'lucas.benitez@irracional.net',
     'nombre_cliente_manual': 'Los Pibes del Martes (Sergio Duarte)', 'telefono_cliente_manual': '3777 540077',
     'dia_semana': DiaSemana.MARTES, 'hora_inicio': time(21, 0), 'hora_fin': time(22, 0),
     'fecha_inicio_vigencia': date(2026, 11, 17), 'fecha_fin_vigencia': date(2026, 12, 15),
     'reservas': [date(2026, 11, 17), date(2026, 11, 24), date(2026, 12, 1)]},
    {'complejo': 'Pádel Costa Goya', 'cancha': 'Pádel 2', 'usuario': 'valeria.sosa@irracional.net',
     'creado_por': 'carolina.insaurralde@irracional.net', 'nombre_cliente_manual': '',
     'telefono_cliente_manual': '', 'dia_semana': DiaSemana.JUEVES, 'hora_inicio': time(20, 0),
     'hora_fin': time(21, 30), 'fecha_inicio_vigencia': date(2026, 11, 19), 'fecha_fin_vigencia': None,
     'reservas': [date(2026, 11, 19), date(2026, 11, 26)]},
]

RESERVAS = [
    {'complejo': 'Complejo El Potrero', 'cancha': 'Cancha 1', 'fecha_turno': date(2026, 11, 20),
     'hora_inicio': time(20, 0), 'hora_fin': time(21, 0), 'usuario': 'facundo.gomez@irracional.net',
     'creado_por': 'facundo.gomez@irracional.net', 'tipo_ocupacion': TipoOcupacion.WEB,
     'estado': EstadoReserva.CONFIRMADA, 'precio_acordado': '38000.00'},
    {'complejo': 'Complejo El Potrero', 'cancha': 'Cancha 1', 'fecha_turno': date(2026, 11, 20),
     'hora_inicio': time(21, 0), 'hora_fin': time(22, 0), 'usuario': None,
     'creado_por': 'lucas.benitez@irracional.net', 'nombre_cliente_manual': 'Diego Maidana',
     'telefono_cliente_manual': '3777 520011', 'tipo_ocupacion': TipoOcupacion.MANUAL,
     'estado': EstadoReserva.SENADA, 'precio_acordado': '38000.00',
     'observaciones': 'Seña de $11.400 recibida por transferencia'},
    {'complejo': 'Complejo El Potrero', 'cancha': 'Cancha 2', 'fecha_turno': date(2026, 11, 19),
     'hora_inicio': time(19, 0), 'hora_fin': time(20, 0), 'usuario': 'valeria.sosa@irracional.net',
     'creado_por': 'valeria.sosa@irracional.net', 'tipo_ocupacion': TipoOcupacion.WEB,
     'estado': EstadoReserva.CANCELADA_JUGADOR, 'precio_acordado': '42000.00'},
    {'complejo': 'Complejo El Potrero', 'cancha': 'Cancha 7', 'fecha_turno': date(2026, 11, 13),
     'hora_inicio': time(21, 0), 'hora_fin': time(22, 0), 'usuario': 'matias.ojeda@irracional.net',
     'creado_por': 'matias.ojeda@irracional.net', 'tipo_ocupacion': TipoOcupacion.WEB,
     'estado': EstadoReserva.COMPLETADA, 'precio_acordado': '56000.00'},
    {'complejo': 'Complejo El Potrero', 'cancha': 'Cancha 7', 'fecha_turno': date(2026, 11, 14),
     'hora_inicio': time(20, 0), 'hora_fin': time(21, 0), 'usuario': 'facundo.gomez@irracional.net',
     'creado_por': 'facundo.gomez@irracional.net', 'tipo_ocupacion': TipoOcupacion.WEB,
     'estado': EstadoReserva.AUSENTE, 'precio_acordado': '56000.00'},
    {'complejo': 'Pádel Costa Goya', 'cancha': 'Pádel 1', 'fecha_turno': date(2026, 11, 20),
     'hora_inicio': time(18, 30), 'hora_fin': time(20, 0), 'usuario': 'valeria.sosa@irracional.net',
     'creado_por': 'valeria.sosa@irracional.net', 'tipo_ocupacion': TipoOcupacion.WEB,
     'estado': EstadoReserva.SENADA, 'precio_acordado': '30000.00'},
    {'complejo': 'Pádel Costa Goya', 'cancha': 'Pádel 3', 'fecha_turno': date(2026, 11, 21),
     'hora_inicio': time(9, 30), 'hora_fin': time(11, 0), 'usuario': None,
     'creado_por': 'carolina.insaurralde@irracional.net', 'nombre_cliente_manual': 'Silvina Leiva',
     'telefono_cliente_manual': '3777 530099', 'tipo_ocupacion': TipoOcupacion.MANUAL,
     'estado': EstadoReserva.PENDIENTE, 'precio_acordado': '34000.00'},
    {'complejo': 'Polideportivo Santa Lucía', 'cancha': 'Estadio Cubierto', 'fecha_turno': date(2026, 11, 22),
     'hora_inicio': time(17, 0), 'hora_fin': time(19, 0), 'usuario': 'matias.ojeda@irracional.net',
     'creado_por': 'matias.ojeda@irracional.net', 'tipo_ocupacion': TipoOcupacion.WEB,
     'estado': EstadoReserva.CONFIRMADA, 'precio_acordado': '45000.00'},
]


class Command(BaseCommand):
    help = 'Carga roles, permisos RBAC, deportes, servicios y datos de demostración de Goya. Es idempotente.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sin-demo',
            action='store_true',
            help='Carga solo los catálogos base (roles, permisos, deportes y servicios).',
        )

    def handle(self, *args, **opciones):
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
                usuarios = self._cargar_usuarios(roles, password)
                canchas = self._cargar_complejos(usuarios, deportes, servicios)
                self._vincular_operadores(usuarios)
                self._cargar_excepciones(canchas, usuarios)
                self._cargar_turnos_fijos(canchas, usuarios)
                self._cargar_reservas(canchas, usuarios)

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
            for codigo in codigos:
                RolPermiso.objects.get_or_create(rol=roles[nombre_rol], permiso=permisos[codigo])

    def _cargar_deportes(self):
        return {nombre: Deporte.objects.get_or_create(nombre=nombre)[0] for nombre in DEPORTES}

    def _cargar_servicios(self):
        return {nombre: Servicio.objects.get_or_create(nombre=nombre)[0] for nombre in SERVICIOS}

    def _cargar_usuarios(self, roles, password):
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
            usuarios[usuario.email] = usuario
        return usuarios

    def _cargar_complejos(self, usuarios, deportes, servicios):
        canchas = {}
        campos_complejo = (
            'direccion', 'latitud', 'longitud', 'telefono_contacto',
            'horas_limite_cancelacion', 'info_sena', 'estado_contrato',
        )

        for datos in COMPLEJOS:
            complejo, _ = Complejo.objects.get_or_create(
                nombre=datos['nombre'],
                defaults={
                    'propietario': usuarios[datos['propietario']],
                    **{campo: datos[campo] for campo in campos_complejo},
                },
            )

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
                        estado=EstadoRegistro.ACTIVO,
                        defaults={
                            'hora_apertura': datos_cancha['apertura'],
                            'hora_cierre': datos_cancha['cierre'],
                            'precio_diferenciado': (
                                Decimal(precio_finde) if precio_finde and dia in FIN_DE_SEMANA else None
                            ),
                        },
                    )

        return canchas

    def _vincular_operadores(self, usuarios):
        for datos in USUARIOS:
            nombre_complejo = datos.get('complejo_operado')
            if not nombre_complejo:
                continue
            usuario = usuarios[datos['email']]
            if usuario.complejo_operado_id is None:
                usuario.complejo_operado = Complejo.objects.get(nombre=nombre_complejo)
                usuario.save(update_fields=['complejo_operado', 'fecha_modificacion'])

    def _cargar_excepciones(self, canchas, usuarios):
        for datos in EXCEPCIONES:
            complejo = Complejo.objects.get(nombre=datos['complejo'])
            cancha = canchas[(complejo.nombre, datos['cancha'])] if datos['cancha'] else None
            ExcepcionHoraria.objects.get_or_create(
                complejo=complejo,
                cancha=cancha,
                fecha_inicio=datos['fecha_inicio'],
                fecha_fin=datos['fecha_fin'],
                hora_inicio=datos['hora_inicio'],
                tipo_motivo=datos['tipo_motivo'],
                defaults={
                    'creado_por': usuarios[datos['creado_por']],
                    'es_dia_completo': datos['es_dia_completo'],
                    'hora_fin': datos['hora_fin'],
                    'descripcion': datos['descripcion'],
                },
            )

    def _cargar_turnos_fijos(self, canchas, usuarios):
        for datos in TURNOS_FIJOS:
            cancha = canchas[(datos['complejo'], datos['cancha'])]
            usuario = usuarios[datos['usuario']] if datos['usuario'] else None
            turno, _ = TurnoFijo.objects.get_or_create(
                cancha=cancha,
                dia_semana=datos['dia_semana'],
                hora_inicio=datos['hora_inicio'],
                fecha_inicio_vigencia=datos['fecha_inicio_vigencia'],
                defaults={
                    'usuario': usuario,
                    'creado_por': usuarios[datos['creado_por']],
                    'nombre_cliente_manual': datos['nombre_cliente_manual'],
                    'telefono_cliente_manual': datos['telefono_cliente_manual'],
                    'hora_fin': datos['hora_fin'],
                    'fecha_fin_vigencia': datos['fecha_fin_vigencia'],
                },
            )

            for fecha in datos['reservas']:
                horario = cancha.horarios.get(dia_semana=fecha.weekday(), estado=EstadoRegistro.ACTIVO)
                Reserva.objects.get_or_create(
                    cancha=cancha,
                    fecha_turno=fecha,
                    hora_inicio=turno.hora_inicio,
                    defaults={
                        'hora_fin': turno.hora_fin,
                        'usuario': usuario,
                        'turno_fijo': turno,
                        'creado_por': turno.creado_por,
                        'nombre_cliente_manual': turno.nombre_cliente_manual,
                        'telefono_cliente_manual': turno.telefono_cliente_manual,
                        'precio_acordado': horario.precio_diferenciado or cancha.precio_base,
                        'tipo_ocupacion': TipoOcupacion.TURNO_FIJO,
                        'estado': EstadoReserva.CONFIRMADA,
                    },
                )

    def _cargar_reservas(self, canchas, usuarios):
        for datos in RESERVAS:
            cancha = canchas[(datos['complejo'], datos['cancha'])]
            Reserva.objects.get_or_create(
                cancha=cancha,
                fecha_turno=datos['fecha_turno'],
                hora_inicio=datos['hora_inicio'],
                defaults={
                    'hora_fin': datos['hora_fin'],
                    'usuario': usuarios[datos['usuario']] if datos['usuario'] else None,
                    'creado_por': usuarios[datos['creado_por']],
                    'nombre_cliente_manual': datos.get('nombre_cliente_manual', ''),
                    'telefono_cliente_manual': datos.get('telefono_cliente_manual', ''),
                    'precio_acordado': Decimal(datos['precio_acordado']),
                    'tipo_ocupacion': datos['tipo_ocupacion'],
                    'estado': datos['estado'],
                    'observaciones': datos.get('observaciones', ''),
                },
            )

    def _resumen(self):
        conteos = [
            ('Roles', Rol.objects.count()),
            ('Permisos', Permiso.objects.count()),
            ('Asignaciones rol-permiso', RolPermiso.objects.count()),
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
