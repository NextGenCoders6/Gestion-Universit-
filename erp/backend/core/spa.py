"""Service de l'interface React (build Vite) par Django.

Toute URL hors API, administration et fichiers reçoit index.html : le routeur
React prend le relais côté navigateur. Les fichiers du build (assets/, icônes)
sont servis depuis FRONTEND_DIST.
"""
from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.static import serve

MESSAGE_BUILD_ABSENT = (
    "Interface non construite : lancez « npm run build » dans erp/frontend, "
    "ou utilisez le serveur de développement Vite (npm run dev)."
)


def spa_index(request, *args, **kwargs):
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.is_file():
        return HttpResponse(MESSAGE_BUILD_ABSENT, status=503, content_type='text/plain; charset=utf-8')
    return HttpResponse(index.read_text(encoding='utf-8'), content_type='text/html; charset=utf-8')


def fichier_frontend(request, chemin):
    if not (settings.FRONTEND_DIST / chemin).is_file():
        raise Http404
    return serve(request, chemin, document_root=settings.FRONTEND_DIST)
