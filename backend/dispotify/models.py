from django.db import models

class Artist(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return f'<artist_id={self.id} | {self.name}>'
    
    class Meta:
        ordering = ['-name']

class Album(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    date = models.DateField()
    author = models.ForeignKey(to=Artist, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'<album_id={self.id} | {self.name} | {self.date}>'

    class Meta:
        ordering = ['-author', '-date']

class Song(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=100, null=True)
    album = models.ForeignKey(to=Album, null=True, on_delete=models.CASCADE)
    artist = models.ManyToManyField(to=Artist)
    duration_seconds = models.IntegerField(null=False)
    bitrate = models.IntegerField(null=False)
    extension = models.CharField(max_length=10)

    def __str__(self) -> str:
        return f'<song_id={self.id} | {self.title}>'
    
    class Meta:
        ordering = ['-title']
