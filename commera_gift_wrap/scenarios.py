"""Devbox scenarios. `seed` prepares data; `run` drives the storefront over HTTP as a real shopper.

bench --site dev.localhost execute commera_gift_wrap.scenarios.seed
bench --site dev.localhost execute commera_gift_wrap.scenarios.run
"""

import json
import time

import frappe
import requests

BASE_URL = "http://127.0.0.1:8000"
SITE = "dev.localhost"
SHOPPER = "gw.shopper@example.com"
SHOPPER_PASSWORD = "GiftWrap#2026"
ADMIN_PASSWORD = "admin"
WRAPPABLE_ITEM = "GW-TEE-01"
NOT_WRAPPABLE_ITEM = "GW-MUG-01"
PRICE_PER_ITEM = 40
GST_RATE = 18


def seed():
	settings = frappe.get_single("Commera Settings")
	for item_code, item_name, not_wrappable in (
		(WRAPPABLE_ITEM, "Gift Wrap Test Tee", 0),
		(NOT_WRAPPABLE_ITEM, "Gift Wrap Test Mug", 1),
	):
		if not frappe.db.exists("Item", item_code):
			item = frappe.new_doc("Item")
			item.update(
				{
					"item_code": item_code,
					"item_name": item_name,
					"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"valuation_rate": 100,
				}
			)
			item.insert()
		frappe.db.set_value("Item", item_code, "commera_gift_wrap_not_wrappable", not_wrappable)
		if not frappe.db.exists(
			"Item Price", {"item_code": item_code, "price_list": settings.sale_price_list}
		):
			item_price = frappe.new_doc("Item Price")
			item_price.update(
				{"item_code": item_code, "price_list": settings.sale_price_list, "price_list_rate": 500}
			)
			item_price.insert()

	stocked = frappe.get_all(
		"Bin",
		filters={
			"warehouse": settings.ecommerce_warehouse,
			"item_code": ["in", [WRAPPABLE_ITEM, NOT_WRAPPABLE_ITEM]],
		},
		fields=["item_code", "actual_qty"],
	)
	stock_by_item = {row.item_code: row.actual_qty for row in stocked}
	low_items = [code for code in (WRAPPABLE_ITEM, NOT_WRAPPABLE_ITEM) if stock_by_item.get(code, 0) < 20]
	if low_items:
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = "Material Receipt"
		stock_entry.company = settings.company
		for item_code in low_items:
			stock_entry.append(
				"items",
				{
					"item_code": item_code,
					"qty": 50,
					"t_warehouse": settings.ecommerce_warehouse,
					"basic_rate": 100,
				},
			)
		stock_entry.insert()
		stock_entry.submit()

	if not frappe.db.exists("User", SHOPPER):
		user = frappe.new_doc("User")
		user.update({"email": SHOPPER, "first_name": "Gift", "last_name": "Shopper", "send_welcome_email": 0})
		user.insert(ignore_permissions=True)
		user.add_roles("Customer")
	user = frappe.get_doc("User", SHOPPER)
	user.new_password = SHOPPER_PASSWORD
	user.save(ignore_permissions=True)

	gift_wrap_settings = frappe.get_single("Gift Wrap Settings")
	gift_wrap_settings.price_per_item = PRICE_PER_ITEM
	gift_wrap_settings.simulate_failure = 0
	gift_wrap_settings.save()
	frappe.db.commit()
	print("seeded", low_items or "stock ok", frappe.get_roles(SHOPPER))


class Client:
	def __init__(self, user: str, password: str):
		self.session = requests.Session()
		self.session.headers["Host"] = SITE
		self.post("login", usr=user, pwd=password)

	def post(self, method: str, **params):
		response = self.send("post", f"{BASE_URL}/api/method/{method}", json=params)
		body = response.json()
		if response.status_code != 200:
			raise ApiError(response.status_code, get_server_message(body))
		return body.get("message")

	def send(self, verb: str, url: str, **kwargs):
		# Other agents restart the shared bench mid-run; a dropped connection never reached a worker.
		for attempt in range(20):
			try:
				return self.session.request(verb, url, **kwargs)
			except requests.ConnectionError:
				print(f"  (server restarting, retry {attempt + 1})")
				time.sleep(3)
		raise RuntimeError(f"{url} unreachable")

	def get(self, method: str, **params):
		params = {
			key: json.dumps(value) if isinstance(value, dict | list) else value
			for key, value in params.items()
		}
		response = self.send("get", f"{BASE_URL}/api/method/{method}", params=params)
		response.raise_for_status()
		return response.json().get("message")


