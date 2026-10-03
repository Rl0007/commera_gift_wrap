<script>
export const extension = {
  label: 'Edit gift message',
  icon: 'message-square',
  requires: 'Gift Wrap Task',
  condition: 'commera_gift_wrap.conditions.has_gift_wrap_task',
}
</script>

<script setup>
import { ref, watch } from 'vue'
import { FormControl } from 'frappe-ui'
import { useAction, useExtension, useMethodAction, useMethodRead } from '@commera/admin'

const MAX_MESSAGE_LENGTH = 200

const { record, toast } = useExtension()
const action = useAction()

const message = ref('')

const taskRequest = useMethodRead('commera_gift_wrap.api.get_order_gift_wrap', {
  params: () => ({ sales_order: record.value.name }),
})
watch(
  () => taskRequest.data,
  (task) => (message.value = task?.message ?? ''),
)

const saveRequest = useMethodAction('commera_gift_wrap.api.update_gift_message')

action.setPrimary({
  label: 'Save message',
  loading: () => taskRequest.loading,
  disabled: () => message.value.trim() === (taskRequest.data?.message ?? ''),
})

action.onSubmit(async () => {
  await saveRequest.submit({ sales_order: record.value.name, message: message.value })
  if (saveRequest.error) throw saveRequest.error
  toast.success('Gift message saved')
  return { reload: true }
})
</script>

<template>
  <FormControl
    v-model="message"
    type="textarea"
    label="Gift message"
    :description="`${message.trim().length} of ${MAX_MESSAGE_LENGTH} characters. Printed on the card inside the wrap.`"
    :rows="4"
  />
</template>
