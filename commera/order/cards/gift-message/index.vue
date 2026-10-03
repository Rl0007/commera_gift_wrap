<script>
export const extension = {
  label: 'Gift wrap',
  requires: 'Gift Wrap Task',
  condition: 'commera_gift_wrap.conditions.has_gift_wrap_task',
}
</script>

<script setup>
import { computed } from 'vue'
import { Skeleton, dayjs } from 'frappe-ui'
import { StatusBadge, useExtension, useMethodRead } from '@commera/admin'

const { record } = useExtension()

const taskRequest = useMethodRead('commera_gift_wrap.api.get_order_gift_wrap', {
  params: () => ({ sales_order: record.value.name }),
})

const task = computed(() => taskRequest.data)
</script>

<template>
  <Skeleton v-if="taskRequest.loading && !task" class="h-16 w-full rounded-4" />
  <template v-else-if="task">
    <div class="flex items-center justify-between gap-3">
      <StatusBadge v-if="task.status === 'Wrapped'" status="fulfilled" label="Wrapped" />
      <StatusBadge v-else status="pending" label="Waiting to wrap" />
      <span class="text-sm text-ink-gray-5 tabular-nums">{{ task.item_count }} items</span>
    </div>
    <p class="mt-3 text-sm text-ink-gray-5">Message</p>
    <p class="mt-1 whitespace-pre-line text-p-base text-ink-gray-7">{{ task.message || 'No message.' }}</p>
    <p v-if="task.status === 'Wrapped'" class="mt-3 text-sm text-ink-gray-5">
      Wrapped {{ dayjs(task.modified).fromNow() }}
    </p>
  </template>
</template>
