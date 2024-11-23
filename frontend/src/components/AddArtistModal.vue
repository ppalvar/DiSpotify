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
          <h5 class="modal-title">Add Artist</h5>
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
              <label for="artistName" class="form-label">Artist Name</label>
              <input
                type="text"
                id="artistName"
                v-model="artistName"
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
import axios from "axios";

export default {
  name: "AddArtistModal",
  data() {
    return {
      artistName: "",
      isVisible: false,
    };
  },
  methods: {
    openModal() {
      this.isVisible = true;
    },
    closeModal() {
      this.isVisible = false;
    },
    async submitForm() {
      try {
        const response = await axios.post(
          "http://localhost:8000/api/artists/",
          {
            name: this.artistName,
          }
        );
        console.log("Artist added successfully:", response.data);
        this.closeModal();
      } catch (error) {
        console.error("Error adding artist:", error);
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
