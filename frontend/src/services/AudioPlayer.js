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

        this.addChunks(initData.chunks, 0, this.CHUNKS_TO_LOAD);

        this.playAudioBuffer();

        this.preloadInterval = window.setInterval(async () => {
            this.currentChunk += this.CHUNKS_TO_LOAD;
            
            if (this.currentChunk > this.totalChunks) {
                clearInterval(this.preloadInterval);
            }
            
            this.loadChunks(this.currentChunk);
        }, 
        this.JUMP_SIZE * 0.8);
    }

    async getFromApi(url, params) {
        try {
            // Convertir los parámetros a query string
            const queryParams = new URLSearchParams();
            for (const [key, value] of Object.entries(params)) {
                // Convertir booleanos a strings 'true'/'false'
                if (typeof value === 'boolean') {
                    queryParams.append(key, value.toString());
                } else {
                    queryParams.append(key, value);
                }
            }

            // Construir la URL completa con los query params
            const urlWithParams = `${url}?${queryParams.toString()}`;

            const response = await fetch(urlWithParams, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }

            const data = await response.json();
            return data;

        } catch (error) {
            console.error('Error en la petición:', error);
            throw error;
        }
    }

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

        this.JUMP_SIZE = (this.chunkSize * this.CHUNKS_TO_LOAD) / (this.bitsPerSample / 8) / this.sampleRate / this.channels;

        this.wavByteArray = new Uint8Array(44 + this.totalChunks * this.chunkSize).fill(0);
    }

    setVolume(value) {
        const volume = Math.max(0, Math.min(1, value / 100)); // Asegurarse de que el volumen esté entre 0 y 1
        this.gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime); // Ajustar el volumen
    }

    addChunks(chunks, chunkIndex, chunkCount) {
        for (let i = 0; i < chunkCount; i++) {
            const index = chunkIndex + i;

            if (this.cachedChunks[index]) continue;
            this.compileChunk(chunks[i], index);
            this.cachedChunks[index] = true;
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

    compileHeader(header) {
        this.addChunkToWAVFile(header, 0);
    }

    compileChunk(chunk, index) {
        const offset = 44 + index * this.chunkSize;
        this.addChunkToWAVFile(chunk, offset);
    }

    addChunkToWAVFile(chunk, offset) {
        const chunkAsBytes = this.base64ToByteArray(chunk);
        this.wavByteArray.set(chunkAsBytes, offset);
    }

    playAudioBuffer(positionInSeconds = 0) {
        const audioData = new Uint8Array(this.wavByteArray);

        this.audioContext.decodeAudioData(audioData.buffer, (buffer) => {
            var source = this.audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(this.gainNode);
            this.gainNode.connect(this.audioContext.destination);

            source.start(0, positionInSeconds, Math.min(this.JUMP_SIZE, this.duration - this.currentPosition));

            this.isPlaying = true;

            source.onended = () => {
                this.currentPosition = this.audioContext.currentTime;
                this.isPlaying = false;
                this.playAudioBuffer(this.currentPosition);
            };
        });
    }

    async loadChunks(chunkIndex, chunkCount=null) {
        const data = await this.getFromApi(this.host, {
            chunk_index: chunkIndex,
            chunk_count: chunkCount === null ? this.CHUNKS_TO_LOAD : chunkCount,
            audio_id: this.audioId,
            include_header: false,
            include_metadata: false
        })

        this.addChunks(data.chunks, data.chunk_index, data.chunk_count);
    }

    copy(src) {
        var dst = new ArrayBuffer(src.byteLength);
        new Uint8Array(dst).set(new Uint8Array(src));
        return new Uint8Array(dst);
    }
}
