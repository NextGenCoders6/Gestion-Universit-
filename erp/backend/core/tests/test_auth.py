from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.models import Employe, Faculte
from core.tests import fabriques as f
from core.urls import urlpatterns as core_urls

MDP = 'Mot-de-passe-1'


@api_view(['DELETE'])
@permission_classes([AllowAny])
def supprimer_faculte(request, pk):
    Faculte.objects.get(pk=pk).delete()
    return Response(status=204)


urlpatterns = [
    path('api/core/', __import__('django.urls', fromlist=['include']).include(core_urls)),
    path('test/faculte/<int:pk>/', supprimer_faculte),
]


def utilisateur(username='agent', groupes=(), personne=True, **kwargs):
    u = User.objects.create_user(username=username, password=MDP)
    definir_droits(u, list(groupes))
    if personne:
        f.personne(user=u, **kwargs)
    return u


class AuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def login(self, username='agent', password=MDP):
        return self.client.post('/api/core/token/', {'username': username, 'password': password}, format='json')

    def test_login_renvoie_moi(self):
        utilisateur(groupes=['rh_responsable'])
        r = self.login()
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        self.assertIn('refresh', r.data)
        user = r.data['user']
        self.assertEqual(user['modules'], [{'code': 'rh', 'libelle': 'Ressources humaines', 'niveaux': ['responsable']}])
        self.assertEqual(user['nom_complet'], 'MABIALA Grâce')
        self.assertIsNone(user['faculte_rattachee'])

    def test_login_mauvais_mot_de_passe(self):
        utilisateur()
        r = self.login(password='faux')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.data['detail'], 'Identifiant ou mot de passe incorrect.')

    def test_login_suspendu(self):
        utilisateur(statut='suspendu', motif_suspension='Frais impayés')
        r = self.login()
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.data['code'], 'profil_suspendu')
        self.assertIn('Frais impayés', r.data['detail'])

    def test_jeton_valide_puis_suspension(self):
        u = utilisateur()
        token = self.login().data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(self.client.get('/api/core/moi/').status_code, 200)
        p = u.personne
        p.statut, p.motif_suspension = 'suspendu', 'Enquête'
        p.save()
        r = self.client.get('/api/core/moi/')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data['code'], 'profil_suspendu')

    def test_refresh_refuse_apres_suspension(self):
        u = utilisateur()
        refresh = self.login().data['refresh']
        p = u.personne
        p.statut, p.motif_suspension = 'suspendu', 'Enquête'
        p.save()
        r = self.client.post('/api/core/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.data['code'], 'profil_suspendu')

    def test_refresh_fait_tourner_le_jeton(self):
        utilisateur()
        refresh = self.login().data['refresh']
        r = self.client.post('/api/core/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.data['refresh'], refresh)

    def test_deconnexion_blackliste(self):
        utilisateur()
        data = self.login().data
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {data["access"]}')
        self.assertEqual(self.client.post('/api/core/deconnexion/', {'refresh': data['refresh']}, format='json').status_code, 205)
        r = self.client.post('/api/core/token/refresh/', {'refresh': data['refresh']}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_moi_sans_module(self):
        u = utilisateur()
        Employe.objects.create(personne=u.personne, fonction='gardien')
        self.client.force_authenticate(u)
        r = self.client.get('/api/core/moi/')
        self.assertEqual(r.data['modules'], [])
        self.assertEqual(r.data['roles'], ['employe'])

    def test_moi_exige_authentification(self):
        self.assertEqual(self.client.get('/api/core/moi/').status_code, 401)

    def test_droits_relus_a_chaque_appel(self):
        u = utilisateur(groupes=['rh_utilisateur'])
        token = self.login().data['access']
        definir_droits(u, [])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(self.client.get('/api/core/moi/').data['modules'], [])

    @override_settings(REST_FRAMEWORK={
        **__import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_RATES': {'anon': '1000/min', 'user': '1000/min', 'login': '3/min', 'login_ip': '100/min'},
    })
    def test_throttle_login(self):
        from rest_framework.settings import api_settings
        from core.throttles import LoginCompteRateThrottle
        LoginCompteRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
        try:
            utilisateur()
            codes = [self.login(password='faux').status_code for _ in range(4)]
            self.assertEqual(codes, [401, 401, 401, 429])
        finally:
            LoginCompteRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES


@override_settings(ROOT_URLCONF='core.tests.test_auth')
class ExceptionsTests(TestCase):
    def test_protected_error_400(self):
        dep = f.departement()
        r = APIClient().delete(f'/test/faculte/{dep.faculte_id}/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('encore utilisé', r.data['detail'])
