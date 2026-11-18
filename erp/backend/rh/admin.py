from django.contrib import admin

from rh.models import Contrat


@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = ('personne', 'type', 'date_debut', 'date_fin')
    list_filter = ('type',)
    search_fields = ('personne__nom', 'personne__prenom')
