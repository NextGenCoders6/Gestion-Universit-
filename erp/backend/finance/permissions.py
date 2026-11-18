from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.droits import a_droit


class LectureFinance(BasePermission):
    """Lecture : tout niveau Finance ; écriture : responsable (les actions d'encaissement l'élargissent)."""

    message = 'Accès non autorisé à la Finance.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and a_droit(user, 'finance')):
            return False
        return request.method in SAFE_METHODS or a_droit(user, 'finance', 'responsable')


class Encaissement(BasePermission):
    message = 'Accès non autorisé à la Finance.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and a_droit(request.user, 'finance'))


class ResponsableFinance(BasePermission):
    message = 'Réservé au responsable Finance.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and a_droit(request.user, 'finance', 'responsable'))


class Tarifs(BasePermission):
    """Lecture : Finance ou Paramètres ; écriture : responsable Paramètres."""

    message = 'La grille de tarifs se modifie dans Paramètres.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return a_droit(user, 'finance') or a_droit(user, 'parametres')
        return a_droit(user, 'parametres')