class ApiError(Exception):
	def __init__(self, status_code: int, message: str):
		super().__init__(f"{status_code}: {message}")
		self.status_code = status_code
		self.message = message


def get_server_message(body: dict) -> str:
	messages = json.loads(body.get("_server_messages") or "[]")
	return " | ".join(json.loads(message).get("message", "") for message in messages) or (
		body.get("exception") or body.get("exc_type") or json.dumps(body)[:2000]
	)


def show_cart(admin: Client, quotation_name: str, label: str) -> dict:
	quotation = admin.get("frappe.client.get", doctype="Quotation", name=quotation_name)
	print(
		f"  [{label}] net_total={quotation['net_total']} grand_total={quotation['grand_total']}"
		f" wrap={quotation.get('commera_gift_wrap_enabled')} message={quotation.get('commera_gift_wrap_message')!r}"
	)
	for row in quotation["taxes"]:
		print(
			f"    tax row {row['idx']}: {row['description']!r} {row['charge_type']} rate={row['rate']}"
			f" amount={row['tax_amount']} app_fee={row.get('commera_app_fee')}"
		)
	return quotation


def gift_wrap_fee_rows(quotation: dict) -> list[dict]:
	return [row for row in quotation["taxes"] if row["description"] == "Gift wrap"]


def expect_refusal(label: str, call) -> str:
	try:
		call()
	except ApiError as error:
		print(f"  [{label}] refused {error.status_code}: {error.message!r}")
		return error.message
	print(f"  [{label}] UNEXPECTED: not refused")
	return ""


def poll(label: str, fetch, seconds: int = 90):
	started = time.time()
	while time.time() - started < seconds:
		if value := fetch():
			print(f"  [{label}] after {round(time.time() - started)}s: {value}")
			return value
		time.sleep(2)
	print(f"  [{label}] nothing after {seconds}s")
	return None


def put_in_cart(shopper: Client, items: list[tuple[str, int]]) -> dict:
	cart = {"items": [{"variant": {"item_code": item_code}, "qty": qty} for item_code, qty in items]}
	return shopper.post("commera.api.payments.generate_quotation_for_cart", cart=cart)


def save_address(shopper: Client):
	address = {
		"billing_address": {
			"first_name": "Gift",
			"last_name": "Shopper",
			"full_address": "12 Ribbon Street",
			"city": "Pune",
			"state": "Maharashtra",
			"country": "India",
			"po_box": "411001",
			"phone_number": "9999900000",
			"email": SHOPPER,
		},
		"shipping_same_as_billing": True,
	}
	return shopper.post("commera.api.payments.update_quotation_address", address=address)


def add_gst_row(admin: Client, quotation_name: str):
	quotation = admin.get("frappe.client.get", doctype="Quotation", name=quotation_name)
	if any(row["charge_type"] == "On Net Total" for row in quotation["taxes"]):
		return
	# The devbox chart has no Tax account. Any chargeable account other than the fee's proves how the
	# rate is computed; sharing the fee's account zeroes the rate through the items' item_tax_rate map.
	tax_account = "Miscellaneous Expenses - LSD"
	quotation["taxes"].insert(
		0,
		{
			"doctype": "Sales Taxes and Charges",
			"charge_type": "On Net Total",
			"account_head": tax_account,
			"description": f"GST {GST_RATE}%",
			"rate": GST_RATE,
		},
	)
	admin.post("frappe.client.save", doc=quotation)


def checkout(shopper: Client, summary_total: float):
	return shopper.post(
		"commera.api.payments.initiate_checkout_with_mode", payment_mode="COD", expected_total=summary_total
	)


