<template>
  <div
    v-if="isVisible"
    class="modal fade show"
    style="display: block"
    @click.self="closeModal"
  >
    <div class="modal-dialog">
      <div class="modal-content bg-dark text-white">
        <div class="modal-header">
          <h5 class="modal-title">Filter by Artist and Album</h5>
          <button
            type="button"
            class="btn-close btn-close-white"
            @click="closeModal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="submitForm">
            <div class="mb-3">
              <label for="artistSelect" class="form-label"
                >Select Artists</label
              >
              <select
                id="artistSelect"
                v-model="selectedArtists"
                class="form-control"
                multiple
              >
                <option
                  v-for="artist in artists"
                  :key="artist.id"
                  :value="artist.id"
                >
                  {{ artist.name }}
                </option>
              </select>
            </div>
            <div class="mb-3">
              <label for="albumSelect" class="form-label">Select Album</label>
              <select
                id="albumSelect"
                v-model="selectedAlbum"
                class="form-control"
              >
                <option
                  v-for="album in albums"
                  :key="album.id"
                  :value="album.id"
                >
                  {{ album.name }}
                </option>
              </select>
            </div>
            <div class="modal-footer">
              <button type="submit" class="btn btn-primary">
                Apply Filters
              </button>
              <button
                type="button"
                class="btn btn-secondary"
                @click="closeModal"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";

export default {
  name: "FilterModal",
  data() {
    return {
      selectedArtists: [],
      selectedAlbum: null,
      artists: [], // Array to hold artist data
      albums: [], // Array to hold album data
      isVisible: false,
    };
  },
  methods: {
    ...mapActions(['filter']),
    
    openModal() {
      this.isVisible = true;
      this.fetchArtists();
      this.fetchAlbums();
    },
    closeModal() {
      this.isVisible = false;
    },
    async fetchArtists() {
      try {
        const response = await axios.get("http://localhost:8000/api/artists/");
        this.artists = response.data;
      } catch (error) {
        console.error("Error fetching artists:", error);
      }
    },
    async fetchAlbums() {
      try {
        const response = await axios.get("http://localhost:8000/api/albums/");
        this.albums = response.data;
      } catch (error) {
        console.error("Error fetching albums:", error);
      }
    },
    submitForm() {
      this.filter({album:this.selectedAlbum, artist:[...this.selectedArtists], name:null})
      this.closeModal();
      // Implement your filter logic here
    },
  },
};
</script>
<style scoped>
.modal-content {
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}
</style>
