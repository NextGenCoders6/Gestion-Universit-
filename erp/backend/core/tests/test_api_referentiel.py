from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.models import AnneeAcademique, ParametresEtablissement
from core.tests import fabriques as f


def client_pour(groupes=(), username='u'):
    u = User.objects.create_user(username=username, password='Mot-de-passe-1')
    definir_droits(u, list(groupes))
    c = APIClient()
    c.force_authenticate(u)
    return c


class ReferentielApiTests(TestCase):
    def setUp(self):
        self.lecteur = client_pour(username='lecteur')
        self.admin = client_pour(['parametres_responsable'], username='param')

    def test_lecture_authentifie_ecriture_parametres(self):
        f.faculte()
        self.assertEqual(self.lecteur.get('/api/core/facultes/').status_code, 200)
        data = {'nom': 'Sciences Économiques', 'code': 'FSE'}
        self.assertEqual(self.lecteur.post('/api/core/facultes/', data, format='json').status_code, 403)
        self.assertEqual(self.admin.post('/api/core/facultes/', data, format='json').status_code, 201)

    def test_anonyme_refuse(self):
        self.assertEqual(APIClient().get('/api/core/facultes/').status_code, 401)

    def test_classe_incoherente_400(self):
        a, port = f.annee(), f.portail()
        fil = f.filiere(port=port)
        r = self.admin.post('/api/core/classes/', {
            'annee': a.pk, 'parcours': f.parcours('Licence', 1).pk, 'filiere': fil.pk,
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('filiere', r.data)

    def test_classe_creee_avec_libelle(self):
        a, port = f.annee(), f.portail()
        r = self.admin.post('/api/core/classes/', {
            'annee': a.pk, 'parcours': f.parcours('Licence', 1).pk, 'portail': port.pk,
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['libelle'], 'L1 MIP — 2026-2027')
        self.assertEqual(r.data['parcours_code'], 'L1')

    def test_filtre_filieres_par_faculte(self):
        fst, fse = f.faculte('FST'), f.faculte('FSE')
        f.filiere(f.departement(fst), f.portail(fst, 'MIP'), 'INFO')
        f.filiere(f.departement(fse, 'Économie'), f.portail(fse, 'ECO'), 'GEST')
        r = self.lecteur.get(f'/api/core/filieres/?faculte={fse.pk}')
        self.assertEqual([x['code'] for x in r.data['results']], ['GEST'])

    def test_supprimer_faculte_utilisee_400(self):
        dep = f.departement()
        r = self.admin.delete(f'/api/core/facultes/{dep.faculte_id}/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('encore utilisé', r.data['detail'])

    def test_definir_en_cours(self):
        a, b = f.annee('2025-2026', en_cours=True), f.annee('2026-2027')
        r = self.admin.post(f'/api/core/annees/{b.pk}/definir_en_cours/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AnneeAcademique.courante(), b)
        self.assertEqual(self.lecteur.post(f'/api/core/annees/{a.pk}/definir_en_cours/').status_code, 403)

    def test_etablissement_get_put(self):
        self.assertEqual(self.lecteur.get('/api/core/etablissement/').data['ville_signature'], 'Liambou')
        r = self.admin.put('/api/core/etablissement/', {
            'nom_secretaire': 'J. Ondongo', 'genre_secretaire': 'F', 'ville_signature': 'Brazzaville',
        }, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['titre_secretaire'], 'La Secrétaire Universitaire')
        self.assertEqual(ParametresEtablissement.get().ville_signature, 'Brazzaville')
        self.assertEqual(self.lecteur.put('/api/core/etablissement/', {}, format='json').status_code, 403)

    def test_ecs_filtre_semestre(self):
        u1 = f.ue('UE1', 'S1')
        f.ec(u1, 'EC1')
        r = self.lecteur.get('/api/core/ecs/?semestre=S2')
        self.assertEqual(r.data['count'], 0)
        r = self.lecteur.get('/api/core/ecs/?semestre=S1')
        self.assertEqual(r.data['results'][0]['ue_code'], 'UE1')
