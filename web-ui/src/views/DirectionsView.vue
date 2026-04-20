<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Compass, Lightbulb, RefreshCw, Rocket, Sparkles, TrendingUp, Trash2 } from 'lucide-vue-next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Badge from '@/components/ui/badge/Badge.vue'
import { formatRelativeTimeFromNow } from '@/i18n'
import { useDirections } from '@/composables/useDirections'
import type { Direction, DirectionRiskLevel, DirectionStatus, DirectionVariant } from '@/types/direction.d.ts'

const { t } = useI18n()
const router = useRouter()
const {
  directions,
  candidatesByDirection,
  experimentsByDirection,
  learningSummaryByDirection,
  recommendationsByDirection,
  isLoading,
  isSaving,
  error,
  activeCount,
  pausedCount,
  archivedCount,
  fetchDirections,
  createDirection,
  updateDirectionStatus,
  deleteDirection,
  generateCandidates,
  refreshCandidates,
  refreshRecommendations,
  updateRecommendationStatus,
  buildDefaultPayload,
} = useDirections()

const form = reactive(buildDefaultPayload())

const variantOptions: Array<{ value: DirectionVariant; labelKey: string }> = [
  { value: 'product', labelKey: 'directions.variants.product' },
  { value: 'service', labelKey: 'directions.variants.service' },
  { value: 'delivery', labelKey: 'directions.variants.delivery' },
  { value: 'generic', labelKey: 'directions.variants.generic' },
]

const riskOptions: Array<{ value: DirectionRiskLevel; labelKey: string }> = [
  { value: 'low', labelKey: 'directions.risk.low' },
  { value: 'medium', labelKey: 'directions.risk.medium' },
  { value: 'high', labelKey: 'directions.risk.high' },
]

const statCards = computed(() => [
  { label: t('directions.stats.total'), value: directions.value.length, icon: Compass },
  { label: t('directions.stats.active'), value: activeCount.value, icon: Rocket },
  { label: t('directions.stats.paused'), value: pausedCount.value, icon: RefreshCw },
  { label: t('directions.stats.archived'), value: archivedCount.value, icon: Lightbulb },
])

function toggleVariant(variant: DirectionVariant, checked: boolean) {
  const next = new Set(form.preferred_variants ?? [])
  if (checked) next.add(variant)
  else next.delete(variant)
  form.preferred_variants = Array.from(next) as DirectionVariant[]
}

async function handleCreateDirection() {
  if (!form.name.trim() || !form.seed_topic.trim()) return
  try {
    await createDirection({
      name: form.name.trim(),
      seed_topic: form.seed_topic.trim(),
      user_goal: form.user_goal?.trim() || null,
      preferred_variants: form.preferred_variants,
      risk_level: form.risk_level,
      status: form.status,
    })
    Object.assign(form, buildDefaultPayload())
  } catch {
    // error 已由 composable 记录
  }
}

async function handleDeleteDirection(direction: Direction) {
  if (!window.confirm(t('directions.actions.confirmDelete', { name: direction.name }))) return
  try {
    await deleteDirection(direction.id)
  } catch {
    // error 已由 composable 记录
  }
}

function directionTone(status: DirectionStatus) {
  if (status === 'active') return 'bg-emerald-100 text-emerald-700'
  if (status === 'paused') return 'bg-amber-100 text-amber-700'
  return 'bg-slate-200 text-slate-700'
}

function candidateTone(variant: DirectionVariant) {
  if (variant === 'product') return 'bg-blue-100 text-blue-700'
  if (variant === 'service') return 'bg-purple-100 text-purple-700'
  if (variant === 'delivery') return 'bg-emerald-100 text-emerald-700'
  return 'bg-slate-100 text-slate-700'
}

function candidateStatusTone(status?: string) {
  if (status === 'hot') return 'bg-emerald-100 text-emerald-700'
  if (status === 'test') return 'bg-blue-100 text-blue-700'
  if (status === 'watch') return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-700'
}

