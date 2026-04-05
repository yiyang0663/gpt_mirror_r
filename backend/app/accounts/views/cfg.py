from rest_framework.response import Response
from rest_framework.views import APIView

from app.settings import ALLOW_FREE_LOGIN, SHOW_GITHUB


class VersionConfig(APIView):

    def get(self, request):
        return Response({'show_github': SHOW_GITHUB, 'allow_free_login': ALLOW_FREE_LOGIN})
