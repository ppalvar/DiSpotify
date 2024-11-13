from rest_framework.response import Response
from rest_framework import status
from .serializers import AudioStreamerSerializer
from rest_framework.views import APIView

class AudioStreamerView(APIView):
    def get(self, request):
        # Obtener los parámetros del query string
        query_params = {
            'chunk_index': int(request.GET.get('chunk_index', 0)),
            'chunk_count': int(request.GET.get('chunk_count', 1)),
            'audio_id': request.GET.get('audio_id', ''),
            'client_id': request.GET.get('client_id', ''),
            'include_header': request.GET.get('include_header', 'false').lower() == 'true',
            'include_metadata': request.GET.get('include_metadata', 'false').lower() == 'true'
        }

        serializer = AudioStreamerSerializer(data=query_params)

        response = serializer.handle_request(query_params)
        return Response(response, status=status.HTTP_200_OK)
