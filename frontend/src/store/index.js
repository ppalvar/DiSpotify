import { createStore } from 'vuex'
import AudioPlayer from '@/services/AudioPlayer'
import PlaylistManager from '@/services/PlaylistManager'

export default createStore({
	state: {
		audioPlayer: new AudioPlayer('http://127.0.0.1:8000/api/streamer'),
		playlistManager: new PlaylistManager(),
		currentSong: {
			name: '-----',
			artist: '-----',
			album: '-----'
		},
		isPlaying: false,
		formattedRemainingTime: '00:00',
		formattedTotalDuration: '00:00',
		progressBarProgress: 0,
		volume: 50,
		songs: [],
		repeat: false,
		filters: {
			artist: null,
			album: null,
		}
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
		},
		SET_CURRENT_SONG(state, song) {
			state.currentSong = {
				name: song.title,
				album: song.album_name,
				artist: song.artist_names.join(', ')
			}
		},
		SET_SONGS(state, songs) {
			state.songs = songs
		},
		SET_REPEAT(state, repeat) {
			state.repeat = repeat
		},
		SET_FILTERS(state, { album, artist }) {
			state.filters = {
				album: album,
				artist: artist,
			}
		}
	},
	actions: {
		async playAudio({ state, commit }, songId) {
			await state.audioPlayer.start(songId, state.volume)
			state.playlistManager.setCurrentSong(songId)

			commit('SET_PLAYING', true)
			commit('SET_CURRENT_SONG', state.playlistManager.getCurrentSong())
			setTimeUpdater(state, commit)

			state.audioPlayer.onPlaybackEnd = async () => {
				if (!state.repeat) {
					state.playlistManager.next()
				}

				const songId = state.playlistManager.getCurrentSong().id

				await state.audioPlayer.start(songId, state.volume)
				commit('SET_PLAYING', true)
				commit('SET_CURRENT_SONG', state.playlistManager.getCurrentSong())
				setTimeUpdater(state, commit)
			}
		},
		//#region controls
		setVolume({ state, commit }, event) {
			const volume = event.target.value
			commit('SET_VOLUME', volume)
			if (state.audioPlayer && state.audioPlayer.sound) {
				state.audioPlayer.sound.volume(volume / 100)
			}
		},
		playAndPause({ state, commit }) {
			if (state.audioPlayer && state.audioPlayer.sound) {
				state.audioPlayer.playAndPause()
				commit('SET_PLAYING', state.audioPlayer.sound.playing())
				setTimeUpdater(state, commit)
			}
		},
		moveToTime({ state, commit }, event) {
			if (state.audioPlayer && state.audioPlayer.sound) {
				const timePercent = event.target.value / 100
				state.audioPlayer.moveToPosition(null, timePercent)

				commit('SET_PLAYING', true)
			}
		},
		prevSong({ state, commit }) {
			if (state.audioPlayer && state.audioPlayer.sound && state.playlistManager) {
				state.playlistManager.prev()
				const songId = state.playlistManager.getCurrentSong().id

				state.audioPlayer.start(songId, state.volume)
				commit('SET_PLAYING', true)
				commit('SET_CURRENT_SONG', state.playlistManager.getCurrentSong())
				setTimeUpdater(state, commit)
			}
		}
		,
		nextSong({ state, commit }) {
			if (state.audioPlayer && state.audioPlayer.sound && state.playlistManager) {
				state.playlistManager.next()
				const songId = state.playlistManager.getCurrentSong().id

				state.audioPlayer.start(songId, state.volume)
				commit('SET_PLAYING', true)
				commit('SET_CURRENT_SONG', state.playlistManager.getCurrentSong())
				setTimeUpdater(state, commit)
			}
		},
		shuffleList({ state, commit }) {
			if (state.playlistManager) {
				state.playlistManager.shuffle()
				commit('SET_SONGS', state.playlistManager.songs)
			}
		},
		setAndUnsetRepeat({ state, commit }) {
			commit('SET_REPEAT', !state.repeat)
		},
		//#endregion

		//#region Songs getters
		async fetchSongs({ state, commit }) {
			const songs = await state.playlistManager.loadSongs()
			commit('SET_SONGS', songs)
		},
		async refreshSongs({ state, commit }) {
			const songs = await state.playlistManager.refresh()
			commit('SET_SONGS', songs)
		},
		async filter({ state, commit }, { album=null, artist=null, name=null}) {
			commit('SET_FILTERS', { album: album, artist: artist, name:name })
			const filteredSongs = await state.playlistManager.filter({ artist: artist, album: album, name:name })
			commit('SET_SONGS', filteredSongs)
		}
		//#endregion
	}
})

function setTimeUpdater(state, commit) {
	const interval = setInterval(() => {
		if (state.audioPlayer.sound.playing()) {
			const currentTime = state.audioPlayer.sound.seek()
			updateTime(currentTime)
		} else {
			clearInterval(interval)
		}
	}, 1000)

	function updateTime(currentTime) {
		const remainingTime = state.audioPlayer.duration - currentTime

		const formattedRemainingTime = formatTime(remainingTime)
		const formattedTotalDuration = formatTime(state.audioPlayer.duration)
		const progressBarProgress = Math.floor((currentTime / state.audioPlayer.duration) * 100)

		commit('SET_TIMES', { remaining: formattedRemainingTime, total: formattedTotalDuration, progress: progressBarProgress })
	}
	function formatTime(seconds) {
		const totalMinutes = Math.floor(seconds / 60)
		const totalSeconds = Math.floor(seconds % 60)
		const formattedMinutes = String(totalMinutes).padStart(2, '0')
		const formattedSeconds = String(totalSeconds).padStart(2, '0')

		return `${formattedMinutes}:${formattedSeconds}`
	}
}