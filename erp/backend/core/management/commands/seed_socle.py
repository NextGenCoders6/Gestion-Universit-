"""Jeu de données de démonstration du socle (idempotent).

Les phases suivantes ajoutent leur propre commande seed_<module> ; seed_demo
les enchaînera en phase 6.
"""
from datetime import date

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.droits import definir_droits, tous_les_groupes
from core.models import (
    AnneeAcademique, Classe, Departement, ElementConstitutif, Employe, Enseignant, Etudiant, Faculte, Filiere,
    JournalAudit, Parcours, Periode, Personne, Portail, UniteEnseignement,
)
from core.models.acces import RattachementFaculte

MOT_DE_PASSE_DEMO = 'Uccb!2026demo'
MODULES_METIER = ('edt', 'scolarite', 'rh', 'finance', 'logistique')

FACULTES = {
    'FST': {
        'nom': 'Faculté des Sciences et Techniques',
        'departements': {
            'Informatique': [('INFO', 'Informatique', 'MIP'), ('MATH', 'Mathématiques', 'MIP')],
            'Biologie': [('BIO', 'Biologie', 'BCG'), ('CHIM', 'Chimie', 'BCG')],
        },
        'portails': [('MIP', 'Mathématiques-Informatique-Physique'), ('BCG', 'Biologie-Chimie-Géologie')],
    },
    'FSE': {
        'nom': 'Faculté des Sciences Économiques',
        'departements': {
            'Économie': [('ECO', 'Économie', 'ECO'), ('FIN', 'Finance', 'ECO')],
            'Gestion': [('GEST', 'Gestion', 'ECO'), ('MKT', 'Marketing', 'ECO')],
        },
        'portails': [('ECO', 'Économie-Gestion')],
    },
}

UES_L1_MIP = [
    ('UE-MIP-S1-1', 'Fondamentaux de l’informatique', 'S1',
     [('ALGO1', 'Algorithmique 1', 4, 'Informatique'), ('PROG1', 'Programmation 1', 3, 'Informatique'),
      ('ARCHI1', 'Architecture des ordinateurs', 2, 'Informatique')]),
    ('UE-MIP-S2-1', 'Mathématiques 1', 'S2',
     [('ANA1', 'Analyse 1', 4, 'Informatique'), ('ALG1', 'Algèbre 1', 4, 'Informatique'),
      ('PROBA1', 'Probabilités', 2, 'Informatique')]),
]


