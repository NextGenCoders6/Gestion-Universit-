"""GET /api/core/lanceur/ : les chiffres des tuiles du launchpad (voir core/lanceur.py)."""
from rest_framework.response import Response
from rest_framework.views import APIView

from core.lanceur import resumes_pour


class LanceurView(APIView):
    def get(self, request):
        return Response(resumes_pour(request))
