class AudioPlayer {
    constructor(host) {
        this.host = host;
        this.clientId = crypto.randomUUID();
        this.audioId = null;
        this.ws = null;
    }

    async start(audioId) {
        this.ws = new WebSocket(this.host);
        this.audioId = audioId;

        this.ws.onopen = async () => {
            this.ws.send(JSON.stringify({
                type: 'init',
                include_header: true,
                audio_id: this.audioId,
                client_id: this.clientId
            }));

            this.ws.onmessage = async (event) => await this.handleMessage(event);

            this.ws.onerror = (error) => console.error('WebSocket error:', error);
            this.ws.onclose = (event) => console.log('WebSocket closed:', event);
        }
    }

    async handleMessage(event) {
        const response = JSON.parse(event.data);
        console.log(response);
        switch (response.type) {
            case 'metadata':
                this.initAudio(response.data);
                await this.startPlaying();
                break;

            case 'chunk':
                this.addChunks(response.data, response.chunk_index, response.chunk_count);
                await this.compileAndPlay(0);
                break;
        }
    }

    async startPlaying() {
        await this.loadChunk(0, 100);
    }

    loadChunk(chunkIndex, count = 1) {
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'request_chunk',
                audio_id: this.audioId,
                client_id: this.clientId,
                chunk_index: chunkIndex,
                chunk_count: count
            }));
        } else {
            console.error("WebSocket no está abierto. No se puede solicitar el chunk.");
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
        this.header = this.base64ToByteArray(metadata.header);

        this.cachedChunks = Array(this.totalChunks);
        this.audioContext = new window.AudioContext();
        this.gainNode = this.audioContext.createGain();
    }

    setVolume(value) {console.log('value');
        const volume = Math.max(0, Math.min(1, value / 100)); // Asegurarse de que el volumen esté entre 0 y 1
        this.gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime); // Ajustar el volumen
    }

    addChunks(chunks, chunkIndex, chunkCount) {
        for (let i = 0; i < chunkCount; i++) {
            const chunk = this.base64ToByteArray(chunks[i]);
            const index = chunkIndex + i;
            if (this.cachedChunks[index]) continue;
            this.cachedChunks[index] = chunk;
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

    async compileAudio() {
        const volumeController = document.getElementById("volume-control");
        this.setVolume(volumeController.value); // Inicializar el volumen

        // const bytesPerSample = this.bitsPerSample / 8;
        // const totalSamples = Math.floor(positionInSeconds * this.sampleRate);
        // const startChunkIndex = Math.floor(totalSamples * bytesPerSample * this.channels / this.chunkSize);

        const audioData = [];
        let totalSize = this.header.length;

        // Recopilar chunks desde el índice calculado
        for (let i = 0; i < this.totalChunks; i++) {
            if (this.cachedChunks[i]) {
                audioData.push(this.cachedChunks[i]);
            } else {
                continue; // Detener si encontramos un chunk no definido
            }
        }

        // Convertir la cabecera y los chunks a un solo Uint8Array
        totalSize += audioData.reduce((acc, chunk) => acc + chunk.length, 0);
        const wavArray = new Uint8Array(totalSize);
        wavArray.set(this.header, 0);
        console.log(wavArray);
        let offset = this.header.length;
        for (const chunk of audioData) {
            wavArray.set(chunk, offset);
            offset += chunk.length;
        }

        return wavArray;
    }

    playAudioBuffer(audioBuffer, positionInSeconds=0) {
        if (positionInSeconds < 0 || positionInSeconds > this.duration) {
            console.error("La posición temporal está fuera de los límites de la duración del audio.");
            return;
        }

        var arrayBuffer = new ArrayBuffer(audioBuffer.length);
        var bufferView = new Uint8Array(arrayBuffer);
        for (let i = 0; i < audioBuffer.length; i++) {
            bufferView[i] = audioBuffer[i];
        }

        this.audioContext.decodeAudioData(arrayBuffer, (buffer) => {
            var source = this.audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(this.gainNode); // Conectar el source al GainNode
            this.gainNode.connect(this.audioContext.destination); // Conectar el GainNode a la salida
            
            source.start(0);

            this.isPlaying = true;

            source.onended = () => {
                this.isPlaying = false;
            };
        });
    }


    async compileAndPlay(positionInSeconds) {
        const buffer = await this.compileAudio();
        this.playAudioBuffer(buffer);
    }
}

// class AudioPlayer {
//     constructor(host) {
//         this.host = host;
//         this.clientId = crypto.randomUUID();
//         this.audioId = null;
//         this.currentAudio = null;
//         this.ws = null;
//     }

//     async start(audioId) {
//         this.ws = new WebSocket(this.host);
//         this.audioId = audioId;

//         this.ws.onopen = async () => {
//             this.ws.send(JSON.stringify({
//                 type: 'init',
//                 include_header: true,
//                 audio_id: this.audioId,
//                 client_id: this.clientId
//             }));

//             this.ws.onmessage = async (event) => await this.handleMessage(event);

//             this.ws.onerror = (error) => console.error('WebSocket error:', error);
//             this.ws.onclose = (event) => console.log('WebSocket closed:', event);
//         }
//     }

//     async handleMessage(event) {
//         const response = JSON.parse(event.data);
//         console.log(response);
//         switch (response.type) {
//             case 'metadata':
//                 this.currentAudio = new AudioFile(this.audioId, response.data);
//                 this.startPlaying();
//                 break;

//             case 'chunk':
//                 this.addChunks(response.data, response.chunk_index, response.chunk_count);
//                 await this.compileAndPlay(0);
//                 break;
//         }
//     }

//     async startPlaying() {
//         await this.loadChunk(0, 100);
//     }

//     loadChunk(chunkIndex, count = 1) {
//         if (this.ws.readyState === WebSocket.OPEN) {
//             this.ws.send(JSON.stringify({
//                 type: 'request_chunk',
//                 audio_id: this.audioId,
//                 client_id: this.clientId,
//                 chunk_index: chunkIndex,
//                 chunk_count: count
//             }));
//         } else {
//             console.error("WebSocket no está abierto. No se puede solicitar el chunk.");
//         }
//     }
// }

