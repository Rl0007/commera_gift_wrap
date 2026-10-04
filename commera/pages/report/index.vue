<script>
export const plugin = { label: 'Wrap report', icon: 'chart-column', requires: 'Gift Wrap Task', order: 2 }
</script>

<script setup>
import { computed } from 'vue'
import { Progress, Skeleton } from 'frappe-ui'
import { EmptyState, shortDate, usePlugin, useMethodRead, usePage } from '@commera/admin'

const { navigate } = usePlugin()
usePage().setActions([{ label: 'Wrap queue', icon: 'gift', onClick: () => navigate('gift-wrap') }])

const reportRequest = useMethodRead('commera_gift_wrap.api.get_wrap_report')

const report = computed(() => reportRequest.data)
const loading = computed(() => reportRequest.loading && !report.value)

const stats = computed(() => [
  { label: 'Waiting to wrap', value: report.value?.waiting ?? 0, note: 'Open in the wrap queue' },
  { label: 'Gift-wrapped orders', value: report.value?.orders_last_30_days ?? 0, note: 'Last 30 days' },
  { label: 'Wrapped', value: report.value?.wrapped_last_30_days ?? 0, note: 'Of those, done' },
  { label: 'Items wrapped', value: report.value?.items_last_30_days ?? 0, note: 'Units in those orders' },
])

const weeks = computed(() => [...(report.value?.weeks ?? [])].reverse())
const busiestWeek = computed(() => Math.max(1, ...weeks.value.map((week) => week.orders)))
const topProducts = computed(() => report.value?.top_products ?? [])

const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`
</script>

<template>
  <div class="grid grid-cols-2 rounded-5 border border-outline-gray-1 sm:grid-cols-4 sm:divide-x sm:divide-outline-gray-2">
    <div v-for="stat in stats" :key="stat.label" class="px-4 py-3.5">
      <Skeleton v-if="loading" class="h-20 w-full rounded-4" />
      <template v-else>
        <p class="text-sm text-ink-gray-5">{{ stat.label }}</p>
        <p class="mt-1 text-2xl text-ink-gray-9 tabular-nums">{{ stat.value }}</p>
        <p class="mt-1 truncate text-sm text-ink-gray-5">{{ stat.note }}</p>
      </template>
    </div>
  </div>

  <div class="mt-8 grid items-start gap-8 lg:grid-cols-2">
    <section>
      <div class="flex items-baseline justify-between">
        <h2 class="text-lg-semibold text-ink-gray-8">By week</h2>
        <span class="text-sm text-ink-gray-5">Last {{ weeks.length || 8 }} weeks</span>
      </div>
      <Skeleton v-if="loading" class="mt-2 h-72 w-full rounded-5" />
      <ul v-else class="mt-2 divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-1">
        <li v-for="week in weeks" :key="week.week_start" class="flex items-center gap-4 px-4 py-2.5">
          <p class="w-20 shrink-0 text-base text-ink-gray-7">{{ shortDate(week.week_start) }}</p>
          <Progress class="min-w-0 flex-1" size="sm" :value="(week.orders / busiestWeek) * 100" />
          <p class="w-32 shrink-0 text-right text-sm text-ink-gray-5 tabular-nums">
            {{ plural(week.orders, 'order') }} · {{ week.wrapped }} wrapped
          </p>
        </li>
      </ul>
    </section>

    <section>
      <div class="flex items-baseline justify-between">
        <h2 class="text-lg-semibold text-ink-gray-8">Most gift-wrapped products</h2>
        <span class="text-sm text-ink-gray-5">All time</span>
      </div>
      <Skeleton v-if="loading" class="mt-2 h-56 w-full rounded-5" />
      <ul
        v-else-if="topProducts.length"
        class="mt-2 divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-1"
      >
        <li v-for="product in topProducts" :key="product.item">
          <router-link
            :to="`/products/${encodeURIComponent(product.item)}`"
            class="flex items-center gap-4 px-4 py-2.5 hover:bg-surface-gray-2"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate text-base text-ink-gray-8">{{ product.item_name }}</p>
              <p class="mt-0.5 text-sm text-ink-gray-5">{{ plural(product.quantity, 'unit') }}</p>
            </div>
            <p class="shrink-0 text-base text-ink-gray-8 tabular-nums">{{ plural(product.orders, 'order') }}</p>
            <span class="lucide-chevron-right size-4 shrink-0 text-ink-gray-4" aria-hidden="true" />
          </router-link>
        </li>
      </ul>
      <EmptyState
        v-else
        compact
        icon="lucide-gift"
        title="No gift-wrapped orders yet"
        description="Products show up here once shoppers pick gift wrap at checkout."
      />
    </section>
  </div>
</template>
