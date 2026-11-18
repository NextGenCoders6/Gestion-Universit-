"""Non-régression des constats de la relecture finale de la phase 1."""
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import IntegrityError
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient

from core.audit import adresse_ip
from core.checks import verifier_cle_secrete
from core.droits import definir_droits
from core.models import Classe, Enseignant, Etudiant, Faculte, JournalAudit, Personne
from core.models.acces import RattachementFaculte
from core.tests import fabriques as f

MDP = 'Mot-de-passe-1'


def compte(username, groupes=(), suspendu=False):
    u = User.objects.create_user(username=username, password=MDP)
    definir_droits(u, list(groupes))
    if suspendu:
        f.personne(nom='Suspendu', user=u, statut='suspendu', motif_suspension='Enquête')
    return u


def client_jwt(username):
    c = APIClient()
    r = c.post('/api/core/token/', {'username': username, 'password': MDP}, format='json')
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {r.data["access"]}')
    return c


class SuspensionPartoutTests(TestCase):
    """Constat 1 : la suspension s'applique à tous les endpoints, pas seulement /moi/."""

    def setUp(self):
        cache.clear()
        self.u = compte('param', ['parametres_responsable'])
        f.personne(nom='Param', user=self.u)
        self.client = client_jwt('param')
        p = self.u.personne
        p.statut, p.motif_suspension = 'suspendu', 'Enquête'
        p.save()

    def test_chaque_endpoint_refuse(self):
        for methode, url, data in [
            ('get', '/api/core/facultes/', None),
            ('get', '/api/core/personnes/', None),
            ('put', '/api/core/etablissement/', {'ville_signature': 'X'}),
            ('post', '/api/core/facultes/', {'nom': 'Droit', 'code': 'FDR'}),
            ('post', '/api/core/utilisateurs/', {'username': 'pirate', 'password': 'Uccb!2026demo',
                                                 'groupes': ['parametres_responsable']}),
            ('get', '/api/core/audit/', None),
        ]:
            r = getattr(self.client, methode)(url, data, format='json')
            self.assertEqual(r.status_code, 403, url)
            self.assertEqual(r.data['code'], 'profil_suspendu', url)
        self.assertFalse(User.objects.filter(username='pirate').exists())


