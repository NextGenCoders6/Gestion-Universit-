from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.models import Enseignant, Employe, JournalAudit
from edt.tests.fabriques import Monde, affectation, enseignant, seance_brute
from rh.models import Contrat
from rh.tests.fabriques import employe, permanent, vacataire

AUJ = date.today()


def client(groupes):
    u = User.objects.create_user('u' + '_'.join(groupes), password='x')
    definir_droits(u, list(groupes))
    c = APIClient()
    c.force_authenticate(u)
    return c


PERSONNE = {'nom': 'Moukoko', 'prenom': 'Albert', 'genre': 'M', 'email': 'albert.moukoko@uccb.cg'}
CONTRAT = {'type': 'vacataire', 'date_debut': str(AUJ - timedelta(days=10)), 'date_fin': str(AUJ + timedelta(days=200)),
           'taux_horaire': '6000', 'rib': 'CG39 3001 0000 1234 5678', 'numero_secu': '1850775123456'}


class Base(TestCase):
    def setUp(self):
        self.m = Monde()
        self.resp = client(['rh_responsable'])
        self.lecteur = client(['rh_utilisateur'])
        self.autre = client(['edt_responsable'])


class EnseignantsTests(Base):
    def test_creation_avec_contrat(self):
        r = self.resp.post('/api/rh/enseignants/', {'personne': PERSONNE, 'departement': self.m.dep.pk,
                                                    'grade': 'Docteur', 'contrat': CONTRAT}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        ens = Enseignant.objects.get(pk=r.data['id'])
        self.assertTrue(ens.matricule.startswith('UCCB-ENS-'))
        self.assertEqual(ens.personne.contrats.get().type, 'vacataire')
        self.assertTrue(r.data['actif'])
        self.assertTrue(JournalAudit.objects.filter(module='rh', action='creation_enseignant').exists())

    def test_contrat_invalide_ne_cree_rien(self):
        r = self.resp.post('/api/rh/enseignants/', {'personne': PERSONNE, 'departement': self.m.dep.pk,
                                                    'contrat': {**CONTRAT, 'taux_horaire': None}}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('taux_horaire', r.data['contrat'])
        self.assertFalse(Enseignant.objects.filter(personne__nom='Moukoko').exists())

    def test_liste_et_filtres(self):
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=5), fin=AUJ + timedelta(days=5))
        permanent(self.m.ens2.personne, debut=AUJ - timedelta(days=500), fin=AUJ - timedelta(days=1))
        r = self.lecteur.get('/api/rh/enseignants/')
        self.assertEqual(r.data['count'], 2)
        self.assertEqual([e['nom_complet'] for e in self.lecteur.get('/api/rh/enseignants/?actif=true').data['results']],
                         ['NGOMA Test'])
        self.assertEqual(self.lecteur.get('/api/rh/enseignants/?type=vacataire').data['count'], 1)
        self.assertEqual(self.lecteur.get('/api/rh/enseignants/?q=okem').data['count'], 1)

    def test_droits(self):
        self.assertEqual(self.lecteur.post('/api/rh/enseignants/', {}, format='json').status_code, 403)
        self.assertEqual(self.autre.get('/api/rh/enseignants/').status_code, 403)


