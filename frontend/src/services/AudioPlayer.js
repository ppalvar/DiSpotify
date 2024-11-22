import { Howl } from "howler";

export default class AudioPlayer {
    constructor(host) {
        this.host = host;
        this.audioId = null;
        this.CHUNKS_TO_LOAD = 10;
        this.onPlaybackEnd = () => { };
    }

    async start(audioId, volume = null) {
        if (audioId != this.audioId) {
            this.audioId = audioId;
    
            const initData = await this.getFromApi(this.host, {
                chunk_index: 0,
                chunk_count: this.CHUNKS_TO_LOAD,
                audio_id: this.audioId,
                include_metadata: true
            });
    
            this.initAudio(initData.metadata);
    
            for (let index = 0; index <= this.totalChunks; index += this.CHUNKS_TO_LOAD) {
                await this.loadChunks(index, Math.min(this.CHUNKS_TO_LOAD, this.totalChunks - index));
            }
        }

        this.isPlaying = true;
        this.playAudioBuffer();

        this.setVolume(volume ?? 50);
    }

    // Función para realizar la petición a la API
    async getFromApi(url, params) {
        try {
            // Convertir los parámetros a query string
            const queryParams = new URLSearchParams();
            for (const [key, value] of Object.entries(params)) {
                queryParams.append(key, (typeof value === 'boolean') ? value.toString() : value);
            }

            // Construir la URL completa con los parámetros
            const urlWithParams = `${url}?${queryParams.toString()}`;

            const response = await fetch(urlWithParams, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }

            return await response.json();

        } catch (error) {
            console.error('Error en la petición:', error);
            throw error;
        }
    }

    initAudio(metadata) {
        this.isPlaying = false;

        this.totalChunks = metadata.total_chunks;
        this.chunkSize = metadata.chunk_size;
        this.duration = metadata.duration;

        this.fileSize = metadata.file_size ?? 0;

        this.audioByteArray = new Uint8Array(this.fileSize).fill(0);

        this.source = null;
    }

    playAndPause() {
        if (this.sound.playing()) {
            this.sound.pause();
        }
        else {
            this.sound.play()
        }

        this.isPlaying = this.sound.playing();
    }

    moveToPosition(positionInSeconds = null, positionInPercent = null) {
        if (positionInSeconds === null) {
            positionInSeconds = positionInPercent * this.duration;
        }

        this.sound.seek(positionInSeconds);
    }

    setVolume(value = null) {
        const volume = Math.max(0, Math.min(1, value / 100));
        this.sound.volume(volume);
    }

    addChunks(chunks, chunkIndex, chunkCount) {
        for (let i = 0; i < chunkCount; i++) {
            const index = chunkIndex + i;
            this.compileChunk(chunks[i], index);
        }
    }

    base64ToByteArray(base64) {
        const binaryString = atob(base64);
        const byteArray = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            byteArray[i] = binaryString.charCodeAt(i);
        }
        return byteArray;
    }

    compileChunk(chunk, index) {
        const offset = index * this.chunkSize;
        const chunkAsBytes = this.base64ToByteArray(chunk);
        this.audioByteArray.set(chunkAsBytes, offset);
    }

    playAudioBuffer() {
        const blob = new Blob([this.audioByteArray], { type: 'audio/mp3' });
        const blobURL = URL.createObjectURL(blob);

        if (this.sound) {
            this.sound.unload()
        }

        this.sound = new Howl({
            src: [blobURL],
            format: ['mp3', 'wav', 'aac'],
            html5: true,
            onloaderror: function (id, error) {
                console.error('Error al cargar el audio:', error);
            },
            onend: () => {
                this.onPlaybackEnd();
            }
        });

        this.sound.play();
        this.isPlaying = true;
    }

    async loadChunks(chunkIndex, chunkCount = null) {
        const data = await this.getFromApi(this.host, {
            chunk_index: chunkIndex,
            chunk_count: chunkCount ?? this.CHUNKS_TO_LOAD,
            audio_id: this.audioId,
            include_header: false,
            include_metadata: false
        });

        this.addChunks(data.chunks, data.chunk_index, data.chunk_count);
    }
}
