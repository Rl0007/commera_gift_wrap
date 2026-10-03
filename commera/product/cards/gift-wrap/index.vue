<script>
export const extension = {
  label: 'Gift wrap',
  requires: 'Gift Wrap Task',
}
</script>

<script setup>
import { computed, watch } from 'vue'
import { useCard, useExtension, useMethodRead } from '@commera/admin'

const { record } = useExtension()
const card = useCard()

const countsRequest = useMethodRead('commera_gift_wrap.api.get_item_gift_wrap', {
  params: () => ({ item: record.value.name }),
})

const stats = computed(() => [
  { label: 'Wrapped', value: countsRequest.data?.wrapped ?? 0 },
  { label: 'Waiting', value: countsRequest.data?.open ?? 0 },
])

// Hidden until the counts arrive, so a product nobody gift-wraps never flashes an empty card.
card.hide()
watch(
  () => countsRequest.data,
  (counts) => card.setHidden(!counts?.wrapped && !counts?.open),
)
</script>

<template>
  <div class="grid grid-cols-2 gap-3">
    <div v-for="stat in stats" :key="stat.label">
      <p class="text-sm text-ink-gray-5">{{ stat.label }}</p>
      <p class="mt-1 text-xl text-ink-gray-9 tabular-nums">{{ stat.value }}</p>
    </div>
  </div>
  <p class="mt-2 text-sm text-ink-gray-5">Gift-wrapped orders with this product or its variants.</p>
</template>
