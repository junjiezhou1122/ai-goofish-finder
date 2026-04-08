export type RadarAnnotationStatus = 'watch' | 'test' | 'sourced' | 'risky' | 'drop'
export type RadarSortField =
  | 'opportunity_score'
  | 'recent_items_24h'
  | 'total_items'
  | 'growth_delta'
  | 'signal_hits'
  | 'median_price'
  | 'latest_crawl_time'
  | 'keyword'
export type RadarSortOrder = 'asc' | 'desc'
export type RadarPoolSource = 'manual' | 'radar' | 'recommendation'
export type RadarRecommendationStatus = 'pending' | 'accepted' | 'dismissed'
export type RadarRecommendationVariantType = 'product' | 'service' | 'delivery' | 'generic'

export interface RadarSummary {
  keywords_tracked: number
  total_items: number
  recent_items_24h: number
  high_opportunity_keywords: number
  average_opportunity_score: number
}

export interface RadarSignal {
  term: string
  count: number
}

export interface RadarKeywordItem {
  keyword: string
  total_items: number
  recent_items_24h: number
  previous_items_24h: number
  growth_delta: number
  unique_sellers: number
  recommended_items: number
  ai_recommended_items: number
  min_price: number | null
  median_price: number | null
  avg_price: number | null
  max_price: number | null
  price_spread: number | null
  signal_hits: number
  top_signals: string[]
  opportunity_score: number
  latest_crawl_time: string | null
  annotation_status: RadarAnnotationStatus
  annotation_note: string
  annotation_updated_at: string | null
}

export interface RadarOverview {
  summary: RadarSummary
  top_opportunities: RadarKeywordItem[]
  top_signals: RadarSignal[]
}

export interface RadarKeywordListResponse {
  items: RadarKeywordItem[]
}

export interface RadarKeywordAnnotation {
  keyword: string
  status: RadarAnnotationStatus
  note: string
  updated_at: string | null
}

export interface RadarKeywordAnnotationResponse {
  annotation: RadarKeywordAnnotation
}

export interface RadarPoolItem {
  id: number
  keyword: string
  source: RadarPoolSource
  note: string
  created_at: string | null
  updated_at: string | null
}

export interface RadarPoolListResponse {
  items: RadarPoolItem[]
}

export interface RadarPoolItemResponse {
  item: RadarPoolItem
}

export interface RadarSnapshot {
  id: number
  note: string
  created_at: string | null
  keyword_count: number
  average_score: number
  top_keyword: string | null
}

export interface RadarSnapshotKeyword {
  keyword: string
  opportunity_score: number
  recent_items_24h: number
  total_items: number
  unique_sellers: number
  recommended_items: number
  signal_hits: number
  median_price: number | null
  price_spread: number | null
  latest_crawl_time: string | null
}

export interface RadarSnapshotListResponse {
  items: RadarSnapshot[]
}

export interface RadarSnapshotResponse {
  snapshot: RadarSnapshot
}

export interface RadarSnapshotKeywordListResponse {
  items: RadarSnapshotKeyword[]
}

export interface RadarRecommendation {
  id: number
  keyword: string
  reason: string
  score: number
  signal_terms: string[]
  source_keywords: string[]
  variant_type: RadarRecommendationVariantType
  status: RadarRecommendationStatus
  created_at: string | null
  updated_at: string | null
}

export interface RadarRecommendationListResponse {
  items: RadarRecommendation[]
}

export interface RadarRecommendationResponse {
  item: RadarRecommendation
}
