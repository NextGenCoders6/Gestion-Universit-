from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from core.spa import fichier_frontend, spa_index
from core.throttles import limiter_connexion_admin

admin.site.site_header = 'UCCB — Administration technique'
admin.site.login = limiter_connexion_admin(admin.site.login)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/core/', include('core.urls')),
    path('api/edt/', include('edt.urls')),
    path('api/scolarite/', include('scolarite.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + [
    # Fichiers du build de l'interface (Vite : base « / »).
    re_path(r'^(?P<chemin>assets/.+|favicon\.svg|icons\.svg)$', fichier_frontend),
    # Toute autre URL hors API / administration / fichiers : l'interface React.
    re_path(r'^(?!api/|admin/|media/|static/|assets/).*$', spa_index),
]
