from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.droits import a_droit


def message_suspension(motif):
    return f'Votre profil est suspendu. Motif : {motif or "non précisé"}.'


class ProfilSuspendu(PermissionDenied):
    """403 dont le corps porte « code: profil_suspendu », repéré par le frontend."""

    def __init__(self, motif):
        super().__init__(detail={'detail': message_suspension(motif), 'code': 'profil_suspendu'})


def personne_suspendue(user):
    personne = getattr(user, 'personne', None) if user and user.pk else None
    return personne if personne is not None and personne.est_suspendue else None


class CompteActif(BasePermission):
    """Refuse toute action à une personne suspendue, même avec un jeton encore valide."""

    def has_permission(self, request, view):
        personne = personne_suspendue(request.user)
        if personne is not None:
            raise ProfilSuspendu(personne.motif_suspension)
        return True


def droit_module(module, niveau=None):
    class DroitModule(BasePermission):
        message = 'Accès non autorisé à ce module.'

        def has_permission(self, request, view):
            return bool(request.user and request.user.is_authenticated and a_droit(request.user, module, niveau))

    DroitModule.__name__ = f'Droit_{module}_{niveau or "tous"}'
    return DroitModule


class LectureAuthentifieeEcritureParametres(BasePermission):
    """Lecture pour tout utilisateur connecté, écriture pour les responsables Paramètres."""

    message = "Seuls les responsables Paramètres peuvent modifier le référentiel."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return a_droit(request.user, 'parametres')
