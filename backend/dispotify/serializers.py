import io
import base64

from mutagen.mp3 import MP3
from dataclasses import dataclass
from rest_framework import serializers
from asgiref.sync import async_to_sync

from .models import Album, Artist, Song
from chord.chord import ChordNode, hash_string


CHUNK_SIZE = 1 << 15  # 32kB


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
        chunk_index: int = data["chunk_index"]
        chunk_count: int = data["chunk_count"]
        audio_id: str = data["audio_id"]
        include_metadata: bool = data["include_metadata"]

        filename = self.get_file_name(audio_id)

        with open(filename, "rb") as wav_file:
            wav_file.seek(0, 2)
            file_size = wav_file.tell()
            audio_data_size = file_size
            total_chunks = (audio_data_size + CHUNK_SIZE - 1) // CHUNK_SIZE

            response = {
                "chunk_index": chunk_index,
                "chunk_count": min(chunk_count, total_chunks - chunk_index),
            }

            if include_metadata:
                song = Song.objects.get(id=audio_id)

                channels = 2  # TODO
                bitrate = song.bitrate
                duration = song.duration_seconds

                response["metadata"] = {
                    "channels": channels,
                    "duration": duration,
                    "total_chunks": total_chunks,
                    "chunk_size": CHUNK_SIZE,
                    "bitrate": bitrate,
                    "file_size": file_size,
                }

            chunks = []
            for i in range(chunk_count):
                current_chunk_index = chunk_index + i
                if current_chunk_index >= total_chunks:
                    break

                offset = current_chunk_index * CHUNK_SIZE
                wav_file.seek(offset)

                chunk_data = wav_file.read(min(CHUNK_SIZE, file_size - offset))
                chunk_data = base64.b64encode(chunk_data)

                chunks.append(chunk_data)

            response["chunks"] = chunks

            return response

    def get_file_name(self, audio_id: str):
        return f"/app/data/audios/{audio_id}"


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ["id", "name"]

        extra_kwargs = {
            "name": {"required": True, "min_length": 1},
            "id": {"required": True},
        }

    def create(self, validated_data):
        print(">>>", validated_data)
        if "id" not in validated_data:
            validated_data["id"] = hash_string(validated_data["name"])
            print("Viva pepe!")
        return super().create(validated_data)


class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ["id", "name", "date", "author"]

        extra_kwargs = {
            "name": {"required": True, "min_length": 1},
            "date": {"required": True},
            "author": {"required": True},
            "id": {"required": False},
        }

    def create(self, validated_data):
        if "id" not in validated_data:
            key = f"{validated_data['name']}:{validated_data['date']}:{validated_data['author']}"
            validated_data["id"] = hash_string(key)
        return super().create(validated_data)


class SongSerializer(serializers.ModelSerializer):
    file_base64 = serializers.CharField(write_only=True, required=False)
    album_name = serializers.SerializerMethodField()
    artist_names = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = [
            "id",
            "title",
            "album",
            "artist",
            "album_name",
            "artist_names",
            "file_base64",
            "duration_seconds",
            "bitrate",
            "extension",
        ]
        extra_kwargs = {
            "title": {"required": True, "min_length": 1},
            "artist": {"required": True},
            "id": {"required": False},
            "duration_seconds": {"required": False},
            "bitrate": {"required": False},
            "extension": {"required": False},
        }

    def get_audio_info(self, audio_bytes: bytes):
        # TODO: test this
        audio_file = io.BytesIO(audio_bytes)
        audio = MP3(audio_file)

        duration_seconds = audio.info.length

        bitrate = audio.info.bitrate  # type: ignore

        channels = audio.info.channels  # type: ignore

        frame_rate = audio.info.sample_rate  # type: ignore

        sample_width = None

        extension = "mp3"

        metadata = AudioMetadata(
            duration_seconds,
            bitrate,
            extension,
            channels,
            frame_rate,
            sample_width,  # type: ignore
        )

        return metadata

    def get_album_name(self, obj):
        return obj.album.name if obj.album else None

    def get_artist_names(self, obj):
        return [artist.name for artist in obj.artist.all()]

    def create(self, validated_data):
        if "id" not in validated_data:
            key = f"{validated_data['title']}:{validated_data['album']}"
            validated_data["id"] = hash_string(key)

        id = validated_data["id"]
        file_base64 = validated_data.pop("file_base64", None)
        data = base64.b64decode(file_base64)
        metadata = self.get_audio_info(data)

        validated_data["duration_seconds"] = metadata.duration_seconds
        validated_data["bitrate"] = metadata.bitrate
        validated_data["extension"] = metadata.extension

        song = super().create(validated_data)

        chord_instance = ChordNode.get_instance()

        assert chord_instance

        song_node_id = int(id, 16) % (1 << chord_instance.id_bitlen)
        succ = async_to_sync(chord_instance.find_successor)(song_node_id)

        if chord_instance.node_id == succ.node_id:
            file_path = f"/app/data/audios/{id}"
            with open(file_path, "wb") as f:
                f.write(data)

        return song
