from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from core.spa import fichier_frontend, spa_index
from finance import urls as finance_urls
from scolarite.views_documents import verifier_document
from core.throttles import limiter_connexion_admin

admin.site.site_header = 'UCCB — Administration technique'
admin.site.login = limiter_connexion_admin(admin.site.login)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/core/', include('core.urls')),
    path('api/edt/', include('edt.urls')),
    # Situation des frais de l'étudiant : servie par la Finance, dans l'espace étudiant.
    path('api/scolarite/moi/frais/', include(finance_urls.urlpatterns_etudiant)),
    path('api/scolarite/', include('scolarite.urls')),
    path('api/rh/', include('rh.urls')),
    path('api/finance/', include('finance.urls')),
    path('api/logistique/', include('logistique.urls')),
    # Page publique ouverte par le QR code des documents officiels (hors SPA).
    path('verifier/<str:jeton>', verifier_document, name='verifier_document'),
    path('verifier/<str:jeton>/', verifier_document),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + [
    # Fichiers du build de l'interface (Vite : base « / »).
    re_path(r'^(?P<chemin>assets/.+|favicon\.svg|icons\.svg)$', fichier_frontend),
    # Toute autre URL hors API / administration / fichiers : l'interface React.
    re_path(r'^(?!api/|admin/|media/|static/|assets/|verifier/).*$', spa_index),
]
