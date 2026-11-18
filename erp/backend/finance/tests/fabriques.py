"""Fabriques de test du module Finance."""
from decimal import Decimal

from finance.models import Tarif


def tarif(annee, parcours, montant='1500000', **kw):
    return Tarif.objects.create(annee=annee, parcours=parcours, montant=Decimal(montant), **kw)
