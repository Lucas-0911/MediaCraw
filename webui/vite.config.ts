import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import type { IncomingMessage } from 'http'
import type { Socket } from 'net'

function isBenignProxyError(err: NodeJS.ErrnoException) {
  return err.code === 'ECONNRESET' || err.code === 'ECONNREFUSED' || err.code === 'EPIPE'
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: '../api/webui',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api/ws': {
        target: 'ws://127.0.0.1:8080',
        changeOrigin: true,
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (err: NodeJS.ErrnoException) => {
            if (isBenignProxyError(err)) return
            console.error('[vite] ws proxy error:', err)
          })
          proxy.on(
            'proxyReqWs',
            (_proxyReq: IncomingMessage, _req: IncomingMessage, socket: Socket) => {
              socket.on('error', (err: NodeJS.ErrnoException) => {
                if (isBenignProxyError(err)) return
                console.error('[vite] ws proxy socket error:', err)
              })
            },
          )
        },
      },
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err: NodeJS.ErrnoException) => {
            if (isBenignProxyError(err)) return
            console.error('[vite] api proxy error:', err)
          })
        },
      },
    },
  },
})
