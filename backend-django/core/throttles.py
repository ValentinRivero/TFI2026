from rest_framework.throttling import SimpleRateThrottle


class PorIpRateThrottle(SimpleRateThrottle):
    """Cuenta por IP aunque la petición traiga un usuario autenticado."""

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class LoginRateThrottle(PorIpRateThrottle):
    """Limita los intentos de inicio de sesión por IP, haya o no un usuario autenticado en la petición."""

    scope = 'login'


class RegistroRateThrottle(PorIpRateThrottle):
    """Frena la creación masiva de cuentas desde una misma IP."""

    scope = 'registro'
