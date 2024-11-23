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
          <h5 class="modal-title">Add Song</h5>
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
              <label for="songTitle" class="form-label">Song Title</label>
              <input
                type="text"
                id="songTitle"
                v-model="songTitle"
                class="form-control"
                required
              />
            </div>
            <div class="mb-3">
              <label for="album" class="form-label">Album</label>
              <select
                id="album"
                v-model="selectedAlbum"
                class="form-select"
                required
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
            <div class="mb-3">
              <label for="artists" class="form-label">Artists</label>
              <select
                id="artists"
                v-model="selectedArtists"
                class="form-select"
                multiple
                required
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
              <label for="musicFile" class="form-label">Music File</label>
              <input
                type="file"
                id="musicFile"
                @change="handleFileUpload"
                class="form-control"
                required
              />
            </div>
            <div class="modal-footer">
              <button type="submit" class="btn btn-primary">Submit</button>
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
import { mapActions } from "vuex";
import axios from "axios";

export default {
  name: "AddSongModal",
  data() {
    return {
      songTitle: "",
      selectedAlbum: null,
      selectedArtists: [],
      musicFile: null,
      isVisible: false,
      albums: [],
      artists: [],
    };
  },
  methods: {
    ...mapActions(["refreshSongs"]),

    openModal() {
      this.isVisible = true;
      this.fetchAlbums();
      this.fetchArtists();
    },
    closeModal() {
      this.isVisible = false;
    },
    async fetchAlbums() {
      try {
        const response = await axios.get("http://localhost:8000/api/albums/");
        this.albums = response.data;
      } catch (error) {
        console.error("Error fetching albums:", error);
      }
    },
    async fetchArtists() {
      try {
        const response = await axios.get("http://localhost:8000/api/artists/");
        this.artists = response.data;
      } catch (error) {
        console.error("Error fetching artists:", error);
      }
    },
    handleFileUpload(event) {
      this.musicFile = event.target.files[0];
    },
    async submitForm() {
      if (!this.musicFile) {
        console.error("No music file selected");
        return;
      }

      try {
        const fileBase64 = await this.convertFileToBase64(this.musicFile);
        const response = await axios.post("http://localhost:8000/api/songs/", {
          title: this.songTitle,
          album: this.selectedAlbum,
          artist: this.selectedArtists,
          file_base64: fileBase64,
        });
        console.log("Song added successfully:", response.data);
        this.closeModal();
        this.refreshSongs();
      } catch (error) {
        console.error("Error adding song:", error);
      }
    },
    convertFileToBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onerror = (error) => reject(error);
        reader.readAsDataURL(file);
      });
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
