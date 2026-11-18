"""Passe finale (phase 6) : unicité des affectations en base."""
from django.db import IntegrityError, transaction
from django.test import TestCase

from edt.models import AffectationEC
from edt.tests.fabriques import Monde


class UniciteAffectationTests(TestCase):
    def test_doublon_refuse_par_la_base(self):
        m = Monde()
        commun = dict(ec=m.algo, classe=m.l1, enseignant=m.ens, heures_prevues=4, type_seance='CM')
        AffectationEC.objects.bulk_create([AffectationEC(**commun)])
        with self.assertRaises(IntegrityError), transaction.atomic():
            AffectationEC.objects.bulk_create([AffectationEC(**commun)])
