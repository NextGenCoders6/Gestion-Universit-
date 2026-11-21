from django.apps import AppConfig


class LogistiqueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logistique'
    verbose_name = 'Logistique'

    def ready(self):
        from core.lanceur import enregistrer
        from logistique.lanceur import resume as resume_lanceur
        enregistrer('logistique', resume_lanceur)