class Command(BaseCommand):
    help = 'Crée le jeu de données de démonstration du socle (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Vide les données du socle avant (DEBUG seulement).')

    def handle(self, *args, **options):
        # Comptes de démo au mot de passe publié : jamais hors développement.
        if not settings.DEBUG:
            raise CommandError('seed_socle est refusé quand DEBUG=False (comptes de démonstration).')
        if options['reset']:
            self._vider()
        with transaction.atomic():
            annee = self._calendrier()
            enseignants = self._organisation(annee)
            self._comptes(enseignants)
        self.stdout.write(self.style.SUCCESS(f'Socle prêt. Mot de passe des comptes de démo : {MOT_DE_PASSE_DEMO}'))

    def _vider(self):
        # Les données des modules (EDT, Scolarité…) protègent le référentiel : on les vide d'abord,
        # module par module dans l'ordre inverse d'installation, modèles du dernier au premier.
        for app in reversed(list(apps.get_app_configs())):
            if app.name in MODULES_METIER:
                for modele in reversed(list(app.get_models())):
                    modele.objects.all().delete()
        for modele in (JournalAudit, RattachementFaculte, ElementConstitutif, UniteEnseignement, Classe,
                       Etudiant, Employe, Enseignant):
            modele.objects.all().delete()
        Departement.objects.update(chef=None)
        Filiere.objects.update(responsable=None)
        Personne.objects.all().delete()
        for modele in (Filiere, Portail, Departement, Faculte, Periode, AnneeAcademique, Parcours):
            modele.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _calendrier(self):
        annee, _ = AnneeAcademique.objects.get_or_create(
            libelle='2026-2027', defaults={'date_debut': date(2026, 10, 1), 'date_fin': date(2027, 7, 31)}
        )
        if not annee.en_cours:
            annee.en_cours = True
            annee.save()
        Periode.objects.get_or_create(annee=annee, numero=1,
                                      defaults={'date_debut': date(2026, 10, 1), 'date_fin': date(2027, 2, 15)})
        Periode.objects.get_or_create(annee=annee, numero=2,
                                      defaults={'date_debut': date(2027, 2, 16), 'date_fin': date(2027, 7, 31)})
        for type_parcours, niveaux in (('Licence', 3), ('Master', 2)):
            for niveau in range(1, niveaux + 1):
                Parcours.objects.get_or_create(type_parcours=type_parcours, niveau=niveau)
        return annee

    def _organisation(self, annee):
        l1 = Parcours.objects.get(type_parcours='Licence', niveau=1)
        superieurs = [Parcours.objects.get(type_parcours='Licence', niveau=n) for n in (2, 3)]
        enseignants = {}
        for code_fac, conf in FACULTES.items():
            fac, _ = Faculte.objects.get_or_create(code=code_fac, defaults={'nom': conf['nom']})
            portails = {}
            for code, nom in conf['portails']:
                portails[code], _ = Portail.objects.get_or_create(faculte=fac, code=code, defaults={'nom': nom})
                Classe.objects.get_or_create(annee=annee, parcours=l1, portail=portails[code])
            for libelle, filieres in conf['departements'].items():
                dep, _ = Departement.objects.get_or_create(faculte=fac, libelle=libelle)
                enseignants[libelle] = self._enseignant(dep)
                for code, nom, code_portail in filieres:
                    fil, _ = Filiere.objects.get_or_create(
                        departement=dep, code=code, defaults={'nom': nom, 'portail': portails[code_portail]}
                    )
                    for parcours in superieurs:
                        Classe.objects.get_or_create(annee=annee, parcours=parcours, filiere=fil)
        mip = Portail.objects.get(code='MIP')
        info = Departement.objects.get(libelle='Informatique')
        for code_ue, libelle, semestre, ecs in UES_L1_MIP:
            ue, _ = UniteEnseignement.objects.get_or_create(
                code=code_ue, defaults={'libelle': libelle, 'semestre': semestre, 'portail': mip}
            )
            for code, lib, credits, _dep in ecs:
                ElementConstitutif.objects.get_or_create(
                    code=code, defaults={'ue': ue, 'libelle': lib, 'credits': credits, 'departement': info,
                                         'heures_cm': credits * 6, 'heures_td': credits * 4, 'heures_tp': credits * 2}
                )
        return enseignants

    def _enseignant(self, dep):
        noms = {'Informatique': ('Ngoma', 'Paul', 'M'), 'Biologie': ('Okemba', 'Sylvie', 'F'),
                'Économie': ('Mavoungou', 'Jean', 'M'), 'Gestion': ('Loemba', 'Clarisse', 'F')}
        nom, prenom, genre = noms[dep.libelle]
        personne, _ = Personne.objects.get_or_create(nom=nom, prenom=prenom, defaults={'genre': genre})
        ens, _ = Enseignant.objects.get_or_create(personne=personne, defaults={'departement': dep, 'grade': 'Docteur'})
        return ens

    def _compte(self, username, groupes=(), personne=None, superuser=False):
        user = User.objects.filter(username=username).first()
        if user is None:
            if superuser:
                user = User.objects.create_superuser(username, f'{username}@uccb.cg', MOT_DE_PASSE_DEMO)
            else:
                user = User.objects.create_user(username, password=MOT_DE_PASSE_DEMO)
        definir_droits(user, list(groupes))
        if personne is not None and personne.user_id != user.pk:
            personne.user = user
            personne.save()
        return user

    def _comptes(self, enseignants):
        self._compte('admin', superuser=True)
        self._compte('parametres', ['parametres_responsable'])
        for groupe in tous_les_groupes():
            if groupe != 'parametres_responsable':
                self._compte(groupe, [groupe])
        fst = Faculte.objects.get(code='FST')
        RattachementFaculte.objects.update_or_create(
            user=User.objects.get(username='scolarite_faculte'), defaults={'faculte': fst}
        )
        chef = enseignants['Informatique']
        dep = chef.departement
        if dep.chef_id != chef.pk:
            dep.chef = chef
            dep.save()
        self._compte('chef', personne=chef.personne)
        gardien, _ = Personne.objects.get_or_create(nom='Bouanga', prenom='Marc', defaults={'genre': 'M'})
        Employe.objects.get_or_create(personne=gardien, defaults={'fonction': 'gardien', 'lieu_travail': 'Campus'})
        self._compte('employe', personne=gardien)
