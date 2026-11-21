"""Résumé EDT du launchpad : séances publiées de la semaine, dans le périmètre de l'utilisateur."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits
from edt.tests.fabriques import Monde, seance_brute
from edt.tests.test_perimetre import compte_de

URL = '/api/core/lanceur/'


def tuiles(user):
    c = APIClient()
    c.force_authenticate(user)
    return {e['module']: e for e in c.get(URL).data}


@patch('edt.lanceur.timezone.localdate', return_value=date(2026, 11, 19))
class ResumeEdtTests(TestCase):
    def setUp(self):
        cache.clear()
        self.m = Monde()
        m = self.m
        seance_brute(m.algo, m.l1, m.ens, jour=date(2026, 11, 17))
        seance_brute(m.bdd, m.l2, m.ens, jour=date(2026, 11, 18))
        seance_brute(m.bdd, m.l2, m.ens, jour=date(2026, 11, 24))                      # semaine suivante
        seance_brute(m.algo, m.l1, m.ens, jour=date(2026, 11, 20), statut='brouillon')
        self.responsable = User.objects.create_user('resp', password='x')
        definir_droits(self.responsable, ['edt_responsable'])

    def test_seances_de_la_semaine(self, _jour):
        self.assertEqual(tuiles(self.responsable)['edt'], {
            'module': 'edt', 'valeur': 2, 'unite': '', 'libelle': 'séances cette semaine',
            'detail': '1 brouillon à publier', 'ton': 'normal'})

    def test_perimetre_chef(self, _jour):
        self.m.dep.chef = self.m.ens
        self.m.dep.save()
        chef = compte_de(self.m.ens, 'chef')   # Informatique : la L2 INFO seulement, pas la L1 MIP
        e = tuiles(chef)['edt']
        self.assertEqual(e['valeur'], 1)
        self.assertEqual(e['detail'], 'Aucun brouillon')

    def test_sans_droit_edt_pas_de_tuile(self, _jour):
        sans = User.objects.create_user('sans', password='x')
        definir_droits(sans, ['parametres_responsable'])
        self.assertNotIn('edt', tuiles(sans))
