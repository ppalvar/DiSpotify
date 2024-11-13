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
      // Iniciar el timer...
    },
    setVolume({ state, commit }, event) {
      const volume = event.target.value
      commit('SET_VOLUME', volume)
      if (state.audioPlayer) {
        state.audioPlayer.setVolume(volume)
      }
    }
  }
})