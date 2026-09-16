import { useEffect, useRef } from 'react'
import { useCrawlerStore } from '@/store/crawlerStore'
import type { LogEntry } from '@/types/crawler'

let globalWs: WebSocket | null = null
let globalReconnectTimer: ReturnType<typeof setTimeout> | null = null
let globalCloseTimer: ReturnType<typeof setTimeout> | null = null
let connectionCount = 0
let intentionalClose = false

function clearTimer(timer: ReturnType<typeof setTimeout> | null) {
  if (timer) clearTimeout(timer)
  return null
}

function connect(addLog: (log: LogEntry) => void) {
  if (intentionalClose) return

  globalReconnectTimer = clearTimer(globalReconnectTimer)

  if (
    globalWs &&
    (globalWs.readyState === WebSocket.OPEN ||
      globalWs.readyState === WebSocket.CONNECTING)
  ) {
    return
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/ws/logs`
  const ws = new WebSocket(wsUrl)
  globalWs = ws

  ws.onopen = () => {
    if (globalWs !== ws) return
  }

  ws.onmessage = (event) => {
    if (globalWs !== ws) return
    if (event.data === 'ping') {
      if (ws.readyState === WebSocket.OPEN) ws.send('pong')
      return
    }
    if (event.data === 'pong') return

    try {
      const log: LogEntry = JSON.parse(event.data)
      if (log.id && log.message) {
        addLog(log)
      }
    } catch {
      // Ignore non-JSON frames (proxy/HMR noise)
    }
  }

  ws.onclose = () => {
    if (globalWs !== ws) return
    globalWs = null
    if (!intentionalClose && connectionCount > 0) {
      globalReconnectTimer = setTimeout(() => connect(addLog), 2000)
    }
  }

  // onerror always precedes onclose; avoid console.error spam
  ws.onerror = () => undefined
}

export function useLogWebSocket() {
  const addLog = useCrawlerStore((state) => state.addLog)
  const addLogRef = useRef(addLog)

  useEffect(() => {
    addLogRef.current = addLog
  }, [addLog])

  useEffect(() => {
    connectionCount++
    intentionalClose = false
    globalCloseTimer = clearTimer(globalCloseTimer)
    connect((log) => addLogRef.current(log))

    const heartbeat = setInterval(() => {
      if (globalWs && globalWs.readyState === WebSocket.OPEN) {
        globalWs.send('ping')
      }
    }, 25000)

    return () => {
      connectionCount--
      clearInterval(heartbeat)

      if (connectionCount > 0) return

      // Delay close so React Strict Mode remount does not drop the socket
      globalCloseTimer = setTimeout(() => {
        if (connectionCount > 0) return
        intentionalClose = true
        globalReconnectTimer = clearTimer(globalReconnectTimer)
        if (globalWs) {
          const ws = globalWs
          globalWs = null
          ws.close(1000, 'unmount')
        }
      }, 150)
    }
  }, [])

  return { ws: globalWs }
}
