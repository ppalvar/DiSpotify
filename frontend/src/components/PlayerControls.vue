<template>
    <div class="player-controls">
      <div class="control-buttons mb-3">
        <button><i class="fas fa-random"></i></button>
        <button><i class="fas fa-step-backward"></i></button>
        <button class="play-button" @click="playAndPause">
          <i class="fas" :class="isPlaying ? 'fa-pause-circle' : 'fa-play-circle'"></i>
        </button>
        <button><i class="fas fa-step-forward"></i></button>
        <button><i class="fas fa-redo"></i></button>
      </div>
  
      <div class="progress-bar-container d-flex align-items-center container-fluid">
        <span class="text-muted me-2">{{ formattedRemainingTime }}</span>
        <input type="range" class="progress-slider" min="0" max="100" :value="progressBarProgress" @click="moveToTime">
        <span class="text-muted ms-2">{{ formattedTotalDuration }}</span>
      </div>
  
      <div class="volume-control d-flex align-items-center">
        <i class="fas fa-volume-up me-2"></i>
        <input
          type="range"
          class="volume-slider"
          min="0"
          max="100"
          :value="volume"
          @input="setVolume"
        >
      </div>
    </div>
  </template>
  
  <script>
  import { mapState, mapActions } from 'vuex'
  
  export default {
    name: 'PlayerControls',
    computed: {
      ...mapState([
        'isPlaying',
        'formattedRemainingTime',
        'formattedTotalDuration',
        'progressBarProgress',
        'volume'
      ])
    },
    methods: {
      ...mapActions(['playAndPause', 'setVolume', 'moveToTime'])
    }
  }
  </script>
  
  <style scoped>
  .player-controls {
      margin-top: 20px;
      text-align: center;
  }
  
  .control-buttons button {
      background: none;
      border: none;
      color: #b3b3b3;
      font-size: 1.2rem;
      padding: 0 10px;
      margin: 0 5px;
  }
  
  .control-buttons button:hover {
      color: white;
  }
  
  .play-button {
      font-size: 2.5rem !important;
  }
  
  .progress-bar-container {
      margin: 20px 0;
  }
  
  .volume-control {
      margin-top: 20px;
  }
  
  input[type="range"] {
      appearance: none;
      width: 100%;
      height: 4px;
      background: #4f4f4f;
      border-radius: 2px;
      margin: 10px 0;
  }
  
  input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 12px;
      height: 12px;
      background: #ffffff;
      border-radius: 50%;
      cursor: pointer;
  }
  </style>