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
          <h5 class="modal-title">Add Album</h5>
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
              <label for="albumName" class="form-label">Album Name</label>
              <input
                type="text"
                id="albumName"
                v-model="albumName"
                class="form-control"
                required
              />
            </div>
            <div class="mb-3">
              <label for="albumAuthor" class="form-label">Author</label>
              <select
                id="albumAuthor"
                v-model="selectedAuthor"
                class="form-select"
                required
              >
                <option
                  v-for="author in authors"
                  :key="author.id"
                  :value="author.id"
                >
                  {{ author.name }}
                </option>
              </select>
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
import axios from "axios";

export default {
  name: "AddAlbumModal",
  data() {
    return {
      albumName: "",
      selectedAuthor: null,
      isVisible: false,
      authors: [],
    };
  },
  methods: {
    openModal() {
      this.isVisible = true;
      this.fetchAuthors();
    },
    closeModal() {
      this.isVisible = false;
    },
    async fetchAuthors() {
      try {
        const response = await axios.get("http://localhost:8000/api/artists/");
        this.authors = response.data;
      } catch (error) {
        console.error("Error fetching authors:", error);
      }
    },
    async submitForm() {
      try {
        const response = await axios.post("http://localhost:8000/api/albums/", {
          name: this.albumName,
          date: new Date().toISOString().split("T")[0], // Assuming you want to use the current date
          author: this.selectedAuthor,
        });
        console.log("Album added successfully:", response.data);
        this.closeModal();
      } catch (error) {
        console.error("Error adding album:", error);
      }
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
