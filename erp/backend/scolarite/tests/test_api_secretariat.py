from core.models import Etudiant, JournalAudit
from scolarite.models import Inscription
from scolarite.tests.api import Base
from scolarite.tests.fabriques import etudiant, inscrit, noter

PERSONNE = {'nom': 'Moukala', 'prenom': 'Divine', 'genre': 'F', 'date_naissance': '2006-03-14',
            'email': 'divine.moukala@example.org', 'lieu_naissance': 'Pointe-Noire'}


class CreationTests(Base):
    def creer(self, c=None, classe=None, **personne):
        return (c or self.secretariat).post('/api/scolarite/etudiants/', {
            'personne': {**PERSONNE, **personne}, 'classe': (classe or self.m.l1).pk,
            'date_inscription': '2026-10-01'}, format='json')

    def test_creation_complete(self):
        r = self.creer()
        self.assertEqual(r.status_code, 201, r.data)
        e = Etudiant.objects.get(pk=r.data['id'])
        self.assertTrue(e.matricule.startswith('UCCB26MOUDI'))
        self.assertEqual(r.data['matricule'], e.matricule)
        i = e.inscriptions.get()
        self.assertEqual((i.classe, i.type, i.statut), (self.m.l1, 'premiere', 'active'))
        self.assertEqual(i.notes.count(), 4)
        self.assertTrue(JournalAudit.objects.filter(module='scolarite', action='creation_etudiant').exists())

    def test_email_et_date_de_naissance_obligatoires(self):
        r = self.creer(email='', date_naissance=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('email', r.data['personne'])
        self.assertIn('date_naissance', r.data['personne'])
        self.assertFalse(Etudiant.objects.exists())

    def test_nom_invalide_ne_cree_rien(self):
        r = self.creer(nom='M0ukala!')
        self.assertEqual(r.status_code, 400)
        self.assertIn('nom', r.data['personne'])
        self.assertFalse(Etudiant.objects.exists())

    def test_classe_hors_perimetre(self):
        r = self.creer(self.secretariat_fst, classe=self.l1_eco)
        self.assertEqual(r.status_code, 400)
        self.assertIn('classe', r.data)

    def test_faculte_en_lecture_seule(self):
        self.assertEqual(self.creer(self.faculte).status_code, 403)
        self.assertEqual(self.faculte.get('/api/scolarite/etudiants/').status_code, 200)

    def test_autre_module_refuse(self):
        self.assertEqual(self.autre.get('/api/scolarite/etudiants/').status_code, 403)


class ListeEtFicheTests(Base):
    def setUp(self):
        super().setUp()
        self.fst = inscrit(self.m.l1, 'Bouanga', 'Paul')
        self.fse_i = inscrit(self.l1_eco, 'Tchicaya', 'Rose')

    def test_liste_et_filtres(self):
        r = self.secretariat.get('/api/scolarite/etudiants/')
        self.assertEqual(r.data['count'], 2)
        r = self.secretariat.get(f'/api/scolarite/etudiants/?classe={self.m.l1.pk}')
        self.assertEqual([e['nom'] for e in r.data['results']], ['Bouanga'])
        self.assertEqual(r.data['results'][0]['inscription_courante']['classe'], self.m.l1.pk)
        self.assertEqual(self.secretariat.get('/api/scolarite/etudiants/?q=tchic').data['count'], 1)
        self.assertEqual(self.secretariat.get(f'/api/scolarite/etudiants/?faculte={self.fse.pk}').data['count'], 1)
        self.assertEqual(self.secretariat.get('/api/scolarite/etudiants/?classe=abc').status_code, 400)

    def test_perimetre_faculte(self):
        r = self.secretariat_fst.get('/api/scolarite/etudiants/')
        self.assertEqual([e['nom'] for e in r.data['results']], ['Bouanga'])
        pk = self.fse_i.etudiant.pk
        self.assertEqual(self.secretariat_fst.get(f'/api/scolarite/etudiants/{pk}/').status_code, 404)
        self.assertEqual(self.faculte_fst.get(f'/api/scolarite/etudiants/{pk}/').status_code, 404)
        self.assertEqual(self.secretariat_fst.post(f'/api/scolarite/etudiants/{pk}/statut/',
                                                   {'statut': 'abandonne'}, format='json').status_code, 404)

    def test_fiche(self):
        r = self.secretariat.get(f'/api/scolarite/etudiants/{self.fst.etudiant.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['personne']['nom'], 'Bouanga')
        self.assertEqual([i['classe_libelle'] for i in r.data['inscriptions']], ['L1 MIP — 2026-2027'])

    def test_abandon_termine_l_inscription(self):
        pk = self.fst.etudiant.pk
        r = self.secretariat.post(f'/api/scolarite/etudiants/{pk}/statut/', {'statut': 'abandonne'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.fst.refresh_from_db()
        self.assertEqual((self.fst.etudiant.statut, self.fst.statut), ('abandonne', 'abandonnee'))
        self.assertTrue(JournalAudit.objects.filter(action='statut_etudiant').exists())
        r = self.secretariat.post(f'/api/scolarite/etudiants/{pk}/statut/', {'statut': 'roi'}, format='json')
        self.assertEqual(r.status_code, 400)


class InscriptionsTests(Base):
    def test_seconde_inscription_meme_annee_refusee(self):
        i = inscrit(self.m.l1)
        r = self.secretariat.post('/api/scolarite/inscriptions/', {
            'etudiant': i.etudiant.pk, 'classe': self.m.l2.pk, 'type': 'reinscription'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('déjà inscrit', str(r.data))

    def test_reinscription_d_un_etudiant_existant(self):
        e = etudiant(annee=self.m.annee)
        r = self.secretariat.post('/api/scolarite/inscriptions/', {
            'etudiant': e.pk, 'classe': self.m.l2.pk, 'type': 'reinscription'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Inscription.objects.get().notes.count(), 1)
        self.assertTrue(JournalAudit.objects.filter(action='inscription').exists())

    def test_changement_de_classe_sans_note(self):
        i = inscrit(self.m.l1)
        r = self.secretariat.patch(f'/api/scolarite/inscriptions/{i.pk}/', {'classe': self.m.l2.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(set(i.notes.values_list('ec__code', flat=True)), {'BDD'})

    def test_changement_de_classe_refuse_apres_saisie(self):
        i = inscrit(self.m.l1)
        noter(i, self.m.algo, devoir=10, session=10)
        r = self.secretariat.patch(f'/api/scolarite/inscriptions/{i.pk}/', {'classe': self.m.l2.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        i.refresh_from_db()
        self.assertEqual(i.classe, self.m.l1)

    def test_liste_filtree_et_perimetre(self):
        inscrit(self.m.l1)
        inscrit(self.l1_eco, 'Tchicaya')
        self.assertEqual(self.secretariat.get('/api/scolarite/inscriptions/').data['count'], 2)
        self.assertEqual(self.secretariat_fst.get('/api/scolarite/inscriptions/').data['count'], 1)
        self.assertEqual(self.faculte.get(f'/api/scolarite/inscriptions/?classe={self.l1_eco.pk}').data['count'], 1)

    def test_reinscription_d_un_etudiant_hors_perimetre(self):
        i = inscrit(self.l1_eco, 'Tchicaya')
        r = self.secretariat_fst.post('/api/scolarite/inscriptions/', {
            'etudiant': i.etudiant.pk, 'classe': self.m.l2.pk, 'type': 'reinscription'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('etudiant', r.data)
