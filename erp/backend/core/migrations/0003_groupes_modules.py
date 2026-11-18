"""Crée les groupes de droits des modules (core.droits.MODULES, figé ici)."""
from django.db import migrations

GROUPES = [
    'scolarite_secretariat', 'scolarite_faculte',
    'edt_utilisateur', 'edt_responsable',
    'rh_utilisateur', 'rh_responsable',
    'finance_utilisateur', 'finance_responsable',
    'logistique_utilisateur', 'logistique_responsable',
    'parametres_responsable',
]


def creer(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for nom in GROUPES:
        Group.objects.get_or_create(name=nom)


def supprimer(apps, schema_editor):
    apps.get_model('auth', 'Group').objects.filter(name__in=GROUPES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0002_rattachement_faculte'),
    ]

    operations = [migrations.RunPython(creer, supprimer)]
