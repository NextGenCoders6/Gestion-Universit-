from django.apps import AppConfig


class EdtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'edt'
    verbose_name = 'Emploi du temps'

    def ready(self):
        from core.models import referentiel
        from edt.validation import refuser_archivage_avec_seances_futures
        if refuser_archivage_avec_seances_futures not in referentiel.VERIFICATIONS_ARCHIVAGE:
            referentiel.VERIFICATIONS_ARCHIVAGE.append(refuser_archivage_avec_seances_futures)
