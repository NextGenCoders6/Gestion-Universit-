"""Authentification JWT de l'ERP : un profil suspendu est refusé sur toute l'API.

La vérification est faite ici, et non par une permission par défaut, parce
qu'une vue qui déclare ses propres permission_classes remplacerait la valeur
par défaut et perdrait le contrôle.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.permissions import ProfilSuspendu, personne_suspendue


class AuthentificationJWT(JWTAuthentication):
    def authenticate(self, request):
        resultat = super().authenticate(request)
        if resultat is not None:
            personne = personne_suspendue(resultat[0])
            if personne is not None:
                raise ProfilSuspendu(personne.motif_suspension)
        return resultat
