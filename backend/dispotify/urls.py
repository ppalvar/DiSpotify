from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter

from dispotify.views import *

artists_router = DefaultRouter()
artists_router.register(r'', ArtistViewSet)

albums_router = DefaultRouter()
albums_router.register('', AlbumViewSet)

songs_router = DefaultRouter()
songs_router.register('', SongViewSet)

urlpatterns = [
    path('streamer/', AudioStreamerView.as_view(), name='streaming_endpoint'),
    path('artists/', include(artists_router.urls)),
    path('albums/', include(albums_router.urls)),
    path('songs/', include(songs_router.urls)),
]