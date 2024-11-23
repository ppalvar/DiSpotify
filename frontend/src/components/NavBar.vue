<template>
  <nav class="navbar navbar-expand-lg navbar-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="#">
        <i class="fab fa-spotify me-2"></i>Spotify Clone
      </a>
      <div class="ms-auto">
        <button class="btn btn-outline-light me-2" @click="openAlbumModal">
          Add Album
        </button>
        <button class="btn btn-outline-light me-2" @click="openArtistModal">
          Add Artist
        </button>
        <button class="btn btn-outline-light" @click="openSongModal">
          Add Song
        </button>
      </div>
    </div>
    <AddArtistModal ref="artistModal" />
    <AddAlbumModal ref="albumModal"/>
    <AddSongModal ref="songModal"/>
  </nav>
</template>

<script>
import AddAlbumModal from './AddAlbumModal.vue';
import AddArtistModal from "./AddArtistModal.vue";
import AddSongModal from './AddSongModal.vue';

export default {
  name: "NavBar",
  components: {
    AddArtistModal,
    AddAlbumModal,
    AddSongModal
},
  methods: {
    openArtistModal() {
      this.$refs.artistModal.openModal();
    },
    openAlbumModal() {
      this.$refs.albumModal.openModal();
    },
    openSongModal() {
      this.$refs.songModal.openModal();
    },
  },
};
</script>

<style scoped>
.navbar {
  background-color: #000000;
  z-index: 1000;
}
</style>
