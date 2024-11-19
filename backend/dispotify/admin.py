from django.contrib import admin
from .models import Artist, Album, Song

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name', 'id')
    ordering = ('-name',)

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    # Cambiado 'artist' por 'author' ya que ese es el nombre del campo en el modelo
    list_display = ('id', 'name', 'date', 'author')
    list_filter = ('date', 'author')
    search_fields = ('name', 'id', 'author__name')
    raw_id_fields = ('author',)  # Cambiado de 'artist' a 'author'
    date_hierarchy = 'date'
    ordering = ('-date',)

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'album')
    search_fields = ('title', 'id', 'album__name')
    filter_horizontal = ('artist',)  # Cambiado de 'album' a 'artist' ya que este es el M2M
    list_filter = ('album', 'artist')