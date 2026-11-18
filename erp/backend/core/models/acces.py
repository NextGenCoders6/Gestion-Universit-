from django.conf import settings
from django.db import models

from .referentiel import Faculte


class RattachementFaculte(models.Model):
    """Limite un utilisateur de la Scolarité à une faculté. Sans rattachement : toutes."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rattachement_faculte')
    # PROTECT : supprimer la faculté élargirait l'accès de l'utilisateur à toutes les facultés.
    faculte = models.ForeignKey(Faculte, on_delete=models.PROTECT, related_name='utilisateurs_rattaches')

    class Meta:
        verbose_name = 'Rattachement à une faculté'

    def __str__(self):
        return f'{self.user} → {self.faculte.code}'
