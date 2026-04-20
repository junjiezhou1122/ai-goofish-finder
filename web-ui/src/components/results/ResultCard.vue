<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ResultItem } from '@/types/result.d.ts'
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import Badge from '@/components/ui/badge/Badge.vue'
import { toast } from '@/components/ui/toast'
import * as radarApi from '@/api/radar'
import { ExternalLink, TrendingUp, TrendingDown, Info, User, Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-vue-next'
import { formatDateTime } from '@/i18n'

interface Props {
  item: ResultItem
}

const props = defineProps<Props>()
const emit = defineEmits<{
  keywordAdded: []
}>()
const { t } = useI18n()

const info = props.item.商品信息
const seller = props.item.卖家信息
const ai = props.item.ai_analysis
const priceInsight = props.item.price_insight

const isRecommended = ai?.is_recommended === true
const recommendationStatus = computed(() => {
  if (ai?.is_recommended === true) return { label: t('results.card.strongRecommend'), color: 'bg-emerald-500', icon: CheckCircle2, text: 'text-emerald-600', bg: 'bg-emerald-50' }
  if (ai?.is_recommended === false) return { label: t('results.card.notRecommended'), color: 'bg-rose-500', icon: XCircle, text: 'text-rose-600', bg: 'bg-rose-50' }
  return { label: t('results.card.pending'), color: 'bg-amber-500', icon: AlertCircle, text: 'text-amber-600', bg: 'bg-amber-50' }
})

const imageUrl = info.商品图片列表?.[0] || info.商品主图链接 || ''
const crawlTime = props.item.爬取时间
  ? formatDateTime(props.item.爬取时间, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  : t('common.unknown')
const matchScore = ai?.value_score ?? 0

const expanded = ref(false)
const sellerItemsExpanded = ref(false)
const isExtractingKeywords = ref(false)

const sellerItems = computed<any[]>(() => {
  const items = seller?.['卖家发布的商品列表']
  return Array.isArray(items) ? items.slice(0, 6) : []
})

const sellerKeywordSuggestions = computed(() => {
  const seen = new Set<string>()
  const signals = ['源码', '教程', '模板', '脚本', '代搭建', '代配置', '自动发货', '秒发', '合集']
  const suggestions: string[] = []

  const collect = (raw: unknown) => {
    const title = String(raw || '').trim()
    if (!title) return

    const normalized = title.replace(/\s+/g, ' ').trim()
    for (const signal of signals) {
      if (!normalized.includes(signal)) continue
      const compact = normalized
        .replace(/[【】\[\]()（）|｜]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
      if (compact.length < 2 || compact.length > 30) continue
      if (seen.has(compact)) continue
      seen.add(compact)
      suggestions.push(compact)
      break
    }
  }

  collect(info.商品标题)
  sellerItems.value.forEach((item) => collect(sellerItemTitle(item)))
  return suggestions.slice(0, 4)
})

function sellerItemTitle(item: any) {
  return item?.title || item?.itemTitle || item?.name || '—'
}

function sellerItemPrice(item: any) {
  return item?.price || item?.priceText || item?.displayPrice || item?.fishPrice || ''
}

function sellerItemLink(item: any) {
  return item?.targetUrl || item?.itemUrl || item?.url || item?.link || ''
}

async function addSuggestedKeyword(keyword: string) {
  isExtractingKeywords.value = true
  try {
    await radarApi.createRadarKeywordPoolItem({
      keyword,
      source: 'recommendation',
      note: t('results.card.sellerKeywordNote', {
        seller: seller.卖家昵称 || info.卖家昵称 || t('results.card.anonymous'),
      }),
    })
    toast({ title: t('results.card.keywordAdded') })
    emit('keywordAdded')
  } catch (error) {
    toast({
      title: t('results.card.keywordAddFailed'),
      description: error instanceof Error ? error.message : t('common.error'),
      variant: 'destructive',
    })
  } finally {
    isExtractingKeywords.value = false
  }
}
</script>

<template>
  <Card class="group flex flex-col h-full border-none shadow-glass hover:shadow-card-hover transition-all duration-300 rounded-2xl overflow-hidden bg-white/80 backdrop-blur-sm">
    <!-- Image Header -->
    <div class="relative aspect-[4/3] overflow-hidden">
      <div class="absolute inset-0 bg-slate-200 animate-pulse" v-if="!imageUrl"></div>
      <img
        v-else
        :src="imageUrl"
        :alt="info.商品标题"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        loading="lazy"
      />
      <!-- Overlays -->
      <div class="absolute top-3 left-3 flex gap-2">
        <Badge v-if="isRecommended" variant="default" class="bg-emerald-500/90 backdrop-blur-md border-none shadow-sm">
          {{ t('results.card.curated') }}
        </Badge>
      </div>
      <div class="absolute top-3 right-3">
         <a
           :href="info.商品链接"
           target="_blank"
           rel="noopener noreferrer"
           :aria-label="t('results.card.detail')"
           class="flex rounded-full bg-white/30 p-1.5 text-white backdrop-blur-md border border-white/40 shadow-sm opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
         >
            <ExternalLink class="w-4 h-4" />
         </a>
      </div>
    </div>

    <CardHeader class="p-4 pb-2">
      <div class="flex justify-between items-start gap-3">
        <CardTitle class="text-base font-semibold text-slate-800 line-clamp-2 leading-snug flex-grow h-10">
          <a :href="info.商品链接" target="_blank" rel="noopener noreferrer" class="hover:text-primary transition-colors">
            {{ info.商品标题 }}
          </a>
        </CardTitle>
      </div>
      <div class="flex items-baseline gap-1 mt-2">
        <span class="text-2xl font-bold text-rose-600 tracking-tight">{{ info.当前售价 }}</span>
        <span v-if="info['商品原价']" class="text-xs text-slate-400 line-through mb-1">{{ info['商品原价'] }}</span>
      </div>
    </CardHeader>

    <CardContent class="p-4 pt-2 flex-grow">
      <!-- AI Insight Section -->
      <div class="rounded-xl p-3 border border-slate-100" :class="recommendationStatus.bg">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <component :is="recommendationStatus.icon" class="w-4 h-4" :class="recommendationStatus.text" />
            <span class="text-sm font-bold" :class="recommendationStatus.text">{{ recommendationStatus.label }}</span>
          </div>
          <div class="flex items-center gap-1">
             <span class="text-[10px] font-medium uppercase tracking-wider text-slate-400">AI Match</span>
             <span class="text-sm font-black" :class="recommendationStatus.text">{{ matchScore }}%</span>
          </div>
        </div>
        
        <div class="w-full h-1.5 bg-white/50 rounded-full overflow-hidden mb-3">
          <div 
            class="h-full transition-all duration-1000 ease-out rounded-full" 
            :class="recommendationStatus.color"
            :style="{ width: `${matchScore}%` }"
          ></div>
        </div>

        <p class="text-xs leading-relaxed text-slate-600" :class="{ 'line-clamp-2': !expanded }">
           {{ ai?.reason || t('results.card.analyzing') }}
        </p>
        
        <button
          type="button"
          v-if="ai?.reason && ai.reason.length > 50"
          @click="expanded = !expanded" 
          class="mt-1 text-[10px] font-bold uppercase text-primary/70 hover:text-primary transition-colors flex items-center gap-1"
        >
          {{ expanded ? t('results.card.collapse') : t('results.card.expand') }}
          <Info class="w-3 h-3" />
        </button>
      </div>

      <!-- Price Stats Grid -->
      <div v-if="priceInsight?.observation_count" class="mt-4 grid grid-cols-2 gap-3">
        <div class="bg-slate-50/50 p-2.5 rounded-xl border border-slate-100/50 group/stat">
          <div class="flex items-center gap-1.5 text-[10px] font-medium text-slate-400 mb-1">
            <TrendingUp class="w-3 h-3" /> {{ t('results.card.marketAvg') }}
          </div>
          <div class="text-sm font-bold text-slate-700">
            {{ priceInsight.market_avg_price ? `¥${priceInsight.market_avg_price}` : '—' }}
          </div>
        </div>
        <div class="bg-slate-50/50 p-2.5 rounded-xl border border-slate-100/50">
          <div class="flex items-center gap-1.5 text-[10px] font-medium text-slate-400 mb-1">
            <TrendingDown class="w-3 h-3" /> {{ t('results.card.historicalLow') }}
          </div>
          <div class="text-sm font-bold text-slate-700">
            {{ priceInsight.min_price ? `¥${priceInsight.min_price}` : '—' }}
          </div>
        </div>
      </div>

      <div class="mt-4 rounded-xl border border-slate-100 bg-slate-50/60 p-3">
        <button
          type="button"
          class="flex w-full items-center justify-between text-left text-xs font-bold text-slate-600 hover:text-slate-900"
          @click="sellerItemsExpanded = !sellerItemsExpanded"
        >
          <span>{{ sellerItemsExpanded ? t('results.card.collapseSellerItems') : t('results.card.expandSellerItems') }}</span>
          <span class="text-slate-400">{{ sellerItems.length }}</span>
        </button>
        <div v-if="sellerItemsExpanded" class="mt-3 space-y-3">
          <div v-if="sellerKeywordSuggestions.length > 0" class="rounded-lg border border-dashed border-primary/30 bg-primary/5 p-3">
            <p class="text-[11px] font-bold uppercase tracking-wide text-primary/80">
              {{ t('results.card.sellerKeywordSuggestions') }}
            </p>
            <div class="mt-2 flex flex-wrap gap-2">
              <button
                v-for="keyword in sellerKeywordSuggestions"
                :key="keyword"
                type="button"
                class="rounded-full border border-primary/20 bg-white px-2.5 py-1 text-[11px] font-medium text-primary transition hover:border-primary/40 hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="isExtractingKeywords"
                @click="addSuggestedKeyword(keyword)"
              >
                {{ keyword }}
              </button>
            </div>
          </div>
          <div v-if="sellerItems.length === 0" class="text-xs text-slate-500">
            {{ t('results.card.sellerItemsEmpty') }}
          </div>
          <a
            v-for="(sellerItem, index) in sellerItems"
            :key="sellerItemLink(sellerItem) || `${info.商品ID}-${index}`"
            :href="sellerItemLink(sellerItem) || undefined"
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs hover:border-primary/40 hover:bg-primary/5"
          >
            <div class="min-w-0">
              <p class="truncate font-medium text-slate-800">{{ sellerItemTitle(sellerItem) }}</p>
              <p class="mt-1 text-slate-500">{{ t('results.card.openSellerItem') }}</p>
            </div>
            <span class="shrink-0 font-semibold text-rose-600">{{ sellerItemPrice(sellerItem) || '—' }}</span>
          </a>
        </div>
      </div>
    </CardContent>

    <CardFooter class="px-4 py-3 bg-slate-50/30 border-t border-slate-100/60 flex items-center justify-between text-[10px]">
      <div class="flex items-center gap-3 text-slate-400">
        <div class="flex items-center gap-1">
          <User class="w-3 h-3" />
          <span class="truncate max-w-[60px]">{{ seller.卖家昵称 || info.卖家昵称 || t('results.card.anonymous') }}</span>
        </div>
        <div class="flex items-center gap-1">
          <Clock class="w-3 h-3" />
          <span>{{ crawlTime }}</span>
        </div>
      </div>
      <a :href="info.商品链接" target="_blank" rel="noopener noreferrer" class="flex items-center gap-1 text-primary font-bold hover:gap-1.5 transition-all">
        {{ t('results.card.detail') }} <ExternalLink class="w-3 h-3" />
      </a>
    </CardFooter>
  </Card>
</template>
