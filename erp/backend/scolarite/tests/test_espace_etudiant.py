from datetime import date, time

from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient

from core.models import JournalAudit
from edt.models import Seance
from edt.tests.fabriques import affectation, enseignant
from scolarite.moteur import deliberation
from scolarite.tests.api import Base, client
from scolarite.tests.fabriques import inscrit, noter

MDP = 'Etudiant-UCCB-2026!'


class ActivationTests(Base):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.i = inscrit(self.m.l1, 'Moukala', 'Divine', email='divine@example.org', date_naissance=date(2006, 3, 14))
        self.e = self.i.etudiant
        self.anonyme = APIClient()

    def activer(self, **kw):
        corps = {'matricule': self.e.matricule, 'email': 'divine@example.org', 'date_naissance': '2006-03-14',
                 'password': MDP, **kw}
        return self.anonyme.post('/api/scolarite/activation/', corps, format='json')

    def test_succes_puis_connexion_par_matricule(self):
        r = self.activer(matricule=self.e.matricule.lower(), email='DIVINE@example.org')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['username'], self.e.matricule)
        self.e.personne.refresh_from_db()
        self.assertEqual(self.e.personne.user.username, self.e.matricule)
        self.assertTrue(JournalAudit.objects.filter(action='activation_compte').exists())
        r = self.anonyme.post('/api/core/token/', {'username': self.e.matricule, 'password': MDP},
                              format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def test_echecs_meme_message(self):
        attendus = []
        attendus.append(self.activer(date_naissance='2006-03-15'))
        attendus.append(self.activer(email='autre@example.org'))
        attendus.append(self.activer(matricule='UCCB26XXXXX99999'))
        self.assertEqual(self.activer().status_code, 201)
        attendus.append(self.activer())  # déjà activé
        for r in attendus:
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.data, {'detail': 'Informations incorrectes ou compte déjà activé.'})
        self.assertEqual(User.objects.filter(username=self.e.matricule).count(), 1)

    def test_etudiant_abandonne(self):
        self.e.statut = 'abandonne'
        self.e.save()
        self.assertEqual(self.activer().status_code, 400)

    def test_mot_de_passe_faible(self):
        r = self.activer(password='123')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.data)
        self.assertIsNone(User.objects.filter(username=self.e.matricule).first())


class EspaceTests(Base):
    def setUp(self):
        super().setUp()
        self.moi = inscrit(self.m.l1, 'Moi')
        self.autre = inscrit(self.m.l1, 'Autre')
        u = User.objects.create_user('etu', password=MDP)
        p = self.moi.etudiant.personne
        p.user = u
        p.save()
        self.etu = client(u)
        noter(self.moi, self.m.algo, devoir=15, session=15)
        noter(self.autre, self.m.algo, devoir=3, session=3)

    def test_notes_de_soi_seulement(self):
        r = self.etu.get('/api/scolarite/moi/notes/')
        self.assertEqual(r.status_code, 200, r.data)
        annee = r.data['inscriptions'][0]
        self.assertEqual(annee['classe'], 'L1 MIP — 2026-2027')
        s1 = annee['semestres'][0]
        self.assertEqual(s1['semestre'], 'S1')
        self.assertFalse(s1['deliberee'])
        self.assertIsNone(s1['resultat'])
        self.assertEqual(s1['ues'][0]['ecs'][0]['note'], 15.0)
        self.assertNotIn('3.0', str(r.data))

    def test_decision_apres_deliberation(self):
        deliberation(self.m.l1, 'S1', enregistrer=True)
        s1 = self.etu.get('/api/scolarite/moi/notes/').data['inscriptions'][0]['semestres'][0]
        self.assertTrue(s1['deliberee'])
        self.assertEqual(s1['resultat']['decision'], 'ADMIS')

    def test_reserve_aux_etudiants(self):
        self.assertEqual(self.secretariat.get('/api/scolarite/moi/notes/').status_code, 403)

    def test_planning_de_sa_classe_publie(self):
        ens = enseignant('Ngoma', self.m.dep)
        lundi = date(2026, 10, 5)
        commun = dict(ec=self.m.algo, enseignant=ens, heure_debut=time(9, 0), heure_fin=time(11, 0), type_seance='CM')
        Seance.objects.bulk_create([
            Seance(classe=self.m.l1, date_seance=lundi, statut='Confirmée', **commun),
            Seance(classe=self.m.l1, date_seance=date(2026, 10, 6), statut='Brouillon', **commun),
            Seance(classe=self.m.l2, date_seance=lundi, statut='Confirmée', ec=self.m.bdd, enseignant=ens,
                   heure_debut=time(14, 15), heure_fin=time(16, 15), type_seance='CM'),
        ])
        r = self.etu.get('/api/scolarite/moi/planning/?date_debut=2026-10-05&date_fin=2026-10-10')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([(s['classe'], s['statut']) for s in r.data], [(self.m.l1.pk, 'Confirmée')])

    def test_enseignants(self):
        ens = enseignant('Ngoma', self.m.dep)
        affectation(self.m.algo, self.m.l1, ens, 10)
        affectation(self.m.prog, self.m.l1, ens, 10)
        affectation(self.m.bdd, self.m.l2, enseignant('Okemba', self.m.dep), 10)
        r = self.etu.get('/api/scolarite/moi/enseignants/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([e['nom_complet'] for e in r.data], ['NGOMA Test'])
        self.assertEqual([x['code'] for x in r.data[0]['ecs']], ['ALGO', 'PROG'])
