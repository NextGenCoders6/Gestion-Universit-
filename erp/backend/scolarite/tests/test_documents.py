from django.test import TestCase, override_settings

from core.documents import qr_data_uri
from scolarite.models import DocumentEmis
from scolarite.moteur import deliberation
from scolarite.tests.api import Base
from scolarite.tests.fabriques import inscrit, noter


class QrTests(TestCase):
    def test_qr_png(self):
        self.assertTrue(qr_data_uri('https://exemple.org/verifier/abc').startswith('data:image/png;base64,iVBOR'))


@override_settings(BASE_URL='https://erp.uccb.test')
class DocumentsTests(Base):
    def setUp(self):
        super().setUp()
        self.i = inscrit(self.m.l1, 'Alpha')
        for ec in (self.m.algo, self.m.prog, self.m.analyse):
            noter(self.i, ec, devoir=13, session=15)
        self.url = f'/api/scolarite/etudiants/{self.i.etudiant.pk}'

    def test_attestation(self):
        r = self.secretariat.get(f'{self.url}/attestation.pdf')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        doc = DocumentEmis.objects.get()
        self.assertEqual((doc.type, doc.inscription, len(doc.jeton)), ('attestation', self.i, 32))
        self.assertEqual(r['X-Verification-Url'], f'https://erp.uccb.test/verifier/{doc.jeton}')

    def test_jetons_uniques(self):
        self.secretariat.get(f'{self.url}/attestation.pdf')
        self.secretariat.get(f'{self.url}/attestation.pdf')
        self.assertEqual(DocumentEmis.objects.values('jeton').distinct().count(), 2)

    def test_releve_exige_une_deliberation(self):
        r = self.secretariat.get(f'{self.url}/releve.pdf?semestre=S1')
        self.assertEqual(r.status_code, 400)
        deliberation(self.m.l1, 'S1', enregistrer=True)
        r = self.secretariat.get(f'{self.url}/releve.pdf?semestre=S1')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))
        doc = DocumentEmis.objects.get()
        self.assertEqual((doc.type, doc.semestre, doc.decision), ('releve', 'S1', 'ADMIS'))

    def test_qr_dans_le_document(self):
        from scolarite.documents import contexte_attestation
        contexte = contexte_attestation(self.i, None)
        self.assertTrue(contexte['qr'].startswith('data:image/png;base64,'))
        self.assertTrue(contexte['url_verification'].startswith('https://erp.uccb.test/verifier/'))

    def test_droits(self):
        self.assertEqual(self.faculte.get(f'{self.url}/attestation.pdf').status_code, 403)
        autre = inscrit(self.l1_eco, 'Tchicaya')
        self.assertEqual(self.secretariat_fst.get(f'/api/scolarite/etudiants/{autre.etudiant.pk}/attestation.pdf')
                         .status_code, 404)

    def test_matrice_a3(self):
        url = f'/api/scolarite/matrice-a3.pdf?classe={self.m.l1.pk}&semestre=S1'
        r = self.faculte.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.assertEqual(self.secretariat.get(url).status_code, 403)
        self.assertEqual(self.faculte_fst.get(f'/api/scolarite/matrice-a3.pdf?classe={self.l1_eco.pk}&semestre=S1')
                         .status_code, 404)


class VerificationTests(Base):
    def setUp(self):
        super().setUp()
        self.i = inscrit(self.m.l1, 'Alpha')
        noter(self.i, self.m.algo, devoir=17.25, session=17.25)
        deliberation(self.m.l1, 'S1', enregistrer=True)
        self.secretariat.get(f'/api/scolarite/etudiants/{self.i.etudiant.pk}/releve.pdf?semestre=S1')
        self.doc = DocumentEmis.objects.get()

    def test_document_connu(self):
        r = self.client.get(f'/verifier/{self.doc.jeton}')
        self.assertEqual(r.status_code, 200)
        page = r.content.decode()
        for texte in ('Document authentique', 'ALPHA Grâce', self.i.etudiant.matricule, 'Relevé de notes', 'S1'):
            self.assertIn(texte, page)
        # Aucune note détaillée : ni la note d'EC, ni le code de l'EC.
        self.assertNotIn('17.25', page)
        self.assertNotIn('17,25', page)
        self.assertNotIn('ALGO', page)

    def test_jeton_inconnu_ou_modifie(self):
        for jeton in ('inconnu', self.doc.jeton[:-1] + ('A' if self.doc.jeton[-1] != 'A' else 'B'),
                      "x' OR 1=1 --", 'é' * 40):
            with self.subTest(jeton=jeton):
                r = self.client.get(f'/verifier/{jeton}')
                self.assertEqual(r.status_code, 404)
                self.assertIn('Document introuvable', r.content.decode())
                self.assertNotIn('ALPHA', r.content.decode())

    def test_hors_spa(self):
        r = self.client.get(f'/verifier/{self.doc.jeton}')
        self.assertNotIn('id="root"', r.content.decode())
