from django.contrib import admin

from logistique.models import AffectationTransport, Bus, Trajet

admin.site.register(Bus)
admin.site.register(Trajet)
admin.site.register(AffectationTransport)
