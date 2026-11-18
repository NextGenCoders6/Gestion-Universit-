"""API du module EDT : séances, affectations, enseignements, référents, espace enseignant."""
from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.droits import definir_droits
from core.models import Classe
from core.tests import fabriques as f
from edt.models import AffectationEC, ReferentClasse, Seance
from edt.tests.fabriques import Monde, affectation, enseignant

LUNDI = date(2026, 10, 5)


def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def compte(username, ens=None, groupes=()):
    u = User.objects.create_user(username, password='Mot-de-passe-1')
    definir_droits(u, list(groupes))
    if ens is not None:
        p = ens.personne
        p.user = u
        p.save()
    return u


class Base(TestCase):
    def setUp(self):
        self.m = Monde()
        self.m.dep.chef = self.m.ens
        self.m.dep.save()
        self.chef = client(compte('chef', self.m.ens))                      # gère L2 INFO
        self.resp = client(compte('resp', groupes=['edt_responsable']))     # gère tout
        self.lecteur = client(compte('lecteur', groupes=['edt_utilisateur']))
        self.prof = client(compte('prof', self.m.ens2))                     # enseignant simple
        fil_math = f.filiere(self.m.dep_math, self.m.mip, 'MATH')
        self.l2_math = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 2), filiere=fil_math)
        self.ec_math = f.ec(f.ue('UE-MATH3', 'S3', fil=fil_math), 'ANA3', credits=3, dep=self.m.dep_math)
        self.matheux = enseignant('Mavoungou', self.m.dep_math)

    def donnees(self, **kw):
        d = {'ec': self.m.bdd.pk, 'classe': self.m.l2.pk, 'enseignant': self.m.ens2.pk, 'type_seance': 'CM',
             'date_seance': '2026-10-05', 'heure_debut': '09:00', 'heure_fin': '11:00'}
        d.update(kw)
        return d


