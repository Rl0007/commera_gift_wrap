<script>
export const extension = {
  label: 'Turn off gift wrap',
  icon: 'gift',
  requires: 'Gift Wrap Task',
  condition: 'commera_gift_wrap.conditions.is_item_wrappable',
  method: 'commera_gift_wrap.api.turn_off_item_gift_wrap',
  confirm: 'Shoppers will not be able to gift wrap a cart with this product, or any of its variants, in it.',
}
</script>
