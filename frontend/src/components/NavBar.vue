<template>
    <nav class="navbar navbar-expand-lg navbar-dark">
      <div class="container-fluid">
        <a class="navbar-brand" href="#">
          <i class="fab fa-spotify me-2"></i>Spotify Clone
        </a>
        <div class="ms-auto">
          <button class="btn btn-outline-light me-2">Login</button>
          <button class="btn btn-light">Logout</button>
        </div>
      </div>
    </nav>
  </template>
  
  <script>
  export default {
    name: 'NavBar'
  }
  </script>
  
  <style scoped>
  .navbar {
      background-color: #000000;
      z-index: 1000;
  }
  </style>