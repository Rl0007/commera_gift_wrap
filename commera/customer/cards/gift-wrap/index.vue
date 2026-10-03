<script>
export const extension = { label: 'Gift wrap', requires: 'Gift Wrap Task' }
</script>

<script setup>
import { computed, watch } from 'vue'
import { StatusBadge, shortDate, useCard, useExtension, useMethodRead } from '@commera/admin'

const { record } = useExtension()
const card = useCard()

const giftWrapRequest = useMethodRead('commera_gift_wrap.api.get_customer_gift_wrap', {
  params: () => ({ customer: record.value.name }),
})

const giftWrap = computed(() => giftWrapRequest.data)

// Hidden until the data arrives, so a customer who never gift-wraps never flashes an empty card.
card.hide()
watch(giftWrap, (data) => card.setHidden(!data?.total && !data?.default_message))
</script>

<template>
  <template v-if="giftWrap">
    <p class="text-2xl text-ink-gray-9 tabular-nums">{{ giftWrap.total }}</p>
    <p class="mt-1 text-sm text-ink-gray-5">Gift-wrapped {{ giftWrap.total === 1 ? 'order' : 'orders' }}</p>

    <ul v-if="giftWrap.orders.length" class="mt-3 divide-y divide-outline-gray-1 border-t border-outline-gray-1">
      <li v-for="order in giftWrap.orders" :key="order.name">
        <router-link :to="`/orders/${order.sales_order}`" class="flex items-center justify-between gap-3 py-2">
          <div class="min-w-0">
            <p class="truncate text-base text-ink-gray-8 tabular-nums">{{ order.sales_order }}</p>
            <p class="truncate text-sm text-ink-gray-5">{{ order.message || shortDate(order.creation) }}</p>
          </div>
          <StatusBadge v-if="order.status === 'Wrapped'" status="fulfilled" label="Wrapped" />
          <StatusBadge v-else status="pending" label="Waiting" />
        </router-link>
      </li>
    </ul>

    <div class="mt-3 border-t border-outline-gray-1 pt-3">
      <p class="text-sm text-ink-gray-5">Default message</p>
      <p class="mt-1 whitespace-pre-line text-p-base text-ink-gray-7">
        {{ giftWrap.default_message || 'None. Set one from More actions.' }}
      </p>
    </div>
  </template>
</template>
