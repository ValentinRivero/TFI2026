import pytest
from django.conf import settings
from rest_framework import status

from core.models import EstadoRegistro, LogAuditoria, Rol, TipoEventoAuditoria, Usuario

pytestmark = pytest.mark.usefixtures('rbac')

URL = '/api/registro/'


def _datos(**cambios):
    datos = {
        'nombre_completo': 'Fabricio Medina',
        'email': 'fabricio@talibre.test',
        'password': 'Pelota&Arco#2026',
        'telefono': '3777 000206',
        'acepta_politica_privacidad': True,
    }
    datos.update(cambios)
    return datos


def test_alta_publica_de_jugador(cliente):
    respuesta = cliente.post(URL, _datos(), format='json')

    assert respuesta.status_code == status.HTTP_201_CREATED
    cuerpo = respuesta.json()
    assert cuerpo['email'] == 'fabricio@talibre.test'
    assert cuerpo['rol'] == 'JUGADOR'
    assert 'password' not in cuerpo

    usuario = Usuario.objects.get(email='fabricio@talibre.test')
    assert usuario.rol.nombre == 'JUGADOR'
    assert usuario.estado == EstadoRegistro.ACTIVO
    assert usuario.password != 'Pelota&Arco#2026'
    assert usuario.check_password('Pelota&Arco#2026')


def test_registra_el_alta_en_auditoria(cliente):
    cliente.post(URL, _datos(), format='json')

    log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.REGISTRO_USUARIO)
    assert log.usuario.email == 'fabricio@talibre.test'
    assert log.ip_origen == '127.0.0.1'
    assert 'Pelota&Arco#2026' not in log.detalle
    assert 'fabricio@talibre.test' not in log.detalle


class TestLimiteDeRegistro:
    def _registrar(self, cliente, numero, ip='127.0.0.1'):
        return cliente.post(URL, _datos(email=f'jugador{numero}@talibre.test'), format='json', REMOTE_ADDR=ip)

    def test_bloquea_con_429_al_superar_diez_altas_por_hora(self, cliente):
        for numero in range(10):
            assert self._registrar(cliente, numero).status_code == status.HTTP_201_CREATED

        respuesta = self._registrar(cliente, 10)

        assert respuesta.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert respuesta.json()['error'] is True
        assert not Usuario.objects.filter(email='jugador10@talibre.test').exists()
        assert LogAuditoria.objects.filter(
            tipo_evento=TipoEventoAuditoria.LIMITE_PETICIONES, accion='POST /api/registro/',
        ).count() == 1

    def test_el_limite_es_por_ip(self, cliente):
        for numero in range(10):
            self._registrar(cliente, numero)

        assert self._registrar(cliente, 10, ip='10.0.0.20').status_code == status.HTTP_201_CREATED

    def test_cuenta_tambien_los_intentos_invalidos(self, cliente):
        for _ in range(10):
            cliente.post(URL, {}, format='json')

        assert self._registrar(cliente, 0).status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_ignora_un_rol_enviado_en_el_body(cliente):
    cliente.post(URL, _datos(rol='SUPERADMIN'), format='json')

    assert Usuario.objects.get(email='fabricio@talibre.test').rol.nombre == 'JUGADOR'


def test_normaliza_el_email(cliente):
    cliente.post(URL, _datos(email='  Fabricio@TaLibre.TEST '), format='json')

    assert Usuario.objects.filter(email='fabricio@talibre.test').exists()


def test_rechaza_email_duplicado_sin_distinguir_mayusculas(cliente, jugador):
    respuesta = cliente.post(URL, _datos(email='JUGADOR@talibre.test'), format='json')

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert respuesta.json()['detail']['email'] == ['Ya existe una cuenta registrada con ese email.']


@pytest.mark.parametrize('password', ['12345678', 'corta1', 'password123'])
def test_rechaza_contrasenas_debiles(cliente, password):
    respuesta = cliente.post(URL, _datos(password=password), format='json')

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert 'password' in respuesta.json()['detail']
    assert not Usuario.objects.filter(email='fabricio@talibre.test').exists()


def test_rechaza_contrasena_parecida_al_email(cliente):
    respuesta = cliente.post(URL, _datos(email='fabriciomedina@talibre.test', password='fabriciomedina'), format='json')

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert 'password' in respuesta.json()['detail']


def test_sanitiza_etiquetas_html_del_nombre(cliente):
    cliente.post(URL, _datos(nombre_completo='<script>alert(1)</script>Juan <b>Pérez</b>'), format='json')

    assert Usuario.objects.get(email='fabricio@talibre.test').nombre_completo == 'Juan Pérez'


