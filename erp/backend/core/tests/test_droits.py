from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import path
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from core.droits import a_droit, definir_droits, faculte_rattachee, modules_accessibles, roles_contextuels
from core.models import Employe, Enseignant
from core.models.acces import RattachementFaculte
from core.permissions import CompteActif, droit_module
from core.tests import fabriques as f


class VueCompteActif(APIView):
    permission_classes = [CompteActif]

    def get(self, request):
        return Response({'ok': True})


class VueRh(APIView):
    permission_classes = [droit_module('rh')]

    def get(self, request):
        return Response({'ok': True})


urlpatterns = [path('actif/', VueCompteActif.as_view()), path('rh/', VueRh.as_view())]


def utilisateur(username='u', groupes=()):
    u = User.objects.create_user(username=username, password='Mot-de-passe-1')
    definir_droits(u, list(groupes))
    return u


class GroupesTests(TestCase):
    def test_groupes_crees_par_migration(self):
        self.assertTrue(Group.objects.filter(name='scolarite_faculte').exists())
        self.assertTrue(Group.objects.filter(name='parametres_responsable').exists())
        self.assertEqual(
            Group.objects.filter(name__regex=r'^(scolarite|edt|rh|finance|logistique|parametres)_').count(), 11
        )


class DroitsTests(TestCase):
    def test_modules_accessibles(self):
        u = utilisateur(groupes=['rh_responsable'])
        self.assertEqual(
            modules_accessibles(u), [{'code': 'rh', 'libelle': 'Ressources humaines', 'niveaux': ['responsable']}]
        )

    def test_ordre_du_registre(self):
        u = utilisateur(groupes=['finance_utilisateur', 'scolarite_faculte'])
        self.assertEqual([m['code'] for m in modules_accessibles(u)], ['scolarite', 'finance'])

    def test_superuser_tout(self):
        u = User.objects.create_superuser('admin', 'a@uccb.cg', 'Mot-de-passe-1')
        modules = modules_accessibles(u)
        self.assertEqual(len(modules), 6)
        self.assertEqual(modules[0]['niveaux'], ['secretariat', 'faculte'])

    def test_a_droit_niveau(self):
        u = utilisateur(groupes=['rh_utilisateur'])
        self.assertTrue(a_droit(u, 'rh'))
        self.assertFalse(a_droit(u, 'rh', 'responsable'))
        self.assertFalse(a_droit(u, 'finance'))

    def test_definir_droits_remplace(self):
        u = utilisateur(groupes=['rh_utilisateur'])
        definir_droits(u, ['finance_responsable'])
        self.assertEqual([m['code'] for m in modules_accessibles(u)], ['finance'])

    def test_definir_droits_refuse_inconnu(self):
        u = utilisateur()
        with self.assertRaises(ValueError):
            definir_droits(u, ['compta_responsable'])

    def test_faculte_rattachee(self):
        u = utilisateur(groupes=['scolarite_faculte'])
        self.assertIsNone(faculte_rattachee(u))
        fac = f.faculte()
        RattachementFaculte.objects.create(user=u, faculte=fac)
        self.assertEqual(faculte_rattachee(u), fac)


class RolesContextuelsTests(TestCase):
    def test_enseignant_chef(self):
        u = utilisateur()
        p = f.personne(user=u)
        dep = f.departement()
        ens = Enseignant.objects.create(personne=p, departement=dep)
        dep.chef = ens
        dep.save()
        self.assertEqual(roles_contextuels(u), ['enseignant', 'chef_departement'])

    def test_employe(self):
        u = utilisateur()
        Employe.objects.create(personne=f.personne(user=u), fonction='gardien')
        self.assertEqual(roles_contextuels(u), ['employe'])

    def test_sans_personne(self):
        self.assertEqual(roles_contextuels(utilisateur()), [])


@override_settings(ROOT_URLCONF='core.tests.test_droits')
class PermissionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_compte_actif_refuse_suspendu(self):
        u = utilisateur()
        f.personne(user=u, statut='suspendu', motif_suspension='Retard de paiement')
        self.client.force_authenticate(u)
        r = self.client.get('/actif/')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data['code'], 'profil_suspendu')
        self.assertIn('Retard de paiement', r.data['detail'])

    def test_compte_actif_sans_personne(self):
        self.client.force_authenticate(utilisateur())
        self.assertEqual(self.client.get('/actif/').status_code, 200)

    def test_droit_module_permission(self):
        u = utilisateur()
        self.client.force_authenticate(u)
        self.assertEqual(self.client.get('/rh/').status_code, 403)
        definir_droits(u, ['rh_utilisateur'])
        self.assertEqual(self.client.get('/rh/').status_code, 200)
