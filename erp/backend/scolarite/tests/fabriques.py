"""Fabriques de test du module Scolarité (s'appuient sur celles du socle)."""
from datetime import date
from decimal import Decimal

from core.models import Classe, Etudiant
from core.tests import fabriques as f


class Monde:
    """Une année, une L1 MIP (S1 : deux UE, S2 : une UE) et une L2 INFO."""

    def __init__(self):
        self.annee = f.annee('2026-2027', en_cours=True)
        self.fac = f.faculte('FST')
        self.dep = f.departement(self.fac, 'Informatique')
        self.mip = f.portail(self.fac, 'MIP')
        self.info = f.filiere(self.dep, self.mip, 'INFO')
        self.l1 = Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 1), portail=self.mip)
        self.l2 = Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 2), filiere=self.info)
        self.ue1 = f.ue('UE-INF-11', 'S1', port=self.mip)
        self.ue2 = f.ue('UE-MAT-11', 'S1', port=self.mip)
        self.ue3 = f.ue('UE-INF-12', 'S2', port=self.mip)
        self.algo = f.ec(self.ue1, 'ALGO', credits=3, dep=self.dep)
        self.prog = f.ec(self.ue1, 'PROG', credits=3, dep=self.dep)
        self.analyse = f.ec(self.ue2, 'ANALYSE', credits=4, dep=self.dep)
        self.reseau = f.ec(self.ue3, 'RESEAU', credits=2, dep=self.dep)
        self.ue_s3 = f.ue('UE-INF-21', 'S3', port=None, fil=self.info)
        self.bdd = f.ec(self.ue_s3, 'BDD', credits=3, dep=self.dep)


def etudiant(nom='Mabiala', prenom='Grâce', annee=None, **kw):
    p = f.personne(nom=nom, prenom=prenom, **kw)
    return Etudiant.objects.create(personne=p, annee_entree=annee or f.annee())


def inscrit(classe, nom='Mabiala', prenom='Grâce', **kw):
    from scolarite.inscriptions import inscrire
    return inscrire(etudiant(nom, prenom, classe.annee, **kw), classe, type='premiere')


def noter(inscription, ec, devoir=None, session=None, sr=None, absent=False):
    n = inscription.notes.get(ec=ec)
    n.note_devoir = None if devoir is None else Decimal(str(devoir))
    n.note_session = None if session is None else Decimal(str(session))
    n.note_sr = None if sr is None else Decimal(str(sr))
    n.est_absent = absent
    n.save()
    return n


AUJOURDHUI = date(2026, 11, 18)
