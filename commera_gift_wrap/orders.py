import frappe
from commera.sdk.events import CommeraEvent

from commera_gift_wrap.cart import GIFT_WRAP_FEE_DESCRIPTION


def create_gift_wrap_task(event: CommeraEvent) -> None:
	order = frappe.db.get_value(
		"Sales Order",
		event.sales_order,
		["name", "customer", "total_qty", "commera_gift_wrap_enabled", "commera_gift_wrap_message"],
		as_dict=True,
	)
	if not order or not order.commera_gift_wrap_enabled or not has_gift_wrap_fee(order.name):
		return
	# Delivery is at least once; the unique sales_order column backs this check up against a race.
	if frappe.db.exists("Gift Wrap Task", {"sales_order": order.name}):
		return

	task = frappe.new_doc("Gift Wrap Task")
	task.update(
		{
			"sales_order": order.name,
			"customer": order.customer,
			"item_count": order.total_qty,
			"message": order.commera_gift_wrap_message,
			"commera_event": event.id,
		}
	)
	try:
		task.insert()
	except frappe.DuplicateEntryError:
		return


def has_gift_wrap_fee(sales_order: str) -> bool:
	return bool(
		frappe.db.exists(
			"Sales Taxes and Charges",
			{
				"parenttype": "Sales Order",
				"parent": sales_order,
				"commera_app_fee": 1,
				"description": GIFT_WRAP_FEE_DESCRIPTION,
			},
		)
	)
