<template>
  <div class="songs-list-area">
    <div class="search-filter-container">
      <div class="row">
        <div class="col-md-8">
          <div class="input-group">
            <input
              type="text"
              class="form-control"
              placeholder="Buscar canciones..."
              @input="getSearchText"
            />
            <button
              class="btn btn-outline-secondary"
              type="button"
              @click="search"
            >
              <i class="fas fa-search"></i>
            </button>
          </div>
        </div>
        <div class="col-md-4 text-end">
          <button class="btn btn-outline-light" @click="openFilterModal">
            <i class="fas fa-filter me-2"></i>Filtrar
          </button>
        </div>
      </div>
    </div>

    <div class="songs-list">
      <div
        class="song-item"
        v-for="song in songs"
        :key="song.id"
        @click="playAudio(song.id)"
      >
        <img
          src="https://placehold.co/40x40"
          class="me-3"
          alt="Album cover"
        />
        <div class="flex-grow-1">
          <h6 class="mb-0">{{ song.title }}</h6>
          <small class="text-muted"
            >{{ song.artist_names.join(", ") }} - {{ song.album_name }}</small
          >
        </div>
        <div class="text-muted">{{ formatTime(song.duration_seconds) }}</div>
      </div>
    </div>
    <FilterModal ref="filterModal" />
  </div>
</template>

<script>
import { mapActions, mapState } from "vuex";
import FilterModal from "./FilterModal.vue";

export default {
  name: "SongsList",
  data() {
    return {
      searchText: "",
    };
  },
  components: {
    FilterModal,
  },
  computed: {
    ...mapState(["songs"]),
  },
  methods: {
    ...mapActions(["playAudio", "fetchSongs", "filter"]),
    search() {
      this.filter({ album: null, artist: null, name: this.searchText });
    },
    getSearchText(event) {
      this.searchText = event.target.value;
    },
    formatTime(time_seconds) {
      const minutes = String(Math.floor(time_seconds / 60)).padStart(2, "0");
      const seconds = String(Math.floor(time_seconds % 60)).padStart(2, "0");

      return `${minutes}:${seconds}`;
    },
    openFilterModal() {
      this.$refs.filterModal.openModal();
    },
  },
  mounted() {
    this.fetchSongs();
  },
};
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
