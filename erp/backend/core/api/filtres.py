from rest_framework.exceptions import ValidationError


def entier(request, nom):
    """Paramètre de requête entier, ou None s'il est absent ; 400 s'il est mal formé."""
    valeur = request.query_params.get(nom)
    if valeur in (None, ''):
        return None
    try:
        return int(valeur)
    except (TypeError, ValueError):
        raise ValidationError({nom: 'Valeur invalide : un identifiant numérique est attendu.'})
