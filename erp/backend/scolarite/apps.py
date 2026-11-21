from django.apps import AppConfig


class ScolariteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scolarite'
    verbose_name = 'Scolarité'

    def ready(self):
        from core.lanceur import enregistrer
        from scolarite.lanceur import resume
        enregistrer('scolarite', resume)