async function handleGenerateCandidates(directionId: number) {
  try {
    await generateCandidates(directionId)
  } catch {
    // error 已由 composable 记录
  }
}

async function handleRefreshCandidates(directionId: number) {
  try {
    await refreshCandidates(directionId)
  } catch {
    // error 已由 composable 记录
  }
}

function recommendationTone(status: string) {
  if (status === 'accepted') return 'bg-emerald-100 text-emerald-700'
  if (status === 'dismissed') return 'bg-slate-200 text-slate-700'
  return 'bg-amber-100 text-amber-700'
}

async function handleRefreshRecommendations(directionId: number) {
  try {
    await refreshRecommendations(directionId)
  } catch {
    // error 已由 composable 记录
  }
}

async function handleRecommendationStatus(directionId: number, recommendationId: number, status: 'accepted' | 'dismissed') {
  try {
    await updateRecommendationStatus(directionId, recommendationId, status)
  } catch {
    // error 已由 composable 记录
  }
}

function openRecommendationTaskDraft(item: {
  direction_id: number
  candidate_id: number
  id: number
  keyword: string
  reason: string
  score: number
}) {
  router.push({
    name: 'Tasks',
    query: {
      create: '1',
      source: 'finder',
      keyword: item.keyword,
      taskName: t('directions.recommendations.taskDraft.taskName', { keyword: item.keyword }),
      description: t('directions.recommendations.taskDraft.description', {
        keyword: item.keyword,
        reason: item.reason,
        score: item.score,
      }),
      decisionMode: 'ai',
      maxPages: item.score >= 80 ? '5' : '3',
      newPublishOption: 'latest',
      analyzeImages: 'true',
      personalOnly: 'true',
      freeShipping: 'true',
      finderDirectionId: String(item.direction_id),
      finderCandidateId: String(item.candidate_id),
      finderRecommendationId: String(item.id),
    },
  })
}

onMounted(() => {
  void fetchDirections().catch(() => {
    // error 已由 composable 记录
  })
})
</script>

