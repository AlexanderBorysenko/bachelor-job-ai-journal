import type { MediaFileRef, MediaEditItem } from '../types/message'

export function existingThumbSrc(f: MediaFileRef): string | null {
  if (f.status === 'ready' && f.kind === 'photo') return `/api/media/${f.shortcode}`
  if (f.has_poster) return `/api/media/${f.shortcode}/poster`
  return null
}

export function editItemSrc(it: MediaEditItem): string | null {
  if (it.type === 'existing') return existingThumbSrc(it)
  return it.kind === 'photo' ? it.previewUrl : null
}
