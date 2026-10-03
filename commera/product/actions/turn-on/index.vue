<script>
export const extension = {
  label: 'Turn on gift wrap',
  icon: 'gift',
  requires: 'Gift Wrap Task',
  condition: 'commera_gift_wrap.conditions.is_item_not_wrappable',
  method: 'commera_gift_wrap.api.turn_on_item_gift_wrap',
  confirm: 'Shoppers will be able to gift wrap this product and its variants again.',
}
</script>
