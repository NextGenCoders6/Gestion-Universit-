from datetime import date, time

from logistique.models import Bus, Trajet
from rh.tests.fabriques import employe, permanent


def bus(numero='01', statut='actif', capacite=50):
    return Bus.objects.create(numero=numero, plaque=f'CG-{numero}-AA', capacite=capacite, statut=statut)


def trajet(nom='Campus — Centre-ville'):
    return Trajet.objects.create(nom=nom, depart='Campus de Liambou', destination='Pointe-Noire centre',
                                 heure_depart=time(6, 30), heure_arrivee=time(7, 30))


def chauffeur(nom='Nzaba', debut=date(2025, 9, 1), fin=None):
    e = employe(nom, 'chauffeur')
    permanent(e.personne, debut=debut, fin=fin, salaire='180000')
    return e
