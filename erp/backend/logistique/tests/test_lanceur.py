"""Résumé Logistique du launchpad : bus en service et alertes."""
from django.core.cache import cache
from django.test import TestCase

from logistique.tests.fabriques import bus
from logistique.tests.test_api import client

URL = '/api/core/lanceur/'


class ResumeLogistiqueTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_logistique_bus_actifs(self):
        bus('01')
        bus('02')
        bus('03', statut='maintenance')
        e = next(x for x in client('lu', ['logistique_utilisateur']).get(URL).data if x['module'] == 'logistique')
        self.assertEqual(e, {'module': 'logistique', 'valeur': 2, 'unite': '', 'libelle': 'bus en service',
                             'detail': 'Aucune alerte', 'ton': 'normal'})
