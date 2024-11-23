from rest_framework import status
from rest_framework import viewsets

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .serializers import *
from rest_framework.views import APIView

from .models import *

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

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    lookup_field = 'id'

    permission_classes = [AllowAny]  # autenticación
    
    def get_queryset(self):
        queryset = Artist.objects.all()
        # Ejemplo de filtrado por nombre
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    lookup_field = 'id'

    permission_classes = [AllowAny]  # autenticación
    
    def get_queryset(self):
        queryset = Album.objects.all()
        # Ejemplo de filtrado por nombre
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset

class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny]  # autenticación

    def get_queryset(self):
        queryset = Song.objects.all()

        # Filtrar por nombre de la canción
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(title__icontains=name)

        # Filtrar por nombre del artista
        artist_ids = self.request.query_params.getlist('artist[]', None)
        if artist_ids:
            queryset = queryset.filter(artist__id__in=artist_ids)

        # Filtrar por nombre del álbum
        album_id = self.request.query_params.get('album', None)
        if album_id:
            queryset = queryset.filter(album__id=album_id)

        return queryset