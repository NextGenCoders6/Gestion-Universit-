"""Outils communs des tests d'API de la Scolarité."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.models import Classe, RattachementFaculte
from core.tests import fabriques as f
from scolarite.tests.fabriques import Monde


def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def compte(username, groupes=(), faculte=None):
    u = User.objects.create_user(username, password='Mot-de-passe-1')
    definir_droits(u, list(groupes))
    if faculte is not None:
        RattachementFaculte.objects.create(user=u, faculte=faculte)
    return u


class Base(TestCase):
    def setUp(self):
        self.m = Monde()
        # Une seconde faculté, hors du périmètre des comptes rattachés à la FST.
        self.fse = f.faculte('FSE')
        dep_eco = f.departement(self.fse, 'Économie')
        self.eco = f.portail(self.fse, 'ECO')
        self.l1_eco = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 1), portail=self.eco)
        f.ec(f.ue('UE-ECO-11', 'S1', port=self.eco), 'MICRO', credits=4, dep=dep_eco)
        self.secretariat = client(compte('secretariat', ['scolarite_secretariat']))
        self.secretariat_fst = client(compte('secretariat_fst', ['scolarite_secretariat'], faculte=self.m.fac))
        self.faculte = client(compte('faculte', ['scolarite_faculte']))
        self.faculte_fst = client(compte('faculte_fst', ['scolarite_faculte'], faculte=self.m.fac))
        self.autre = client(compte('autre', ['edt_responsable']))
