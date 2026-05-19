import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import ElementPlus from 'unplugin-element-plus/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

const localApiTarget = process.env.VITE_LOCAL_API_TARGET || 'http://127.0.0.1:8086'

export default defineConfig({
  plugins: [
    vue(),
    ElementPlus({}),
    AutoImport({
      dts: 'src/auto-imports.d.ts',
      resolvers: [ElementPlusResolver()]
    }),
    Components({
      dts: 'src/components.d.ts',
      resolvers: [ElementPlusResolver({ importStyle: 'css' })]
    })
  ],
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/@element-plus/icons-vue')) return 'vendor-element-icons'
          if (id.includes('node_modules/vue')) return 'vendor-vue'
          if (id.includes('node_modules/echarts')) return 'vendor-echarts'
          if (id.includes('node_modules/mammoth')) return 'vendor-mammoth'
          if (id.includes('node_modules/pdfjs-dist')) return 'vendor-pdfjs'
          return undefined
        }
      }
    }
  },
  server: {
    proxy: {
      '/api': localApiTarget,
      '/v1': localApiTarget,
      '/health': localApiTarget
    }
  }
})
