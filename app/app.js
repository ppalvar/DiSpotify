const app = Vue.createApp({
    data() {
        return {
            audioPlayer: null,
            formattedRemainingTime: '00:00',
            formattedTotalDuration: '00:00',
            progressBarProgress: 0
        };
    },
    methods: {
        playAudio() {
            if (!this.audioPlayer) {
                this.audioPlayer = new AudioPlayer('ws://localhost:8765');

            }
            this.audioPlayer.start('2');
            this.startTimer();
        },
        startTimer() {
            const interval = setInterval(() => {
                this.formattedTotalDuration = this.formatTime(this.audioPlayer.duration);
                if (this.audioPlayer.isPlaying) {
                    const currentTime = this.audioPlayer.audioContext.currentTime;
                    this.updateTime(currentTime);
                } else {
                    clearInterval(interval); // Detener el intervalo si no está reproduciendo
                }
            }, 1000);
        },
        updateTime(currentTime) {
            const remainingTime = this.audioPlayer.duration - currentTime;
            
            this.formattedRemainingTime = this.formatTime(remainingTime);
            this.progressBarProgress = Math.floor((currentTime / this.audioPlayer.duration) * 100);
        },
        formatTime(seconds) {
            const totalMinutes = Math.floor(seconds / 60);
            const totalSeconds = Math.floor(seconds % 60);
            const formattedMinutes = String(totalMinutes).padStart(2, '0');
            const formattedSeconds = String(totalSeconds).padStart(2, '0');
            return `${formattedMinutes}:${formattedSeconds}`;
        },
        setVolume(event) {
            const volumeValue = event.target.value;
            console.log(this.audioPlayer.currentAudio);
            if (this.audioPlayer.currentAudio) {
                this.audioPlayer.setVolume(volumeValue); // Suponiendo que setVolume está implementado en AudioFile
            }
        }
    }
});

app.mount('#app');