export interface MediaFileRef {
  shortcode: string
  kind: string
  status: string
  has_poster: boolean
}

export interface RawMessage {
  id: string
  source_type: string
  content: string
  descriptive?: string | null
  media_files?: MediaFileRef[]
  classified_date: string
  created_at: string
}

export type MediaEditItem =
  | { type: 'existing'; shortcode: string; kind: string; status: string; has_poster: boolean }
  | { type: 'new'; file: File; kind: 'photo' | 'video'; previewUrl: string }
