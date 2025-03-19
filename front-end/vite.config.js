import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import vueDevTools from 'vite-plugin-vue-devtools';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: { // 替换 devServer 为 server
    proxy: { // 直接在 server 下配置 proxy
      '/api': {
        target: 'http://192.168.1.208:9006', // 后端接口地址
        changeOrigin: true, // 允许跨域
        ws: true, // 支持 WebSocket
        rewrite: (path) => path.replace(/^\/api/, ''), // 重写路径，替换 /api 为 ''
      },
    },
  },
});
