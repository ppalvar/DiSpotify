import os
import struct, base64
from .models import *
from rest_framework import serializers
from django.core.files.base import ContentFile

HEADER_SIZE = 44
CHUNK_SIZE = 1 << 15 #32kB

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
            'name': {'required': True, 'min_length': 1}
        }

class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ['id', 'name', 'date', 'author']
        
        extra_kwargs = {
            'name': {'required': True, 'min_length': 1},
            'date': {'required': True},
            'author': {'required': True},
        }

class SongSerializer(serializers.ModelSerializer):
    file_base64 = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Song
        fields = ['id', 'title', 'album', 'artist', 'file_base64']
        extra_kwargs = {
            'title': {'required': True, 'min_length': 1},
            'artist': {'required': True},
        }

    def create(self, validated_data):
        file_base64 = validated_data.pop('file_base64', None)
        song = super().create(validated_data)

        data = ContentFile(base64.b64decode(file_base64), name=f'{song.id}.wav')

        # Guardar el archivo en disco
        file_path = os.path.join('media', 'songs', data.name)
        with open(file_path, 'wb') as f:
            f.write(data.read())

        return song