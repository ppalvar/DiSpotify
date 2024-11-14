<template>
    <div class="songs-list-area">
      <div class="search-filter-container">
        <div class="row">
          <div class="col-md-8">
            <div class="input-group">
              <input type="text" class="form-control" placeholder="Buscar canciones...">
              <button class="btn btn-outline-secondary" type="button">
                <i class="fas fa-search"></i>
              </button>
            </div>
          </div>
          <div class="col-md-4 text-end">
            <button class="btn btn-outline-light">
              <i class="fas fa-filter me-2"></i>Filtrar
            </button>
          </div>
        </div>
      </div>
  
      <div class="songs-list">
        <div class="song-item" v-for="song in songs" :key="song.id" @click="playAudio">
          <img src="https://via.placeholder.com/40" class="me-3" alt="Album cover">
          <div class="flex-grow-1">
            <h6 class="mb-0">{{ song.name }}</h6>
            <small class="text-muted">{{ song.artist }} - {{ song.album }}</small>
          </div>
          <div class="text-muted">{{ song.duration }}</div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import { mapActions } from 'vuex'

  export default {
    name: 'SongsList',
    data() {
      return {
        songs: [
          {
            id: '1',
            name: 'Nombre de la Canción',
            artist: 'Artista',
            album: 'Álbum',
            duration: '3:45'
          },
          {
            id: '2',
            name: 'Otra Canción',
            artist: 'Otro Artista',
            album: 'Otro Álbum',
            duration: '4:20'
          }
        ]
      }
    },
    methods: {
      ...mapActions(['playAudio'])
    }
  }
  </script>
  
  <style scoped>
  .songs-list-area {
      width: 66.666%;
      overflow-y: auto;
      padding: 20px;
  }
  
  .search-filter-container {
      margin-bottom: 20px;
  }
  
  .song-item {
      padding: 0.5rem;
      border-radius: 4px;
      transition: background-color 0.3s;
      display: flex;
      align-items: center;
      margin-bottom: 8px;
  }
  
  .song-item:hover {
      background-color: #282828;
  }
  
  .song-item img {
      width: 40px;
      height: 40px;
      object-fit: cover;
  }
  
  /* Scrollbar personalizada */
  .songs-list-area::-webkit-scrollbar {
      width: 8px;
  }
  
  .songs-list-area::-webkit-scrollbar-track {
      background: #121212;
  }
  
  .songs-list-area::-webkit-scrollbar-thumb {
      background: #555;
      border-radius: 4px;
  }
  
  .songs-list-area::-webkit-scrollbar-thumb:hover {
      background: #666;
  }
  </style>