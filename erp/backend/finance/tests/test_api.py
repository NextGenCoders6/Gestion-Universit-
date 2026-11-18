from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.models import JournalAudit
from edt.tests.fabriques import affectation, seance_brute
from finance import paiements
from finance.models import FraisScolarite, Operation, Paie, Tarif
from finance.tests.fabriques import tarif
from rh import vacations
from rh.tests.fabriques import employe, permanent, vacataire
from scolarite.tests.fabriques import Monde, inscrit

D = Decimal
AUJ = date.today()


def client(nom, groupes):
    u = User.objects.create_user(nom, password='x')
    definir_droits(u, list(groupes))
    c = APIClient()
    c.force_authenticate(u)
    return c


class Base(TestCase):
    def setUp(self):
        self.m = Monde()
        tarif(self.m.annee, self.m.l1.parcours, nombre_mensualites=10)
        self.a = inscrit(self.m.l1, 'Alpha').frais
        self.b = inscrit(self.m.l1, 'Beta').frais
        self.c = inscrit(self.m.l2, 'Gamma').frais       # L2 : pas de tarif
        self.util = client('fin_u', ['finance_utilisateur'])
        self.resp = client('fin_r', ['finance_responsable'])
        self.param = client('param', ['parametres_responsable'])
        self.autre = client('autre', ['rh_responsable'])


