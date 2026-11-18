from django.contrib import admin

from core import models

for modele in (
    models.AnneeAcademique, models.Periode, models.Faculte, models.Departement, models.Portail,
    models.Filiere, models.Parcours, models.Classe, models.UniteEnseignement,
    models.ElementConstitutif, models.ParametresEtablissement,
):
    admin.site.register(modele)


@admin.register(models.Personne)
class PersonneAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'email', 'statut', 'user')
    search_fields = ('nom', 'prenom', 'email')
    list_filter = ('statut', 'genre')


@admin.register(models.Etudiant, models.Enseignant, models.Employe)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('matricule', 'personne')
    search_fields = ('matricule', 'personne__nom', 'personne__prenom')
