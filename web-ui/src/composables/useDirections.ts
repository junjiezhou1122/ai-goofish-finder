import { computed, ref } from 'vue'
import * as directionsApi from '@/api/directions'
import type {
  Direction,
  DirectionCandidate,
  DirectionCreatePayload,
  DirectionExperiment,
  DirectionLearningSummary,
  DirectionRecommendation,
  DirectionStatus,
  DirectionUpdatePayload,
  DirectionVariant,
} from '@/types/direction.d.ts'

export function useDirections() {
  const directions = ref<Direction[]>([])
  const candidatesByDirection = ref<Record<number, DirectionCandidate[]>>({})
  const recommendationsByDirection = ref<Record<number, DirectionRecommendation[]>>({})
  const experimentsByDirection = ref<Record<number, DirectionExperiment[]>>({})
  const learningSummaryByDirection = ref<Record<number, DirectionLearningSummary>>({})
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<Error | null>(null)

  const activeCount = computed(() => directions.value.filter((item) => item.status === 'active').length)
  const pausedCount = computed(() => directions.value.filter((item) => item.status === 'paused').length)
  const archivedCount = computed(() => directions.value.filter((item) => item.status === 'archived').length)

  async function fetchDirections() {
    isLoading.value = true
    error.value = null
    try {
      directions.value = await directionsApi.getDirections()
      const candidateEntries = await Promise.all(
        directions.value.map(async (direction) => [
          direction.id,
          await directionsApi.getDirectionCandidates(direction.id),
        ] as const),
      )
      const recommendationEntries = await Promise.all(
        directions.value.map(async (direction) => [
          direction.id,
          await directionsApi.getDirectionRecommendations(direction.id),
        ] as const),
      )
      const experimentEntries = await Promise.all(
        directions.value.map(async (direction) => [
          direction.id,
          await directionsApi.getDirectionExperiments(direction.id),
        ] as const),
      )
      const summaryEntries = await Promise.all(
        directions.value.map(async (direction) => [
          direction.id,
          await directionsApi.getDirectionLearningSummary(direction.id),
        ] as const),
      )
      candidatesByDirection.value = Object.fromEntries(candidateEntries)
      recommendationsByDirection.value = Object.fromEntries(recommendationEntries)
      experimentsByDirection.value = Object.fromEntries(experimentEntries)
      learningSummaryByDirection.value = Object.fromEntries(summaryEntries)
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function createDirection(payload: DirectionCreatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const created = await directionsApi.createDirection(payload)
      directions.value = [created, ...directions.value.filter((item) => item.id !== created.id)]
      return created
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function updateDirection(directionId: number, payload: DirectionUpdatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await directionsApi.updateDirection(directionId, payload)
      directions.value = directions.value.map((item) => (item.id === directionId ? updated : item))
      return updated
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function deleteDirection(directionId: number) {
    isSaving.value = true
    error.value = null
    try {
      await directionsApi.deleteDirection(directionId)
      directions.value = directions.value.filter((item) => item.id !== directionId)
      const next = { ...candidatesByDirection.value }
      delete next[directionId]
      candidatesByDirection.value = next
      const nextRecommendations = { ...recommendationsByDirection.value }
      delete nextRecommendations[directionId]
      recommendationsByDirection.value = nextRecommendations
      const nextExperiments = { ...experimentsByDirection.value }
      delete nextExperiments[directionId]
      experimentsByDirection.value = nextExperiments
      const nextSummaries = { ...learningSummaryByDirection.value }
      delete nextSummaries[directionId]
      learningSummaryByDirection.value = nextSummaries
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function updateDirectionStatus(directionId: number, status: DirectionStatus) {
    return await updateDirection(directionId, { status })
  }

  async function fetchDirectionCandidates(directionId: number) {
    error.value = null
    try {
      const items = await directionsApi.getDirectionCandidates(directionId)
      candidatesByDirection.value = {
        ...candidatesByDirection.value,
        [directionId]: items,
      }
      return items
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    }
  }

  async function generateCandidates(directionId: number) {
    isSaving.value = true
    error.value = null
    try {
      const items = await directionsApi.generateDirectionCandidates(directionId)
      candidatesByDirection.value = {
        ...candidatesByDirection.value,
        [directionId]: items,
      }
      recommendationsByDirection.value = {
        ...recommendationsByDirection.value,
        [directionId]: [],
      }
      return items
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function refreshCandidates(directionId: number) {
    isSaving.value = true
    error.value = null
    try {
      const items = await directionsApi.refreshDirectionCandidates(directionId)
      candidatesByDirection.value = {
        ...candidatesByDirection.value,
        [directionId]: items,
      }
      return items
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function fetchRecommendations(directionId: number) {
    error.value = null
    try {
      const items = await directionsApi.getDirectionRecommendations(directionId)
      recommendationsByDirection.value = {
        ...recommendationsByDirection.value,
        [directionId]: items,
      }
      return items
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    }
  }

  async function fetchExperiments(directionId: number) {
    error.value = null
    try {
      const items = await directionsApi.getDirectionExperiments(directionId)
      experimentsByDirection.value = {
        ...experimentsByDirection.value,
        [directionId]: items,
      }
      return items
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    }
  }

  async function fetchLearningSummary(directionId: number) {
    error.value = null
    try {
      const summary = await directionsApi.getDirectionLearningSummary(directionId)
      learningSummaryByDirection.value = {
        ...learningSummaryByDirection.value,
        [directionId]: summary,
      }
      return summary
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    }
  }

  async function refreshRecommendations(directionId: number) {
    isSaving.value = true
    error.value = null
    try {
      const items = await directionsApi.refreshDirectionRecommendations(directionId)
      recommendationsByDirection.value = {
        ...recommendationsByDirection.value,
        [directionId]: items,
      }
      return items
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function generateRecommendations(directionId: number) {
    isSaving.value = true
    error.value = null
    try {
      const items = await directionsApi.generateDirectionRecommendations(directionId)
      recommendationsByDirection.value = {
        ...recommendationsByDirection.value,
        [directionId]: items,
      }
      return items
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSaving.value = false
    }
  }

  async function updateRecommendationStatus(
    directionId: number,
    recommendationId: number,
    status: 'pending' | 'accepted' | 'dismissed',
  ) {
    isSaving.value = true
    error.value = null
    try {
      const item = await directionsApi.updateDirectionRecommendation(recommendationId, status)
      recommendationsByDirection.value = {
        ...recommendationsByDirection.value,
        [directionId]: (recommendationsByDirection.value[directionId] || []).map((current) =>
          current.id === recommendationId ? item : current,
        ),
      }
      await fetchExperiments(directionId).catch(() => undefined)
      await fetchLearningSummary(directionId).catch(() => undefined)
      return item
    } catch (e) {
      if (e instanceof Error) error.value = e
      throw e
    } finally {
      isSaving.value = false
    }
  }

  function buildDefaultPayload(seedTopic = ''): DirectionCreatePayload {
    return {
      name: seedTopic ? `${seedTopic} 方向` : '',
      seed_topic: seedTopic,
      user_goal: '',
      preferred_variants: ['product', 'service', 'delivery'] satisfies DirectionVariant[],
      risk_level: 'medium',
      status: 'active',
    }
  }

  return {
    directions,
    candidatesByDirection,
    recommendationsByDirection,
    experimentsByDirection,
    learningSummaryByDirection,
    isLoading,
    isSaving,
    error,
    activeCount,
    pausedCount,
    archivedCount,
    fetchDirections,
    createDirection,
    updateDirection,
    updateDirectionStatus,
    deleteDirection,
    fetchDirectionCandidates,
    generateCandidates,
    refreshCandidates,
    fetchRecommendations,
    fetchExperiments,
    fetchLearningSummary,
    refreshRecommendations,
    generateRecommendations,
    updateRecommendationStatus,
    buildDefaultPayload,
  }
}
