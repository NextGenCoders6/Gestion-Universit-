from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.throttles import limiter_connexion_admin

admin.site.site_header = 'UCCB — Administration technique'
admin.site.login = limiter_connexion_admin(admin.site.login)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/core/', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
