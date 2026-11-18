from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import ParametresEtablissement
from core.permissions import LectureAuthentifieeEcritureParametres


class EtablissementSerializer(serializers.ModelSerializer):
    titre_secretaire = serializers.CharField(read_only=True)

    class Meta:
        model = ParametresEtablissement
        fields = ['nom_secretaire', 'genre_secretaire', 'ville_signature', 'titre_secretaire']


class EtablissementView(APIView):
    permission_classes = [LectureAuthentifieeEcritureParametres]

    def get(self, request):
        return Response(EtablissementSerializer(ParametresEtablissement.get()).data)

    def put(self, request):
        serializer = EtablissementSerializer(ParametresEtablissement.get(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
