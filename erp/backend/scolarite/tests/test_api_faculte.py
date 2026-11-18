import io

from openpyxl import load_workbook

from core.models import AnneeAcademique, Classe, JournalAudit
from core.tests import fabriques as f
from scolarite.models import Inscription, Note, ResultatSemestre
from scolarite.tests.api import Base
from scolarite.tests.fabriques import inscrit, noter


class SaisieTests(Base):
    def setUp(self):
        super().setUp()
        self.a = inscrit(self.m.l1, 'Alpha')
        self.b = inscrit(self.m.l1, 'Beta')
        self.na = self.a.notes.get(ec=self.m.algo)
        self.nb = self.b.notes.get(ec=self.m.algo)

    def test_grille(self):
        r = self.faculte.get(f'/api/scolarite/saisie/?classe={self.m.l1.pk}&ec={self.m.algo.pk}')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([l['nom_complet'] for l in r.data['lignes']], ['ALPHA Grâce', 'BETA Grâce'])
        self.assertEqual(r.data['lignes'][0]['note_id'], self.na.pk)
        self.assertIsNone(r.data['lignes'][0]['devoir'])

    def test_ec_hors_programme(self):
        r = self.faculte.get(f'/api/scolarite/saisie/?classe={self.m.l1.pk}&ec={self.m.bdd.pk}')
        self.assertEqual(r.status_code, 400)

    def test_saisie_partielle_erreurs_par_cellule(self):
        r = self.faculte.post('/api/scolarite/saisie/', {'notes': [
            {'note_id': self.na.pk, 'devoir': '12,5', 'session': 14, 'sr': None, 'absent': False},
            {'note_id': self.nb.pk, 'devoir': 21, 'session': 'abc', 'sr': None, 'absent': False},
        ]}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['enregistrees'], 1)
        erreurs = r.data['erreurs'][str(self.nb.pk)]
        self.assertEqual(set(erreurs), {'devoir', 'session'})
        self.na.refresh_from_db()
        self.assertEqual(float(self.na.moyenne), 13.25)
        self.nb.refresh_from_db()
        self.assertIsNone(self.nb.note_devoir)

    def test_sr_sans_session(self):
        r = self.faculte.post('/api/scolarite/saisie/', {'notes': [
            {'note_id': self.na.pk, 'devoir': 10, 'session': None, 'sr': 12, 'absent': False}]}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('sr', r.data['erreurs'][str(self.na.pk)])

    def test_note_hors_perimetre(self):
        autre = inscrit(self.l1_eco, 'Tchicaya').notes.first()
        r = self.faculte_fst.post('/api/scolarite/saisie/', {'notes': [
            {'note_id': autre.pk, 'devoir': 10, 'session': 10}]}, format='json')
        self.assertEqual(r.status_code, 400)
        autre.refresh_from_db()
        self.assertIsNone(autre.note_devoir)

    def test_annee_archivee(self):
        AnneeAcademique.objects.filter(pk=self.m.annee.pk).update(statut='archivee', en_cours=False)
        r = self.faculte.post('/api/scolarite/saisie/', {'notes': [
            {'note_id': self.na.pk, 'devoir': 10, 'session': 10}]}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_secretariat_refuse(self):
        self.assertEqual(self.secretariat.get(f'/api/scolarite/saisie/?classe={self.m.l1.pk}&ec={self.m.algo.pk}')
                         .status_code, 403)


class DeliberationTests(Base):
    def setUp(self):
        super().setUp()
        self.a = inscrit(self.m.l1, 'Alpha')
        self.b = inscrit(self.m.l1, 'Beta')
        for i, v in ((self.a, 14), (self.b, 9)):
            noter(i, self.m.algo, devoir=v, session=v)
            noter(i, self.m.prog, devoir=v, session=v)
        noter(self.a, self.m.analyse, devoir=14, session=14)   # Beta : ANALYSE non saisie
        self.url = f'/api/scolarite/deliberation/?classe={self.m.l1.pk}&semestre=S1'

    def test_calcul_a_la_volee(self):
        r = self.faculte.get(self.url)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([l['nom_complet'] for l in r.data['lignes']], ['ALPHA Grâce', 'BETA Grâce'])
        alpha, beta = r.data['lignes']
        self.assertEqual((alpha['decision'], alpha['mention'], alpha['rang']), ('ADMIS', 'BIEN', 1))
        self.assertEqual(beta['ecs_non_saisis'], ['ANALYSE'])
        self.assertEqual(r.data['ecs_non_saisis'], 1)
        self.assertEqual([u['code'] for u in r.data['ues']], ['UE-INF-11', 'UE-MAT-11'])
        self.assertFalse(r.data['deliberee'])
        self.assertFalse(ResultatSemestre.objects.exists())

    def test_semestre_hors_niveau(self):
        self.assertEqual(self.faculte.get(f'/api/scolarite/deliberation/?classe={self.m.l1.pk}&semestre=S3')
                         .status_code, 400)

    def test_enregistrement(self):
        r = self.faculte.post('/api/scolarite/deliberation/', {'classe': self.m.l1.pk, 'semestre': 'S1'},
                              format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data['deliberee'])
        self.assertEqual(ResultatSemestre.objects.count(), 2)
        self.assertTrue(JournalAudit.objects.filter(action='deliberation').exists())

    def test_perimetre(self):
        url = f'/api/scolarite/deliberation/?classe={self.l1_eco.pk}&semestre=S1'
        self.assertEqual(self.faculte_fst.get(url).status_code, 404)
        self.assertEqual(self.faculte.get(url).status_code, 200)

    def test_export_excel(self):
        r = self.faculte.get(f'/api/scolarite/deliberation/excel/?classe={self.m.l1.pk}&semestre=S1')
        self.assertEqual(r.status_code, 200)
        self.assertIn('spreadsheetml', r['Content-Type'])
        self.assertIn('attachment', r['Content-Disposition'])
        feuille = load_workbook(io.BytesIO(r.content)).active
        lignes = list(feuille.iter_rows(values_only=True))
        entetes = next(l for l in lignes if l and l[0] == 'Rang')
        self.assertEqual(list(entetes), ['Rang', 'Matricule', 'Nom et prénom', 'UE-INF-11', 'UE-MAT-11',
                                         'Moyenne', 'Crédits', 'Décision', 'Mention'])
        donnees = lignes[lignes.index(entetes) + 1:]
        self.assertEqual(donnees[0][2], 'ALPHA Grâce')
        self.assertEqual(donnees[0][5], 14.0)
        self.assertEqual(donnees[0][7], 'ADMIS')

    def test_releve_etudiant(self):
        r = self.faculte.get(f'/api/scolarite/etudiants/{self.a.etudiant.pk}/notes/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([s['semestre'] for s in r.data['semestres']], ['S1', 'S2'])
        self.assertEqual(r.data['semestres'][0]['ligne']['moyenne'], 14.0)
        self.assertIsNone(r.data['semestres'][0]['resultat'])
        self.assertEqual(self.secretariat.get(f'/api/scolarite/etudiants/{self.a.etudiant.pk}/notes/').status_code,
                         200)
        autre = inscrit(self.l1_eco, 'Tchicaya')
        self.assertEqual(self.faculte_fst.get(f'/api/scolarite/etudiants/{autre.etudiant.pk}/notes/').status_code,
                         404)


class PassageTests(Base):
    """Promotion (L2 → L3…) et orientation (L1 → L2) vers l'année suivante."""

    def setUp(self):
        super().setUp()
        self.suivante = f.annee('2027-2028')
        self.l3_suivante = Classe.objects.create(annee=self.suivante, parcours=f.parcours('Licence', 3),
                                                 filiere=self.m.info)
        self.l2_suivante = Classe.objects.create(annee=self.suivante, parcours=f.parcours('Licence', 2),
                                                 filiere=self.m.info)
        f.ec(f.ue('UE-INF-31', 'S5', port=None, fil=self.m.info), 'IA', credits=3, dep=self.m.dep)
        self.l2_i = inscrit(self.m.l2, 'Deux')
        self.l1_i = inscrit(self.m.l1, 'Un')
        for i in (self.l2_i, self.l1_i):
            for s in i.classe.semestres:
                ResultatSemestre.objects.create(inscription=i, semestre=s, moyenne=12, credits_obtenus=30,
                                                credits_totaux=30, decision='ADMIS', mention='PASSABLE', rang=1)

    def test_liste(self):
        r = self.faculte.get(f'/api/scolarite/promotion/?classe={self.m.l2.pk}')
        self.assertEqual(r.status_code, 200, r.data)
        ligne = r.data['etudiants'][0]
        self.assertEqual(ligne['nom_complet'], 'DEUX Grâce')
        self.assertEqual([x['decision'] for x in ligne['resultats']], ['ADMIS', 'ADMIS'])
        self.assertEqual(r.data['classe_cible'], self.l3_suivante.pk)

    def test_promotion_idempotente(self):
        corps = {'classe': self.m.l2.pk, 'etudiants': [self.l2_i.etudiant.pk]}
        r = self.faculte.post('/api/scolarite/promotion/', corps, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['promus'], 1)
        nouvelle = Inscription.objects.get(etudiant=self.l2_i.etudiant, annee=self.suivante)
        self.assertEqual((nouvelle.classe, nouvelle.type), (self.l3_suivante, 'reinscription'))
        self.assertEqual(set(nouvelle.notes.values_list('ec__code', flat=True)), {'IA'})
        self.l2_i.refresh_from_db()
        self.assertEqual(self.l2_i.statut, 'terminee')
        r = self.faculte.post('/api/scolarite/promotion/', corps, format='json')
        self.assertEqual(r.data['promus'], 0)
        self.assertIn("déjà inscrit pour l'année suivante", r.data['ignores'][0]['motif'])
        self.assertEqual(Inscription.objects.filter(etudiant=self.l2_i.etudiant).count(), 2)

    def test_sans_resultats_ignore(self):
        ResultatSemestre.objects.filter(inscription=self.l2_i, semestre='S4').delete()
        r = self.faculte.post('/api/scolarite/promotion/', {'classe': self.m.l2.pk,
                                                             'etudiants': [self.l2_i.etudiant.pk]}, format='json')
        self.assertEqual(r.data['promus'], 0)
        self.assertIn('S4', r.data['ignores'][0]['motif'])

    def test_classe_cible_absente(self):
        self.l3_suivante.delete()
        r = self.faculte.post('/api/scolarite/promotion/', {'classe': self.m.l2.pk,
                                                             'etudiants': [self.l2_i.etudiant.pk]}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('L3 INFO', str(r.data))

    def test_l1_passe_par_l_orientation(self):
        r = self.faculte.post('/api/scolarite/promotion/', {'classe': self.m.l1.pk,
                                                             'etudiants': [self.l1_i.etudiant.pk]}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('orientation', str(r.data))

    def test_orientation(self):
        corps = {'classe': self.m.l1.pk, 'choix': {str(self.l1_i.etudiant.pk): self.m.info.pk}}
        r = self.faculte.post('/api/scolarite/orientation/', corps, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['promus'], 1)
        nouvelle = Inscription.objects.get(etudiant=self.l1_i.etudiant, annee=self.suivante)
        self.assertEqual(nouvelle.classe, self.l2_suivante)
        r = self.faculte.post('/api/scolarite/orientation/', corps, format='json')
        self.assertEqual(r.data['promus'], 0)
        self.assertIn('déjà inscrit', r.data['ignores'][0]['motif'])

    def test_orientation_filiere_d_un_autre_portail(self):
        fil_eco = f.filiere(f.departement(self.fse, 'Économie'), self.eco, 'ECO')
        corps = {'classe': self.m.l1.pk, 'choix': {str(self.l1_i.etudiant.pk): fil_eco.pk}}
        r = self.faculte.post('/api/scolarite/orientation/', corps, format='json')
        self.assertEqual(r.data['promus'], 0)
        self.assertIn('portail', r.data['ignores'][0]['motif'])
        self.assertFalse(Inscription.objects.filter(annee=self.suivante).exists())

    def test_options_d_orientation(self):
        r = self.faculte.get(f'/api/scolarite/orientation/?classe={self.m.l1.pk}')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([x['code'] for x in r.data['filieres']], ['INFO'])
        self.assertEqual(len(r.data['etudiants']), 1)

    def test_perimetre(self):
        self.assertEqual(self.faculte_fst.get(f'/api/scolarite/promotion/?classe={self.l1_eco.pk}').status_code, 404)
