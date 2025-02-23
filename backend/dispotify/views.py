from rest_framework import status
from rest_framework import viewsets

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Album, Artist, Song
from .decorators import chord_distribute

from .serializers import (
    AlbumSerializer,
    ArtistSerializer,
    AudioStreamerSerializer,
    SongSerializer,
)


class AudioStreamerView(APIView):
    @chord_distribute(1)
    def get(self, request):
        query_params = {  # type: ignore
            "chunk_index": int(request.GET.get("chunk_index", 0)),
            "chunk_count": int(request.GET.get("chunk_count", 1)),
            "audio_id": request.GET.get("audio_id", ""),
            "client_id": request.GET.get("client_id", ""),
            "include_header": request.GET.get("include_header", "false").lower()
            == "true",
            "include_metadata": request.GET.get("include_metadata", "false").lower()
            == "true",
        }

        serializer = AudioStreamerSerializer(data=query_params)  # type: ignore

        response = serializer.handle_request(query_params)  # type: ignore
        return Response(response, status=status.HTTP_200_OK)


class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    lookup_field = "id"

    permission_classes = [AllowAny]

    @chord_distribute(100, "metadata")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Artist.objects.all()

        name = self.request.query_params.get("name", None)  # type: ignore
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
    lookup_field = "id"

    permission_classes = [AllowAny]

    @chord_distribute(100, "metadata")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Album.objects.all()

        name = self.request.query_params.get("name", None)  # type: ignore
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    lookup_field = "id"
    permission_classes = [AllowAny]

    @chord_distribute(100, "metadata")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @chord_distribute(1, "metadata")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Song.objects.all()

        name = self.request.query_params.get("name", None)  # type: ignore
        if name is not None:
            queryset = queryset.filter(title__icontains=name)

        artist_ids = self.request.query_params.getlist("artist[]", None)  # type: ignore
        if artist_ids:
            queryset = queryset.filter(artist__id__in=artist_ids)

        album_id = self.request.query_params.get("album", None)  # type: ignore
        if album_id:
            queryset = queryset.filter(album__id=album_id)

        return queryset
