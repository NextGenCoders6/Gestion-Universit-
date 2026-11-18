"""Inscription d'un étudiant dans une classe annuelle."""
from django.db import transaction
from django.utils import timezone

from scolarite.models import Inscription, Note

# Rappels appelés après chaque inscription (la Finance y branchera la facturation en phase 5).
APRES_INSCRIPTION = []

# Fonctions (inscription) → message ou None : un message masque à l'étudiant moyennes et décisions de cette
# inscription (la Finance y branche les mensualités échues non payées).
MOTIFS_MASQUAGE_RESULTATS = []


@transaction.atomic
def inscrire(etudiant, classe, *, type, date=None):
    """Crée l'inscription, les lignes de notes vides du programme de la classe, puis prévient les rappels."""
    inscription = Inscription.objects.create(etudiant=etudiant, classe=classe, type=type,
                                             date_inscription=date or timezone.localdate())
    Note.objects.bulk_create([Note(inscription=inscription, ec=ec) for ec in classe.ecs_au_programme()])
    for rappel in list(APRES_INSCRIPTION):
        rappel(inscription)
    return inscription
