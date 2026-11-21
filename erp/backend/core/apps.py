from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Socle'

    def ready(self):
        from core import checks  # noqa: F401  (enregistre les vérifications système)
        from core.lanceur import enregistrer, resume_parametres
        enregistrer('parametres', resume_parametres)
