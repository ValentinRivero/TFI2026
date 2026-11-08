import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from conftest import PASSWORD_PRUEBA
from core.models import EstadoUsuario, LogAuditoria, Rol, TipoEventoAuditoria

URL_LOGIN = '/api/token/'
URL_REFRESH = '/api/token/refresh/'
URL_LOGOUT = '/api/token/logout/'


def _login(cliente, email='jugador@talibre.test', password=PASSWORD_PRUEBA):
    return cliente.post(URL_LOGIN, {'email': email, 'password': password}, format='json')


class TestLogin:
    def test_devuelve_access_en_el_cuerpo_y_refresh_solo_en_cookie(self, cliente, jugador):
        respuesta = _login(cliente)

        assert respuesta.status_code == status.HTTP_200_OK
        assert set(respuesta.json()) == {'access'}
        assert 'refresh' in respuesta.cookies

    def test_el_access_lleva_el_claim_rol_y_el_id_de_usuario(self, cliente, jugador):
        access = AccessToken(_login(cliente).json()['access'])

        assert access['rol'] == 'JUGADOR'
        assert access['usuario_id'] == str(jugador.id)

    def test_el_refresh_tambien_lleva_el_claim_rol(self, cliente, dueno):
        respuesta = _login(cliente, 'dueno@talibre.test')

        assert RefreshToken(respuesta.cookies['refresh'].value)['rol'] == 'DUENO_COMPLEJO'

    @override_settings(DEBUG=False)
    def test_cookie_httponly_strict_y_secure_restringida_a_token(self, cliente, jugador):
        cookie = _login(cliente).cookies['refresh']

        assert cookie['httponly'] is True
        assert cookie['samesite'] == 'Strict'
        assert cookie['path'] == '/api/token/'
        assert cookie['secure'] is True
        assert int(cookie['max-age']) > 0

    @override_settings(DEBUG=True)
    def test_cookie_sin_secure_en_desarrollo(self, cliente, jugador):
        assert not _login(cliente).cookies['refresh']['secure']

    def test_email_sin_distinguir_mayusculas(self, cliente, jugador):
        assert _login(cliente, ' JUGADOR@TaLibre.test').status_code == status.HTTP_200_OK

    def test_ignora_un_access_vencido_en_el_header(self, cliente, jugador):
        cliente.credentials(HTTP_AUTHORIZATION='Bearer vencido')

        assert _login(cliente).status_code == status.HTTP_200_OK

    def test_registra_login_exitoso(self, cliente, jugador):
        _login(cliente)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.LOGIN_EXITOSO)
        assert log.usuario == jugador

    def test_contrasena_incorrecta_responde_401_y_audita_sin_guardarla(self, cliente, jugador, log_seguridad):
        respuesta = _login(cliente, password='ClaveEquivocada#99')

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json() == {'error': True, 'detail': 'Email o contraseña incorrectos.'}
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.LOGIN_FALLIDO)
        assert log.usuario == jugador
        assert 'ClaveEquivocada#99' not in log.detalle
        assert 'ClaveEquivocada#99' not in log_seguridad.text
        assert 'LOGIN_FALLIDO' in log_seguridad.text

    def test_email_inexistente_responde_igual_y_audita(self, cliente, rbac):
        respuesta = _login(cliente, 'nadie@talibre.test')

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json()['detail'] == 'Email o contraseña incorrectos.'
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.LOGIN_FALLIDO)
        assert log.usuario is None
        assert log.detalle == 'Email no registrado.'

    @pytest.mark.parametrize('email, password', [
        ('nadie@talibre.test', PASSWORD_PRUEBA),
        ('jugador@talibre.test', 'ClaveEquivocada#99'),
    ])
    def test_la_auditoria_del_login_fallido_no_guarda_el_email(self, cliente, jugador, log_seguridad, email, password):
        _login(cliente, email, password)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.LOGIN_FALLIDO)
        assert email not in log.detalle
        assert email not in log.accion
        assert email not in log_seguridad.text

    @pytest.mark.parametrize('estado', [EstadoUsuario.SUSPENDIDO, EstadoUsuario.BAJA])
    def test_cuenta_no_activa_responde_401_y_audita(self, cliente, jugador, estado):
        jugador.estado = estado
        jugador.save(update_fields=['estado'])

        respuesta = _login(cliente)

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json()['detail'] == 'La cuenta no está activa.'
        assert 'refresh' not in respuesta.cookies
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.LOGIN_FALLIDO)
        assert log.usuario == jugador

    def test_faltan_campos_responde_400(self, cliente, rbac):
        respuesta = cliente.post(URL_LOGIN, {'email': 'no-es-un-email'}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert {'email', 'password'}.issubset(respuesta.json()['detail'])


class TestLimiteDeLogin:
    def test_bloquea_con_429_al_sexto_intento_fallido(self, cliente, jugador):
        for _ in range(5):
            assert _login(cliente, password='Incorrecta#1').status_code == status.HTTP_401_UNAUTHORIZED

        respuesta = _login(cliente, password='Incorrecta#1')

        assert respuesta.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert respuesta.json()['error'] is True
        assert respuesta.json()['detail'].startswith('Superaste el límite de solicitudes.')
        assert 'Retry-After' in respuesta

    def test_el_bloqueo_alcanza_tambien_a_la_contrasena_correcta(self, cliente, jugador):
        for _ in range(5):
            _login(cliente, password='Incorrecta#1')

        assert _login(cliente).status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_audita_el_429(self, cliente, jugador):
        for _ in range(6):
            _login(cliente, password='Incorrecta#1')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.LIMITE_PETICIONES)
        assert log.accion == 'POST /api/token/'
        assert log.ip_origen == '127.0.0.1'
        assert log.detalle.startswith('Superaste el límite de solicitudes.')

    def test_una_rafaga_de_rechazos_deja_un_solo_registro_por_ventana(self, cliente, jugador, log_seguridad):
        for _ in range(30):
            _login(cliente, password='Incorrecta#1')

        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.LIMITE_PETICIONES).count() == 1
        assert log_seguridad.text.count('evento=LIMITE_PETICIONES') == 1

    def test_cada_ip_rechazada_queda_registrada(self, cliente, jugador):
        for ip in ('10.0.0.1', '10.0.0.2'):
            for _ in range(6):
                cliente.post(
                    URL_LOGIN, {'email': 'jugador@talibre.test', 'password': 'Incorrecta#1'},
                    format='json', REMOTE_ADDR=ip,
                )

        ips = set(
            LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.LIMITE_PETICIONES)
            .values_list('ip_origen', flat=True)
        )
        assert ips == {'10.0.0.1', '10.0.0.2'}

    def test_el_limite_es_por_ip(self, cliente, jugador):
        for _ in range(5):
            _login(cliente, password='Incorrecta#1')

        otra_ip = cliente.post(
            URL_LOGIN, {'email': 'jugador@talibre.test', 'password': PASSWORD_PRUEBA},
            format='json', REMOTE_ADDR='10.0.0.8',
        )

        assert otra_ip.status_code == status.HTTP_200_OK


