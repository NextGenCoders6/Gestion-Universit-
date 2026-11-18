from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
    verbose_name = 'Finance'

    def ready(self):
        from finance.frais import creer_dossier
        from scolarite import inscriptions
        if creer_dossier not in inscriptions.APRES_INSCRIPTION:
            inscriptions.APRES_INSCRIPTION.append(creer_dossier)
