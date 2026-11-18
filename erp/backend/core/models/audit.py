from django.conf import settings
from django.db import models


class JournalAudit(models.Model):
    """Trace des actions sensibles de tous les modules (repris d'AuditLog)."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_audit'
    )
    module = models.CharField(max_length=20)
    action = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Entrée du journal d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ['-date', '-pk']

    def __str__(self):
        return f'{self.date:%Y-%m-%d %H:%M} {self.module} {self.action}'
