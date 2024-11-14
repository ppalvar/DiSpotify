import { Howl } from "howler";

export default class AudioPlayer {
    constructor(host) {
        this.host = host;
        this.audioId = null;
        this.CHUNKS_TO_LOAD = 10;
    }

    async start(audioId) {
        this.audioId = audioId;

        const initData = await this.getFromApi(this.host, {
            chunk_index: 0,
            chunk_count: this.CHUNKS_TO_LOAD,
            audio_id: this.audioId,
            include_header: true,
            include_metadata: true
        });

        this.initAudio(initData.metadata);
        this.compileHeader(initData.header);

        // Cargar los fragmentos de audio
        for (let index = 0; index <= this.totalChunks; index += this.CHUNKS_TO_LOAD) {
            await this.loadChunks(index, Math.min(this.CHUNKS_TO_LOAD, this.totalChunks - index));
        }

        this.isPlaying = true;
        this.playAudioBuffer();
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

    // Inicializa los parámetros de audio
    initAudio(metadata) {
        this.isPlaying = false;

        this.totalChunks = metadata.total_chunks;
        this.chunkSize = metadata.chunk_size;
        this.channels = metadata.channels;
        this.sampleRate = metadata.sample_rate;
        this.bitsPerSample = metadata.bits_per_sample;
        this.duration = metadata.duration;

        this.cachedChunks = Array(this.totalChunks + 1).fill(false); // Uno extra para el header
        this.audioContext = new window.AudioContext();
        this.gainNode = this.audioContext.createGain();

        this.currentPosition = 0;
        this.currentChunk = 0;

        // Calcular el tamaño de salto en base a los parámetros
        this.JUMP_SIZE = (this.chunkSize * this.CHUNKS_TO_LOAD) / (this.bitsPerSample / 8) / this.sampleRate / this.channels;

        // Crear el array de bytes para el WAV
        this.wavByteArray = new Uint8Array(44 + this.totalChunks * this.chunkSize).fill(0);

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
        console.log(this.sound.seek())
    }

    // Establece el volumen del audio
    setVolume(value) {
        const volume = Math.max(0, Math.min(1, value / 100)); // Asegurarse de que el volumen esté entre 0 y 1
        this.gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime); // Ajustar el volumen
    }

    // Añade fragmentos a los datos de audio
    addChunks(chunks, chunkIndex, chunkCount) {
        for (let i = 0; i < chunkCount; i++) {
            const index = chunkIndex + i;

            if (this.cachedChunks[index]) continue;
            this.compileChunk(chunks[i], index);
            this.cachedChunks[index] = true;
        }
    }

    // Convierte una cadena base64 a un array de bytes
    base64ToByteArray(base64) {
        const binaryString = atob(base64);
        const byteArray = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            byteArray[i] = binaryString.charCodeAt(i);
        }
        return byteArray;
    }

    // Compila y agrega el header al archivo WAV
    compileHeader(header) {
        this.addChunkToWAVFile(header, 0);
    }

    // Compila y agrega un fragmento de audio al archivo WAV
    compileChunk(chunk, index) {
        const offset = 44 + index * this.chunkSize;
        this.addChunkToWAVFile(chunk, offset);
    }

    // Agrega los datos de un fragmento a la estructura del WAV
    addChunkToWAVFile(chunk, offset) {
        const chunkAsBytes = this.base64ToByteArray(chunk);
        this.wavByteArray.set(chunkAsBytes, offset);
    }

    // Reproduce el buffer de audio
    playAudioBuffer() {
        const blob = new Blob([this.wavByteArray], {type:'audio/wav'});
        const blobURL = URL.createObjectURL(blob);
        
        this.sound = new Howl({
            src: [blobURL],
            format: ['wav'],
            html5: true,
            onload: function () {
                console.log('Audio cargado y listo para reproducir');
            },
            onloaderror: function (id, error) {
                console.error('Error al cargar el audio:', error);
            }
        });

        this.sound.play();
        this.isPlaying = true;
    }

    // Carga los fragmentos de audio desde la API
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

    // Copia un array buffer
    copy(src) {
        const dst = new ArrayBuffer(src.byteLength);
        new Uint8Array(dst).set(new Uint8Array(src));
        return new Uint8Array(dst);
    }
}
