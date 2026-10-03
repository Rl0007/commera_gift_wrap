<script>
export const extension = { label: 'Wrap queue', icon: 'gift', requires: 'Gift Wrap Task', order: 1 }
</script>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button, TabButtons, dayjs } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import {
  EmptyState,
  ListPagination,
  ListSkeleton,
  StatusBadge,
  useExtension,
  useMethodAction,
  useMethodRead,
  usePage,
} from '@commera/admin'

const TABS = [
  { label: 'Open', value: 'Open' },
  { label: 'Wrapped', value: 'Wrapped' },
]
const ROW_HEIGHT = 60

const { navigate, toast } = useExtension()
usePage().setActions([{ label: 'Wrap report', icon: 'chart-column', onClick: () => navigate('report') }])

const status = ref('Open')
const page = ref(1)
const pageSize = ref(20)

const tasksRequest = useMethodRead('commera_gift_wrap.api.get_wrap_tasks', {
  params: () => ({
    status: status.value,
    start: (page.value - 1) * pageSize.value,
    page_length: pageSize.value,
  }),
  refetch: true,
})

watch(status, () => (page.value = 1))

const rows = computed(() => tasksRequest.data?.rows ?? [])
const total = computed(() => tasksRequest.data?.total ?? 0)

// Below `sm` the List drops to two tracks, so a wider skeleton row would wrap to double height.
const skeletonColumns = window.matchMedia('(max-width: 639.98px)').matches ? 2 : 5

const wrapAction = useMethodAction('commera_gift_wrap.api.mark_wrapped')
const wrappingTask = ref(null)

async function markWrapped(task) {
  wrappingTask.value = task.name
  await wrapAction.submit({ task: task.name })
  wrappingTask.value = null
  if (wrapAction.error) return
  toast.success(`${task.sales_order} marked wrapped`)
  tasksRequest.reload()
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <TabButtons v-model="status" size="sm" :options="TABS" />
  </div>

  <div class="mt-3 overflow-x-auto">
    <List
      class="max-sm:[--list-columns:minmax(0,1fr)_auto] sm:min-w-[44rem]"
      :row-height="ROW_HEIGHT"
      :columns="['1fr', '5rem', '1fr', '7rem', '9rem']"
    >
      <ListHeader>
        <ListHeaderCell>Order</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Items</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Message</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Age</ListHeaderCell>
        <ListHeaderCell class="justify-end">{{ status === 'Open' ? 'Action' : 'Status' }}</ListHeaderCell>
      </ListHeader>

      <ListSkeleton v-if="tasksRequest.loading && !rows.length" :columns="skeletonColumns" />

      <ListRows v-else :items="rows" row-key="name" v-slot="{ item }">
        <ListRow :to="`/orders/${item.sales_order}`" :value="item.name">
          <ListCell>
            <div class="min-w-0">
              <p class="truncate text-base text-ink-gray-8">{{ item.customer }}</p>
              <p class="truncate text-sm text-ink-gray-4 tabular-nums">{{ item.sales_order }}</p>
            </div>
          </ListCell>
          <ListCell class="max-sm:hidden">
            <span class="text-base text-ink-gray-7 tabular-nums">{{ item.item_count }}</span>
          </ListCell>
          <ListCell class="max-sm:hidden">
            <span class="truncate text-base text-ink-gray-7">{{ item.message || '—' }}</span>
          </ListCell>
          <ListCell class="max-sm:hidden">
            <span class="text-sm text-ink-gray-5">{{ dayjs(item.creation).fromNow() }}</span>
          </ListCell>
          <ListCell>
            <div class="flex w-full justify-end">
              <Button
                v-if="item.status === 'Open'"
                label="Mark wrapped"
                icon-left="lucide-gift"
                :loading="wrappingTask === item.name"
                @click.stop.prevent="markWrapped(item)"
              />
              <StatusBadge v-else status="fulfilled" label="Wrapped" />
            </div>
          </ListCell>
        </ListRow>
      </ListRows>
    </List>
  </div>

  <ListPagination v-if="total" v-model:page="page" v-model:page-size="pageSize" :total="total" />

  <EmptyState
    v-if="!tasksRequest.loading && !rows.length"
    icon="lucide-gift"
    :title="status === 'Open' ? 'Nothing waiting to be wrapped' : 'Nothing wrapped yet'"
    :description="
      status === 'Open'
        ? 'An order placed with gift wrap lands here for you to wrap before it ships.'
        : 'Orders you mark wrapped from the Open tab show up here.'
    "
  />
</template>
