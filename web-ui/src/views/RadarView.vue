<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { BarChart3, History, Lightbulb, Plus, RefreshCw, TrendingUp, Zap } from 'lucide-vue-next'
import { useRadar } from '@/composables/useRadar'
import { formatDateTime, formatNumber, formatRelativeTimeFromNow } from '@/i18n'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Badge from '@/components/ui/badge/Badge.vue'
import type { Task } from '@/types/task.d.ts'
import type {
  RadarAnnotationStatus,
  RadarKeywordItem,
  RadarPoolItem,
  RadarRecommendation,
  RadarRecommendationVariantType,
  RadarSortField,
} from '@/types/radar.d.ts'

const router = useRouter()
const { t } = useI18n()
const {
  summary,
  topOpportunities,
  topSignals,
  keywords,
  pool,
  snapshots,
  snapshotKeywords,
  recommendations,
  selectedSnapshot,
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
} = useRadar()

type AnnotationDraft = { status: RadarAnnotationStatus; note: string }
const annotationDrafts = reactive<Record<string, AnnotationDraft>>({})
const filters = reactive({
  keyword: '',
  status: 'all' as RadarAnnotationStatus | 'all',
  minScore: '0',
  recentOnly: false,
  momentumOnly: false,
})
const expandedKeywords = ref<Record<string, boolean>>({})
const poolKeyword = ref('')
const poolNote = ref('')
const snapshotNote = ref('')
const editingPoolId = ref<number | null>(null)
const poolDrafts = reactive<Record<number, { keyword: string; note: string }>>({})
const recommendationVariantOptions: Array<{ value: RadarRecommendationVariantType; labelKey: string }> = [
  { value: 'product', labelKey: 'radar.recommendations.variant.product' },
  { value: 'service', labelKey: 'radar.recommendations.variant.service' },
  { value: 'delivery', labelKey: 'radar.recommendations.variant.delivery' },
]

const statCards = computed(() => [
  {
    label: t('radar.stats.keywordsTracked'),
    value: formatNumber(summary.value.keywords_tracked),
    hint: t('radar.stats.keywordsTrackedHint'),
  },
  {
    label: t('radar.stats.totalSamples'),
    value: formatNumber(summary.value.total_items),
    hint: t('radar.stats.totalSamplesHint'),
  },
  {
    label: t('radar.stats.recentItems'),
    value: formatNumber(summary.value.recent_items_24h),
    hint: t('radar.stats.recentItemsHint'),
  },
  {
    label: t('radar.stats.highOpportunity'),
    value: formatNumber(summary.value.high_opportunity_keywords),
    hint: t('radar.stats.highOpportunityHint', { score: summary.value.average_opportunity_score }),
  },
])

const statusOptions: Array<{ value: RadarAnnotationStatus; labelKey: string }> = [
  { value: 'watch', labelKey: 'radar.annotation.status.watch' },
  { value: 'test', labelKey: 'radar.annotation.status.test' },
  { value: 'sourced', labelKey: 'radar.annotation.status.sourced' },
  { value: 'risky', labelKey: 'radar.annotation.status.risky' },
  { value: 'drop', labelKey: 'radar.annotation.status.drop' },
]

const filterStatusOptions: Array<{ value: RadarAnnotationStatus | 'all'; labelKey: string }> = [
  { value: 'all', labelKey: 'radar.filters.statusAll' },
  ...statusOptions,
]

const sortOptions: Array<{ value: RadarSortField; labelKey: string }> = [
  { value: 'opportunity_score', labelKey: 'radar.sort.options.opportunityScore' },
  { value: 'recent_items_24h', labelKey: 'radar.sort.options.recentItems' },
  { value: 'growth_delta', labelKey: 'radar.sort.options.growthDelta' },
  { value: 'signal_hits', labelKey: 'radar.sort.options.signalHits' },
  { value: 'median_price', labelKey: 'radar.sort.options.medianPrice' },
  { value: 'total_items', labelKey: 'radar.sort.options.totalItems' },
  { value: 'latest_crawl_time', labelKey: 'radar.sort.options.lastSeen' },
  { value: 'keyword', labelKey: 'radar.sort.options.keyword' },
]

const minScore = computed(() => Number.parseInt(filters.minScore, 10) || 0)

const filteredKeywords = computed(() => {
  const keywordQuery = filters.keyword.trim().toLowerCase()
  return keywords.value.filter((item) => {
    if (keywordQuery && !item.keyword.toLowerCase().includes(keywordQuery)) {
      return false
    }
    if (filters.status !== 'all' && item.annotation_status !== filters.status) {
      return false
    }
    if (item.opportunity_score < minScore.value) {
      return false
    }
    if (filters.recentOnly && item.recent_items_24h <= 0) {
      return false
    }
    if (filters.momentumOnly && item.growth_delta <= 0) {
      return false
    }
    return true
  })
})

