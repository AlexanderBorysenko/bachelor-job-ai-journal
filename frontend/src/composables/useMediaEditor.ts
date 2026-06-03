import { ref } from 'vue'
import { uploadMessageMedia, updateMessageMedia } from '../api'
import type { RawMessage, MediaEditItem } from '../types/message'

export function useMediaEditor() {
  const items = ref<MediaEditItem[]>([])
  const saving = ref(false)
  const fileInput = ref<HTMLInputElement | null>(null)

  function itemKey(it: MediaEditItem) {
    return it.type === 'existing' ? it.shortcode : it.previewUrl
  }

  function start(message: RawMessage) {
    items.value = (message.media_files || []).map((f) => ({
      type: 'existing' as const,
      shortcode: f.shortcode,
      kind: f.kind,
      status: f.status,
      has_poster: f.has_poster,
    }))
  }

  function reset() {
    for (const it of items.value) {
      if (it.type === 'new') URL.revokeObjectURL(it.previewUrl)
    }
    items.value = []
  }

  function addFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const isImage = file.type.startsWith('image/')
      const isVideo = file.type.startsWith('video/')
      if (!isImage && !isVideo) continue
      items.value.push({
        type: 'new',
        file,
        kind: isVideo ? 'video' : 'photo',
        previewUrl: URL.createObjectURL(file),
      })
    }
  }

  function onPickFiles(e: Event) {
    const input = e.target as HTMLInputElement
    if (input.files) addFiles(input.files)
    input.value = ''
  }

  function onPaste(e: ClipboardEvent) {
    if (!e.clipboardData) return
    const files = Array.from(e.clipboardData.files)
    if (files.length) {
      e.preventDefault()
      addFiles(files)
    }
  }

  function removeItem(idx: number) {
    const [it] = items.value.splice(idx, 1)
    if (it && it.type === 'new') URL.revokeObjectURL(it.previewUrl)
  }

  async function save(messageId: string) {
    saving.value = true
    try {
      const shortcodes: string[] = []
      for (const it of items.value) {
        if (it.type === 'existing') {
          shortcodes.push(it.shortcode)
        } else {
          const { data } = await uploadMessageMedia(messageId, it.file)
          shortcodes.push(data.shortcode)
        }
      }
      await updateMessageMedia(messageId, shortcodes)
    } finally {
      saving.value = false
    }
  }

  return { items, saving, fileInput, itemKey, start, reset, addFiles, onPickFiles, onPaste, removeItem, save }
}
