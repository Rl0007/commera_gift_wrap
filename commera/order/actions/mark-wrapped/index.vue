<script>
export const plugin = {
  label: 'Mark gift wrapped',
  icon: 'gift',
  requires: 'Gift Wrap Task',
  condition: 'commera_gift_wrap.conditions.has_open_gift_wrap_task',
  method: 'commera_gift_wrap.api.mark_order_wrapped',
  confirm: 'Mark this order as gift wrapped? It moves to the Wrapped tab.',
}
</script>