const filteredTopOpportunities = computed(() =>
  topOpportunities.value.filter((item) =>
    filteredKeywords.value.some((candidate) => candidate.keyword === item.keyword),
  ),
)

const snapshotKeywordMap = computed(() =>
  new Map(snapshotKeywords.value.map((item) => [item.keyword, item])),
)

const snapshotSummaryComparison = computed(() => {
  if (!selectedSnapshot.value) return null
  return {
    keywordCountDelta: summary.value.keywords_tracked - selectedSnapshot.value.keyword_count,
    averageScoreDelta: Number((summary.value.average_opportunity_score - selectedSnapshot.value.average_score).toFixed(1)),
  }
})

const snapshotComparisonRows = computed(() =>
  filteredKeywords.value.slice(0, 8).map((current) => {
    const previous = snapshotKeywordMap.value.get(current.keyword)
    return {
      keyword: current.keyword,
      currentScore: current.opportunity_score,
      previousScore: previous?.opportunity_score ?? null,
      scoreDelta: previous ? current.opportunity_score - previous.opportunity_score : null,
      currentRecent: current.recent_items_24h,
      previousRecent: previous?.recent_items_24h ?? null,
      recentDelta: previous ? current.recent_items_24h - previous.recent_items_24h : null,
      currentMedian: current.median_price,
      previousMedian: previous?.median_price ?? null,
      medianDelta:
        previous && current.median_price !== null && previous.median_price !== null
          ? Number((current.median_price - previous.median_price).toFixed(2))
          : null,
      isNew: !previous,
    }
  }),
)

function scoreTone(score: number) {
  if (score >= 80) return 'bg-emerald-100 text-emerald-700'
  if (score >= 60) return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-700'
}

function statusTone(status: RadarAnnotationStatus) {
  if (status === 'sourced') return 'bg-emerald-100 text-emerald-700'
  if (status === 'test') return 'bg-blue-100 text-blue-700'
  if (status === 'risky') return 'bg-rose-100 text-rose-700'
  if (status === 'drop') return 'bg-slate-200 text-slate-700'
  return 'bg-amber-100 text-amber-700'
}

function recommendationTone(status: RadarRecommendation['status']) {
  if (status === 'accepted') return 'bg-emerald-100 text-emerald-700'
  if (status === 'dismissed') return 'bg-slate-200 text-slate-700'
  return 'bg-amber-100 text-amber-700'
}

function deltaTone(value: number | null) {
  if (value === null) return 'text-slate-400'
  if (value > 0) return 'text-emerald-600'
  if (value < 0) return 'text-rose-600'
  return 'text-slate-500'
}

function formatDelta(value: number | null, digits = 0) {
  if (value === null) return '—'
  const rounded = digits > 0 ? value.toFixed(digits) : `${Math.round(value)}`
  return value > 0 ? `+${rounded}` : rounded
}

function formatPrice(value: number | null) {
  return value === null ? '—' : `¥${value}`
}

function getDraft(item: RadarKeywordItem): AnnotationDraft {
  const existing = annotationDrafts[item.keyword]
  if (existing) return existing

  const created: AnnotationDraft = {
    status: item.annotation_status,
    note: item.annotation_note,
  }
  annotationDrafts[item.keyword] = created
  return created
}

function toggleExpanded(keyword: string) {
  expandedKeywords.value = {
    ...expandedKeywords.value,
    [keyword]: !expandedKeywords.value[keyword],
  }
}

function isExpanded(keyword: string) {
  return !!expandedKeywords.value[keyword]
}

function getPoolDraft(item: RadarPoolItem) {
  const existing = poolDrafts[item.id]
  if (existing) return existing
  const created = { keyword: item.keyword, note: item.note }
  poolDrafts[item.id] = created
  return created
}

async function handleSave(item: RadarKeywordItem) {
  const draft = getDraft(item)
  const updated = await saveAnnotation(item.keyword, draft.status, draft.note)
  annotationDrafts[item.keyword] = {
    status: updated.status,
    note: updated.note,
  }
}

async function handleSortChange() {
  await setSorting(sortBy.value, sortOrder.value)
}

function buildBaseTaskDraftQuery(keyword: string, source: 'radar' | 'recommendation' | 'pool') {
  return {
    create: '1',
    keyword,
    analyzeImages: 'true',
    personalOnly: 'true',
    freeShipping: 'true',
    source,
  }
}

function buildRadarTaskDraftQuery(item: RadarKeywordItem) {
  const note = item.annotation_note.trim()
  return {
    ...buildBaseTaskDraftQuery(item.keyword, 'radar'),
    taskName: t('radar.taskDraft.taskName.radar', { keyword: item.keyword }),
    description: t('radar.taskDraft.description.radar', {
      keyword: item.keyword,
      score: item.opportunity_score,
      recent: item.recent_items_24h,
      note: note || t('radar.taskDraft.noteFallback.radar'),
    }),
    decisionMode: 'ai',
    maxPages: item.opportunity_score >= 80 ? '5' : '3',
    newPublishOption: item.recent_items_24h > 0 ? 'latest' : 'threeDays',
  }
}

