import { ref, onMounted, onUnmounted } from 'vue'

type Handler = (data: any) => void

export function useEvents(handlers: Record<string, Handler>) {
  const connected = ref(false)
  let source: EventSource | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connect() {
    const token = localStorage.getItem('access_token')
    if (!token) return

    source = new EventSource(`/api/events?token=${encodeURIComponent(token)}`)

    source.addEventListener('connected', () => {
      connected.value = true
    })

    for (const [event, handler] of Object.entries(handlers)) {
      source.addEventListener(event, (e: MessageEvent) => {
        try {
          handler(JSON.parse(e.data))
        } catch {
          handler(e.data)
        }
      })
    }

    source.onerror = () => {
      connected.value = false
      source?.close()
      source = null
      reconnectTimer = setTimeout(connect, 3000)
    }
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    source?.close()
    source = null
    connected.value = false
  }

  onMounted(connect)
  onUnmounted(disconnect)

  return { connected }
}
