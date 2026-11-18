"""Passe finale (phase 6) : défauts reportés de la Scolarité."""
from unittest import mock

from django.core.checks import Warning as Avertissement
from django.test import TestCase, override_settings

from core.models import AnneeAcademique, Classe
from core.tests import fabriques as f
from scolarite.models import DocumentEmis, Inscription, ResultatSemestre
from scolarite.tests.api import Base
from scolarite.tests.fabriques import inscrit


class PromotionTests(Base):
    def setUp(self):
        super().setUp()
        self.suivante = f.annee('2027-2028')
        self.l3 = Classe.objects.create(annee=self.suivante, parcours=f.parcours('Licence', 3), filiere=self.m.info)
        self.a, self.b = inscrit(self.m.l2, 'Alpha'), inscrit(self.m.l2, 'Beta')
        for i in (self.a, self.b):
            for s in ('S3', 'S4'):
                ResultatSemestre.objects.create(inscription=i, semestre=s, moyenne=12, credits_obtenus=30,
                                                credits_totaux=30, decision='ADMIS', mention='PASSABLE', rang=1)

    def promouvoir(self):
        return self.faculte.post('/api/scolarite/promotion/', {
            'classe': self.m.l2.pk, 'etudiants': [self.a.etudiant.pk, self.b.etudiant.pk]}, format='json')

    def test_erreur_par_etudiant_sans_echec_global(self):
        AnneeAcademique.objects.filter(pk=self.suivante.pk).update(statut='archivee')
        r = self.promouvoir()
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['promus'], 0)
        self.assertEqual(len(r.data['ignores']), 2)
        self.assertIn('archivée', r.data['ignores'][0]['motif'])

    def test_diplome_refuse(self):
        e = self.b.etudiant
        e.statut = 'diplome'
        e.save()
        r = self.promouvoir()
        self.assertEqual(r.data['promus'], 1)
        self.assertIn('BETA', r.data['ignores'][0]['motif'])
        self.assertFalse(Inscription.objects.filter(etudiant=e, annee=self.suivante).exists())

    def test_classe_d_une_annee_archivee(self):
        AnneeAcademique.objects.filter(pk=self.m.annee.pk).update(statut='archivee', en_cours=False)
        self.assertEqual(self.promouvoir().status_code, 400)


class AnneeArchiveeTests(Base):
    def setUp(self):
        super().setUp()
        self.i = inscrit(self.m.l1, 'Alpha')
        AnneeAcademique.objects.filter(pk=self.m.annee.pk).update(statut='archivee', en_cours=False)

    def test_statut_ne_touche_pas_l_inscription_archivee(self):
        r = self.secretariat.post(f'/api/scolarite/etudiants/{self.i.etudiant.pk}/statut/', {'statut': 'abandonne'},
                                  format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.i.refresh_from_db()
        self.assertEqual(self.i.statut, 'active')

    def test_date_d_inscription_figee(self):
        r = self.secretariat.patch(f'/api/scolarite/inscriptions/{self.i.pk}/', {'date_inscription': '2026-10-15'},
                                   format='json')
        self.assertEqual(r.status_code, 400)


class DocumentsTests(Base):
    def test_pdf_en_echec(self):
        from core.documents import ErreurPdf
        i = inscrit(self.m.l1, 'Alpha')
        with mock.patch('scolarite.documents.rendre_pdf', side_effect=ErreurPdf('boum')):
            r = self.secretariat.get(f'/api/scolarite/etudiants/{i.etudiant.pk}/attestation.pdf')
        self.assertEqual(r.status_code, 503)
        self.assertIn('PDF', str(r.data))
        self.assertFalse(DocumentEmis.objects.exists())

    def test_verifier_avec_barre_finale(self):
        r = self.client.get('/verifier/inconnu/')
        self.assertEqual(r.status_code, 404)
        self.assertIn('Document introuvable', r.content.decode())


class BaseUrlTests(TestCase):
    @override_settings(DEBUG=False, BASE_URL='http://localhost:8000')
    def test_avertissement_hors_developpement(self):
        from core.checks import verifier_base_url
        alertes = verifier_base_url(None)
        self.assertEqual([a.id for a in alertes], ['core.W002'])
        self.assertIsInstance(alertes[0], Avertissement)

    @override_settings(DEBUG=False, BASE_URL='https://erp.uccb.cg')
    def test_adresse_publique(self):
        from core.checks import verifier_base_url
        self.assertEqual(verifier_base_url(None), [])