function buildRecommendationTaskDraftQuery(item: RadarRecommendation) {
  const signalTerms = item.signal_terms.join('\n')
  return {
    ...buildBaseTaskDraftQuery(item.keyword, 'recommendation'),
    taskName: t('radar.taskDraft.taskName.recommendation', { keyword: item.keyword }),
    description: t('radar.taskDraft.description.recommendation', {
      keyword: item.keyword,
      reason: item.reason,
      sources: item.source_keywords.join('、') || item.keyword,
    }),
    decisionMode: signalTerms ? 'keyword' : 'ai',
    keywordRules: signalTerms,
    maxPages: item.score >= 80 ? '5' : '3',
    newPublishOption: 'latest',
  }
}

function buildPoolTaskDraftQuery(item: RadarPoolItem) {
  const note = item.note.trim()
  return {
    ...buildBaseTaskDraftQuery(item.keyword, 'pool'),
    taskName: t('radar.taskDraft.taskName.pool', { keyword: item.keyword }),
    description: t('radar.taskDraft.description.pool', {
      keyword: item.keyword,
      note: note || t('radar.taskDraft.noteFallback.pool'),
    }),
    decisionMode: 'ai',
    maxPages: '3',
    newPublishOption: 'threeDays',
  }
}

async function handleQuickAddToPool(item: RadarKeywordItem) {
  await createPoolItem(item.keyword, item.annotation_note, 'radar')
}

function openTaskDraft(query: Record<string, string>) {
  router.push({
    name: 'Tasks',
    query,
  })
}

function openExistingTask(task: Task) {
  router.push({
    name: 'Tasks',
    query: {
      edit: String(task.id),
    },
  })
}

function linkedTask(keyword: string) {
  return findTaskByKeyword(keyword)
}

async function handleCreatePoolItem() {
  await createPoolItem(poolKeyword.value, poolNote.value, 'manual')
  poolKeyword.value = ''
  poolNote.value = ''
}

function startEditingPool(item: RadarPoolItem) {
  editingPoolId.value = item.id
  getPoolDraft(item)
}

function cancelEditingPool(itemId: number) {
  editingPoolId.value = null
  delete poolDrafts[itemId]
}

async function handleUpdatePoolItem(item: RadarPoolItem) {
  const draft = getPoolDraft(item)
  const updated = await updatePoolItem(item.id, draft)
  poolDrafts[item.id] = { keyword: updated.keyword, note: updated.note }
  editingPoolId.value = null
}

async function handleCaptureSnapshot() {
  await captureSnapshot(snapshotNote.value)
  snapshotNote.value = ''
}

async function handleAcceptRecommendation(item: RadarRecommendation) {
  await updateRecommendation(item.id, 'accepted', true)
}

async function handleDismissRecommendation(item: RadarRecommendation) {
  await updateRecommendation(item.id, 'dismissed', false)
}

function toggleRecommendationVariant(variant: RadarRecommendationVariantType) {
  const next = recommendationVariantTypes.value.includes(variant)
    ? recommendationVariantTypes.value.filter((item) => item !== variant)
    : [...recommendationVariantTypes.value, variant]
  recommendationVariantTypes.value = next
}

async function handleRecommendationStrategyChange() {
  await applyRecommendationStrategy(recommendationMinScore.value, recommendationVariantTypes.value)
}
</script>

