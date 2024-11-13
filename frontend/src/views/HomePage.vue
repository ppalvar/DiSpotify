<template>
  <div class="main-container">
    <CurrentSong />
    <SongsList />
  </div>
</template>

<script>
import CurrentSong from '@/components/CurrentSong.vue'
import SongsList from '@/components/SongsList.vue'

export default {
  name: 'HomePage',
  components: {
    CurrentSong,
    SongsList
  }
}
</script>

<style scoped>
.main-container {
    display: flex;
    flex: 1;
    overflow: hidden;
}
</style>