def test_conserva_el_ampersand_sin_escaparlo(cliente):
    cliente.post(URL, _datos(nombre_completo='Pérez & Hijos'), format='json')

    assert Usuario.objects.get(email='fabricio@talibre.test').nombre_completo == 'Pérez & Hijos'


def test_no_reconstruye_etiquetas_codificadas(cliente):
    cliente.post(URL, _datos(nombre_completo='&lt;script&gt;alert(1)&lt;/script&gt;Ana'), format='json')

    nombre = Usuario.objects.get(email='fabricio@talibre.test').nombre_completo
    assert nombre == 'Ana'


@pytest.mark.parametrize('capas', [1, 5, 6, 8, 20])
def test_la_sanitizacion_nunca_devuelve_html_aunque_se_agoten_las_pasadas(capas):
    from core.serializers import limpiar_texto

    entrada = '<script>alert(1)</script><img src=x onerror=alert(1)>Ana'
    for _ in range(capas):
        entrada = entrada.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    salida = limpiar_texto(entrada)

    assert '<' not in salida
    assert '>' not in salida
    assert salida.endswith('Ana')


@pytest.mark.parametrize('capas', [6, 8, 20])
def test_al_agotar_las_pasadas_la_salida_es_la_de_nh3_sin_desescapar(capas):
    import nh3

    from core.serializers import MAXIMO_PASADAS_SANITIZACION, limpiar_texto

    assert capas > MAXIMO_PASADAS_SANITIZACION
    entrada = '<script>alert(1)</script><b>Ana</b>'
    for _ in range(capas):
        entrada = entrada.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    salida = limpiar_texto(entrada)

    # La última operación es nh3.clean: la salida es un punto fijo suyo y conserva las entidades escapadas.
    assert nh3.clean(salida, tags=set()) == salida
    assert '&lt;script&gt;' in salida or '&amp;' in salida


def test_rechaza_nombre_que_queda_vacio_al_sanitizar(cliente):
    respuesta = cliente.post(URL, _datos(nombre_completo='<b></b>'), format='json')

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert 'nombre_completo' in respuesta.json()['detail']


def test_rechaza_telefono_invalido(cliente):
    respuesta = cliente.post(URL, _datos(telefono='llamame'), format='json')

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert 'telefono' in respuesta.json()['detail']


def test_telefono_es_opcional(cliente):
    datos = _datos()
    del datos['telefono']

    respuesta = cliente.post(URL, datos, format='json')

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert Usuario.objects.get(email='fabricio@talibre.test').telefono == ''


def test_sin_rol_jugador_activo_responde_503(cliente):
    Rol.objects.get(nombre='JUGADOR').desactivar()

    respuesta = cliente.post(URL, _datos(), format='json')

    assert respuesta.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert respuesta.json()['error'] is True
    assert not Usuario.objects.filter(email='fabricio@talibre.test').exists()


class TestConsentimiento:
    def test_guarda_la_constancia_de_la_version_aceptada(self, cliente):
        cliente.post(URL, _datos(), format='json')

        usuario = Usuario.objects.get(email='fabricio@talibre.test')
        assert usuario.version_politica_aceptada == settings.POLITICA_PRIVACIDAD_VERSION
        assert usuario.fecha_aceptacion_politica is not None

    def test_la_auditoria_deja_evidencia_con_ip(self, cliente):
        cliente.post(URL, _datos(), format='json')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.REGISTRO_USUARIO)
        assert f'Política de privacidad {settings.POLITICA_PRIVACIDAD_VERSION} aceptada' in log.detalle
        assert log.ip_origen == '127.0.0.1'

    @pytest.mark.parametrize('valor', [False, 'false', 0])
    def test_rechaza_el_registro_sin_aceptacion_expresa(self, cliente, valor):
        respuesta = cliente.post(URL, _datos(acepta_politica_privacidad=valor), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail']['acepta_politica_privacidad'] == [
            'Para usar TaLibre tenés que aceptar la política de privacidad.'
        ]
        assert not Usuario.objects.filter(email='fabricio@talibre.test').exists()

    def test_rechaza_el_registro_si_falta_el_campo(self, cliente):
        datos = _datos()
        del datos['acepta_politica_privacidad']

        respuesta = cliente.post(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'acepta_politica_privacidad' in respuesta.json()['detail']

    def test_la_respuesta_informa_que_no_debe_volver_a_aceptar(self, cliente):
        cuerpo = cliente.post(URL, _datos(), format='json').json()

        assert cuerpo['debe_aceptar_politica'] is False
        assert 'acepta_politica_privacidad' not in cuerpo
