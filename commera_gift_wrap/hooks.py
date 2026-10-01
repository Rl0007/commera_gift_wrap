app_name = "commera_gift_wrap"
app_title = "Commera Gift Wrap"
app_publisher = "BWH Tech"
app_description = "Gift wrap at checkout for Commera stores"
app_email = "dev@bwh.tech"
app_license = "mit"

required_apps = ["commera"]

after_install = "commera_gift_wrap.install.add_custom_fields"
after_migrate = "commera_gift_wrap.install.add_custom_fields"

commera_api_version = [1]
commera_cart_fees = ["commera_gift_wrap.cart.get_gift_wrap_fees"]
commera_validate_cart = ["commera_gift_wrap.cart.get_gift_wrap_refusal"]
commera_order_placed = ["commera_gift_wrap.orders.create_gift_wrap_task"]
