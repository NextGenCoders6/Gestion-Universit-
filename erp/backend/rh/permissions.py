from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.droits import a_droit


class LectureRH(BasePermission):
    """Lecture : tout niveau RH ; écriture : responsable RH."""

    message = 'Accès non autorisé aux ressources humaines.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and a_droit(user, 'rh')):
            return False
        return request.method in SAFE_METHODS or a_droit(user, 'rh', 'responsable')


class LectureVacations(BasePermission):
    """Vacations en lecture : la RH (toutes) et la faculté (son périmètre)."""

    message = 'Accès non autorisé aux vacations.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (a_droit(user, 'rh') or a_droit(user, 'scolarite', 'faculte')))


class ConfirmationVacations(BasePermission):
    message = 'La confirmation des vacations est réservée à la faculté.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and a_droit(user, 'scolarite', 'faculte'))


def voit_donnees_sensibles(user):
    return a_droit(user, 'rh', 'responsable')
