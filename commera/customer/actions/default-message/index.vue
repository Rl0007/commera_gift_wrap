<script>
export const extension = {
  label: 'Set default gift message',
  icon: 'message-square',
  requires: 'Gift Wrap Task',
  condition: 'commera_gift_wrap.conditions.can_edit_customer',
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

const giftWrapRequest = useMethodRead('commera_gift_wrap.api.get_customer_gift_wrap', {
  params: () => ({ customer: record.value.name }),
})
watch(
  () => giftWrapRequest.data,
  (data) => (message.value = data?.default_message ?? ''),
)

const saveRequest = useMethodAction('commera_gift_wrap.api.set_customer_default_message')

action.setPrimary({
  label: () => (message.value.trim() ? 'Save message' : 'Clear message'),
  loading: () => giftWrapRequest.loading,
  disabled: () => message.value.trim() === (giftWrapRequest.data?.default_message ?? ''),
})

action.onSubmit(async () => {
  await saveRequest.submit({ customer: record.value.name, message: message.value })
  if (saveRequest.error) throw saveRequest.error
  toast.success(message.value.trim() ? 'Default gift message saved' : 'Default gift message cleared')
  return { reload: true }
})
</script>

<template>
  <FormControl
    v-model="message"
    type="textarea"
    label="Default gift message"
    :description="`${message.trim().length} of ${MAX_MESSAGE_LENGTH} characters. Filled in when this customer picks gift wrap without writing one.`"
    :rows="4"
  />
</template>
