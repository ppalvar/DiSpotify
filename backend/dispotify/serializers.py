import struct, base64
from rest_framework import serializers

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