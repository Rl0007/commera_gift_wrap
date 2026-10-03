import frappe
from commera.sdk import orders
from commera.sdk.events import CommeraEvent
from commera.sdk.types import Order

from commera_gift_wrap.cart import GIFT_WRAP_FEE_DESCRIPTION


def create_gift_wrap_task(event: CommeraEvent) -> None:
	if frappe.db.get_single_value("Gift Wrap Settings", "simulate_task_failure"):
		raise RuntimeError("Gift Wrap Settings: simulated task hook failure")
	order = orders.get_order(
		event.sales_order, extra_fields=["commera_gift_wrap_enabled", "commera_gift_wrap_message"]
	)
	gift_wrap = order["app_fields"]
	if not gift_wrap["commera_gift_wrap_enabled"] or not has_gift_wrap_fee(order):
		return
	# Delivery is at least once; the unique sales_order column backs this check up against a race.
	if frappe.db.exists("Gift Wrap Task", {"sales_order": order["name"]}):
		return

	task = frappe.new_doc("Gift Wrap Task")
	task.update(
		{
			"sales_order": order["name"],
			"customer": order["customer"],
			"item_count": sum(line["qty"] for line in order["items"]),
			"message": gift_wrap["commera_gift_wrap_message"],
			"commera_event": event.id,
		}
	)
	try:
		task.insert()
	except frappe.DuplicateEntryError:
		return


def has_gift_wrap_fee(order: Order) -> bool:
	return any(fee["description"] == GIFT_WRAP_FEE_DESCRIPTION for fee in order["app_fees"])
