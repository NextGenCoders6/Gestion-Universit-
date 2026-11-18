from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.models import JournalAudit, RattachementFaculte
from core.tests import fabriques as f
from edt.tests.fabriques import Monde, affectation, enseignant, seance_brute
from rh.models import HistoriqueVacation, Vacation
from rh.tests.fabriques import vacataire

AUJ = date.today()


def client(nom, groupes, faculte=None):
    u = User.objects.create_user(nom, password='x')
    definir_droits(u, list(groupes))
    if faculte is not None:
        RattachementFaculte.objects.create(user=u, faculte=faculte)
    c = APIClient()
    c.force_authenticate(u)
    return c


class ConfirmationAPITests(TestCase):
    def setUp(self):
        self.m = Monde()
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200), taux='5000')
        self.aff = affectation(self.m.algo, self.m.l1, self.m.ens, 4)
        for i in (3, 4):
            seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=AUJ - timedelta(days=i))
        self.fac = client('fac', ['scolarite_faculte'])
        self.fac_fst = client('fac_fst', ['scolarite_faculte'], faculte=self.m.fac)
        self.url = f'/api/rh/vacations/{self.aff.pk}'
        # Une affectation d'un EC de la FSE.
        fse = f.faculte('FSE')
        dep_eco = f.departement(fse, 'Économie')
        ec_eco = f.ec(f.ue('UE-ECO-31', 'S3', port=None, fil=self.m.info), 'MICRO', credits=2, dep=dep_eco)
        ens_eco = enseignant('Mavoungou', dep_eco)
        vacataire(ens_eco.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200))
        self.aff_fse = affectation(ec_eco, self.m.l2, ens_eco, 2, hors_departement=True)

    def test_confirmation_par_defaut(self):
        r = self.fac.post(f'{self.url}/confirmer/', {}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['vacation']['montant'], 20000.0)
        self.assertTrue(JournalAudit.objects.filter(module='rh', action='confirmation_vacation').exists())
        r = self.fac.get('/api/rh/vacations/?etat=confirmee')
        self.assertEqual([l['affectation'] for l in r.data], [self.aff.pk])

    def test_heures_modifiees(self):
        r = self.fac.post(f'{self.url}/confirmer/', {'heures_retenues': 3}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('motif', r.data)
        r = self.fac.post(f'{self.url}/confirmer/', {'heures_retenues': '3', 'motif': 'Séance écourtée'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['vacation']['heures_retenues'], 3.0)

    def test_double_confirmation(self):
        self.fac.post(f'{self.url}/confirmer/', {}, format='json')
        r = self.fac.post(f'{self.url}/confirmer/', {}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('déjà confirmée', str(r.data))
        self.assertEqual(Vacation.objects.count(), 1)

    def test_sans_contrat(self):
        self.m.ens.personne.contrats.all().delete()
        r = self.fac.post(f'{self.url}/confirmer/', {}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('contrat de vacataire', str(r.data))

    def test_retrait(self):
        self.fac.post(f'{self.url}/confirmer/', {}, format='json')
        self.assertEqual(self.fac.post(f'{self.url}/retirer/', {}, format='json').status_code, 400)
        r = self.fac.post(f'{self.url}/retirer/', {'motif': 'Erreur de classe'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIsNone(r.data['vacation'])
        self.assertEqual(HistoriqueVacation.objects.filter(action='retrait').count(), 1)
        self.assertEqual(self.fac.post(f'{self.url}/retirer/', {'motif': 'x'}, format='json').status_code, 400)

    def test_perimetre(self):
        url = f'/api/rh/vacations/{self.aff_fse.pk}'
        self.assertEqual(self.fac_fst.post(f'{url}/confirmer/', {}, format='json').status_code, 404)
        self.assertEqual(self.fac_fst.post(f'{url}/retirer/', {'motif': 'x'}, format='json').status_code, 404)
        self.assertEqual([l['affectation'] for l in self.fac_fst.get('/api/rh/vacations/').data], [self.aff.pk])
        self.assertEqual(self.fac_fst.post(f'{self.url}/confirmer/', {}, format='json').status_code, 200)

    def test_rh_et_secretariat_refuses(self):
        for groupes in (['rh_responsable'], ['scolarite_secretariat']):
            c = client('_'.join(groupes), groupes)
            self.assertEqual(c.post(f'{self.url}/confirmer/', {}, format='json').status_code, 403)