def run():
	admin = Client("Administrator", ADMIN_PASSWORD)
	shopper = Client(SHOPPER, SHOPPER_PASSWORD)
	admin.post(
		"frappe.client.set_value",
		doctype="Gift Wrap Settings",
		name="Gift Wrap Settings",
		fieldname="simulate_failure",
		value=0,
	)

	print("Setup: cart with 2 tees, address, GST 18% On Net Total on this cart only")
	quotation_name = put_in_cart(shopper, [(WRAPPABLE_ITEM, 2)])["name"]
	save_address(shopper)
	add_gst_row(admin, quotation_name)
	print("  quotation", quotation_name)

	print("S1: enable wrap -> Gift wrap line, total includes it, no tax on it")
	response = shopper.post(
		"commera_gift_wrap.cart.set_gift_wrap", enabled=1, message="Happy birthday, Asha!"
	)
	summary = response["checkout_summary"]
	print("  summary taxes:", summary["taxes"], "subtotal", summary["subtotal"], "total", summary["total"])
	quotation = show_cart(admin, quotation_name, "S1")
	gst = next(row for row in quotation["taxes"] if row["charge_type"] == "On Net Total")
	print(
		f"  check: fee={gift_wrap_fee_rows(quotation)[0]['tax_amount']} (want {2 * PRICE_PER_ITEM}),"
		f" GST={gst['tax_amount']} (18% of net {quotation['net_total']} = {quotation['net_total'] * GST_RATE / 100})"
	)

	print("S2: change qty 2 -> 3, fee follows, still one row")
	put_in_cart(shopper, [(WRAPPABLE_ITEM, 3)])
	quotation = show_cart(admin, quotation_name, "S2")
	print(
		f"  check: gift wrap rows={len(gift_wrap_fee_rows(quotation))}, fee={[row['tax_amount'] for row in gift_wrap_fee_rows(quotation)]} (want {3 * PRICE_PER_ITEM})"
	)

	print("S4: 250-char message -> checkout refused, no order")
	shopper.post("commera_gift_wrap.cart.set_gift_wrap", enabled=1, message="x" * 250)
	quotation = show_cart(admin, quotation_name, "S4")
	expect_refusal("S4 checkout", lambda: checkout(shopper, quotation["grand_total"]))
	print(
		"  docstatus after refusal:",
		admin.get(
			"frappe.client.get_value", doctype="Quotation", filters=quotation_name, fieldname="docstatus"
		),
	)
	print(
		"  orders from this cart:",
		admin.get(
			"frappe.client.get_list",
			doctype="Sales Order Item",
			filters={"prevdoc_docname": quotation_name},
			fields=["parent"],
			parent="Sales Order",
		),
	)

	print("S4b: not-wrappable mug in the cart -> refused with its name")
	shopper.post("commera_gift_wrap.cart.set_gift_wrap", enabled=1, message="Happy birthday, Asha!")
	put_in_cart(shopper, [(WRAPPABLE_ITEM, 3), (NOT_WRAPPABLE_ITEM, 1)])
	quotation = show_cart(admin, quotation_name, "S4b")
	expect_refusal("S4b checkout", lambda: checkout(shopper, quotation["grand_total"]))
	put_in_cart(shopper, [(WRAPPABLE_ITEM, 3)])

	print("S5: fee hook crashes -> generic message, Error Log names the handler")
	admin.post(
		"frappe.client.set_value",
		doctype="Gift Wrap Settings",
		name="Gift Wrap Settings",
		fieldname="simulate_failure",
		value=1,
	)
	crash_started = admin.get(
		"frappe.client.get_value", doctype="Quotation", filters=quotation_name, fieldname="modified"
	)
	quotation = show_cart(admin, quotation_name, "S5 before")
	expect_refusal("S5 checkout", lambda: checkout(shopper, quotation["grand_total"]))
	expect_refusal(
		"S5 set_gift_wrap",
		lambda: shopper.post("commera_gift_wrap.cart.set_gift_wrap", enabled=1, message="Hi"),
	)
	admin.post(
		"frappe.client.set_value",
		doctype="Gift Wrap Settings",
		name="Gift Wrap Settings",
		fieldname="simulate_failure",
		value=0,
	)
	poll(
		"S5 Error Log",
		lambda: admin.get(
			"frappe.client.get_list",
			doctype="Error Log",
			filters={
				"method": ["like", 'commera_checkout["cart_fees"] hook failed: commera_gift_wrap%'],
				"creation": [">=", crash_started["modified"]],
			},
			fields=["name", "method", "reference_doctype", "reference_name", "creation"],
		),
		seconds=360,
	)

	print("S6: disable wrap -> fee row gone")
	shopper.post("commera_gift_wrap.cart.set_gift_wrap", enabled=0)
	quotation = show_cart(admin, quotation_name, "S6")
	print(f"  check: gift wrap rows={len(gift_wrap_fee_rows(quotation))}")

	print("S3: re-enable and place a COD order")
	response = shopper.post(
		"commera_gift_wrap.cart.set_gift_wrap", enabled=1, message="Happy birthday, Asha!"
	)
	quotation = show_cart(admin, quotation_name, "S3 cart")
	checkout_response = checkout(shopper, response["checkout_summary"]["cash_on_delivery"]["total"])
	print("  checkout:", checkout_response)
	confirmation = shopper.post(
		"commera.api.payments.confirm_payment", reference_id=quotation_name, payment_mode="COD"
	)
	print("  confirm:", confirmation)
	sales_order_name = confirmation["order_name"]
	sales_order = admin.get("frappe.client.get", doctype="Sales Order", name=sales_order_name)
	print(
		f"  SO {sales_order_name} docstatus={sales_order['docstatus']} grand_total={sales_order['grand_total']}"
		f" wrap={sales_order.get('commera_gift_wrap_enabled')} message={sales_order.get('commera_gift_wrap_message')!r}"
	)
	for row in sales_order["taxes"]:
		print(
			f"    SO tax row: {row['description']!r} amount={row['tax_amount']} app_fee={row.get('commera_app_fee')}"
		)
	poll(
		"S3 Gift Wrap Task",
		lambda: admin.get(
			"frappe.client.get_list",
			doctype="Gift Wrap Task",
			filters={"sales_order": sales_order_name},
			fields=["name", "sales_order", "customer", "item_count", "message", "commera_event", "owner"],
		),
	)
	print(
		"  deliveries:",
		admin.get(
			"frappe.client.get_list",
			doctype="Commera Event Delivery",
			parent="Commera Event",
			filters={"parent": f"{sales_order_name}-order_placed"},
			fields=["app", "handler", "status", "attempts"],
		),
	)

	print("Control: order without wrap -> no task")
	plain_cart = put_in_cart(shopper, [(WRAPPABLE_ITEM, 1)])["name"]
	plain_summary = save_address(shopper)["checkout_summary"]
	checkout(shopper, plain_summary["cash_on_delivery"]["total"])
	plain_order = shopper.post(
		"commera.api.payments.confirm_payment", reference_id=plain_cart, payment_mode="COD"
	)["order_name"]
	time.sleep(20)
	print(
		"  plain order",
		plain_order,
		"tasks:",
		admin.get("frappe.client.get_list", doctype="Gift Wrap Task", filters={"sales_order": plain_order}),
		"deliveries:",
		admin.get(
			"frappe.client.get_list",
			doctype="Commera Event Delivery",
			parent="Commera Event",
			filters={"parent": f"{plain_order}-order_placed", "app": "commera_gift_wrap"},
			fields=["status", "attempts"],
		),
	)


def prepare_browser_cart():
	shopper = Client(SHOPPER, SHOPPER_PASSWORD)
	quotation_name = put_in_cart(shopper, [(WRAPPABLE_ITEM, 2)])["name"]
	save_address(shopper)
	response = shopper.post(
		"commera_gift_wrap.cart.set_gift_wrap", enabled=1, message="Happy birthday, Asha!"
	)
	print(quotation_name, response["checkout_summary"])
