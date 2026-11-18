import io
import shutil
import tempfile
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from edt.models import DocumentPedagogique
from edt.tests.fabriques import affectation
from edt.tests.test_api import Base

MEDIA = tempfile.mkdtemp(prefix='erp-media-tests-')


def pdf(nom='cours.pdf', contenu=b'%PDF-1.4\n% test\n'):
    return SimpleUploadedFile(nom, contenu, content_type='application/pdf')


def docx_a_macros():
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types><Default ContentType="application/vnd.ms-word.document.macroEnabled"/></Types>')
        z.writestr('word/document.xml', '<w/>')
        z.writestr('word/vbaProject.bin', b'x')
    return SimpleUploadedFile('piege.docx', tampon.getvalue())


@override_settings(MEDIA_ROOT=MEDIA)
class DocumentsTests(Base):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def deposer(self, client, url='/api/edt/moi/documents/', fichier=None, **kw):
        donnees = {'titre': 'Chapitre 1', 'type_doc': 'cours', 'ec': self.m.bdd.pk, 'classe': self.m.l2.pk,
                   'fichier': fichier or pdf()}
        donnees.update(kw)
        return client.post(url, donnees, format='multipart')

    def test_enseignant_affecte_depose_et_telecharge(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 20)
        r = self.deposer(self.prof)
        self.assertEqual(r.status_code, 201, r.data)
        doc = DocumentPedagogique.objects.get()
        self.assertEqual(doc.enseignant, self.m.ens2)
        self.assertEqual(len(self.prof.get('/api/edt/moi/documents/').data), 1)
        t = self.resp.get(f'/api/edt/documents/{doc.pk}/telecharger/')
        self.assertEqual(t.status_code, 200)
        self.assertIn('attachment', t['Content-Disposition'])

    def test_enseignant_non_affecte_refuse(self):
        self.assertEqual(self.deposer(self.prof).status_code, 403)

    def test_fichier_deguise_refuse(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 20)
        r = self.deposer(self.prof, fichier=SimpleUploadedFile('faux.pdf', b'MZ\x90\x00 programme'))
        self.assertEqual(r.status_code, 400)
        self.assertIn('fichier', r.data)

    def test_extension_refusee(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 20)
        self.assertEqual(self.deposer(self.prof, fichier=SimpleUploadedFile('a.exe', b'MZ')).status_code, 400)

    def test_document_a_macros_refuse(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 20)
        self.assertEqual(self.deposer(self.prof, fichier=docx_a_macros()).status_code, 400)

    @override_settings(DOCUMENT_MAX_UPLOAD_BYTES=10)
    def test_trop_gros_refuse(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 20)
        self.assertEqual(self.deposer(self.prof).status_code, 400)

    def test_gestionnaire_depose_pour_un_enseignant_et_hors_perimetre_404(self):
        r = self.deposer(self.chef, url='/api/edt/documents/', enseignant=self.m.ens2.pk)
        self.assertEqual(r.status_code, 201, r.data)
        doc_math = DocumentPedagogique.objects.create(titre='x', type_doc='cours', ec=self.ec_math,
                                                      classe=self.l2_math, enseignant=self.matheux, fichier=pdf('m.pdf'))
        self.assertEqual(self.chef.get(f'/api/edt/documents/{doc_math.pk}/telecharger/').status_code, 404)
