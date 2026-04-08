import { computed, ref } from 'vue'
import * as radarApi from '@/api/radar'
import * as taskApi from '@/api/tasks'
import type { Task } from '@/types/task.d.ts'
import type {
  RadarAnnotationStatus,
  RadarKeywordItem,
  RadarOverview,
  RadarPoolItem,
  RadarRecommendation,
  RadarRecommendationStatus,
  RadarRecommendationVariantType,
  RadarSnapshot,
  RadarSnapshotKeyword,
  RadarSortField,
  RadarSortOrder,
} from '@/types/radar.d.ts'

export function useRadar() {
  const overview = ref<RadarOverview | null>(null)
  const keywords = ref<RadarKeywordItem[]>([])
  const pool = ref<RadarPoolItem[]>([])
  const snapshots = ref<RadarSnapshot[]>([])
  const snapshotKeywords = ref<RadarSnapshotKeyword[]>([])
  const recommendations = ref<RadarRecommendation[]>([])
  const tasks = ref<Task[]>([])
  const selectedSnapshot = ref<RadarSnapshot | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<Error | null>(null)
  const sortBy = ref<RadarSortField>('opportunity_score')
  const sortOrder = ref<RadarSortOrder>('desc')
  const recommendationMinScore = ref(60)
  const recommendationVariantTypes = ref<RadarRecommendationVariantType[]>(['product', 'service', 'delivery'])

  async function fetchRecommendationsOnly() {
    const recommendationResponse = await radarApi.getRadarRecommendations(20, {
      minScore: recommendationMinScore.value,
      variantTypes: recommendationVariantTypes.value,
    })
    recommendations.value = recommendationResponse.items
  }

  async function fetchRadar() {
    isLoading.value = true
    error.value = null
    try {
      const [overviewResponse, keywordResponse, poolResponse, snapshotResponse, recommendationResponse, taskResponse] = await Promise.all([
        radarApi.getRadarOverview(),
        radarApi.getRadarKeywords(50, { sortBy: sortBy.value, sortOrder: sortOrder.value }),
        radarApi.getRadarKeywordPool(),
        radarApi.getRadarSnapshots(),
        radarApi.getRadarRecommendations(20, {
          minScore: recommendationMinScore.value,
          variantTypes: recommendationVariantTypes.value,
        }),
        taskApi.getAllTasks(),
      ])
      overview.value = overviewResponse
      keywords.value = keywordResponse.items
      pool.value = poolResponse.items
      snapshots.value = snapshotResponse.items
      recommendations.value = recommendationResponse.items
      tasks.value = taskResponse
      const firstSnapshot = snapshotResponse.items[0] ?? null
      selectedSnapshot.value = firstSnapshot
      snapshotKeywords.value = firstSnapshot
        ? (await radarApi.getRadarSnapshotKeywords(firstSnapshot.id)).items
        : []
    } catch (e) {
      if (e instanceof Error) error.value = e
    } finally {
      isLoading.value = false
    }
  }

  async function refreshKeywords() {
    const keywordResponse = await radarApi.getRadarKeywords(50, { sortBy: sortBy.value, sortOrder: sortOrder.value })
    keywords.value = keywordResponse.items
  }

  async function refreshTasksOnly() {
    tasks.value = await taskApi.getAllTasks()
  }

  async function saveAnnotation(keyword: string, status: RadarAnnotationStatus, note: string) {
    isSaving.value = true
    error.value = null
    try {
      const response = await radarApi.updateRadarKeywordAnnotation(keyword, { status, note })
      const updated = response.annotation
      const applyUpdate = (item: RadarKeywordItem) => {
        if (item.keyword !== updated.keyword) return item
        return {
          ...item,
          annotation_status: updated.status,
          annotation_note: updated.note,
          annotation_updated_at: updated.updated_at,
        }
      }
      keywords.value = keywords.value.map(applyUpdate)
      if (overview.value) {
        overview.value = {
          ...overview.value,
          top_opportunities: overview.value.top_opportunities.map(applyUpdate),
        }
      }
      return updated
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function setSorting(nextSortBy: RadarSortField, nextSortOrder: RadarSortOrder) {
    isLoading.value = true
    error.value = null
    sortBy.value = nextSortBy
    sortOrder.value = nextSortOrder
    try {
      await refreshKeywords()
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function createPoolItem(keyword: string, note = '', source: 'manual' | 'radar' | 'recommendation' = 'manual') {
    isSaving.value = true
    error.value = null
    try {
      const response = await radarApi.createRadarKeywordPoolItem({ keyword, note, source })
      pool.value = [response.item, ...pool.value.filter((item) => item.keyword !== response.item.keyword)]
      return response.item
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function updatePoolItem(itemId: number, payload: { keyword?: string; note?: string }) {
    isSaving.value = true
    error.value = null
    try {
      const response = await radarApi.updateRadarKeywordPoolItem(itemId, payload)
      pool.value = pool.value.map((item) => (item.id === itemId ? response.item : item))
      return response.item
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function deletePoolItem(itemId: number) {
    isSaving.value = true
    error.value = null
    try {
      await radarApi.deleteRadarKeywordPoolItem(itemId)
      pool.value = pool.value.filter((item) => item.id !== itemId)
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function captureSnapshot(note = '') {
    isSaving.value = true
    error.value = null
    try {
      const response = await radarApi.createRadarSnapshot(note)
      snapshots.value = [response.snapshot, ...snapshots.value.filter((item) => item.id !== response.snapshot.id)]
      selectedSnapshot.value = response.snapshot
      snapshotKeywords.value = (await radarApi.getRadarSnapshotKeywords(response.snapshot.id)).items
      return response.snapshot
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function selectSnapshot(snapshotId: number) {
    isLoading.value = true
    error.value = null
    try {
      const snapshotResponse = await radarApi.getRadarSnapshot(snapshotId)
      const keywordsResponse = await radarApi.getRadarSnapshotKeywords(snapshotId)
      selectedSnapshot.value = snapshotResponse.snapshot
      snapshotKeywords.value = keywordsResponse.items
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function refreshRecommendations() {
    isSaving.value = true
    error.value = null
    try {
      const response = await radarApi.refreshRadarRecommendations(20, {
        minScore: recommendationMinScore.value,
        variantTypes: recommendationVariantTypes.value,
      })
      recommendations.value = response.items
      return response.items
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function applyRecommendationStrategy(
    minScore: number,
    variantTypes: RadarRecommendationVariantType[],
  ) {
    isLoading.value = true
    error.value = null
    recommendationMinScore.value = minScore
    recommendationVariantTypes.value = variantTypes
    try {
      await fetchRecommendationsOnly()
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateRecommendation(
    recommendationId: number,
    status: RadarRecommendationStatus,
    addToPool = false,
  ) {
    isSaving.value = true
    error.value = null
    try {
      const response = await radarApi.updateRadarRecommendation(recommendationId, {
        status,
        add_to_pool: addToPool,
      })
      recommendations.value = recommendations.value.map((item) =>
        item.id === recommendationId ? response.item : item,
      )
      if (status === 'accepted' && addToPool) {
        await fetchPoolOnly()
      }
      await refreshTasksOnly()
      return response.item
    } catch (e) {
      if (e instanceof Error) {
        error.value = e
        throw e
      }
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function fetchPoolOnly() {
    const poolResponse = await radarApi.getRadarKeywordPool()
    pool.value = poolResponse.items
  }

  const normalizedKeywordTaskMap = computed(() => {
    const map = new Map<string, Task>()
    tasks.value.forEach((task) => {
      const normalizedKeyword = task.keyword.trim().toLowerCase()
      if (!normalizedKeyword || map.has(normalizedKeyword)) return
      map.set(normalizedKeyword, task)
    })
    return map
  })

  function findTaskByKeyword(keyword: string) {
    return normalizedKeywordTaskMap.value.get(keyword.trim().toLowerCase()) ?? null
  }

  const summary = computed(() => overview.value?.summary ?? {
    keywords_tracked: 0,
    total_items: 0,
    recent_items_24h: 0,
    high_opportunity_keywords: 0,
    average_opportunity_score: 0,
  })

  const topOpportunities = computed(() => overview.value?.top_opportunities ?? [])
  const topSignals = computed(() => overview.value?.top_signals ?? [])

  fetchRadar()

  return {
    overview,
    keywords,
    pool,
    snapshots,
    snapshotKeywords,
    recommendations,
    tasks,
    selectedSnapshot,
    summary,
    topOpportunities,
    topSignals,
    isLoading,
    isSaving,
    error,
    sortBy,
    sortOrder,
    recommendationMinScore,
    recommendationVariantTypes,
    fetchRadar,
    saveAnnotation,
    setSorting,
    createPoolItem,
    updatePoolItem,
    deletePoolItem,
    captureSnapshot,
    selectSnapshot,
    refreshRecommendations,
    applyRecommendationStrategy,
    updateRecommendation,
    findTaskByKeyword,
  }
}
