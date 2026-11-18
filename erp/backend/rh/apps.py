from django.apps import AppConfig


class RhConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rh'
    verbose_name = 'Ressources humaines'

    def ready(self):
        from edt import models as edt_models
        from rh.vacations import refuser_modification_si_confirmee
        if refuser_modification_si_confirmee not in edt_models.VERIFICATIONS_AFFECTATION:
            edt_models.VERIFICATIONS_AFFECTATION.append(refuser_modification_si_confirmee)
