"""Passe finale (phase 6) : défauts reportés de la Finance."""
from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from finance import journal, paiements
from finance.tests.fabriques import tarif
from scolarite.tests.fabriques import Monde, inscrit


class DateMinimaleTests(TestCase):
    def test_bornes(self):
        with mock.patch('finance.journal.timezone.localdate', return_value=date(2026, 11, 18)):
            self.assertEqual(journal.date_valide(date(2025, 9, 1)), date(2025, 9, 1))
            for jour in (date(1900, 1, 1), date(2025, 8, 31)):
                with self.subTest(jour=jour), self.assertRaises(ValidationError) as ctx:
                    journal.date_valide(jour)
                self.assertIn('date', ctx.exception.message_dict)
        with mock.patch('finance.journal.timezone.localdate', return_value=date(2027, 3, 1)):
            self.assertEqual(journal.date_valide(date(2025, 9, 1)), date(2025, 9, 1))


class CaissierMasqueTests(TestCase):
    def test_etudiant_ne_voit_pas_le_caissier(self):
        m = Monde()
        tarif(m.annee, m.l1.parcours)
        i = inscrit(m.l1)
        caisse = User.objects.create_user('caisse_principale')
        paiements.encaisser(i.frais, '150000', 'especes', par=caisse)
        u = User.objects.create_user('etu', password='x')
        p = i.etudiant.personne
        p.user = u
        p.save()
        c = APIClient()
        c.force_authenticate(u)
        r = c.get('/api/scolarite/moi/frais/')
        self.assertNotIn('caisse_principale', str(r.data))
        self.assertNotIn('par', r.data[0]['paiements'][0])
