from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.droits import a_droit


class LectureLogistique(BasePermission):
    """Lecture : tout niveau Logistique ; écriture : responsable."""

    message = 'Accès non autorisé à la Logistique.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and a_droit(user, 'logistique')):
            return False
        return request.method in SAFE_METHODS or a_droit(user, 'logistique', 'responsable')
