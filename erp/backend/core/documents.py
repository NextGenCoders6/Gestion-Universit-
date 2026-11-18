"""Documents officiels : PDF (xhtml2pdf), QR codes, images intégrées.

xhtml2pdf ne sait pas résoudre seul les URL /static/ et /media/ : `link_callback`
les traduit en chemins disque (repris de l'ancienne scolarité, pdf_utils.py).
Le logo et les QR codes sont intégrés en data URI, sans dépendre des fichiers
statiques collectés.
"""
import base64
import io
import os
from functools import lru_cache
from pathlib import Path

import qrcode
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa

LOGO = Path(__file__).resolve().parent / 'static' / 'core' / 'logo_uccb.jpg'


class ErreurPdf(RuntimeError):
    pass


def link_callback(uri, rel):
    """Convertit une URI /static/ ou /media/ en chemin disque pour xhtml2pdf."""
    if uri.startswith(settings.STATIC_URL):
        chemin = finders.find(uri[len(settings.STATIC_URL):])
    elif settings.MEDIA_URL and uri.startswith(settings.MEDIA_URL):
        chemin = os.path.join(settings.MEDIA_ROOT, uri[len(settings.MEDIA_URL):])
    else:
        return uri
    return chemin or uri


def data_uri(contenu, type_mime):
    return f'data:{type_mime};base64,{base64.b64encode(contenu).decode()}'


@lru_cache(maxsize=1)
def logo_data_uri():
    return data_uri(LOGO.read_bytes(), 'image/jpeg') if LOGO.exists() else ''


def qr_data_uri(texte):
    """QR code PNG (data URI) encodant `texte`."""
    image = qrcode.make(texte, box_size=6, border=2)
    flux = io.BytesIO()
    image.save(flux, format='PNG')
    return data_uri(flux.getvalue(), 'image/png')


def rendre_pdf(gabarit, contexte):
    """Rend le gabarit Django en PDF (bytes) ; ErreurPdf si xhtml2pdf échoue."""
    html = render_to_string(gabarit, {'logo': logo_data_uri(), **contexte})
    flux = io.BytesIO()
    resultat = pisa.CreatePDF(html, dest=flux, encoding='utf-8', link_callback=link_callback)
    if resultat.err:
        raise ErreurPdf(f'Génération du PDF impossible ({resultat.err} erreur(s)).')
    return flux.getvalue()


def reponse_pdf(contenu, nom_fichier):
    reponse = HttpResponse(contenu, content_type='application/pdf')
    reponse['Content-Disposition'] = f'inline; filename="{nom_fichier}"'
    return reponse
