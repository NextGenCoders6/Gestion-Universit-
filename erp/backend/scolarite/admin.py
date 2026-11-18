from django.contrib import admin

from scolarite.models import Inscription, Note, ResultatSemestre


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'classe', 'type', 'statut', 'date_inscription')
    list_filter = ('annee', 'statut', 'type')
    search_fields = ('etudiant__matricule', 'etudiant__personne__nom')


admin.site.register(Note)
admin.site.register(ResultatSemestre)
