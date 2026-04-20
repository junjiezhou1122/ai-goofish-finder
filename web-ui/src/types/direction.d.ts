export type DirectionVariant = 'product' | 'service' | 'delivery' | 'generic'
export type DirectionRiskLevel = 'low' | 'medium' | 'high'
export type DirectionStatus = 'active' | 'paused' | 'archived'
export type DirectionCandidateSourceType = 'seed' | 'rule' | 'llm'
export type DirectionCandidateLifecycleStatus = 'seed' | 'candidate' | 'validating' | 'validated' | 'rejected' | 'archived'
export type CandidateOpportunityStatus = 'cold' | 'watch' | 'test' | 'hot'
export type CandidateSuggestedAction = 'collect_more' | 'watch' | 'test_now' | 'promote'
export type DirectionRecommendationStatus = 'pending' | 'accepted' | 'dismissed'

export interface Direction {
  id: number
  name: string
  seed_topic: string
  user_goal: string | null
  preferred_variants: DirectionVariant[]
  risk_level: DirectionRiskLevel
  status: DirectionStatus
  created_at: string | null
  updated_at: string | null
}

export interface DirectionCandidate {
  id: number
  direction_id: number
  keyword: string
  source_type: DirectionCandidateSourceType
  source_detail: string | null
  lifecycle_status: DirectionCandidateLifecycleStatus
  variant_type: DirectionVariant
  confidence: number
  created_at: string | null
  updated_at: string | null
  evidence?: DirectionCandidateEvidence
  state?: DirectionCandidateState
}

export interface DirectionCandidateEvidence {
  sample_count: number
  recent_items_24h: number
  previous_items_24h: number
  unique_sellers: number
  recommended_items: number
  ai_recommended_items: number
  median_price: number | null
  price_spread: number | null
  signal_hits: number
  top_signals: string[]
  latest_crawl_time: string | null
  updated_at: string | null
}

export interface DirectionCandidateState {
  heat_score: number
  momentum_score: number
  commercial_score: number
  competition_score: number
  confidence_score: number
  opportunity_score: number
  status: CandidateOpportunityStatus
  suggested_action: CandidateSuggestedAction
  updated_at: string | null
}

export interface DirectionRecommendation {
  id: number
  direction_id: number
  candidate_id: number
  keyword: string
  reason: string
  score: number
  recommended_action: string
  status: DirectionRecommendationStatus
  created_at: string | null
  updated_at: string | null
}

export interface DirectionExperiment {
  id: number
  direction_id: number
  candidate_id: number | null
  recommendation_id: number | null
  task_id: number | null
  task_name: string | null
  keyword: string
  status: 'draft' | 'running' | 'completed' | 'failed' | 'cancelled'
  source: string
  sample_count?: number
  latest_crawl_time?: string | null
  created_at: string | null
  updated_at: string | null
}

export interface DirectionLearningSummary {
  accepted_recommendations: number
  dismissed_recommendations: number
  created_tasks: number
  total_experiments: number
  completed_experiments: number
  running_experiments: number
}

export interface DirectionCreatePayload {
  name: string
  seed_topic: string
  user_goal?: string | null
  preferred_variants?: DirectionVariant[]
  risk_level?: DirectionRiskLevel
  status?: DirectionStatus
}

export type DirectionUpdatePayload = Partial<DirectionCreatePayload>
