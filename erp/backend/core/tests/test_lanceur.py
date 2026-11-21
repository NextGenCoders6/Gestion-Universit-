"""Launchpad : GET /api/core/lanceur/ renvoie le chiffre de chaque module accessible."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.lanceur import RESUMES, entree
from core.tests import fabriques as f

URL = '/api/core/lanceur/'


def client_de(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


class LanceurTests(TestCase):
    def setUp(self):
        cache.clear()
        self.parametres = User.objects.create_user('parametres', password='x')
        definir_droits(self.parametres, ['parametres_responsable'])
        User.objects.create_user('inactif', password='x', is_active=False)

    def test_reserve_aux_modules_accessibles(self):
        r = client_de(self.parametres).get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([e['module'] for e in r.data], ['parametres'])

    def test_parametres(self):
        f.annee(en_cours=True)
        (e,) = client_de(self.parametres).get(URL).data
        self.assertEqual(e, {'module': 'parametres', 'valeur': 1, 'unite': '', 'libelle': 'comptes actifs',
                             'detail': 'Année en cours : 2026-2027', 'ton': 'normal'})

    def test_parametres_sans_annee_courante(self):
        (e,) = client_de(self.parametres).get(URL).data
        self.assertEqual(e['detail'], 'Aucune année en cours')
        self.assertEqual(e['ton'], 'alerte')

    def test_resume_en_erreur_isole(self):
        def casse(request):
            raise RuntimeError('panne')
        admin = User.objects.create_superuser('admin', password='x')
        with patch.dict(RESUMES, {'parametres': casse}), self.assertLogs('core.lanceur', level='ERROR'):
            r = client_de(admin).get(URL)
        self.assertEqual(r.status_code, 200)
        entrees = {e['module']: e for e in r.data}
        self.assertEqual(entrees['parametres'], entree('parametres'))

    def test_anonyme_refuse(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)
