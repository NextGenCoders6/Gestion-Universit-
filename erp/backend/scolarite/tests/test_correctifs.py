"""Non-régression des constats de la relecture finale de la phase 3."""
from core.models import Classe
from core.tests import fabriques as f
from scolarite.inscriptions import inscrire
from scolarite.models import DocumentEmis, Note, ResultatSemestre
from scolarite.moteur import deliberation
from scolarite.tests.api import Base
from scolarite.tests.fabriques import inscrit, noter


class PerimetreParInscriptionTests(Base):
    """Important 1 : une inscription passée dans ma faculté ne m'ouvre pas les autres."""

    def setUp(self):
        super().setUp()
        from scolarite.tests.api import client, compte
        self.secretariat_fse = client(compte('secretariat_fse', ['scolarite_secretariat'], faculte=self.fse))
        self.faculte_fse = client(compte('faculte_fse', ['scolarite_faculte'], faculte=self.fse))
        i_eco = inscrit(self.l1_eco, 'Transfert')
        self.etudiant = i_eco.etudiant
        suivante = f.annee('2027-2028')
        l2 = Classe.objects.create(annee=suivante, parcours=f.parcours('Licence', 2), filiere=self.m.info)
        self.i_fst = inscrire(self.etudiant, l2, type='reinscription')
        i_eco.statut = 'terminee'
        i_eco.save()

    def test_notes_limitees_aux_inscriptions_visibles(self):
        r = self.faculte_fse.get(f'/api/scolarite/etudiants/{self.etudiant.pk}/notes/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['classe'], 'L1 ECO — 2026-2027')
        r = self.faculte_fse.get(f'/api/scolarite/etudiants/{self.etudiant.pk}/notes/?annee={self.i_fst.annee_id}')
        self.assertEqual(r.status_code, 404)

    def test_attestation_hors_perimetre(self):
        r = self.secretariat_fse.get(f'/api/scolarite/etudiants/{self.etudiant.pk}/attestation.pdf'
                                     f'?annee={self.i_fst.annee_id}')
        self.assertEqual(r.status_code, 404)
        self.assertFalse(DocumentEmis.objects.exists())

    def test_fiche_et_statut(self):
        r = self.secretariat_fse.get(f'/api/scolarite/etudiants/{self.etudiant.pk}/')
        self.assertEqual([i['classe_libelle'] for i in r.data['inscriptions']], ['L1 ECO — 2026-2027'])
        r = self.secretariat_fse.post(f'/api/scolarite/etudiants/{self.etudiant.pk}/statut/', {'statut': 'abandonne'},
                                      format='json')
        self.assertEqual(r.status_code, 404)
        self.i_fst.refresh_from_db()
        self.assertEqual(self.i_fst.statut, 'active')


class VerrouApresDeliberationTests(Base):
    """Important 2 : après délibération, les notes du semestre sont figées jusqu'à réouverture."""

    def setUp(self):
        super().setUp()
        self.i = inscrit(self.m.l1, 'Alpha')
        for ec in (self.m.algo, self.m.prog, self.m.analyse):
            noter(self.i, ec, devoir=14, session=14)
        deliberation(self.m.l1, 'S1', enregistrer=True)
        self.note = self.i.notes.get(ec=self.m.algo)

    def saisir(self):
        return self.faculte.post('/api/scolarite/saisie/', {'notes': [
            {'note_id': self.note.pk, 'devoir': 2, 'session': 2}]}, format='json')

    def test_saisie_refusee_puis_reouverture(self):
        r = self.saisir()
        self.assertEqual(r.status_code, 400)
        self.assertIn('délibéré', str(r.data['erreurs']))
        self.note.refresh_from_db()
        self.assertEqual(float(self.note.moyenne), 14.0)
        grille = self.faculte.get(f'/api/scolarite/saisie/?classe={self.m.l1.pk}&ec={self.m.algo.pk}')
        self.assertTrue(grille.data['deliberee'])

        r = self.faculte.delete(f'/api/scolarite/deliberation/?classe={self.m.l1.pk}&semestre=S1')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(r.data['deliberee'])
        self.assertFalse(ResultatSemestre.objects.exists())
        self.assertEqual(self.saisir().status_code, 200)

    def test_autre_semestre_non_verrouille(self):
        reseau = self.i.notes.get(ec=self.m.reseau)
        r = self.faculte.post('/api/scolarite/saisie/', {'notes': [
            {'note_id': reseau.pk, 'devoir': 12, 'session': 12}]}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_reouverture_reservee_et_perimetre(self):
        url = f'/api/scolarite/deliberation/?classe={self.m.l1.pk}&semestre=S1'
        self.assertEqual(self.secretariat.delete(url).status_code, 403)
        url_eco = f'/api/scolarite/deliberation/?classe={self.l1_eco.pk}&semestre=S1'
        self.assertEqual(self.faculte_fst.delete(url_eco).status_code, 404)


class ECAjouteApresInscriptionTests(Base):
    """Important 3 : un EC ajouté au programme après les inscriptions peut recevoir des notes."""

    def test_lignes_creees_a_l_ouverture_de_la_grille(self):
        i = inscrit(self.m.l1, 'Alpha')
        nouveau = f.ec(self.m.ue1, 'NOUVEAU', credits=2, dep=self.m.dep)
        r = self.faculte.get(f'/api/scolarite/saisie/?classe={self.m.l1.pk}&ec={nouveau.pk}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['lignes']), 1)
        self.assertTrue(Note.objects.filter(inscription=i, ec=nouveau).exists())
        self.faculte.get(f'/api/scolarite/saisie/?classe={self.m.l1.pk}&ec={nouveau.pk}')
        self.assertEqual(Note.objects.filter(inscription=i, ec=nouveau).count(), 1)
