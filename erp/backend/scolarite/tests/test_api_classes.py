from scolarite.tests.api import Base


class ClassesTests(Base):
    def test_classes_du_perimetre_avec_programme(self):
        r = self.faculte_fst.get(f'/api/scolarite/classes/?annee={self.m.annee.pk}')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([c['libelle'] for c in r.data], ['L1 MIP — 2026-2027', 'L2 INFO — 2026-2027'])
        l1 = r.data[0]
        self.assertEqual((l1['niveau'], l1['semestres']), ('L1', ['S1', 'S2']))
        self.assertEqual([(e['code'], e['semestre']) for e in l1['ecs']],
                         [('ALGO', 'S1'), ('PROG', 'S1'), ('ANALYSE', 'S1'), ('RESEAU', 'S2')])
        self.assertEqual(len(self.faculte.get('/api/scolarite/classes/').data), 3)
        self.assertEqual(self.autre.get('/api/scolarite/classes/').status_code, 403)
