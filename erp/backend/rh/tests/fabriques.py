"""Fabriques de test du module RH."""
from datetime import date
from decimal import Decimal

from core.models import Employe
from core.tests import fabriques as f
from edt.tests.fabriques import enseignant
from rh.models import Contrat


def employe(nom='Bouanga', fonction='gardien', **kw):
    return Employe.objects.create(personne=f.personne(nom=nom, prenom='Marc', genre='M'), fonction=fonction, **kw)


def vacataire(personne, debut=date(2026, 9, 1), fin=date(2027, 7, 31), taux='5000'):
    return Contrat.objects.create(personne=personne, type='vacataire', date_debut=debut, date_fin=fin,
                                  taux_horaire=Decimal(taux))


def permanent(personne, debut=date(2025, 9, 1), fin=None, salaire='450000'):
    return Contrat.objects.create(personne=personne, type='permanent', date_debut=debut, date_fin=fin,
                                  salaire_mensuel=Decimal(salaire))


__all__ = ['employe', 'enseignant', 'vacataire', 'permanent']
