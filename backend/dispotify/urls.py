from django.contrib import admin
from django.urls import path
from dispotify.views import AudioStreamerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('streamer/', AudioStreamerView.as_view(), name='streaming_endpoint'),
]