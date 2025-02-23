<template>
  <div class="current-song-area">
    <div class="current-song-info">
      <img src="https://placehold.co/250x250?text=⚜" alt="Current song" />
      <h4 class="mb-1">{{ currentSong.name }}</h4>
      <p class="text-muted mb-3">
        {{ currentSong.artist }} - {{ currentSong.album }}
      </p>
    </div>
    <PlayerControls />
  </div>
</template>

<script>
import PlayerControls from "./PlayerControls.vue";
import { mapState } from "vuex";

export default {
  name: "CurrentSong",
  components: {
    PlayerControls,
  },
  computed: {
    ...mapState(["currentSong"]),
  },
};
</script>

<style scoped>
.current-song-area {
  width: 33.333%;
  background-color: #181818;
  padding: 20px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #282828;
}

.current-song-info {
  text-align: center;
  padding: 20px;
}

.current-song-info img {
  width: 250px;
  height: 250px;
  object-fit: cover;
  margin-bottom: 20px;
  box-shadow: 0 4px 60px rgba(0, 0, 0, 0.5);
}
</style>