class EmployesTests(Base):
    def test_fonction_autre_exige_un_libelle(self):
        r = self.resp.post('/api/rh/employes/', {'personne': {**PERSONNE, 'email': 'e@uccb.cg'}, 'fonction': 'autre'},
                           format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('fonction_autre', r.data)
        r = self.resp.post('/api/rh/employes/', {
            'personne': {**PERSONNE, 'email': 'e@uccb.cg'}, 'fonction': 'chauffeur', 'lieu_travail': 'Campus',
            'contrat': {'type': 'permanent', 'date_debut': str(AUJ), 'salaire_mensuel': '180000'}}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(Employe.objects.get(pk=r.data['id']).matricule.startswith('UCCB-PERS-'))


class ContratsTests(Base):
    def setUp(self):
        super().setUp()
        self.c = vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=30), fin=AUJ + timedelta(days=10))
        Contrat.objects.filter(pk=self.c.pk).update(rib='CG39 3001 0000 1234 5678', numero_secu='1850775123456')

    def test_masquage_pour_le_lecteur(self):
        clair = self.resp.get(f'/api/rh/contrats/{self.c.pk}/').data
        self.assertEqual(clair['rib'], 'CG39 3001 0000 1234 5678')
        masque = self.lecteur.get(f'/api/rh/contrats/{self.c.pk}/').data
        self.assertEqual((masque['rib'], masque['numero_secu']), ('•••• 5678', '•••• 3456'))

    def test_chevauchement(self):
        r = self.resp.post('/api/rh/contrats/', {'personne': self.m.ens.pk, 'type': 'vacataire',
                                                 'date_debut': str(AUJ), 'taux_horaire': '5000'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('date_debut', r.data)

    def test_terminer_et_echeance(self):
        self.assertEqual(self.lecteur.get('/api/rh/contrats/?echeance=30').data['count'], 1)
        r = self.resp.post(f'/api/rh/contrats/{self.c.pk}/terminer/', {'date_fin': str(AUJ - timedelta(days=1))},
                           format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['etat'], 'expire')
        self.assertTrue(JournalAudit.objects.filter(action='fin_contrat').exists())
        self.assertEqual(self.lecteur.post(f'/api/rh/contrats/{self.c.pk}/terminer/', {}).status_code, 403)


class TableauDeBordTests(Base):
    def test_indicateurs(self):
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=30), fin=AUJ + timedelta(days=10))
        permanent(self.m.ens2.personne, debut=AUJ - timedelta(days=30))
        g = employe('Gardien', 'gardien')
        permanent(g.personne, debut=AUJ - timedelta(days=30), salaire='120000')
        employe('Ancien', 'chauffeur')
        affectation(self.m.algo, self.m.l1, self.m.ens, 2)
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=AUJ - timedelta(days=3))
        r = self.lecteur.get('/api/rh/tableau-de-bord/')
        self.assertEqual(r.status_code, 200, r.data)
        d = r.data
        self.assertEqual((d['enseignants_actifs'], d['enseignants_permanents'], d['enseignants_vacataires']), (2, 1, 1))
        self.assertEqual(d['personnel_actif'], 1)
        self.assertEqual(d['personnel_par_fonction'], [{'fonction': 'gardien', 'libelle': 'Gardien / Agent de sécurité', 'n': 1}])
        self.assertEqual(len(d['contrats_a_echeance']), 1)
        self.assertEqual(d['vacations_a_confirmer'], 1)


class VacationsListeTests(Base):
    def setUp(self):
        super().setUp()
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200))
        self.terminee = affectation(self.m.algo, self.m.l1, self.m.ens, 2)
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=AUJ - timedelta(days=3))
        self.en_cours = affectation(self.m.bdd, self.m.l2, self.m.ens, 10)
        permanent(self.m.ens2.personne, debut=AUJ - timedelta(days=60))
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 4)    # permanent : payé au mois, pas une vacation

    def test_par_etat(self):
        r = self.lecteur.get('/api/rh/vacations/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(len(r.data), 2)
        a_confirmer = self.lecteur.get('/api/rh/vacations/?etat=a_confirmer').data
        self.assertEqual([l['affectation'] for l in a_confirmer], [self.terminee.pk])
        self.assertEqual(a_confirmer[0]['heures_effectuees'], 2.0)
        self.assertTrue(a_confirmer[0]['terminee'])
        self.assertEqual([l['affectation'] for l in self.lecteur.get('/api/rh/vacations/?etat=en_cours').data],
                         [self.en_cours.pk])

    def test_requetes_bornees(self):
        def compter():
            with CaptureQueriesContext(connection) as ctx:
                self.lecteur.get('/api/rh/vacations/')
            return len(ctx)
        compter()
        avant = compter()
        for nom in ('Alpha', 'Beta', 'Gamma'):
            ens = enseignant(nom, self.m.dep)
            vacataire(ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200))
            affectation(self.m.bdd, self.m.l2, ens, 3)
        self.assertEqual(compter(), avant)
