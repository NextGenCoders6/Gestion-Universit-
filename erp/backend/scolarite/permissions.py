from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.droits import a_droit


class Secretariat(BasePermission):
    """Lecture : tout niveau de la Scolarité ; écriture : secrétariat."""

    message = 'Accès non autorisé à la Scolarité.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and a_droit(user, 'scolarite')):
            return False
        return request.method in SAFE_METHODS or a_droit(user, 'scolarite', 'secretariat')


class Faculte(BasePermission):
    """Notes, délibérations, promotion : niveau faculté."""

    message = 'Réservé à la faculté (notes et délibérations).'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and a_droit(user, 'scolarite', 'faculte'))
