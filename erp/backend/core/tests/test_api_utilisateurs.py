from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits, modules_accessibles
from core.models import JournalAudit
from core.models.acces import RattachementFaculte
from core.tests import fabriques as f


def client_pour(groupes=(), username='u'):
    u = User.objects.create_user(username=username, password='Mot-de-passe-1')
    definir_droits(u, list(groupes))
    c = APIClient()
    c.force_authenticate(u)
    return c, u


class UtilisateursApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin, self.admin_user = client_pour(['parametres_responsable'], username='param')

    def test_creer_utilisateur_avec_droits(self):
        p = f.personne()
        fac = f.faculte()
        r = self.admin.post('/api/core/utilisateurs/', {
            'username': 'g.mabiala', 'password': 'Uccb!2026demo', 'personne_id': p.pk,
            'groupes': ['rh_responsable', 'scolarite_faculte'], 'faculte_rattachee_id': fac.pk,
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        u = User.objects.get(username='g.mabiala')
        self.assertEqual([m['code'] for m in modules_accessibles(u)], ['scolarite', 'rh'])
        self.assertEqual(u.personne, p)
        self.assertEqual(RattachementFaculte.objects.get(user=u).faculte, fac)
        self.assertEqual(sorted(r.data['groupes']), ['rh_responsable', 'scolarite_faculte'])
        self.assertTrue(JournalAudit.objects.filter(action='creation_utilisateur', module='parametres').exists())

    def test_modifier_droits_retire_rattachement(self):
        _, cible = client_pour(['scolarite_faculte'], username='cible')
        RattachementFaculte.objects.create(user=cible, faculte=f.faculte())
        r = self.admin.patch(f'/api/core/utilisateurs/{cible.pk}/', {
            'groupes': ['finance_utilisateur'], 'faculte_rattachee_id': None,
        }, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(RattachementFaculte.objects.filter(user=cible).exists())
        self.assertTrue(JournalAudit.objects.filter(action='modification_droits').exists())

    def test_groupe_inconnu_400(self):
        r = self.admin.post('/api/core/utilisateurs/', {
            'username': 'x', 'password': 'Uccb!2026demo', 'groupes': ['compta_responsable'],
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('groupes', r.data)

    def test_mot_de_passe_trop_simple_400(self):
        r = self.admin.post('/api/core/utilisateurs/', {'username': 'x', 'password': '1234', 'groupes': []}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.data)

    def test_changer_mot_de_passe(self):
        _, cible = client_pour(username='cible')
        r = self.admin.post(f'/api/core/utilisateurs/{cible.pk}/mot_de_passe/', {'password': 'Nouveau!2026x'}, format='json')
        self.assertEqual(r.status_code, 200)
        cible.refresh_from_db()
        self.assertTrue(cible.check_password('Nouveau!2026x'))
        self.assertTrue(JournalAudit.objects.filter(action='mot_de_passe').exists())

    def test_non_parametres_403(self):
        c, _ = client_pour(['rh_responsable'], username='rh')
        self.assertEqual(c.get('/api/core/utilisateurs/').status_code, 403)
        self.assertEqual(c.get('/api/core/audit/').status_code, 403)

    def test_modules(self):
        r = self.admin.get('/api/core/modules/')
        self.assertEqual(r.data[0], {'code': 'scolarite', 'libelle': 'Scolarité', 'niveaux': ['secretariat', 'faculte']})
        self.assertEqual(len(r.data), 6)

    def test_audit_filtre_module(self):
        JournalAudit.objects.create(module='rh', action='x')
        JournalAudit.objects.create(module='parametres', action='y')
        r = self.admin.get('/api/core/audit/?module=rh')
        self.assertEqual([e['action'] for e in r.data['results']], ['x'])


class PersonnesApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin, _ = client_pour(['parametres_responsable'], username='param')

    def test_suspendre_exige_motif(self):
        u = User.objects.create_user(username='etu', password='Mot-de-passe-1')
        p = f.personne(user=u)
        self.assertEqual(self.admin.post(f'/api/core/personnes/{p.pk}/suspendre/', {}, format='json').status_code, 400)
        r = self.admin.post(f'/api/core/personnes/{p.pk}/suspendre/', {'motif': 'Fraude'}, format='json')
        self.assertEqual(r.status_code, 200)
        login = APIClient().post('/api/core/token/', {'username': 'etu', 'password': 'Mot-de-passe-1'}, format='json')
        self.assertEqual(login.status_code, 401)
        self.assertEqual(login.data['code'], 'profil_suspendu')
        self.assertEqual(self.admin.post(f'/api/core/personnes/{p.pk}/reactiver/').status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.statut, 'actif')
        self.assertEqual(JournalAudit.objects.filter(action__in=['suspension', 'reactivation']).count(), 2)

    def test_lecture_exige_un_module(self):
        sans, _ = client_pour(username='sans')
        avec, _ = client_pour(['rh_utilisateur'], username='avec')
        f.personne()
        self.assertEqual(sans.get('/api/core/personnes/').status_code, 403)
        self.assertEqual(avec.get('/api/core/personnes/').status_code, 200)
        self.assertEqual(avec.post('/api/core/personnes/', {'nom': 'A', 'prenom': 'B', 'genre': 'M'}, format='json').status_code, 403)

    def test_recherche_et_role(self):
        from core.models import Enseignant
        f.personne(nom='Ngoma', prenom='Paul')
        ens = f.personne(nom='Okemba', prenom='Jean')
        Enseignant.objects.create(personne=ens, departement=f.departement())
        self.assertEqual(self.admin.get('/api/core/personnes/?q=ngom').data['count'], 1)
        r = self.admin.get('/api/core/personnes/?role=enseignant')
        self.assertEqual([p['nom'] for p in r.data['results']], ['Okemba'])
        self.assertEqual(r.data['results'][0]['roles'], ['enseignant'])

    def test_creer_personne(self):
        r = self.admin.post('/api/core/personnes/', {'nom': 'Moukala', 'prenom': 'Rita', 'genre': 'F', 'email': ''}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['nom_complet'], 'MOUKALA Rita')
