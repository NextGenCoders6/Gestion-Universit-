from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from finance import paiements
from finance.tests.fabriques import tarif
from scolarite.moteur import deliberation
from scolarite.tests.fabriques import Monde, inscrit, noter


class EspaceFraisTests(TestCase):
    def setUp(self):
        self.m = Monde()
        tarif(self.m.annee, self.m.l1.parcours)
        self.i = inscrit(self.m.l1, 'Moi')
        u = User.objects.create_user('etu', password='x')
        p = self.i.etudiant.personne
        p.user = u
        p.save()
        self.etu = APIClient()
        self.etu.force_authenticate(u)
        noter(self.i, self.m.algo, devoir=15, session=15)
        deliberation(self.m.l1, 'S1', enregistrer=True)
        self.autre = inscrit(self.m.l1, 'Autre')

    def jour(self, j):
        return mock.patch('finance.frais.timezone.localdate', return_value=j)

    def test_situation_des_frais(self):
        p = paiements.encaisser(self.i.frais, '150000', 'especes', date=date(2026, 10, 15))
        paiements.encaisser(self.autre.frais, '300000', 'especes', date=date(2026, 10, 15))
        with self.jour(date(2026, 12, 6)):
            r = self.etu.get('/api/scolarite/moi/frais/')
        self.assertEqual(r.status_code, 200, r.data)
        dossier = r.data[0]
        self.assertEqual((dossier['montant_du'], dossier['montant_paye'], dossier['en_retard']), (1500000.0, 150000.0, True))
        self.assertEqual(dossier['prochaine_echeance']['numero'], 2)
        self.assertEqual([x['montant'] for x in dossier['paiements']], [150000.0])
        self.assertEqual(self.etu.get(f'/api/scolarite/moi/frais/paiements/{p.pk}/recu.pdf').status_code, 200)
        autre = self.autre.frais.paiements.get()
        self.assertEqual(self.etu.get(f'/api/scolarite/moi/frais/paiements/{autre.pk}/recu.pdf').status_code, 404)

    def test_resultats_masques_si_retard(self):
        with self.jour(date(2026, 11, 5)):
            s1 = self.etu.get('/api/scolarite/moi/notes/').data['inscriptions'][0]['semestres'][0]
        self.assertTrue(s1['deliberee'])
        self.assertEqual(s1['resultat']['decision'], 'ADMIS')    # à jour : 1re mensualité due ce jour-là
        with self.jour(date(2026, 11, 6)):
            r = self.etu.get('/api/scolarite/moi/notes/').data
        s1 = r['inscriptions'][0]['semestres'][0]
        self.assertIsNone(s1['resultat'])
        self.assertTrue(r['inscriptions'][0]['resultats_masques'])
        self.assertIn('mensualité', r['inscriptions'][0]['message_resultats'])
        self.assertEqual(s1['ues'][0]['ecs'][0]['note'], 15.0)   # les notes restent visibles
        paiements.encaisser(self.i.frais, Decimal('150000'), 'especes')
        with self.jour(date(2026, 11, 6)):
            s1 = self.etu.get('/api/scolarite/moi/notes/').data['inscriptions'][0]['semestres'][0]
        self.assertEqual(s1['resultat']['decision'], 'ADMIS')
