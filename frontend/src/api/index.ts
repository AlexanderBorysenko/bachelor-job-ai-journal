import api from './client'

// Auth
export const authTelegram = (data: Record<string, unknown>) =>
  api.post('/auth/telegram', data)

// Buffer
export const getBuffer = (params?: { date_from?: string; date_to?: string }) =>
  api.get('/buffer', { params })

export const updateMessage = (id: string, body: { content?: string; classified_date?: string }) =>
  api.patch(`/buffer/${id}`, body)

export const deleteMessage = (id: string) =>
  api.delete(`/buffer/${id}`)

export const bake = () =>
  api.post('/buffer/bake')

// Entries
export const getEntries = (params?: { page?: number; per_page?: number; date_from?: string; date_to?: string }) =>
  api.get('/entries', { params })

export const getEntryByDate = (date: string) =>
  api.get(`/entries/by-date/${date}`)

export const getEntry = (id: string) =>
  api.get(`/entries/${id}`)

export const getEntryRaw = (id: string) =>
  api.get(`/entries/${id}/raw`)

export const updateEntry = (id: string, body: { content: string }) =>
  api.patch(`/entries/${id}`, body)

export const deleteEntry = (id: string) =>
  api.delete(`/entries/${id}`)

// Highlights
export const getHighlights = (params?: { category?: string; page?: number; per_page?: number }) =>
  api.get('/highlights', { params })

export const getHighlightCategories = () =>
  api.get('/highlights/categories')

export const createCategory = (body: { name: string; description: string; icon?: string }) =>
  api.post('/highlights/categories', body)

export const getHighlight = (id: string) =>
  api.get(`/highlights/${id}`)

export const deleteHighlight = (id: string) =>
  api.delete(`/highlights/${id}`)
