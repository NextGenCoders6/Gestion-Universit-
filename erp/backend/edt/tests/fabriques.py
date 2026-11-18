"""Fabriques de test du module EDT (s'appuient sur celles du socle)."""
from datetime import date, time

from core.models import Classe, Enseignant
from core.tests import fabriques as f
from edt.models import AffectationEC, Seance


class Monde:
    """Une année avec ses deux périodes, une classe L1 MIP et une L2 INFO, des EC."""

    def __init__(self):
        self.annee = f.annee('2026-2027', en_cours=True)
        self.p1 = f.periode(self.annee, 1)
        self.p2 = f.periode(self.annee, 2)
        self.fac = f.faculte()
        self.dep = f.departement(self.fac, 'Informatique')
        self.dep_math = f.departement(self.fac, 'Mathématiques')
        self.mip = f.portail(self.fac, 'MIP')
        self.info = f.filiere(self.dep, self.mip, 'INFO')
        self.l1 = Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 1), portail=self.mip)
        self.l2 = Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 2), filiere=self.info)
        self.ue_s1 = f.ue('UE-S1', 'S1', port=self.mip)
        self.ue_s3 = f.ue('UE-S3', 'S3', fil=self.info)
        self.algo = f.ec(self.ue_s1, 'ALGO', credits=2, dep=self.dep)   # 24 h
        self.bdd = f.ec(self.ue_s3, 'BDD', credits=3, dep=self.dep)     # 36 h
        self.ens = enseignant('Ngoma', self.dep)
        self.ens2 = enseignant('Okemba', self.dep)


def enseignant(nom, dep):
    return Enseignant.objects.create(personne=f.personne(nom=nom, prenom='Test'), departement=dep)


def affectation(ec, classe, ens, heures=24, type_seance=None, **kw):
    return AffectationEC.objects.create(ec=ec, classe=classe, enseignant=ens, heures_prevues=heures,
                                        type_seance=type_seance, **kw)


def seance_brute(ec, classe, ens, jour=date(2026, 10, 5), debut=time(9, 0), fin=time(11, 0),
                 statut='Confirmée', type_seance='CM', **kw):
    """Crée une séance sans passer par les règles de validation (pour tester les quotas)."""
    s = Seance(ec=ec, classe=classe, enseignant=ens, date_seance=jour, heure_debut=debut, heure_fin=fin,
               statut=statut, type_seance=type_seance, **kw)
    Seance.objects.bulk_create([s])
    return Seance.objects.order_by('-pk').first()