class SeancesApiTests(Base):
    def test_chef_cree_un_brouillon_dans_sa_classe(self):
        r = self.chef.post('/api/edt/seances/', self.donnees(), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['statut'], 'brouillon')
        self.assertEqual(r.data['ec_code'], 'BDD')
        self.assertEqual(r.data['classe_libelle'], 'L2 INFO — 2026-2027')

    def test_chef_refuse_hors_perimetre(self):
        r = self.chef.post('/api/edt/seances/', self.donnees(ec=self.ec_math.pk, classe=self.l2_math.pk,
                                                             enseignant=self.matheux.pk), format='json')
        self.assertEqual(r.status_code, 403)

    def test_seance_autre_departement_404(self):
        s = Seance.objects.create(ec=self.ec_math, classe=self.l2_math, enseignant=self.matheux, date_seance=LUNDI,
                                  heure_debut=time(9, 0), heure_fin=time(11, 0), type_seance='CM')
        self.assertEqual(self.chef.get(f'/api/edt/seances/{s.pk}/').status_code, 404)
        self.assertEqual(self.chef.patch(f'/api/edt/seances/{s.pk}/', {'libelle': 'x'}, format='json').status_code, 404)
        self.assertEqual(self.chef.delete(f'/api/edt/seances/{s.pk}/').status_code, 404)
        self.assertEqual(self.resp.get(f'/api/edt/seances/{s.pk}/').status_code, 200)

    def test_edt_utilisateur_lecture_seule(self):
        self.assertEqual(self.lecteur.get('/api/edt/seances/').status_code, 200)
        self.assertEqual(self.lecteur.post('/api/edt/seances/', self.donnees(), format='json').status_code, 403)

    def test_enseignant_simple_sans_acces_au_module(self):
        self.assertEqual(self.prof.get('/api/edt/seances/').status_code, 403)

    def test_regle_metier_en_400_par_champ(self):
        r = self.chef.post('/api/edt/seances/', self.donnees(date_seance='2026-10-11'), format='json')  # dimanche
        self.assertEqual(r.status_code, 400)
        self.assertIn('date_seance', r.data)

    def test_publier_puis_depublier(self):
        sid = self.chef.post('/api/edt/seances/', self.donnees(), format='json').data['id']
        r = self.chef.post(f'/api/edt/seances/{sid}/publier/')
        self.assertEqual(r.data['statut'], 'Confirmée')
        self.assertEqual(self.chef.post(f'/api/edt/seances/{sid}/publier/').status_code, 400)
        self.assertEqual(self.chef.post(f'/api/edt/seances/{sid}/depublier/').data['statut'], 'brouillon')

    def test_publier_masse_tout_ou_rien(self):
        a = self.chef.post('/api/edt/seances/', self.donnees(), format='json').data['id']
        b = self.chef.post('/api/edt/seances/', self.donnees(enseignant=self.m.ens.pk, heure_debut='10:00'),
                           format='json').data['id']
        r = self.chef.post('/api/edt/seances/publier_masse/', {'seance_ids': [a, b]}, format='json')
        self.assertEqual(r.status_code, 400)  # même classe, même créneau : conflit
        self.assertTrue(r.data['erreurs'])
        self.assertFalse(Seance.objects.filter(statut='Confirmée').exists())
        self.chef.delete(f'/api/edt/seances/{b}/')
        r = self.chef.post('/api/edt/seances/publier_masse/', {'seance_ids': [a]}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_reporter(self):
        sid = self.chef.post('/api/edt/seances/', self.donnees(), format='json').data['id']
        self.chef.post(f'/api/edt/seances/{sid}/publier/')
        r = self.chef.patch(f'/api/edt/seances/{sid}/reporter/', {
            'date_report': '2026-10-06', 'heure_debut_report': '09:00', 'heure_fin_report': '11:00'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['statut'], 'Reportée')
        self.assertEqual(r.data['creneau_effectif']['jour'], '2026-10-06')
        r = self.chef.patch(f'/api/edt/seances/{sid}/reporter/', {
            'date_report': '2026-10-11', 'heure_debut_report': '09:00', 'heure_fin_report': '11:00'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_annuler_par_patch_mais_pas_confirmer(self):
        sid = self.chef.post('/api/edt/seances/', self.donnees(), format='json').data['id']
        self.assertEqual(self.chef.patch(f'/api/edt/seances/{sid}/', {'statut': 'Confirmée'}, format='json').status_code, 400)
        self.assertEqual(self.chef.patch(f'/api/edt/seances/{sid}/', {'statut': 'Annulée'}, format='json').data['statut'], 'Annulée')

    def test_conflits_listes(self):
        Seance.objects.bulk_create([
            Seance(ec=self.m.bdd, classe=self.m.l2, enseignant=self.m.ens2, date_seance=LUNDI, heure_debut=time(9, 0),
                   heure_fin=time(11, 0), type_seance='CM', statut='Confirmée'),
            Seance(ec=self.m.bdd, classe=self.m.l2, enseignant=self.m.ens, date_seance=LUNDI, heure_debut=time(10, 0),
                   heure_fin=time(11, 0), type_seance='CM', statut='Confirmée'),
        ])
        r = self.chef.get(f'/api/edt/seances/conflits/?annee={self.m.annee.pk}')
        self.assertEqual(r.data['count'], 2)

    def test_filtres(self):
        self.chef.post('/api/edt/seances/', self.donnees(), format='json')
        self.assertEqual(self.resp.get(f'/api/edt/seances/?classe={self.m.l2.pk}').data['count'], 1)
        self.assertEqual(self.resp.get('/api/edt/seances/?date_debut=2026-10-06').data['count'], 0)
        self.assertEqual(self.resp.get('/api/edt/seances/?classe=abc').status_code, 400)

    def test_seances_liees(self):
        sid = self.chef.post('/api/edt/seances/', self.donnees(), format='json').data['id']
        self.assertEqual(self.chef.get(f'/api/edt/seances/{sid}/seances_liees/').data['count'], 0)


class AffectationsApiTests(Base):
    def test_chef_cree_et_voit_les_heures(self):
        r = self.chef.post('/api/edt/affectations/', {'ec': self.m.bdd.pk, 'classe': self.m.l2.pk,
                                                      'enseignant': self.m.ens2.pk, 'heures_prevues': 40}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['heures_restantes'], 40)
        self.assertTrue(r.data['warnings'])  # 40 h > 36 h de l'EC

    def test_hors_perimetre_refuse(self):
        r = self.chef.post('/api/edt/affectations/', {'ec': self.ec_math.pk, 'classe': self.l2_math.pk,
                                                      'enseignant': self.matheux.pk, 'heures_prevues': 10}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_regle_hors_departement(self):
        donnees = {'ec': self.m.bdd.pk, 'classe': self.m.l2.pk, 'enseignant': self.matheux.pk, 'heures_prevues': 10}
        self.assertEqual(self.chef.post('/api/edt/affectations/', donnees, format='json').status_code, 400)
        donnees['hors_departement'] = True
        self.assertEqual(self.chef.post('/api/edt/affectations/', donnees, format='json').status_code, 201)


class EnseignementsApiTests(Base):
    def test_une_ligne_par_ec_et_classe_du_perimetre(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 20)
        r = self.chef.get('/api/edt/enseignements/')
        self.assertEqual(r.status_code, 200)
        lignes = r.data['results']
        self.assertEqual([(l['ec_code'], l['classe_libelle']) for l in lignes], [('BDD', 'L2 INFO — 2026-2027')])
        self.assertEqual(lignes[0]['heures_max'], 36)
        self.assertEqual(len(lignes[0]['affectations']), 1)
        tous = self.resp.get('/api/edt/enseignements/').data['results']
        self.assertEqual({l['ec_code'] for l in tous}, {'ALGO', 'BDD', 'ANA3'})


class ReferentsApiTests(Base):
    def test_responsable_gere_les_referents(self):
        r = self.resp.post('/api/edt/referents/', {'enseignant': self.matheux.pk, 'classes': [self.m.l1.pk]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.chef.post('/api/edt/referents/', {'enseignant': self.m.ens2.pk, 'classes': []},
                                        format='json').status_code, 403)
        self.assertEqual(ReferentClasse.objects.get().classes.get(), self.m.l1)


class EspaceEnseignantTests(Base):
    def test_planning_personnel_seances_publiees(self):
        Seance.objects.bulk_create([
            Seance(ec=self.m.bdd, classe=self.m.l2, enseignant=self.m.ens2, date_seance=LUNDI, heure_debut=time(9, 0),
                   heure_fin=time(11, 0), type_seance='CM', statut='Confirmée'),
            Seance(ec=self.m.bdd, classe=self.m.l2, enseignant=self.m.ens2, date_seance=LUNDI, heure_debut=time(14, 15),
                   heure_fin=time(16, 15), type_seance='CM', statut='brouillon'),
        ])
        r = self.prof.get('/api/edt/moi/planning/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)

    def test_mes_enseignements(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 20)
        r = self.prof.get('/api/edt/moi/enseignements/')
        self.assertEqual(r.data[0]['ec_code'], 'BDD')
        self.assertEqual(r.data[0]['heures_prevues'], 20)

    def test_reserve_aux_enseignants(self):
        self.assertEqual(self.lecteur.get('/api/edt/moi/planning/').status_code, 403)

    def test_liste_enseignants_pour_les_formulaires(self):
        r = self.chef.get('/api/edt/enseignants/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        self.assertIn('departement_libelle', r.data['results'][0])
