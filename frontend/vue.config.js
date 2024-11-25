const { defineConfig } = require('@vue/cli-service');

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    host: '0.0.0.0', // Escuchar en todas las interfaces de red
    port: 8080, // Puerto en el que el servidor estará escuchando
    watchFiles: {
      paths: ['src/**/*', 'public/**/*'], // Rutas a observar
      options: {
        usePolling: true, // Usa polling para observar cambios
      },
    },
  },
});