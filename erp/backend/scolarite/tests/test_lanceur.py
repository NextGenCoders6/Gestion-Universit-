"""Résumé Scolarité du launchpad : inscrits actifs de l'année, dans le périmètre de la faculté."""
from django.core.cache import cache

from scolarite.tests.api import Base, client, compte
from scolarite.tests.fabriques import inscrit

URL = '/api/core/lanceur/'


def tuile(c, module='scolarite'):
    return next(e for e in c.get(URL).data if e['module'] == module)


class ResumeScolariteTests(Base):
    def setUp(self):
        super().setUp()
        cache.clear()
        inscrit(self.m.l1, 'Moukala', 'Divine')
        inscrit(self.m.l1, 'Ngoma', 'Paul')
        partie = inscrit(self.m.l2, 'Bouanga', 'Léa')
        partie.statut = 'abandonnee'
        partie.save()

    def test_compte_les_inscrits_actifs_de_l_annee(self):
        self.assertEqual(tuile(self.secretariat), {
            'module': 'scolarite', 'valeur': 2, 'unite': '', 'libelle': 'étudiants inscrits',
            'detail': 'Année 2026-2027', 'ton': 'normal'})

    def test_perimetre_faculte(self):
        rattache = client(compte('fse', ['scolarite_secretariat'], faculte=self.fse))
        self.assertEqual(tuile(rattache)['valeur'], 0)

    def test_sans_annee_courante(self):
        self.m.annee.en_cours = False
        self.m.annee.save()
        e = tuile(self.secretariat)
        self.assertIsNone(e['valeur'])
        self.assertEqual(e['detail'], 'Aucune année en cours')