class TestRefresh:
    def test_lee_la_cookie_sin_body_y_rota(self, cliente, jugador):
        refresh_original = _login(cliente).cookies['refresh'].value

        respuesta = cliente.post(URL_REFRESH)

        assert respuesta.status_code == status.HTTP_200_OK
        assert set(respuesta.json()) == {'access'}
        assert AccessToken(respuesta.json()['access'])['usuario_id'] == str(jugador.id)
        refresh_nuevo = respuesta.cookies['refresh'].value
        assert refresh_nuevo != refresh_original
        assert respuesta.cookies['refresh']['httponly'] is True
        assert respuesta.cookies['refresh']['path'] == '/api/token/'

    def test_el_refresh_rotado_queda_en_blacklist(self, cliente, jugador):
        refresh_original = _login(cliente).cookies['refresh'].value
        cliente.post(URL_REFRESH)

        cliente.cookies['refresh'] = refresh_original
        respuesta = cliente.post(URL_REFRESH)

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json()['error'] is True

    def test_sin_cookie_responde_401(self, cliente, rbac):
        respuesta = cliente.post(URL_REFRESH)

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json() == {'error': True, 'detail': 'No hay una sesión activa.'}

    def test_cookie_invalida_responde_401(self, cliente, rbac):
        cliente.cookies['refresh'] = 'no-es-un-jwt'

        assert cliente.post(URL_REFRESH).status_code == status.HTTP_401_UNAUTHORIZED

    def test_ignora_un_access_vencido_en_el_header(self, cliente, jugador):
        _login(cliente)
        cliente.credentials(HTTP_AUTHORIZATION='Bearer vencido')

        assert cliente.post(URL_REFRESH).status_code == status.HTTP_200_OK

    def test_rechaza_si_la_cuenta_se_suspendio(self, cliente, jugador):
        _login(cliente)
        jugador.estado = EstadoUsuario.SUSPENDIDO
        jugador.save(update_fields=['estado'])

        respuesta = cliente.post(URL_REFRESH)

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json()['detail'] == 'La cuenta no está activa.'

    def test_actualiza_el_claim_rol_desde_la_base(self, cliente, jugador):
        _login(cliente)
        jugador.rol = Rol.objects.get(nombre='DUENO_COMPLEJO')
        jugador.save(update_fields=['rol'])

        access = AccessToken(cliente.post(URL_REFRESH).json()['access'])

        assert access['rol'] == 'DUENO_COMPLEJO'


class TestLogout:
    def test_envia_el_refresh_a_blacklist_y_borra_la_cookie(self, cliente, jugador):
        refresh = RefreshToken(_login(cliente).cookies['refresh'].value)

        respuesta = cliente.post(URL_LOGOUT)

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        assert BlacklistedToken.objects.filter(token__jti=refresh['jti']).exists()
        cookie = respuesta.cookies['refresh']
        assert cookie.value == ''
        assert cookie['path'] == '/api/token/'
        assert int(cookie['max-age']) == 0

    def test_despues_del_logout_el_refresh_no_sirve(self, cliente, jugador):
        refresh = _login(cliente).cookies['refresh'].value
        cliente.post(URL_LOGOUT)

        cliente.cookies['refresh'] = refresh
        assert cliente.post(URL_REFRESH).status_code == status.HTTP_401_UNAUTHORIZED

    def test_registra_el_cierre_de_sesion(self, cliente, jugador):
        _login(cliente)
        cliente.post(URL_LOGOUT)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.LOGOUT)
        assert log.usuario == jugador

    def test_sin_cookie_responde_401(self, cliente, rbac):
        respuesta = cliente.post(URL_LOGOUT)

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json()['error'] is True

    def test_con_refresh_ya_revocado_es_idempotente(self, cliente, jugador):
        refresh = _login(cliente).cookies['refresh'].value
        cliente.post(URL_LOGOUT)

        cliente.cookies['refresh'] = refresh
        respuesta = cliente.post(URL_LOGOUT)

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.LOGOUT).count() == 1
