"""Résumé RH du launchpad : contrats arrivant à échéance sous 30 jours."""
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from rh.tests.fabriques import employe, permanent
from rh.tests.test_api import client

URL = '/api/core/lanceur/'


def tuile(c):
    return next(e for e in c.get(URL).data if e['module'] == 'rh')


class ResumeRhTests(TestCase):
    def setUp(self):
        cache.clear()
        self.lecteur = client(['rh_utilisateur'])

    def test_rh_contrats_a_echeance(self):
        jour = timezone.localdate()
        permanent(employe('Gardien').personne, debut=jour - timedelta(days=200), fin=jour + timedelta(days=10))
        permanent(employe('Cuisinier', 'cuisinier').personne, debut=jour - timedelta(days=200), fin=None)
        e = tuile(self.lecteur)
        self.assertEqual((e['valeur'], e['libelle'], e['ton']), (1, 'contrats à échéance', 'alerte'))
        self.assertEqual(e['detail'], 'Aucune vacation à confirmer')

    def test_rh_sans_echeance(self):
        e = tuile(self.lecteur)
        self.assertEqual((e['valeur'], e['ton']), (0, 'normal'))

    def test_rh_mis_en_cache(self):
        from rh import views
        with patch('rh.views.lignes_vacations', wraps=views.lignes_vacations) as calcul:
            tuile(self.lecteur)
            tuile(self.lecteur)
        self.assertEqual(calcul.call_count, 1)

    def test_rh_ignore_les_parametres_de_l_url(self):
        e = next(x for x in self.lecteur.get(URL + '?annee=abc&faculte=99').data if x['module'] == 'rh')
        self.assertEqual(e['valeur'], 0)