class SuperuserProtegeTests(TestCase):
    """Constat 2 : un responsable Paramètres ne touche pas aux superusers."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'a@uccb.cg', MDP)
        self.param = compte('param', ['parametres_responsable'])
        self.client = APIClient()
        self.client.force_authenticate(self.param)

    def test_superuser_invisible_et_intouchable(self):
        noms = [u['username'] for u in self.client.get('/api/core/utilisateurs/').data['results']]
        self.assertNotIn('admin', noms)
        self.assertEqual(self.client.post(f'/api/core/utilisateurs/{self.admin.pk}/mot_de_passe/',
                                          {'password': 'Nouveau!2026x'}, format='json').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/core/utilisateurs/{self.admin.pk}/',
                                           {'is_active': False}, format='json').status_code, 404)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(MDP))
        self.assertTrue(self.admin.is_active)

    def test_superuser_voit_les_superusers(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        noms = [u['username'] for u in c.get('/api/core/utilisateurs/').data['results']]
        self.assertIn('admin', noms)


class ProxyEtIpTests(TestCase):
    """Constat 3 : X-Forwarded-For ne contourne ni la limitation ni le journal."""

    def setUp(self):
        cache.clear()
        compte('cible')

    def test_xff_ne_contourne_pas_la_limitation(self):
        c = APIClient()
        codes = [
            c.post('/api/core/token/', {'username': 'cible', 'password': 'faux'}, format='json',
                   HTTP_X_FORWARDED_FOR=f'10.0.0.{i}').status_code
            for i in range(35)
        ]
        self.assertIn(429, codes)

    def test_adresse_ip_ignore_xff_sans_proxy(self):
        req = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='not-an-ip-' + 'a' * 60, REMOTE_ADDR='192.168.1.5')
        self.assertEqual(adresse_ip(req), '192.168.1.5')

    @override_settings(REST_FRAMEWORK={**__import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK,
                                       'NUM_PROXIES': 1})
    def test_adresse_ip_derriere_un_proxy(self):
        # Le proxy ajoute l'adresse réelle en dernier ; la première est falsifiable.
        req = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='1.2.3.4, 41.202.1.9', REMOTE_ADDR='10.0.0.2')
        self.assertEqual(adresse_ip(req), '41.202.1.9')
        invalide = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='nimporte', REMOTE_ADDR='10.0.0.2')
        self.assertEqual(adresse_ip(invalide), '10.0.0.2')


class ErreursHorsChampTests(TestCase):
    """Constat 4 : les erreurs générales arrivent en non_field_errors, les incohérences par champ."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(compte('param', ['parametres_responsable']))
        self.annee, self.portail = f.annee(), f.portail()
        self.filiere = f.filiere(port=self.portail)

    def test_portail_et_filiere_par_champ(self):
        r = self.client.post('/api/core/classes/', {
            'annee': self.annee.pk, 'parcours': f.parcours('Licence', 1).pk,
            'portail': self.portail.pk, 'filiere': self.filiere.pk,
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('portail', r.data)
        self.assertIn('filiere', r.data)

    def test_doublon_en_non_field_errors_sans_jargon(self):
        donnees = {'annee': self.annee.pk, 'parcours': f.parcours('Licence', 1).pk, 'portail': self.portail.pk}
        self.client.post('/api/core/classes/', donnees, format='json')
        r = self.client.post('/api/core/classes/', donnees, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertNotIn('__all__', r.data)
        self.assertEqual(r.data['non_field_errors'], ['Cette classe existe déjà pour cette année.'])


class CascadesTests(TestCase):
    """Constats 5 et 6 : pas d'élargissement d'accès ni de perte de rôles en cascade."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(compte('param', ['parametres_responsable']))

    def test_faculte_rattachee_protegee(self):
        fac = Faculte.objects.create(nom='Vide', code='VID')
        RattachementFaculte.objects.create(user=compte('sco', ['scolarite_faculte']), faculte=fac)
        r = self.client.delete(f'/api/core/facultes/{fac.pk}/')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(RattachementFaculte.objects.filter(faculte=fac).exists())

    def test_personne_avec_role_ou_compte_protegee(self):
        ens = Enseignant.objects.create(personne=f.personne(nom='Ngoma'), departement=f.departement())
        r = self.client.delete(f'/api/core/personnes/{ens.pk}/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('encore utilisée', r.data['detail'])
        avec_compte = f.personne(nom='Compte', user=compte('lie'))
        self.assertEqual(self.client.delete(f'/api/core/personnes/{avec_compte.pk}/').status_code, 400)

    def test_suppression_personne_libre_journalisee(self):
        libre = f.personne(nom='Libre')
        self.assertEqual(self.client.delete(f'/api/core/personnes/{libre.pk}/').status_code, 204)
        self.assertTrue(JournalAudit.objects.filter(action='suppression_personne').exists())


class MatriculesTests(TestCase):
    """Constat 7 : pas de réutilisation de numéro, nouvel essai en cas de collision."""

    def test_numero_etudiant_jamais_reutilise(self):
        a = f.annee()
        e1 = Etudiant.objects.create(personne=f.personne(nom='Mabiala'), annee_entree=a)
        Etudiant.objects.create(personne=f.personne(nom='Ngoma', prenom='Paul'), annee_entree=a)
        e1.delete()
        e3 = Etudiant.objects.create(personne=f.personne(nom='Okemba', prenom='Jean'), annee_entree=a)
        self.assertTrue(e3.matricule.endswith('00003'), e3.matricule)

    def test_numero_enseignant_jamais_reutilise(self):
        dep = f.departement()
        e1 = Enseignant.objects.create(personne=f.personne(nom='Un'), departement=dep)
        Enseignant.objects.create(personne=f.personne(nom='Deux'), departement=dep)
        e1.delete()
        e3 = Enseignant.objects.create(personne=f.personne(nom='Trois'), departement=dep)
        self.assertEqual(e3.matricule, 'UCCB-ENS-00003')

    def test_collision_concurrente_reessaie(self):
        dep = f.departement()
        Enseignant.objects.create(personne=f.personne(nom='Un'), departement=dep)
        from core.models import personnes
        reel = personnes._prochain_numero
        appels = []

        def simule(modele, prefixe):
            appels.append(1)
            return 'UCCB-ENS-00001' if len(appels) == 1 else reel(modele, prefixe)

        with mock.patch.object(personnes, '_prochain_numero', side_effect=simule):
            e = Enseignant.objects.create(personne=f.personne(nom='Deux'), departement=dep)
        self.assertEqual(e.matricule, 'UCCB-ENS-00002')
        self.assertEqual(len(appels), 2)


class ContraintesClasseTests(TestCase):
    """Constat 8 : contraintes d'unicité sans condition (créées aussi sous MySQL)."""

    def test_contraintes_sans_condition(self):
        for c in Classe._meta.constraints:
            self.assertIsNone(getattr(c, 'condition', None), c.name)

    def test_null_distincts_autorises(self):
        a, port = f.annee(), f.portail()
        fil = f.filiere(port=port)
        Classe.objects.create(annee=a, parcours=f.parcours('Licence', 1), portail=port)
        Classe.objects.create(annee=a, parcours=f.parcours('Licence', 2), filiere=fil)
        Classe.objects.create(annee=a, parcours=f.parcours('Licence', 3), filiere=fil)
        self.assertEqual(Classe.objects.count(), 3)


class FiltresInvalidesTests(TestCase):
    """Constat 9 : un filtre mal formé donne 400, jamais 500."""

    def test_filtres_invalides(self):
        c = APIClient()
        c.force_authenticate(compte('param', ['parametres_responsable']))
        for url in ['/api/core/periodes/?annee=abc', '/api/core/classes/?faculte=x', '/api/core/audit/?utilisateur=x']:
            r = c.get(url)
            self.assertEqual(r.status_code, 400, url)


class ProductionTests(TestCase):
    """Constat 10 : pas de clé secrète par défaut ni de comptes de démo en production."""

    @override_settings(DEBUG=False, SECRET_KEY='cle-de-developpement-a-remplacer')
    def test_cle_par_defaut_refusee_hors_debug(self):
        self.assertEqual([e.id for e in verifier_cle_secrete(None)], ['core.E001'])

    @override_settings(DEBUG=True, SECRET_KEY='cle-de-developpement-a-remplacer')
    def test_cle_par_defaut_tolere_en_debug(self):
        self.assertEqual(verifier_cle_secrete(None), [])

    @override_settings(DEBUG=False)
    def test_seed_refuse_hors_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_socle', verbosity=0)
        self.assertFalse(User.objects.filter(username='admin').exists())
