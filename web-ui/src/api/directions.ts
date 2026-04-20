import { http } from '@/lib/http'
import type { Direction, DirectionCandidate, DirectionCreatePayload, DirectionExperiment, DirectionLearningSummary, DirectionRecommendation, DirectionUpdatePayload } from '@/types/direction.d.ts'

export async function getDirections(): Promise<Direction[]> {
  return await http('/api/finder/directions')
}

export async function createDirection(payload: DirectionCreatePayload): Promise<Direction> {
  const result = await http('/api/finder/directions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return result.direction
}

export async function updateDirection(directionId: number, payload: DirectionUpdatePayload): Promise<Direction> {
  const result = await http(`/api/finder/directions/${directionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return result.direction
}

export async function deleteDirection(directionId: number): Promise<void> {
  await http(`/api/finder/directions/${directionId}`, {
    method: 'DELETE',
  })
}

export async function getDirectionCandidates(directionId: number): Promise<DirectionCandidate[]> {
  const result = await http(`/api/finder/directions/${directionId}/candidates`)
  return result.items
}

export async function generateDirectionCandidates(directionId: number): Promise<DirectionCandidate[]> {
  const result = await http(`/api/finder/directions/${directionId}/generate-candidates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      include_llm: true,
      max_llm_candidates: 12,
    }),
  })
  return result.items
}

export async function refreshDirectionCandidates(directionId: number): Promise<DirectionCandidate[]> {
  const result = await http(`/api/finder/directions/${directionId}/refresh-candidates`, {
    method: 'POST',
  })
  return result.items
}

export async function getDirectionRecommendations(directionId: number): Promise<DirectionRecommendation[]> {
  const result = await http(`/api/finder/directions/${directionId}/recommendations`)
  return result.items
}

export async function refreshDirectionRecommendations(directionId: number): Promise<DirectionRecommendation[]> {
  const result = await http(`/api/finder/directions/${directionId}/refresh-recommendations`, {
    method: 'POST',
  })
  return result.items
}

export async function generateDirectionRecommendations(directionId: number): Promise<DirectionRecommendation[]> {
  const result = await http(`/api/finder/directions/${directionId}/generate-recommendations`, {
    method: 'POST',
  })
  return result.items
}

export async function updateDirectionRecommendation(
  recommendationId: number,
  status: 'pending' | 'accepted' | 'dismissed',
): Promise<DirectionRecommendation> {
  const result = await http(`/api/finder/recommendations/${recommendationId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
  return result.item
}

export async function getDirectionExperiments(directionId: number): Promise<DirectionExperiment[]> {
  const result = await http(`/api/finder/directions/${directionId}/experiments`)
  return result.items
}

export async function getDirectionLearningSummary(directionId: number): Promise<DirectionLearningSummary> {
  const result = await http(`/api/finder/directions/${directionId}/learning-summary`)
  return result.summary
}
