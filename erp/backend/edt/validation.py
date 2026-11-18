"""Règles de validation des séances et affectations.

Port de uccb_backend/EDT_app/validation_seance.py sur le référentiel du socle.
"""
from django.core.exceptions import ValidationError


def valider_ec_dans_classe(ec, classe):
    """L'EC appartient au programme de la classe : même portail/filière et semestre du niveau."""
    ue = ec.ue
    meme_rattachement = (ue.portail_id and ue.portail_id == classe.portail_id) or (
        ue.filiere_id and ue.filiere_id == classe.filiere_id)
    if not meme_rattachement or ue.semestre not in classe.semestres:
        raise ValidationError({'ec': (
            f"L'EC {ec.code} ({ue.semestre}) ne fait pas partie du programme de la classe {classe.libelle}."
        )})
