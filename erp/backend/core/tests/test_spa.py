import tempfile
from pathlib import Path

from django.test import TestCase, override_settings


class SpaTests(TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        Path(self.dossier.name, 'index.html').write_text('<div id="root">ERP</div>', encoding='utf-8')

    def tearDown(self):
        self.dossier.cleanup()

    def test_route_profonde_sert_index(self):
        with override_settings(FRONTEND_DIST=Path(self.dossier.name)):
            r = self.client.get('/rh/enseignants')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="root"')

    def test_racine_sert_index(self):
        with override_settings(FRONTEND_DIST=Path(self.dossier.name)):
            self.assertEqual(self.client.get('/').status_code, 200)

    def test_api_inconnue_404_pas_index(self):
        with override_settings(FRONTEND_DIST=Path(self.dossier.name)):
            r = self.client.get('/api/inexistant/')
        self.assertEqual(r.status_code, 404)
        self.assertNotContains(r, 'id="root"', status_code=404)

    def test_build_absent_503(self):
        with override_settings(FRONTEND_DIST=Path(self.dossier.name) / 'absent'):
            r = self.client.get('/parametres')
        self.assertEqual(r.status_code, 503)
        self.assertContains(r, 'npm run build', status_code=503)