<template>
  <div class="space-y-8 animate-fade-in">
    <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div>
        <h1 class="flex items-center gap-3 text-3xl font-black tracking-tight text-slate-800">
          <Compass class="h-8 w-8 text-primary" />
          {{ t('directions.title') }}
        </h1>
        <p class="mt-1 text-sm font-medium text-slate-500">
          {{ t('directions.description') }}
        </p>
      </div>
      <Button variant="outline" :disabled="isLoading" @click="fetchDirections">
        <RefreshCw class="h-4 w-4" />
        {{ t('common.refresh') }}
      </Button>
    </div>

    <div v-if="error" class="app-alert-error" role="alert">
      {{ error.message }}
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
      <Card v-for="stat in statCards" :key="stat.label" class="app-surface border-none">
        <CardContent class="flex items-center justify-between p-5">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{{ stat.label }}</p>
            <p class="mt-2 text-3xl font-black text-slate-900">{{ stat.value }}</p>
          </div>
          <component :is="stat.icon" class="h-6 w-6 text-primary" />
        </CardContent>
      </Card>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
      <Card class="app-surface border-none">
        <CardHeader>
          <CardTitle class="text-lg font-bold text-slate-800">{{ t('directions.form.title') }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">{{ t('directions.form.name') }}</label>
            <input v-model="form.name" class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-0 focus:border-primary" :placeholder="t('directions.form.namePlaceholder')" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">{{ t('directions.form.seedTopic') }}</label>
            <input v-model="form.seed_topic" class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-0 focus:border-primary" :placeholder="t('directions.form.seedTopicPlaceholder')" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">{{ t('directions.form.userGoal') }}</label>
            <textarea v-model="form.user_goal" rows="4" class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-0 focus:border-primary" :placeholder="t('directions.form.userGoalPlaceholder')" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">{{ t('directions.form.riskLevel') }}</label>
            <select v-model="form.risk_level" class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-primary">
              <option v-for="option in riskOptions" :key="option.value" :value="option.value">{{ t(option.labelKey) }}</option>
            </select>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">{{ t('directions.form.preferredVariants') }}</label>
            <div class="grid grid-cols-2 gap-2">
              <label v-for="option in variantOptions" :key="option.value" class="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                <input
                  :checked="form.preferred_variants?.includes(option.value)"
                  type="checkbox"
                  @change="toggleVariant(option.value, ($event.target as HTMLInputElement).checked)"
                />
                {{ t(option.labelKey) }}
              </label>
            </div>
          </div>
          <Button class="w-full" :disabled="isSaving || !form.name.trim() || !form.seed_topic.trim()" @click="handleCreateDirection">
            <Rocket class="h-4 w-4" />
            {{ isSaving ? t('common.saving') : t('directions.form.submit') }}
          </Button>
        </CardContent>
      </Card>

      <div class="space-y-4">
        <Card class="app-surface border-none">
          <CardHeader>
            <CardTitle class="text-lg font-bold text-slate-800">{{ t('directions.title') }}</CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="isLoading" class="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
              {{ t('common.loading') }}
            </div>
            <div v-else-if="!directions.length" class="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
              {{ t('directions.empty.description') }}
            </div>
            <div v-else class="grid gap-4">
              <article v-for="direction in directions" :key="direction.id" class="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-sm">
                <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div class="space-y-2">
                    <div class="flex flex-wrap items-center gap-2">
                      <h3 class="text-lg font-bold text-slate-900">{{ direction.name }}</h3>
                      <Badge :class="directionTone(direction.status)">{{ t(`directions.status.${direction.status}`) }}</Badge>
                    </div>
                    <p class="text-sm text-slate-600">
                      {{ t('directions.card.seedTopic', { topic: direction.seed_topic }) }}
                    </p>
                    <p class="text-sm text-slate-500">
                      {{ direction.user_goal || t('directions.card.emptyGoal') }}
                    </p>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <Button size="sm" variant="outline" :disabled="isSaving" @click="handleGenerateCandidates(direction.id)">
                      <Sparkles class="h-4 w-4" />
                      {{ t('directions.actions.generateCandidates') }}
                    </Button>
                    <Button size="sm" variant="outline" :disabled="isSaving" @click="handleRefreshCandidates(direction.id)">
                      <TrendingUp class="h-4 w-4" />
                      {{ t('directions.actions.refreshCandidates') }}
                    </Button>
                    <Button v-if="direction.status !== 'active'" size="sm" variant="outline" :disabled="isSaving" @click="updateDirectionStatus(direction.id, 'active')">
                      {{ t('directions.actions.activate') }}
                    </Button>
                    <Button v-if="direction.status === 'active'" size="sm" variant="outline" :disabled="isSaving" @click="updateDirectionStatus(direction.id, 'paused')">
                      {{ t('directions.actions.pause') }}
                    </Button>
                    <Button v-if="direction.status !== 'archived'" size="sm" variant="outline" :disabled="isSaving" @click="updateDirectionStatus(direction.id, 'archived')">
                      {{ t('directions.actions.archive') }}
                    </Button>
                    <Button size="sm" variant="destructive" :disabled="isSaving" @click="handleDeleteDirection(direction)">
                      <Trash2 class="h-4 w-4" />
                      {{ t('common.delete') }}
                    </Button>
                  </div>
                </div>
                <div class="mt-4 flex flex-wrap gap-2">
                  <Badge v-for="variant in direction.preferred_variants" :key="variant" variant="outline">
                    {{ t(`directions.variants.${variant}`) }}
                  </Badge>
                  <Badge variant="outline">{{ t(`directions.risk.${direction.risk_level}`) }}</Badge>
                </div>
                <div class="mt-4 grid gap-3 text-xs text-slate-500 md:grid-cols-2">
                  <p>{{ t('directions.card.createdAt', { time: formatRelativeTimeFromNow(direction.created_at) }) }}</p>
                  <p>{{ t('directions.card.updatedAt', { time: formatRelativeTimeFromNow(direction.updated_at) }) }}</p>
                </div>
                <div class="mt-4 rounded-2xl border border-slate-100 bg-slate-50/80 p-4">
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <p class="text-sm font-semibold text-slate-700">{{ t('directions.learning.title') }}</p>
                  </div>
                  <div class="grid gap-2 text-xs text-slate-500 md:grid-cols-3">
                    <p>{{ t('directions.learning.accepted', { count: learningSummaryByDirection[direction.id]?.accepted_recommendations || 0 }) }}</p>
                    <p>{{ t('directions.learning.dismissed', { count: learningSummaryByDirection[direction.id]?.dismissed_recommendations || 0 }) }}</p>
                    <p>{{ t('directions.learning.createdTasks', { count: learningSummaryByDirection[direction.id]?.created_tasks || 0 }) }}</p>
                    <p>{{ t('directions.learning.totalExperiments', { count: learningSummaryByDirection[direction.id]?.total_experiments || 0 }) }}</p>
                    <p>{{ t('directions.learning.runningExperiments', { count: learningSummaryByDirection[direction.id]?.running_experiments || 0 }) }}</p>
                    <p>{{ t('directions.learning.completedExperiments', { count: learningSummaryByDirection[direction.id]?.completed_experiments || 0 }) }}</p>
                  </div>
                </div>
                <div class="mt-4 rounded-2xl border border-slate-100 bg-slate-50/80 p-4">
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <p class="text-sm font-semibold text-slate-700">{{ t('directions.candidates.title') }}</p>
                    <p class="text-xs text-slate-500">
                      {{ t('directions.candidates.count', { count: candidatesByDirection[direction.id]?.length || 0 }) }}
                    </p>
                  </div>
                  <div
                    v-if="!(candidatesByDirection[direction.id]?.length)"
                    class="text-sm text-slate-500"
                  >
                    {{ t('directions.candidates.empty') }}
                  </div>
                  <div v-else class="flex flex-wrap gap-2">
                    <div
                      v-for="candidate in candidatesByDirection[direction.id]"
                      :key="candidate.id"
                      class="rounded-xl border border-slate-200 bg-white px-3 py-2"
                    >
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="text-sm font-medium text-slate-800">{{ candidate.keyword }}</span>
                        <Badge :class="candidateTone(candidate.variant_type)">{{ t(`directions.variants.${candidate.variant_type}`) }}</Badge>
                        <Badge variant="outline">{{ t(`directions.candidates.source.${candidate.source_type}`) }}</Badge>
                        <Badge :class="candidateStatusTone(candidate.state?.status)">
                          {{ t(`directions.candidates.status.${candidate.state?.status || 'cold'}`) }}
                        </Badge>
                        <Badge variant="outline">
                          {{ t('directions.candidates.score', { score: candidate.state?.opportunity_score || 0 }) }}
                        </Badge>
                      </div>
                      <div class="mt-2 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                        <p>{{ t('directions.candidates.metrics.samples', { count: candidate.evidence?.sample_count || 0 }) }}</p>
                        <p>{{ t('directions.candidates.metrics.recent', { count: candidate.evidence?.recent_items_24h || 0 }) }}</p>
                        <p>{{ t('directions.candidates.metrics.recommended', { count: candidate.evidence?.recommended_items || 0 }) }}</p>
                        <p>{{ t('directions.candidates.metrics.signals', { count: candidate.evidence?.signal_hits || 0 }) }}</p>
                      </div>
                      <div v-if="candidate.evidence?.top_signals?.length" class="mt-2 flex flex-wrap gap-1">
                        <Badge v-for="signal in candidate.evidence.top_signals" :key="signal" variant="outline">
                          {{ signal }}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="mt-4 rounded-2xl border border-slate-100 bg-slate-50/80 p-4">
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <p class="text-sm font-semibold text-slate-700">{{ t('directions.recommendations.title') }}</p>
                    <div class="flex items-center gap-2">
                      <p class="text-xs text-slate-500">
                        {{ t('directions.recommendations.count', { count: recommendationsByDirection[direction.id]?.length || 0 }) }}
                      </p>
                      <Button size="sm" variant="outline" :disabled="isSaving" @click="handleRefreshRecommendations(direction.id)">
                        <Sparkles class="h-4 w-4" />
                        {{ t('directions.recommendations.refresh') }}
                      </Button>
                    </div>
                  </div>
                  <div
                    v-if="!(recommendationsByDirection[direction.id]?.length)"
                    class="text-sm text-slate-500"
                  >
                    {{ t('directions.recommendations.empty') }}
                  </div>
                  <div v-else class="grid gap-3">
                    <article
                      v-for="recommendation in recommendationsByDirection[direction.id]"
                      :key="recommendation.id"
                      class="rounded-xl border border-slate-200 bg-white px-4 py-3"
                    >
                      <div class="flex flex-wrap items-center gap-2">
                        <h4 class="text-sm font-semibold text-slate-800">{{ recommendation.keyword }}</h4>
                        <Badge variant="outline">{{ t('directions.recommendations.score', { score: recommendation.score }) }}</Badge>
                        <Badge :class="recommendationTone(recommendation.status)">
                          {{ t(`directions.recommendations.status.${recommendation.status}`) }}
                        </Badge>
                      </div>
                      <p class="mt-2 text-sm text-slate-600">{{ recommendation.reason }}</p>
                      <div class="mt-3 flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          :disabled="isSaving"
                          @click="openRecommendationTaskDraft(recommendation)"
                        >
                          {{ t('directions.recommendations.createTask') }}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          :disabled="isSaving || recommendation.status === 'accepted'"
                          @click="handleRecommendationStatus(direction.id, recommendation.id, 'accepted')"
                        >
                          {{ t('directions.recommendations.accept') }}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          :disabled="isSaving || recommendation.status === 'dismissed'"
                          @click="handleRecommendationStatus(direction.id, recommendation.id, 'dismissed')"
                        >
                          {{ t('directions.recommendations.dismiss') }}
                        </Button>
                      </div>
                    </article>
                  </div>
                </div>
                <div class="mt-4 rounded-2xl border border-slate-100 bg-slate-50/80 p-4">
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <p class="text-sm font-semibold text-slate-700">{{ t('directions.experiments.title') }}</p>
                    <p class="text-xs text-slate-500">
                      {{ t('directions.experiments.count', { count: experimentsByDirection[direction.id]?.length || 0 }) }}
                    </p>
                  </div>
                  <div
                    v-if="!(experimentsByDirection[direction.id]?.length)"
                    class="text-sm text-slate-500"
                  >
                    {{ t('directions.experiments.empty') }}
                  </div>
                  <div v-else class="grid gap-3">
                    <article
                      v-for="experiment in experimentsByDirection[direction.id]"
                      :key="experiment.id"
                      class="rounded-xl border border-slate-200 bg-white px-4 py-3"
                    >
                      <div class="flex flex-wrap items-center gap-2">
                        <h4 class="text-sm font-semibold text-slate-800">{{ experiment.task_name || experiment.keyword }}</h4>
                        <Badge variant="outline">{{ experiment.keyword }}</Badge>
                        <Badge :class="candidateStatusTone(experiment.status === 'completed' ? 'hot' : experiment.status === 'running' ? 'test' : 'watch')">
                          {{ t(`directions.experiments.status.${experiment.status}`) }}
                        </Badge>
                      </div>
                      <p class="mt-2 text-xs text-slate-500">
                        {{ t('directions.experiments.createdAt', { time: formatRelativeTimeFromNow(experiment.created_at) }) }}
                      </p>
                      <div class="mt-2 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                        <p>{{ t('directions.experiments.samples', { count: experiment.sample_count || 0 }) }}</p>
                        <p>
                          {{ experiment.latest_crawl_time
                            ? t('directions.experiments.latestSeen', { time: formatRelativeTimeFromNow(experiment.latest_crawl_time) })
                            : t('directions.experiments.noActivity') }}
                        </p>
                      </div>
                    </article>
                  </div>
                </div>
              </article>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
