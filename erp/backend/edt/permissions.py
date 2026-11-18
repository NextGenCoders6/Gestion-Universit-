from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.droits import a_droit
from edt.perimetre import classes_gerables, peut_gerer_classe


class LectureEdt(BasePermission):
    """Lecture : tout niveau du module ; écriture : responsable ou périmètre (chef, référent)."""

    message = "Accès non autorisé à l'emploi du temps."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and a_droit(user, 'edt')):
            return False
        if request.method in SAFE_METHODS:
            return True
        return a_droit(user, 'edt', 'responsable') or a_droit(user, 'edt', 'perimetre')

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        classe = getattr(obj, 'classe', None)
        return classe is None or peut_gerer_classe(request.user, classe)


GestionEdt = LectureEdt  # même règle ; nom explicite pour les vues d'écriture

__all__ = ['LectureEdt', 'GestionEdt', 'classes_gerables']
