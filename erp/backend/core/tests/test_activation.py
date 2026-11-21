"""Activation du compte par l'étudiant ou l'enseignant lui-même (POST /api/core/activation/)."""
from datetime import date

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Enseignant, Etudiant, JournalAudit
from core.tests import fabriques as f

MDP = 'Etudiant-UCCB-2026!'
URL = '/api/core/activation/'
ECHEC = {'detail': 'Informations incorrectes ou compte déjà activé.'}


class ActivationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.e = Etudiant.objects.create(
            personne=f.personne('Moukala', 'Divine', email='divine@example.org', date_naissance=date(2006, 3, 14)),
            annee_entree=f.annee(),
        )
        self.ens = Enseignant.objects.create(
            personne=f.personne('Mbemba', 'Christelle', email='c.mbemba@example.org', date_naissance=date(1985, 5, 2)),
            departement=f.departement(),
        )
        self.anonyme = APIClient()

    def activer(self, **kw):
        corps = {'matricule': self.e.matricule, 'email': 'divine@example.org', 'date_naissance': '2006-03-14',
                 'password': MDP, **kw}
        return self.anonyme.post(URL, corps, format='json')

    def activer_enseignant(self, **kw):
        corps = {'matricule': self.ens.matricule, 'email': 'c.mbemba@example.org', 'date_naissance': '1985-05-02',
                 'password': MDP, **kw}
        return self.anonyme.post(URL, corps, format='json')

    def connecter(self, username):
        return self.anonyme.post('/api/core/token/', {'username': username, 'password': MDP}, format='json')

    def test_succes_puis_connexion_par_matricule(self):
        r = self.activer(matricule=self.e.matricule.lower(), email='DIVINE@example.org')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data, {'detail': 'Compte activé. Connectez-vous avec votre matricule.',
                                  'username': self.e.matricule})
        self.e.personne.refresh_from_db()
        self.assertEqual(self.e.personne.user.username, self.e.matricule)
        self.assertEqual(self.connecter(self.e.matricule).status_code, 200)

    def test_enseignant_active_son_compte(self):
        r = self.activer_enseignant(matricule=self.ens.matricule.lower())
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['username'], self.ens.matricule)
        self.ens.personne.refresh_from_db()
        self.assertEqual(self.ens.personne.user.username, self.ens.matricule)
        moi = self.connecter(self.ens.matricule)
        self.assertEqual(moi.status_code, 200, moi.data)
        self.assertIn('enseignant', moi.data['user']['roles'])

    def test_echecs_meme_message(self):
        reponses = [
            self.activer(date_naissance='2006-03-15'),
            self.activer(email='autre@example.org'),
            self.activer(matricule='UCCB26XXXXX99999'),
            self.activer_enseignant(date_naissance='1985-05-03'),
        ]
        self.assertEqual(self.activer().status_code, 201)
        self.assertEqual(self.activer_enseignant().status_code, 201)
        reponses += [self.activer(), self.activer_enseignant()]  # déjà activés
        for r in reponses:
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.data, ECHEC)
        self.assertEqual(User.objects.filter(username=self.e.matricule).count(), 1)
        self.assertEqual(User.objects.filter(username=self.ens.matricule).count(), 1)

    def test_etudiant_abandonne(self):
        self.e.statut = 'abandonne'
        self.e.save()
        self.assertEqual(self.activer().data, ECHEC)

    def test_personne_suspendue_refusee(self):
        for fiche in (self.e, self.ens):
            fiche.personne.statut = 'suspendu'
            fiche.personne.motif_suspension = 'Dossier incomplet'
            fiche.personne.save()
        self.assertEqual(self.activer().data, ECHEC)
        self.assertEqual(self.activer_enseignant().data, ECHEC)

    def test_mot_de_passe_faible(self):
        r = self.activer(password='123')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.data)
        self.assertIsNone(User.objects.filter(username=self.e.matricule).first())

    def test_journal_module_core(self):
        self.activer_enseignant()
        self.assertTrue(JournalAudit.objects.filter(module='core', action='activation_compte',
                                                    description=self.ens.matricule).exists())
