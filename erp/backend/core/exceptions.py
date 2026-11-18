"""Gestionnaire d'exceptions DRF global, repris de uccb_backend/EDT_app/exception_handlers.py.

- ValidationError Django (full_clean dans save()) → 400 par champ, jamais 500.
- Suppression d'un élément encore utilisé (ProtectedError) → 400 expliqué.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    if isinstance(exc, (ProtectedError, RestrictedError)):
        objets = exc.protected_objects if isinstance(exc, ProtectedError) else exc.restricted_objects
        types = sorted({str(o._meta.verbose_name_plural) for o in list(objets)[:50]})
        return Response(
            {
                'detail': (
                    'Suppression impossible : cet élément est encore utilisé par '
                    + ', '.join(types)
                    + ". Supprimez ou déplacez d'abord ces éléments."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, 'error_dict') else {'non_field_errors': exc.messages}
        exc = DRFValidationError(detail)
    return drf_exception_handler(exc, context)
