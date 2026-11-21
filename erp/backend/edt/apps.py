from django.apps import AppConfig


class EdtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'edt'
    verbose_name = 'Emploi du temps'

    def ready(self):
        from core.lanceur import enregistrer
        from edt.lanceur import resume as resume_lanceur
        enregistrer('edt', resume_lanceur)

        from core.models import referentiel
        from edt.validation import refuser_archivage_avec_seances_futures
        if refuser_archivage_avec_seances_futures not in referentiel.VERIFICATIONS_ARCHIVAGE:
            referentiel.VERIFICATIONS_ARCHIVAGE.append(refuser_archivage_avec_seances_futures)

        from core import droits
        from edt.droits import niveaux_edt, role_referent
        if role_referent not in droits.ROLES_CONTEXTUELS:
            droits.ROLES_CONTEXTUELS.append(role_referent)
        if niveaux_edt not in droits.NIVEAUX_CONTEXTUELS:
            droits.NIVEAUX_CONTEXTUELS.append(niveaux_edt)
