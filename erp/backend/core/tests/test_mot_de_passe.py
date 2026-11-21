"""Mot de passe oublié : demande du lien par e-mail, puis choix d'un nouveau mot de passe."""
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import JournalAudit
from core.tests import fabriques as f

URL_DEMANDE = '/api/core/mot-de-passe/oubli/'
MESSAGE_DEMANDE = {'detail': "Si un compte correspond, un e-mail contenant un lien vient d'être envoyé."}
MDP = 'Ancien-UCCB-2026!'


@override_settings(BASE_URL='http://testserver-erp')
class DemandeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('Divine.Moukala', password=MDP)
        self.personne = f.personne('Moukala', 'Divine', email='divine@example.org', user=self.user)
        self.anonyme = APIClient()

    def demander(self, identifiant):
        return self.anonyme.post(URL_DEMANDE, {'identifiant': identifiant}, format='json')

    def test_par_identifiant_un_email_avec_lien(self):
        r = self.demander('  divine.moukala ')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, MESSAGE_DEMANDE)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['divine@example.org'])
        self.assertEqual(mail.outbox[0].subject, 'UCCB — Réinitialisation de votre mot de passe')
        self.assertIn('MOUKALA Divine', mail.outbox[0].body)
        self.assertRegex(mail.outbox[0].body, r'http://testserver-erp/reinitialisation/[\w-]+/[\w-]+')

    def test_par_email_casse_differente(self):
        self.assertEqual(self.demander('DIVINE@Example.org').data, MESSAGE_DEMANDE)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['divine@example.org'])

    def test_adresse_du_compte_sans_personne(self):
        User.objects.create_user('caissier', email='caisse@example.org', password=MDP)
        self.demander('caissier')
        self.assertEqual([m.to for m in mail.outbox], [['caisse@example.org']])

    def test_identifiant_prioritaire_sur_email(self):
        homonyme = User.objects.create_user('paul@example.org', email='paul.compte@example.org', password=MDP)
        f.personne('Ngoma', 'Paul', email='paul@example.org',
                   user=User.objects.create_user('paul.ngoma', password=MDP))
        self.demander('PAUL@example.org')
        self.assertEqual([m.to for m in mail.outbox], [[homonyme.email]])

    def test_cas_sans_envoi_meme_reponse(self):
        inactif = User.objects.create_user('inactif', email='inactif@example.org', password=MDP, is_active=False)
        f.personne('Suspendu', 'Jean', email='jean@example.org', statut='suspendu', motif_suspension='Impayés',
                   user=User.objects.create_user('jean', password=MDP))
        User.objects.create_user('sans.adresse', password=MDP)
        for saisie in ('inconnu', inactif.username, 'jean', 'sans.adresse', ''):
            r = self.demander(saisie)
            self.assertEqual(r.status_code, 200, saisie)
            self.assertEqual(r.data, MESSAGE_DEMANDE, saisie)
        self.assertEqual(mail.outbox, [])

    def test_panne_smtp_reponse_neutre(self):
        with patch('core.api.mot_de_passe.send_mail', side_effect=SMTPException('serveur injoignable')):
            with self.assertLogs('core.api.mot_de_passe', level='ERROR'):
                r = self.demander('divine.moukala')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, MESSAGE_DEMANDE)

    def test_journal_a_chaque_envoi(self):
        self.demander('inconnu')
        self.assertFalse(JournalAudit.objects.filter(action='demande_reinitialisation').exists())
        self.demander('divine.moukala')
        self.assertTrue(JournalAudit.objects.filter(module='core', action='demande_reinitialisation',
                                                    description='Divine.Moukala').exists())


URL_REINIT = '/api/core/mot-de-passe/reinitialisation/'
NOUVEAU = 'Nouveau-UCCB-2027!'
LIEN_INVALIDE = {'detail': "Ce lien n'est plus valable. Faites une nouvelle demande."}


class ReinitialisationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('divine', email='divine@example.org', password=MDP)
        self.anonyme = APIClient()

    def lien(self):
        from core.api.mot_de_passe import lien_reinitialisation
        self.user.refresh_from_db()
        uid, jeton = lien_reinitialisation(self.user).rstrip('/').split('/')[-2:]
        return uid, jeton

    def reinitialiser(self, uid, jeton, password=NOUVEAU):
        return self.anonyme.post(URL_REINIT, {'uid': uid, 'jeton': jeton, 'password': password}, format='json')

    def connecter(self, password):
        return self.anonyme.post('/api/core/token/', {'username': 'divine', 'password': password}, format='json')

    def test_succes_puis_connexion(self):
        r = self.reinitialiser(*self.lien())
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data, {'detail': 'Mot de passe modifié. Connectez-vous.'})
        self.assertEqual(self.connecter(NOUVEAU).status_code, 200)
        self.assertEqual(self.connecter(MDP).status_code, 401)

    def test_lien_utilise_deux_fois(self):
        lien = self.lien()
        self.assertEqual(self.reinitialiser(*lien).status_code, 200)
        r = self.reinitialiser(*lien, password='Encore-UCCB-2028!')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, LIEN_INVALIDE)

    def test_lien_apres_reconnexion(self):
        lien = self.lien()
        self.assertEqual(self.connecter(MDP).status_code, 200)
        self.assertEqual(self.reinitialiser(*lien).data, LIEN_INVALIDE)

    def test_lien_expire(self):
        from datetime import datetime, timedelta
        lien = self.lien()
        plus_tard = datetime.now() + timedelta(hours=1, minutes=1)
        with patch('django.contrib.auth.tokens.PasswordResetTokenGenerator._now', return_value=plus_tard):
            self.assertEqual(self.reinitialiser(*lien).data, LIEN_INVALIDE)

    def test_uid_invalide(self):
        _, jeton = self.lien()
        for uid in ('zz', 'OTk5OQ', ''):
            r = self.reinitialiser(uid, jeton)
            self.assertEqual(r.status_code, 400, uid)
            self.assertEqual(r.data, LIEN_INVALIDE, uid)

    def test_mot_de_passe_faible(self):
        r = self.reinitialiser(*self.lien(), password='123')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.data)
        self.assertEqual(self.connecter(MDP).status_code, 200)

    def test_sessions_fermees(self):
        refresh = self.connecter(MDP).data['refresh']
        self.assertEqual(self.reinitialiser(*self.lien()).status_code, 200)
        r = self.anonyme.post('/api/core/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_journal(self):
        self.reinitialiser(*self.lien())
        self.assertTrue(JournalAudit.objects.filter(module='core', action='reinitialisation_mot_de_passe',
                                                    description='divine').exists())
