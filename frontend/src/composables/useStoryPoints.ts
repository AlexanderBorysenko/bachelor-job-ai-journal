import { ref } from 'vue'
import {
  getStoryTimeline,
  getEntryStoryPoints,
  createStoryPoint,
  updateStoryPoint,
  reorderStoryPoints,
  deleteStoryPoint,
} from '../api'

export interface StoryPoint {
  id: string
  entry_id: string
  date: string
  title: string
  order: number
  source: string
}

export interface TimelineGroup {
  date: string
  entry_id: string
  points: { id: string; title: string; order: number }[]
}

// Module-level singletons so the rail and the editor share one source of truth.
const timeline = ref<TimelineGroup[]>([])
const loading = ref(false)

export function useStoryPoints() {
  async function loadTimeline() {
    loading.value = true
    try {
      const { data } = await getStoryTimeline()
      timeline.value = data.groups
    } finally {
      loading.value = false
    }
  }

  async function loadForEntry(entryId: string): Promise<StoryPoint[]> {
    const { data } = await getEntryStoryPoints(entryId)
    return data.items
  }

  async function addPoint(entryId: string, title: string): Promise<StoryPoint> {
    const { data } = await createStoryPoint(entryId, title)
    await loadTimeline()
    return data
  }

  async function renamePoint(id: string, title: string): Promise<StoryPoint> {
    const { data } = await updateStoryPoint(id, title)
    await loadTimeline()
    return data
  }

  async function reorder(entryId: string, orderedIds: string[]): Promise<StoryPoint[]> {
    const { data } = await reorderStoryPoints(entryId, orderedIds)
    await loadTimeline()
    return data.items
  }

  async function removePoint(id: string): Promise<void> {
    await deleteStoryPoint(id)
    await loadTimeline()
  }

  // Future AI-generation seam: a generateWithAI(entryId) method lands here and
  // calls a future backend endpoint, then refreshes — no component change needed.

  return { timeline, loading, loadTimeline, loadForEntry, addPoint, renamePoint, reorder, removePoint }
}
