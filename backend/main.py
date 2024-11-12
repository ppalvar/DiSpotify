import json
import wave
import struct
import base64
import asyncio
import websockets
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class AudioChunk:
    index: int
    data: bytes
    timestamp: float

class WAVStreamManager:
    def __init__(self, audio_id: str):
        self.filename = f'{audio_id}.wav'
        self.header = None
        self.header_size = 44
        self.chunk_size = 1 << 15  # 32KB por chunk
        self.chunks_cache: Dict[int, AudioChunk] = {}
        self.total_chunks = 0
        self.initialize_audio()

    def initialize_audio(self):
        """Inicializa el archivo de audio y calcula el número total de chunks"""
        with open(self.filename, 'rb') as file:
            # Leemos y guardamos la cabecera

            self.header = file.read(self.header_size)

            # Calculamos el tamaño total del archivo
            file.seek(0, 2)  # Vamos al final del archivo
            file_size = file.tell()
            
            # Calculamos el número total de chunks
            audio_data_size = file_size - self.header_size
            self.total_chunks = (audio_data_size + self.chunk_size - 1) // self.chunk_size

    def get_chunk(self, chunk_index: int, num_chunks: int = 1) -> Optional[List[bytes]]:
        """Obtiene uno o más chunks específicos del archivo"""
        if not 0 <= chunk_index < self.total_chunks:
            return None

        chunks = []
        for i in range(num_chunks):
            current_chunk_index = chunk_index + i
            if current_chunk_index >= self.total_chunks:  # Verificamos si estamos fuera de los límites
                break
            
            # Si el chunk está en caché, lo agregamos
            if current_chunk_index in self.chunks_cache:
                chunks.append(self.chunks_cache[current_chunk_index].data)
            else:
                # Leemos el chunk del archivo
                with open(self.filename, 'rb') as file:
                    offset = self.header_size + (current_chunk_index * self.chunk_size)
                    file.seek(offset)
                    chunk_data = file.read(self.chunk_size)
                    
                    # Guardamos en caché
                    self.chunks_cache[current_chunk_index] = AudioChunk(
                        index=current_chunk_index,
                        data=chunk_data,
                        timestamp=asyncio.get_event_loop().time()
                    )
                    
                    chunks.append(chunk_data)

        return chunks if chunks else None

    def get_header(self) -> bytes:
        """Devuelve la cabecera del archivo WAV"""
        return base64.b64encode(self.header).decode('utf-8')
    
    def get_wav_duration(self):
        with wave.open(self.filename, 'r') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return duration

    def get_metadata(self, include_header=False) -> dict:
        """Obtiene metadatos del archivo WAV"""
        # Parseamos la cabecera para obtener información relevante
        channels = struct.unpack_from('<H', self.header, 22)[0]
        sample_rate = struct.unpack_from('<I', self.header, 24)[0]
        bits_per_sample = struct.unpack_from('<H', self.header, 34)[0]

        response = {
            'total_chunks': self.total_chunks,
            'chunk_size': self.chunk_size,
            'channels': channels,
            'sample_rate': sample_rate,
            'bits_per_sample': bits_per_sample,
            'duration': self.get_wav_duration()
        }

        if include_header:
            response['header'] = self.get_header()
        
        return response

class AudioStreamServer:
    def __init__(self):
        self.stream_managers: Dict[str, WAVStreamManager] = {}

    async def handle_client(self, websocket, path):
        try:
            # Esperamos el mensaje inicial del cliente
            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self.process_message(data)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    }))

        except websockets.exceptions.ConnectionClosed:
            print("Cliente desconectado")

    async def process_message(self, data: dict) -> dict:
        msg_type = data.get('type')
        client_id = data.get('client_id')
        audio_id = data.get('audio_id')

        if msg_type == 'init':
            # Inicializa un nuevo stream
            include_header = data.get('include_header', False)

            if client_id not in self.stream_managers:
                self.stream_managers[client_id] = WAVStreamManager(audio_id)
            
            return {
                'type': 'metadata',
                'data': self.stream_managers[client_id].get_metadata(include_header)
            }

        elif msg_type == 'request_header':
            if client_id not in self.stream_managers:
                return {'type': 'error', 'message': 'Audio no inicializado'}
            
            header = self.stream_managers[client_id].get_header()
            return {
                'type': 'header',
                'data': header  # Convertimos a cadena para enviar por JSON
            }

        elif msg_type == 'request_chunk':
            chunk_index = data.get('chunk_index')
            chunk_count = data.get('chunk_count', 1)
            
            if client_id not in self.stream_managers:
                return {'type': 'error', 'message': 'Audio no inicializado'}

            chunks = self.stream_managers[client_id].get_chunk(chunk_index, chunk_count)
            if chunks is None:
                return {'type': 'error', 'message': 'Chunk inválido'}
            
            return {
                'type': 'chunk',
                'chunk_index': chunk_index,
                'chunk_count': chunk_count,
                'data': [base64.b64encode(chunk).decode('utf-8') for chunk in chunks]
            }

        return {'type': 'error', 'message': 'Tipo de mensaje no reconocido'}

# Inicialización del servidor
async def main():
    server = AudioStreamServer()
    
    print("Streaming service started.")
    
    async with websockets.serve(server.handle_client, "localhost", 8765):
        await asyncio.Future()  # Ejecuta indefinidamente
    

if __name__ == '__main__':
    asyncio.run(main())