<template>
  <div class="space-y-8 animate-fade-in">
    <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="flex items-center gap-3 text-3xl font-black tracking-tight text-slate-800">
          <BarChart3 class="h-8 w-8 text-primary" />
          {{ t('radar.title') }}
        </h1>
        <p class="mt-1 font-medium text-slate-500">
          {{ t('radar.description') }}
        </p>
      </div>
      <div class="flex flex-wrap gap-3">
        <Button variant="outline" class="gap-2" :disabled="isSaving" @click="handleCaptureSnapshot">
          <History class="h-4 w-4" />
          {{ t('radar.snapshots.capture') }}
        </Button>
        <Button variant="outline" class="gap-2" :disabled="isLoading" @click="fetchRadar">
          <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': isLoading }" />
          {{ t('common.refresh') }}
        </Button>
      </div>
    </div>

    <div v-if="error" class="app-alert-error" role="alert">
      {{ error.message }}
    </div>

    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
      <Card v-for="stat in statCards" :key="stat.label" class="app-surface border-none">
        <CardContent class="p-6">
          <p class="text-sm font-bold uppercase tracking-wider text-slate-400">{{ stat.label }}</p>
          <h3 class="mt-2 text-3xl font-black text-slate-800">{{ stat.value }}</h3>
          <p class="mt-3 text-xs font-medium text-slate-500">{{ stat.hint }}</p>
        </CardContent>
      </Card>
    </div>

    <Card class="app-surface border-none">
      <CardHeader>
        <CardTitle class="text-lg font-bold text-slate-800">
          {{ t('radar.filters.title') }}
        </CardTitle>
      </CardHeader>
      <CardContent class="grid gap-4 md:grid-cols-2 xl:grid-cols-7">
        <label class="grid gap-2 text-sm font-medium text-slate-700">
          {{ t('radar.filters.keywordLabel') }}
          <input
            v-model="filters.keyword"
            type="search"
            class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
            :placeholder="t('radar.filters.keywordPlaceholder')"
          />
        </label>

        <label class="grid gap-2 text-sm font-medium text-slate-700">
          {{ t('radar.filters.statusLabel') }}
          <select
            v-model="filters.status"
            class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
          >
            <option v-for="option in filterStatusOptions" :key="option.value" :value="option.value">
              {{ t(option.labelKey) }}
            </option>
          </select>
        </label>

        <label class="grid gap-2 text-sm font-medium text-slate-700">
          {{ t('radar.filters.minScoreLabel') }}
          <select
            v-model="filters.minScore"
            class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
          >
            <option value="0">0+</option>
            <option value="40">40+</option>
            <option value="60">60+</option>
            <option value="80">80+</option>
          </select>
        </label>

        <label class="grid gap-2 text-sm font-medium text-slate-700">
          {{ t('radar.sort.label') }}
          <select
            v-model="sortBy"
            class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
            @change="handleSortChange"
          >
            <option v-for="option in sortOptions" :key="option.value" :value="option.value">
              {{ t(option.labelKey) }}
            </option>
          </select>
        </label>

        <label class="grid gap-2 text-sm font-medium text-slate-700">
          {{ t('radar.sort.orderLabel') }}
          <select
            v-model="sortOrder"
            class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
            @change="handleSortChange"
          >
            <option value="desc">{{ t('common.desc') }}</option>
            <option value="asc">{{ t('common.asc') }}</option>
          </select>
        </label>

        <label class="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm font-medium text-slate-700">
          <input v-model="filters.recentOnly" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
          {{ t('radar.filters.recentOnly') }}
        </label>

        <label class="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm font-medium text-slate-700">
          <input v-model="filters.momentumOnly" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
          {{ t('radar.filters.momentumOnly') }}
        </label>
      </CardContent>
    </Card>

    <div class="grid grid-cols-1 gap-8 xl:grid-cols-3">
      <Card class="app-surface border-none xl:col-span-2">
        <CardHeader class="flex flex-row items-center justify-between border-b border-slate-100/70 pb-4">
          <CardTitle class="flex items-center gap-2 text-lg font-bold text-slate-800">
            <TrendingUp class="h-5 w-5 text-emerald-500" />
            {{ t('radar.topOpportunities.title') }}
          </CardTitle>
        </CardHeader>
        <CardContent class="p-0">
          <div v-if="!isLoading && filteredTopOpportunities.length === 0" class="px-6 py-10 text-sm text-slate-500">
            {{ t('radar.empty') }}
          </div>
          <div v-else class="divide-y divide-slate-100/60">
            <article
              v-for="item in filteredTopOpportunities"
              :key="item.keyword"
              class="grid gap-4 px-6 py-5 md:grid-cols-[minmax(0,1fr)_140px_180px] md:items-center"
            >
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="truncate text-base font-bold text-slate-800">{{ item.keyword }}</h3>
                  <Badge :class="scoreTone(item.opportunity_score)">
                    {{ t('radar.scoreLabel', { score: item.opportunity_score }) }}
                  </Badge>
                  <Badge v-if="linkedTask(item.keyword)" variant="outline">
                    {{ t('radar.taskDraft.linked') }}
                  </Badge>
                </div>
                <p class="mt-2 text-sm text-slate-500">
                  {{ t('radar.keywordMeta', {
                    samples: item.total_items,
                    sellers: item.unique_sellers,
                    recent: item.recent_items_24h,
                  }) }}
                </p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <Badge v-for="signal in item.top_signals" :key="signal" variant="outline">
                    {{ signal }}
                  </Badge>
                </div>
              </div>

              <div class="space-y-1 text-sm text-slate-600">
                <p>{{ t('radar.priceRange') }}: <span class="font-semibold text-slate-900">{{ item.min_price !== null ? `¥${item.min_price}` : '—' }} ~ {{ item.max_price !== null ? `¥${item.max_price}` : '—' }}</span></p>
                <p>{{ t('radar.medianPrice') }}: <span class="font-semibold text-slate-900">{{ item.median_price !== null ? `¥${item.median_price}` : '—' }}</span></p>
                <p>{{ t('radar.recommendedCount') }}: <span class="font-semibold text-slate-900">{{ item.recommended_items }}</span></p>
              </div>

              <div class="space-y-2 text-sm text-slate-600 md:text-right">
                <p>
                  {{ t('radar.growthDelta') }}:
                  <span class="font-semibold" :class="item.growth_delta > 0 ? 'text-emerald-600' : 'text-slate-900'">
                    {{ item.growth_delta >= 0 ? `+${item.growth_delta}` : item.growth_delta }}
                  </span>
                </p>
                <p>{{ t('radar.signalHits') }}: <span class="font-semibold text-slate-900">{{ item.signal_hits }}</span></p>
                <p>{{ t('radar.lastSeen') }}: <span class="font-semibold text-slate-900">{{ formatRelativeTimeFromNow(item.latest_crawl_time) }}</span></p>
                <div class="flex justify-end gap-2 pt-1">
                  <Button size="sm" variant="outline" :disabled="isSaving" @click="handleQuickAddToPool(item)">
                    {{ t('radar.pool.addFromRadar') }}
                  </Button>
                  <Button
                    v-if="linkedTask(item.keyword)"
                    size="sm"
                    variant="outline"
                    @click="openExistingTask(linkedTask(item.keyword)!)"
                  >
                    {{ t('radar.taskDraft.openExisting') }}
                  </Button>
                  <Button v-else size="sm" :disabled="isSaving" @click="openTaskDraft(buildRadarTaskDraftQuery(item))">
                    {{ t('radar.taskDraft.create') }}
                  </Button>
                </div>
              </div>
            </article>
          </div>
        </CardContent>
      </Card>

      <div class="space-y-8">
        <Card class="app-surface border-none">
          <CardHeader>
            <CardTitle class="flex items-center gap-2 text-lg font-bold text-slate-800">
              <Zap class="h-5 w-5 text-amber-500" />
              {{ t('radar.topSignals.title') }}
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-3">
            <div v-if="!isLoading && topSignals.length === 0" class="text-sm text-slate-500">
              {{ t('radar.noSignals') }}
            </div>
            <div
              v-for="signal in topSignals"
              :key="signal.term"
              class="flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-3"
            >
              <span class="font-medium text-slate-700">{{ signal.term }}</span>
              <Badge variant="secondary">{{ signal.count }}</Badge>
            </div>
          </CardContent>
        </Card>

        <Card class="app-surface border-none">
          <CardHeader>
            <CardTitle class="flex items-center gap-2 text-lg font-bold text-slate-800">
              <Lightbulb class="h-5 w-5 text-primary" />
              {{ t('radar.recommendations.title') }}
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="space-y-3 rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
              <label class="grid gap-2 text-sm font-medium text-slate-700">
                {{ t('radar.recommendations.minScore') }}
                <select
                  v-model="recommendationMinScore"
                  class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
                  @change="handleRecommendationStrategyChange"
                >
                  <option :value="40">40+</option>
                  <option :value="60">60+</option>
                  <option :value="75">75+</option>
                  <option :value="90">90+</option>
                </select>
              </label>
              <div class="grid gap-2">
                <p class="text-sm font-medium text-slate-700">{{ t('radar.recommendations.variantLabel') }}</p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="option in recommendationVariantOptions"
                    :key="option.value"
                    type="button"
                    class="rounded-full border px-3 py-1 text-xs font-medium transition"
                    :class="recommendationVariantTypes.includes(option.value) ? 'border-primary bg-primary/10 text-primary' : 'border-slate-200 bg-white text-slate-600'"
                    @click="toggleRecommendationVariant(option.value)"
                  >
                    {{ t(option.labelKey) }}
                  </button>
                </div>
              </div>
              <div class="flex justify-end gap-2">
                <Button size="sm" variant="outline" :disabled="isSaving" @click="handleRecommendationStrategyChange">
                  {{ t('radar.recommendations.applyStrategy') }}
                </Button>
                <Button size="sm" variant="outline" :disabled="isSaving" @click="refreshRecommendations">
                  {{ t('radar.recommendations.refresh') }}
                </Button>
              </div>
            </div>
            <div v-if="!isLoading && recommendations.length === 0" class="text-sm text-slate-500">
              {{ t('radar.recommendations.empty') }}
            </div>
            <article
              v-for="item in recommendations"
              :key="item.id"
              class="space-y-3 rounded-2xl border border-slate-100 bg-slate-50/70 p-4"
            >
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="font-semibold text-slate-800">{{ item.keyword }}</h3>
                <Badge :class="scoreTone(item.score)">{{ t('radar.scoreLabel', { score: item.score }) }}</Badge>
                <Badge variant="outline">{{ t(`radar.recommendations.variant.${item.variant_type}`) }}</Badge>
                <Badge :class="recommendationTone(item.status)">{{ t(`radar.recommendations.status.${item.status}`) }}</Badge>
                <Badge v-if="linkedTask(item.keyword)" variant="outline">{{ t('radar.taskDraft.linked') }}</Badge>
              </div>
              <p class="text-sm text-slate-600">{{ item.reason }}</p>
              <div class="flex flex-wrap gap-2">
                <Badge v-for="signal in item.signal_terms" :key="signal" variant="outline">{{ signal }}</Badge>
              </div>
              <p class="text-xs text-slate-500">
                {{ t('radar.recommendations.sourceKeywords', { keywords: item.source_keywords.join('、') || '—' }) }}
              </p>
              <div v-if="item.status === 'pending'" class="flex flex-wrap gap-2">
                <Button size="sm" :disabled="isSaving" @click="handleAcceptRecommendation(item)">
                  {{ t('radar.recommendations.accept') }}
                </Button>
                <Button
                  v-if="linkedTask(item.keyword)"
                  size="sm"
                  variant="outline"
                  @click="openExistingTask(linkedTask(item.keyword)!)"
                >
                  {{ t('radar.taskDraft.openExisting') }}
                </Button>
                <Button v-else size="sm" variant="outline" :disabled="isSaving" @click="openTaskDraft(buildRecommendationTaskDraftQuery(item))">
                  {{ t('radar.taskDraft.create') }}
                </Button>
                <Button size="sm" variant="outline" :disabled="isSaving" @click="handleDismissRecommendation(item)">
                  {{ t('radar.recommendations.dismiss') }}
                </Button>
              </div>
            </article>
          </CardContent>
        </Card>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-8 xl:grid-cols-3">
      <Card class="app-surface border-none xl:col-span-2">
        <CardHeader>
          <CardTitle class="text-lg font-bold text-slate-800">
            {{ t('radar.keywordTable.title') }}
          </CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div v-if="!isLoading && filteredKeywords.length === 0" class="py-8 text-center text-slate-500">
            {{ t('radar.empty') }}
          </div>
          <article
            v-for="item in filteredKeywords"
            :key="item.keyword"
            class="rounded-3xl border border-slate-200/80 bg-white/80 p-5 shadow-sm"
          >
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div class="min-w-0 space-y-3">
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="text-lg font-bold text-slate-900">{{ item.keyword }}</h3>
                  <Badge :class="scoreTone(item.opportunity_score)">{{ t('radar.scoreLabel', { score: item.opportunity_score }) }}</Badge>
                  <Badge :class="statusTone(item.annotation_status)">
                    {{ t(`radar.annotation.status.${item.annotation_status}`) }}
                  </Badge>
                  <Badge v-if="linkedTask(item.keyword)" variant="outline">{{ t('radar.taskDraft.linked') }}</Badge>
                </div>
                <p class="text-sm text-slate-500">
                  {{ t('radar.keywordMeta', {
                    samples: item.total_items,
                    sellers: item.unique_sellers,
                    recent: item.recent_items_24h,
                  }) }}
                </p>
                <div class="flex flex-wrap gap-2 text-xs text-slate-500">
                  <span>{{ t('radar.priceRange') }}: {{ item.min_price !== null ? `¥${item.min_price}` : '—' }} ~ {{ item.max_price !== null ? `¥${item.max_price}` : '—' }}</span>
                  <span>·</span>
                  <span>{{ t('radar.medianPrice') }}: {{ item.median_price !== null ? `¥${item.median_price}` : '—' }}</span>
                  <span>·</span>
                  <span>{{ t('radar.signalHits') }}: {{ item.signal_hits }}</span>
                </div>
                <div class="flex flex-wrap gap-2">
                  <Badge v-for="signal in item.top_signals" :key="signal" variant="outline">{{ signal }}</Badge>
                </div>
                <div class="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" :disabled="isSaving" @click="handleQuickAddToPool(item)">
                    <Plus class="mr-1 h-4 w-4" />
                    {{ t('radar.pool.addFromRadar') }}
                  </Button>
                  <Button
                    v-if="linkedTask(item.keyword)"
                    size="sm"
                    variant="outline"
                    @click="openExistingTask(linkedTask(item.keyword)!)"
                  >
                    {{ t('radar.taskDraft.openExisting') }}
                  </Button>
                  <Button v-else size="sm" :disabled="isSaving" @click="openTaskDraft(buildRadarTaskDraftQuery(item))">
                    {{ t('radar.taskDraft.create') }}
                  </Button>
                  <button
                    type="button"
                    class="w-fit text-xs font-semibold text-primary"
                    @click="toggleExpanded(item.keyword)"
                  >
                    {{ isExpanded(item.keyword) ? t('radar.annotation.collapse') : t('radar.annotation.expand') }}
                  </button>
                </div>
              </div>

              <div v-if="isExpanded(item.keyword)" class="grid gap-3 lg:min-w-[320px]">
                <label class="grid gap-2 text-sm font-medium text-slate-700">
                  {{ t('radar.annotation.statusLabel') }}
                  <select
                    :model-value="getDraft(item).status"
                    class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
                    @change="getDraft(item).status = ($event.target as HTMLSelectElement).value as RadarAnnotationStatus"
                  >
                    <option v-for="option in statusOptions" :key="option.value" :value="option.value">
                      {{ t(option.labelKey) }}
                    </option>
                  </select>
                </label>

                <label class="grid gap-2 text-sm font-medium text-slate-700">
                  {{ t('radar.annotation.noteLabel') }}
                  <textarea
                    :value="getDraft(item).note"
                    rows="3"
                    class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                    :placeholder="t('radar.annotation.notePlaceholder')"
                    @input="getDraft(item).note = ($event.target as HTMLTextAreaElement).value"
                  />
                </label>

                <div class="flex items-center justify-between gap-3 text-xs text-slate-500">
                  <span>
                    {{ item.annotation_updated_at ? t('radar.annotation.updatedAt', { time: formatRelativeTimeFromNow(item.annotation_updated_at) }) : t('radar.annotation.notSaved') }}
                  </span>
                  <Button size="sm" :disabled="isSaving" @click="handleSave(item)">
                    {{ isSaving ? t('radar.annotation.saving') : t('radar.annotation.save') }}
                  </Button>
                </div>
              </div>
            </div>
          </article>
        </CardContent>
      </Card>

      <div class="space-y-8">
        <Card class="app-surface border-none">
          <CardHeader>
            <CardTitle class="text-lg font-bold text-slate-800">
              {{ t('radar.pool.title') }}
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="grid gap-3">
              <input
                v-model="poolKeyword"
                type="text"
                class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
                :placeholder="t('radar.pool.keywordPlaceholder')"
              />
              <textarea
                v-model="poolNote"
                rows="2"
                class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                :placeholder="t('radar.pool.notePlaceholder')"
              />
              <Button :disabled="isSaving || !poolKeyword.trim()" @click="handleCreatePoolItem">
                {{ t('radar.pool.addManual') }}
              </Button>
            </div>
            <div v-if="!isLoading && pool.length === 0" class="text-sm text-slate-500">
              {{ t('radar.pool.empty') }}
            </div>
            <article
              v-for="item in pool"
              :key="item.id"
              class="space-y-3 rounded-2xl border border-slate-100 bg-slate-50/70 p-4"
            >
              <template v-if="editingPoolId === item.id">
                <div class="grid gap-3">
                  <input
                    v-model="getPoolDraft(item).keyword"
                    type="text"
                    class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800"
                  />
                  <textarea
                    v-model="getPoolDraft(item).note"
                    rows="2"
                    class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                  />
                  <div class="flex gap-2">
                    <Button size="sm" :disabled="isSaving" @click="handleUpdatePoolItem(item)">{{ t('common.save') }}</Button>
                    <Button size="sm" variant="outline" @click="cancelEditingPool(item.id)">{{ t('common.cancel') }}</Button>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="font-semibold text-slate-800">{{ item.keyword }}</h3>
                  <Badge variant="outline">{{ t(`radar.pool.source.${item.source}`) }}</Badge>
                  <Badge v-if="linkedTask(item.keyword)" variant="outline">{{ t('radar.taskDraft.linked') }}</Badge>
                </div>
                <p v-if="item.note" class="text-sm text-slate-600">{{ item.note }}</p>
                <p class="text-xs text-slate-500">
                  {{ t('radar.pool.updatedAt', { time: formatRelativeTimeFromNow(item.updated_at) }) }}
                </p>
                <div class="flex flex-wrap gap-2">
                  <Button
                    v-if="linkedTask(item.keyword)"
                    size="sm"
                    variant="outline"
                    @click="openExistingTask(linkedTask(item.keyword)!)"
                  >
                    {{ t('radar.taskDraft.openExisting') }}
                  </Button>
                  <Button v-else size="sm" @click="openTaskDraft(buildPoolTaskDraftQuery(item))">{{ t('radar.taskDraft.create') }}</Button>
                  <Button size="sm" variant="outline" @click="startEditingPool(item)">{{ t('common.edit') }}</Button>
                  <Button size="sm" variant="destructive" :disabled="isSaving" @click="deletePoolItem(item.id)">{{ t('common.delete') }}</Button>
                </div>
              </template>
            </article>
          </CardContent>
        </Card>

        <Card class="app-surface border-none">
          <CardHeader>
            <CardTitle class="text-lg font-bold text-slate-800">
              {{ t('radar.snapshots.title') }}
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <textarea
              v-model="snapshotNote"
              rows="2"
              class="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
              :placeholder="t('radar.snapshots.notePlaceholder')"
            />
            <div v-if="!isLoading && snapshots.length === 0" class="text-sm text-slate-500">
              {{ t('radar.snapshots.empty') }}
            </div>
            <article
              v-for="snapshot in snapshots"
              :key="snapshot.id"
              class="space-y-3 rounded-2xl border p-4"
              :class="selectedSnapshot?.id === snapshot.id ? 'border-primary bg-primary/5' : 'border-slate-100 bg-slate-50/70'"
            >
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h3 class="font-semibold text-slate-800">#{{ snapshot.id }}</h3>
                  <p class="text-xs text-slate-500">{{ snapshot.created_at ? formatDateTime(snapshot.created_at) : '—' }}</p>
                </div>
                <Button size="sm" variant="outline" :disabled="isLoading" @click="selectSnapshot(snapshot.id)">
                  {{ t('radar.snapshots.view') }}
                </Button>
              </div>
              <p v-if="snapshot.note" class="text-sm text-slate-600">{{ snapshot.note }}</p>
              <p class="text-xs text-slate-500">
                {{ t('radar.snapshots.meta', {
                  count: snapshot.keyword_count,
                  score: snapshot.average_score,
                  keyword: snapshot.top_keyword || '—',
                }) }}
              </p>
            </article>
            <div v-if="selectedSnapshot" class="space-y-4 rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
              <div>
                <h3 class="font-semibold text-slate-800">{{ t('radar.snapshots.detailTitle', { id: selectedSnapshot.id }) }}</h3>
                <p class="mt-1 text-xs text-slate-500">{{ t('radar.snapshots.compareHint') }}</p>
              </div>
              <div v-if="snapshotSummaryComparison" class="grid gap-3 sm:grid-cols-2">
                <div class="rounded-2xl border border-slate-200 bg-white p-3">
                  <p class="text-xs font-medium text-slate-500">{{ t('radar.snapshots.compareKeywords') }}</p>
                  <p class="mt-2 text-lg font-bold text-slate-900">{{ summary.keywords_tracked }}</p>
                  <p class="text-xs" :class="deltaTone(snapshotSummaryComparison.keywordCountDelta)">
                    {{ t('radar.snapshots.compareDelta', { value: formatDelta(snapshotSummaryComparison.keywordCountDelta) }) }}
                  </p>
                </div>
                <div class="rounded-2xl border border-slate-200 bg-white p-3">
                  <p class="text-xs font-medium text-slate-500">{{ t('radar.snapshots.compareScore') }}</p>
                  <p class="mt-2 text-lg font-bold text-slate-900">{{ summary.average_opportunity_score }}</p>
                  <p class="text-xs" :class="deltaTone(snapshotSummaryComparison.averageScoreDelta)">
                    {{ t('radar.snapshots.compareDelta', { value: formatDelta(snapshotSummaryComparison.averageScoreDelta, 1) }) }}
                  </p>
                </div>
              </div>
              <div v-if="snapshotComparisonRows.length === 0" class="text-sm text-slate-500">
                {{ t('radar.snapshots.detailEmpty') }}
              </div>
              <div v-for="item in snapshotComparisonRows" :key="item.keyword" class="space-y-2 rounded-2xl border border-slate-200 bg-white p-3">
                <div class="flex items-center justify-between gap-3">
                  <span class="truncate font-medium text-slate-800">{{ item.keyword }}</span>
                  <Badge v-if="item.isNew" variant="outline">{{ t('radar.snapshots.newKeyword') }}</Badge>
                </div>
                <div class="grid gap-2 text-xs text-slate-600">
                  <div class="flex items-center justify-between gap-3">
                    <span>{{ t('radar.snapshots.metric.score') }}</span>
                    <span class="flex items-center gap-2">
                      <span class="font-semibold text-slate-900">{{ item.currentScore }}</span>
                      <span :class="deltaTone(item.scoreDelta)">{{ formatDelta(item.scoreDelta) }}</span>
                    </span>
                  </div>
                  <div class="flex items-center justify-between gap-3">
                    <span>{{ t('radar.snapshots.metric.recent') }}</span>
                    <span class="flex items-center gap-2">
                      <span class="font-semibold text-slate-900">{{ item.currentRecent }}</span>
                      <span :class="deltaTone(item.recentDelta)">{{ formatDelta(item.recentDelta) }}</span>
                    </span>
                  </div>
                  <div class="flex items-center justify-between gap-3">
                    <span>{{ t('radar.snapshots.metric.medianPrice') }}</span>
                    <span class="flex items-center gap-2">
                      <span class="font-semibold text-slate-900">{{ formatPrice(item.currentMedian) }}</span>
                      <span :class="deltaTone(item.medianDelta)">{{ formatDelta(item.medianDelta, 2) }}</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
