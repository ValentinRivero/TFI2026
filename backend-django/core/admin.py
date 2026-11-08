from django.contrib import admin

from .models import (
    Cancha,
    Complejo,
    ComplejoServicio,
    Deporte,
    ExcepcionHoraria,
    HorarioApertura,
    LogAuditoria,
    Permiso,
    Reserva,
    Rol,
    RolPermiso,
    Servicio,
    TurnoFijo,
    Usuario,
)


class AdminBase(admin.ModelAdmin):
    list_display = ('__str__', 'estado', 'fecha_creacion')
    list_filter = ('estado',)
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    actions = ('desactivar_seleccionados',)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='Desactivar seleccionados (baja lógica)', permissions=('change',))
    def desactivar_seleccionados(self, request, queryset):
        cantidad = 0
        for instancia in queryset:
            instancia.desactivar()
            cantidad += 1
        self.message_user(request, f'{cantidad} registro(s) desactivado(s).')


@admin.register(Usuario)
class UsuarioAdmin(AdminBase):
    list_display = ('email', 'nombre_completo', 'rol', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'rol')
    search_fields = ('email', 'nombre_completo')
    exclude = ('password',)
    # La constancia de consentimiento solo la escribe el titular al aceptar la política.
    readonly_fields = AdminBase.readonly_fields + ('version_politica_aceptada', 'fecha_aceptacion_politica')


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(AdminBase):
    list_display = ('fecha_creacion', 'tipo_evento', 'accion', 'usuario', 'complejo', 'ip_origen')
    list_filter = ('tipo_evento',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


for modelo in (
    Rol,
    Permiso,
    RolPermiso,
    Complejo,
    Servicio,
    ComplejoServicio,
    Deporte,
    Cancha,
    HorarioApertura,
    ExcepcionHoraria,
    TurnoFijo,
    Reserva,
):
    admin.site.register(modelo, AdminBase)
