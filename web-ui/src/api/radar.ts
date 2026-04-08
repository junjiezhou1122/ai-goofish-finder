import { http } from '@/lib/http'
import type {
  RadarOverview,
  RadarKeywordListResponse,
  RadarKeywordAnnotationResponse,
  RadarAnnotationStatus,
  RadarSortField,
  RadarSortOrder,
  RadarPoolListResponse,
  RadarPoolItemResponse,
  RadarPoolSource,
  RadarSnapshotListResponse,
  RadarSnapshotResponse,
  RadarSnapshotKeywordListResponse,
  RadarRecommendationListResponse,
  RadarRecommendationResponse,
  RadarRecommendationStatus,
  RadarRecommendationVariantType,
} from '@/types/radar.d.ts'

export async function getRadarOverview(limit = 12): Promise<RadarOverview> {
  return await http('/api/radar/overview', { params: { limit } })
}

export async function getRadarKeywords(
  limit = 50,
  options: { sortBy?: RadarSortField; sortOrder?: RadarSortOrder } = {},
): Promise<RadarKeywordListResponse> {
  return await http('/api/radar/keywords', {
    params: {
      limit,
      sort_by: options.sortBy,
      sort_order: options.sortOrder,
    },
  })
}

export async function updateRadarKeywordAnnotation(
  keyword: string,
  payload: { status: RadarAnnotationStatus; note: string },
): Promise<RadarKeywordAnnotationResponse> {
  return await http(`/api/radar/keywords/${encodeURIComponent(keyword)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function getRadarKeywordPool(): Promise<RadarPoolListResponse> {
  return await http('/api/radar/pool')
}

export async function createRadarKeywordPoolItem(payload: {
  keyword: string
  source?: RadarPoolSource
  note?: string
}): Promise<RadarPoolItemResponse> {
  return await http('/api/radar/pool', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateRadarKeywordPoolItem(
  itemId: number,
  payload: { keyword?: string; source?: RadarPoolSource; note?: string },
): Promise<RadarPoolItemResponse> {
  return await http(`/api/radar/pool/${itemId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function deleteRadarKeywordPoolItem(itemId: number): Promise<{ deleted: boolean; id: number }> {
  return await http(`/api/radar/pool/${itemId}`, {
    method: 'DELETE',
  })
}

export async function getRadarSnapshots(limit = 10): Promise<RadarSnapshotListResponse> {
  return await http('/api/radar/snapshots', { params: { limit } })
}

export async function createRadarSnapshot(note = ''): Promise<RadarSnapshotResponse> {
  return await http('/api/radar/snapshots', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note }),
  })
}

export async function getRadarSnapshot(snapshotId: number): Promise<RadarSnapshotResponse> {
  return await http(`/api/radar/snapshots/${snapshotId}`)
}

export async function getRadarSnapshotKeywords(
  snapshotId: number,
  limit = 50,
): Promise<RadarSnapshotKeywordListResponse> {
  return await http(`/api/radar/snapshots/${snapshotId}/keywords`, {
    params: { limit },
  })
}

export async function getRadarRecommendations(
  limit = 20,
  options: { minScore?: number; variantTypes?: RadarRecommendationVariantType[] } = {},
): Promise<RadarRecommendationListResponse> {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (options.minScore !== undefined) params.set('min_score', String(options.minScore))
  ;(options.variantTypes ?? []).forEach((item) => params.append('variant_type', item))
  return await http(`/api/radar/recommendations?${params.toString()}`)
}

export async function refreshRadarRecommendations(
  limit = 20,
  options: { minScore?: number; variantTypes?: RadarRecommendationVariantType[] } = {},
): Promise<RadarRecommendationListResponse> {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (options.minScore !== undefined) params.set('min_score', String(options.minScore))
  ;(options.variantTypes ?? []).forEach((item) => params.append('variant_type', item))
  return await http(`/api/radar/recommendations/refresh?${params.toString()}`, {
    method: 'POST',
  })
}

export async function updateRadarRecommendation(
  recommendationId: number,
  payload: { status: RadarRecommendationStatus; add_to_pool?: boolean },
): Promise<RadarRecommendationResponse> {
  return await http(`/api/radar/recommendations/${recommendationId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
