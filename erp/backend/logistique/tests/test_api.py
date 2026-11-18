from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.models import JournalAudit
from finance import transports
from logistique.models import AffectationTransport
from logistique.tests.fabriques import bus, chauffeur, trajet

AUJ = date.today()


def client(nom, groupes):
    u = User.objects.create_user(nom, password='x')
    definir_droits(u, list(groupes))
    c = APIClient()
    c.force_authenticate(u)
    return c


class Base(TestCase):
    def setUp(self):
        self.b = bus('01')
        self.t = trajet()
        self.c = chauffeur()
        self.c2 = chauffeur('Malonga')
        self.resp = client('log_r', ['logistique_responsable'])
        self.util = client('log_u', ['logistique_utilisateur'])
        self.fin = client('fin_r', ['finance_responsable'])
        self.fin_u = client('fin_u', ['finance_utilisateur'])
        self.autre = client('autre', ['rh_responsable'])

    def affecter(self, c=None, chauffeur=None, b=None, debut=None):
        return (c or self.resp).post('/api/logistique/affectations/', {
            'bus': (b or self.b).pk, 'chauffeur': (chauffeur or self.c).pk, 'trajet': self.t.pk,
            'date_debut': str(debut or AUJ)}, format='json')


class AffectationsAPITests(Base):
    def test_creation_et_refus(self):
        r = self.affecter()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['chauffeur_nom'], 'NZABA Marc')
        self.assertTrue(r.data['active'])
        self.assertTrue(JournalAudit.objects.filter(module='logistique', action='affectation').exists())
        b2 = bus('02')
        r = self.affecter(b=b2)
        self.assertEqual(r.status_code, 400)
        self.assertIn('chauffeur', r.data)
        r = self.affecter(chauffeur=self.c2)
        self.assertEqual(r.status_code, 400)
        self.assertIn('bus', r.data)

    def test_terminer_et_liste_active(self):
        a = self.affecter().data
        self.assertEqual(len(self.util.get('/api/logistique/affectations/?actives=true').data['results']), 1)
        r = self.resp.post(f"/api/logistique/affectations/{a['id']}/terminer/", {'date_fin': str(AUJ)}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.affecter(chauffeur=self.c2, debut=AUJ + timedelta(days=1)).status_code, 201)

    def test_statut_du_bus(self):
        a = self.affecter().data
        r = self.resp.post(f'/api/logistique/bus/{self.b.pk}/statut/', {'statut': 'maintenance'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['affectations_terminees'], 1)
        self.assertEqual(AffectationTransport.objects.get(pk=a['id']).date_fin, AUJ)
        self.assertEqual(self.affecter(chauffeur=self.c2).status_code, 400)

    def test_chauffeurs_disponibles(self):
        self.affecter()
        r = self.util.get(f'/api/logistique/chauffeurs/?date={AUJ}')
        self.assertEqual([x['nom_complet'] for x in r.data], ['MALONGA Marc'])

    def test_droits(self):
        self.assertEqual(self.affecter(c=self.util).status_code, 403)
        self.assertEqual(self.util.get('/api/logistique/bus/').status_code, 200)
        self.assertEqual(self.autre.get('/api/logistique/bus/').status_code, 403)

    def test_bus_utilise_non_supprimable(self):
        self.affecter()
        r = self.resp.delete(f'/api/logistique/bus/{self.b.pk}/')
        self.assertEqual(r.status_code, 400)

    def test_tableau_de_bord(self):
        self.affecter()
        bus('02', statut='maintenance')
        transports.enregistrer(self.b, 'carburant', '45000')
        d = self.util.get('/api/logistique/tableau-de-bord/').data
        self.assertEqual(d['bus_par_statut'], {'actif': 1, 'maintenance': 1, 'hors_service': 0})
        self.assertEqual((d['affectations_actives'], d['chauffeurs_disponibles']), (1, 1))
        self.assertEqual(d['couts_mois'], 45000.0)
        self.assertEqual(d['alertes'], [])


class CoutsEtTransportsTests(Base):
    def test_couts_lus_par_la_logistique(self):
        transports.enregistrer(self.b, 'carburant', '45000')
        r = self.util.get('/api/logistique/couts/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['total'], 45000.0)
        self.assertEqual(r.data['par_bus'][0]['numero'], '01')

    def test_saisie_reservee_au_responsable_finance(self):
        corps = {'bus': self.b.pk, 'type': 'carburant', 'montant': '45000', 'description': 'Plein'}
        self.assertEqual(self.resp.post('/api/finance/transports/', corps, format='json').status_code, 403)
        self.assertEqual(self.fin_u.post('/api/finance/transports/', corps, format='json').status_code, 403)
        r = self.fin.post('/api/finance/transports/', corps, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.fin_u.get('/api/finance/transports/').data['count'], 1)
        r = self.fin.post('/api/finance/transports/', {**corps, 'montant': '-5'}, format='json')
        self.assertEqual(r.status_code, 400)
        dep = self.fin.get('/api/finance/transports/').data['results'][0]
        self.assertEqual(self.fin_u.get(f"/api/finance/transports/{dep['id']}/recu.pdf").status_code, 200)
        r = self.fin.post(f"/api/finance/transports/{dep['id']}/annuler/", {'motif': 'Doublon'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.util.get('/api/logistique/couts/').data['total'], 0.0)
