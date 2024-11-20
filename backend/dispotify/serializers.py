import os, io
import uuid
import time
from pydub import AudioSegment
import struct, base64
from .models import *
from dataclasses import dataclass
from rest_framework import serializers
from django.core.files.base import ContentFile

HEADER_SIZE = 44
CHUNK_SIZE = 1 << 15 #32kB

@dataclass
class AudioMetadata:
    duration_seconds: int
    bitrate: int
    extension: str
    channels: int
    frame_rate: int
    sample_width: int 

class AudioStreamerSerializer(serializers.Serializer):
    chunk_index = serializers.IntegerField()
    chunk_count = serializers.IntegerField()
    audio_id = serializers.CharField(max_length=50)
    client_id = serializers.CharField(max_length=50)
    include_header = serializers.BooleanField(default=False)
    include_metadata = serializers.BooleanField(default=False)
    
    def handle_request(self, data):
        chunk_index : int = data['chunk_index']
        chunk_count : int = data['chunk_count']
        audio_id : str = data['audio_id']
        include_header : bool = data['include_header']
        include_metadata : bool = data['include_metadata']

        filename = self.get_file_name(audio_id)
    
    
        with open(filename, 'rb') as wav_file:
            header = wav_file.read(HEADER_SIZE)

            wav_file.seek(0, 2)
            file_size = wav_file.tell()
            audio_data_size = file_size - HEADER_SIZE
            total_chunks = (audio_data_size + CHUNK_SIZE - 1) // CHUNK_SIZE
            
            response = {
                'chunk_index': chunk_index,
                'chunk_count': min(chunk_count, total_chunks - chunk_index  ),
            }

            if include_header:
                response['header'] = base64.b64encode(header)
            
            if include_metadata:
                channels = struct.unpack_from('<H', header, 22)[0]
                sample_rate = struct.unpack_from('<I', header, 24)[0]
                bits_per_sample = struct.unpack_from('<H', header, 34)[0]
                duration = audio_data_size / (bits_per_sample // 8) / sample_rate / channels

                response['metadata'] = {
                    'channels' : channels,
                    'sample_rate' : sample_rate,
                    'bits_per_sample' : bits_per_sample,
                    'duration' : duration,
                    'total_chunks': total_chunks,
                    'chunk_size': CHUNK_SIZE
                }
            
            chunks = []
            for i in range(chunk_count):
                current_chunk_index = chunk_index + i
                if current_chunk_index >= total_chunks:
                    break
                
                offset = HEADER_SIZE + (current_chunk_index * CHUNK_SIZE)
                wav_file.seek(offset)
                
                chunk_data = wav_file.read(CHUNK_SIZE)
                chunk_data = base64.b64encode(chunk_data)

                chunks.append(chunk_data)
            
            response['chunks'] = chunks

            return response


    def get_file_name(self, audio_id: str):
        return f'../audios/{audio_id}.wav'


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['id', 'name']
        
        extra_kwargs = {
            'name': {'required': True, 'min_length': 1},
            'id': {'required': False}
        }
    
    def create(self, validated_data):
        if 'id' not in validated_data:
            validated_data['id'] = str(uuid.uuid4())  # Asignar un UUID aleatorio
        return super().create(validated_data)

class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ['id', 'name', 'date', 'author']
        
        extra_kwargs = {
            'name': {'required': True, 'min_length': 1},
            'date': {'required': True},
            'author': {'required': True},
            'id': {'required': False}
            }
    
    def create(self, validated_data):
        if 'id' not in validated_data:
            validated_data['id'] = str(uuid.uuid4())  # Asignar un UUID aleatorio
        return super().create(validated_data)

class SongSerializer(serializers.ModelSerializer):
    file_base64 = serializers.CharField(write_only=True, required=False)
    album_name = serializers.SerializerMethodField()
    artist_names = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = ['id', 'title', 'album', 'artist', 'album_name', 'artist_names', 'file_base64', 'duration_seconds', 'bitrate', 'extension']
        extra_kwargs = {
            'title': {'required': True, 'min_length': 1},
            'artist': {'required': True},
            'id': {'required': False},
            'duration_seconds': {'required': False},
            'bitrate': {'required': False},
            'extension': {'required': False},
        }
    
    def get_audio_info(self, audio_bytes: bytes):
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

        # Obtener la duración en segundos
        duration_seconds = len(audio) / 1000.0

        # Obtener el bitrate
        bitrate = audio.frame_rate * audio.frame_width * audio.channels

        extension = 'unknown'  # Cambia esto si conoces el formato

        # Otros datos interesantes
        channels = audio.channels
        frame_rate = audio.frame_rate
        sample_width = audio.sample_width

        metadata = AudioMetadata(duration_seconds, bitrate, extension, channels, frame_rate, sample_width)

        return metadata

    def get_album_name(self, obj):
        return obj.album.name if obj.album else None

    def get_artist_names(self, obj):
        return [artist.name for artist in obj.artist.all()]

    def create(self, validated_data):
        if 'id' not in validated_data:
            validated_data['id'] = str(uuid.uuid4())

        id = validated_data['id']
        file_base64 = validated_data.pop('file_base64', None)
        data = base64.b64decode(file_base64)
        metadata = self.get_audio_info(data)
        
        validated_data['duration_seconds'] = metadata.duration_seconds
        validated_data['bitrate'] = metadata.bitrate
        validated_data['extension'] = metadata.extension

        song = super().create(validated_data)

        # Guardar el archivo en disco
        file_path = f'../audios/{id}'
        with open(file_path, 'wb') as f:
            f.write(data)

        return song
    