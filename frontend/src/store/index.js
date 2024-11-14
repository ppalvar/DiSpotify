import { createStore } from 'vuex'
import AudioPlayer from '@/services/AudioPlayer'

export default createStore({
	state: {
		audioPlayer: null,
		currentSong: {
			name: 'Nombre de la Canción',
			artist: 'Artista',
			album: 'Álbum'
		},
		isPlaying: false,
		formattedRemainingTime: '00:00',
		formattedTotalDuration: '00:00',
		progressBarProgress: 0,
		volume: 50
	},
	mutations: {
		SET_AUDIO_PLAYER(state, player) {
			state.audioPlayer = player
		},
		SET_PLAYING(state, isPlaying) {
			state.isPlaying = isPlaying
		},
		SET_TIMES(state, { remaining, total, progress }) {
			state.formattedRemainingTime = remaining
			state.formattedTotalDuration = total
			state.progressBarProgress = progress
		},
		SET_VOLUME(state, volume) {
			state.volume = volume
		}
	},
	actions: {
		async playAudio({ state, commit }) {
			if (!state.audioPlayer) {
				const player = new AudioPlayer('http://127.0.0.1:8000/api/streamer')
				commit('SET_AUDIO_PLAYER', player)
			}
			await state.audioPlayer.start('1')
			commit('SET_PLAYING', true)

			setTimeUpdater(state, commit);
		},
		setVolume({ state, commit }, event) {
			const volume = event.target.value
			commit('SET_VOLUME', volume)
			if (state.audioPlayer) {
				state.audioPlayer.sound.volume(volume / 100)
			}
		},
		playAndPause({ state, commit }) {
			if (state.audioPlayer) {
				state.audioPlayer.playAndPause()
				commit('SET_PLAYING', !state.sound.playing())
				setTimeUpdater(state, commit)
			}
		},
		moveToTime({ state, commit }, event) {
			const timePercent = event.target.value / 100
			state.audioPlayer.moveToPosition(null, timePercent)

			commit('SET_PLAYING', true)
		}
	}
})

function setTimeUpdater(state, commit) {
	const interval = setInterval(() => {
		if (state.audioPlayer.sound.playing()) {
			const currentTime = state.audioPlayer.sound.seek();
			updateTime(currentTime)
		} else {
			clearInterval(interval)
		}
	}, 1000)

	function updateTime(currentTime) {
		const remainingTime = state.audioPlayer.duration - currentTime;

		const formattedRemainingTime = formatTime(remainingTime);
		const formattedTotalDuration = formatTime(state.audioPlayer.duration);
		const progressBarProgress = Math.floor((currentTime / state.audioPlayer.duration) * 100);

		commit('SET_TIMES', { remaining: formattedRemainingTime, total: formattedTotalDuration, progress: progressBarProgress });
	}
	function formatTime(seconds) {
		const totalMinutes = Math.floor(seconds / 60);
		const totalSeconds = Math.floor(seconds % 60);
		const formattedMinutes = String(totalMinutes).padStart(2, '0');
		const formattedSeconds = String(totalSeconds).padStart(2, '0');

		return `${formattedMinutes}:${formattedSeconds}`;
	}
}