class FraisTests(Base):
    def test_liste_et_filtres(self):
        paiements.encaisser(self.a, '1500000', 'especes')
        r = self.util.get('/api/finance/frais/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['count'], 3)
        self.assertEqual([x['nom_complet'] for x in self.util.get('/api/finance/frais/?statut=paye').data['results']],
                         ['ALPHA Grâce'])
        sans = self.util.get('/api/finance/frais/?q=gamma').data['results'][0]
        self.assertTrue(sans['sans_tarif'])
        self.assertEqual(self.autre.get('/api/finance/frais/').status_code, 403)

    def test_fiche_avec_echeancier(self):
        r = self.util.get(f'/api/finance/frais/{self.b.pk}/')
        self.assertEqual(len(r.data['echeances']), 10)
        self.assertEqual(r.data['echeances'][0]['montant'], 150000.0)

    def test_encaissement_par_l_utilisateur(self):
        r = self.util.post(f'/api/finance/frais/{self.a.pk}/paiements/', {'montant': '200000', 'mode': 'mobile_money',
                                                                          'reference': 'MM-1'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['dossier']['montant_paye'], 200000.0)
        self.assertTrue(JournalAudit.objects.filter(module='finance', action='paiement_frais').exists())
        r = self.util.post(f'/api/finance/frais/{self.a.pk}/paiements/', {'montant': '2000000', 'mode': 'especes'},
                           format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('montant', r.data)
        self.assertEqual(Operation.objects.count(), 1)

    def test_ajustement_annulation_reserves_au_responsable(self):
        p = paiements.encaisser(self.a, '100000', 'especes')
        url_aj = f'/api/finance/frais/{self.a.pk}/ajuster/'
        self.assertEqual(self.util.post(url_aj, {'montant': '900000'}, format='json').status_code, 403)
        self.assertEqual(self.resp.post(url_aj, {'montant': '900000'}, format='json').status_code, 200)
        url_an = f'/api/finance/paiements/{p.pk}/annuler/'
        self.assertEqual(self.util.post(url_an, {'motif': 'x'}, format='json').status_code, 403)
        r = self.resp.post(url_an, {'motif': 'Erreur'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.a.refresh_from_db()
        self.assertEqual(self.a.montant_paye, D('0'))

    def test_echeancier_adapte(self):
        url = f'/api/finance/frais/{self.b.pk}/echeancier/'
        corps = {'echeances': [{'mois': '2026-10', 'date_limite': '2026-11-05', 'montant': '750000'},
                               {'mois': '2026-11', 'date_limite': '2026-12-05', 'montant': '750000'}]}
        self.assertEqual(self.util.put(url, corps, format='json').status_code, 403)
        r = self.resp.put(url, corps, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(len(r.data['echeances']), 2)
        corps['echeances'][1]['montant'] = '1'
        self.assertEqual(self.resp.put(url, corps, format='json').status_code, 400)

    def test_recu(self):
        p = paiements.encaisser(self.a, '100000', 'especes')
        r = self.util.get(f'/api/finance/paiements/{p.pk}/recu.pdf')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))


class PaieTests(Base):
    def setUp(self):
        super().setUp()
        g = employe('Gardien')
        permanent(g.personne, debut=date(2026, 1, 1), salaire='120000')

    def test_generation_et_paiement(self):
        url = '/api/finance/paie/generer/'
        self.assertEqual(self.util.post(url, {'mois': '2026-10'}, format='json').status_code, 403)
        r = self.resp.post(url, {'mois': '2026-10'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['creees'], 1)
        self.assertEqual(self.resp.post(url, {'mois': '2026-10'}, format='json').data['creees'], 0)
        ligne = self.util.get('/api/finance/paie/?mois=2026-10&role=employe').data['results'][0]
        self.assertEqual((ligne['montant_du'], ligne['statut']), (120000.0, 'en_attente'))
        r = self.util.post(f"/api/finance/paie/{ligne['id']}/paiements/", {'montant': '1', 'mode': 'especes'},
                           format='json')
        self.assertEqual(r.status_code, 403)
        r = self.resp.post(f"/api/finance/paie/{ligne['id']}/paiements/", {'montant': '120000', 'mode': 'virement'},
                           format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['paie']['statut'], 'paye')


class JournalEtTableauTests(Base):
    def test_operations_manuelles_et_filtres(self):
        paiements.encaisser(self.a, '300000', 'especes')
        self.assertEqual(self.util.post('/api/finance/operations/', {'libelle': 'Don', 'montant': '5000'},
                                        format='json').status_code, 403)
        r = self.resp.post('/api/finance/operations/', {'libelle': 'Achat de craies', 'montant': '-15000'},
                           format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.util.get('/api/finance/operations/?categorie=manuelle').data['count'], 1)
        self.assertEqual(self.util.get('/api/finance/operations/?q=craies').data['count'], 1)
        r = self.resp.post(f"/api/finance/operations/{r.data['id']}/annuler/", {'motif': 'Doublon'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def test_tableau_de_bord(self):
        paiements.encaisser(self.a, '1500000', 'especes')
        paiements.encaisser(self.b, '100000', 'especes')
        paiements.operation_manuelle('Craies', '-15000')
        d = self.util.get(f'/api/finance/tableau-de-bord/?annee={self.m.annee.pk}').data
        self.assertEqual((d['frais_attendus'], d['frais_encaisses']), (3000000.0, 1600000.0))
        self.assertAlmostEqual(d['taux_recouvrement'], 53.3, places=1)
        self.assertEqual(d['dossiers_sans_tarif'], 1)
        self.assertEqual((d['recettes'], d['depenses'], d['solde']), (1600000.0, 15000.0, 1585000.0))
        self.assertEqual(len(d['tresorerie']), 12)
        self.assertEqual(d['tresorerie'][-1]['recettes'], 1600000.0)


class TarifsTests(Base):
    def test_ecriture_reservee_a_parametres(self):
        corps = {'annee': self.m.annee.pk, 'parcours': self.m.l2.parcours.pk, 'montant': '1200000',
                 'nombre_mensualites': 6, 'jour_echeance': 10}
        self.assertEqual(self.resp.post('/api/finance/tarifs/', corps, format='json').status_code, 403)
        r = self.param.post('/api/finance/tarifs/', corps, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(len(r.data['echeancier']), 6)
        self.assertEqual(r.data['echeancier'][0]['date_limite'], '2026-11-10')
        self.c.refresh_from_db()
        self.assertEqual(self.c.montant_du, D('1200000'))
        self.assertEqual(self.util.get('/api/finance/tarifs/').status_code, 200)
        self.assertEqual(self.param.get('/api/finance/tarifs/').status_code, 200)
        self.assertTrue(JournalAudit.objects.filter(action='tarif').exists())


class VacationPayeeTests(TestCase):
    def test_vacation_dans_la_paie(self):
        from edt.tests.fabriques import Monde as MondeEdt
        m = MondeEdt()
        vacataire(m.ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200), taux='5000')
        a = affectation(m.algo, m.l1, m.ens, 2)
        seance_brute(m.algo, m.l1, m.ens, jour=AUJ - timedelta(days=3))
        vacations.confirmer(a)
        lignes = client('fu', ['finance_utilisateur']).get('/api/finance/paie/?origine=vacation').data['results']
        self.assertEqual([(l['origine'], l['montant_du']) for l in lignes], [('vacation', 10000.0)])
        self.assertIn('ALGO', lignes[0]['libelle'])
        self.assertEqual(Paie.objects.count(), 1)
        self.assertTrue(Tarif.objects.count() == 0 and FraisScolarite.objects.count() == 0)
