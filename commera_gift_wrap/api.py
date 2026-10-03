import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce, Count, Sum
from frappe.utils.data import add_days, cint, cstr, getdate, nowdate

from commera_gift_wrap.cart import MAX_MESSAGE_LENGTH

TASK_STATUSES = ("Open", "Wrapped")
REPORT_WEEKS = 8
TOP_PRODUCTS = 5
RECENT_CUSTOMER_ORDERS = 3


@frappe.whitelist(methods=["GET"])
def get_wrap_tasks(status: str = "Open", start: int = 0, page_length: int = 20) -> dict:
	if status not in TASK_STATUSES:
		frappe.throw(_("Status must be one of {0}.").format(", ".join(TASK_STATUSES)))

	filters = {"status": status}
	rows = frappe.get_list(
		"Gift Wrap Task",
		filters=filters,
		fields=["name", "sales_order", "customer", "item_count", "message", "status", "creation"],
		# Open tasks are worked oldest first; wrapped ones are read as a log, newest first.
		order_by="creation asc" if status == "Open" else "modified desc",
		start=cint(start),
		page_length=cint(page_length),
	)
	total = frappe.get_list("Gift Wrap Task", filters=filters, fields=[{"COUNT": "*", "as": "count"}])
	return {"rows": rows, "total": total[0].count}


@frappe.whitelist(methods=["POST"])
def mark_wrapped(task: str) -> dict:
	wrap_task = save_task_wrapped(task)
	return {"name": wrap_task.name, "status": wrap_task.status}


@frappe.whitelist(methods=["POST"])
def mark_order_wrapped(name: str) -> str:
	task = frappe.db.get_value("Gift Wrap Task", {"sales_order": name})
	if not task:
		frappe.throw(_("Order {0} has no gift wrap to mark.").format(name))
	save_task_wrapped(task)
	return _("Order {0} marked wrapped.").format(name)


def save_task_wrapped(task: str):
	wrap_task = frappe.get_doc("Gift Wrap Task", task, for_update=True)
	wrap_task.check_permission("write")
	if wrap_task.status != "Wrapped":
		wrap_task.status = "Wrapped"
		wrap_task.save()
	return wrap_task


@frappe.whitelist(methods=["GET"])
def get_order_gift_wrap(sales_order: str) -> dict | None:
	frappe.has_permission("Sales Order", "read", sales_order, throw=True)
	tasks = frappe.get_list(
		"Gift Wrap Task",
		filters={"sales_order": sales_order},
		fields=["name", "status", "message", "item_count", "creation", "modified"],
		limit=1,
	)
	return tasks[0] if tasks else None


@frappe.whitelist(methods=["GET"])
def get_item_gift_wrap(item: str) -> dict:
	frappe.has_permission("Item", "read", item, throw=True)
	frappe.has_permission("Gift Wrap Task", "read", throw=True)
	orders_by_status = get_item_wrap_counts(item)
	return {"open": orders_by_status.get("Open", 0), "wrapped": orders_by_status.get("Wrapped", 0)}


def get_item_wrap_counts(item: str) -> dict:
	item_codes = [item, *frappe.get_all("Item", filters={"variant_of": item}, pluck="name")]
	wrap_task = DocType("Gift Wrap Task")
	order_item = DocType("Sales Order Item")
	rows = (
		frappe.qb.from_(wrap_task)
		.join(order_item)
		.on((order_item.parent == wrap_task.sales_order) & (order_item.parenttype == "Sales Order"))
		.where(order_item.item_code.isin(item_codes))
		.groupby(wrap_task.status)
		.select(wrap_task.status, Count(wrap_task.name).distinct().as_("orders"))
		.run(as_dict=True)
	)
	return {row.status: cint(row.orders) for row in rows}


@frappe.whitelist(methods=["POST"])
def update_gift_message(sales_order: str, message: str) -> dict:
	task = frappe.db.get_value("Gift Wrap Task", {"sales_order": sales_order})
	if not task:
		frappe.throw(_("Order {0} has no gift wrap.").format(sales_order))
	wrap_task = frappe.get_doc("Gift Wrap Task", task, for_update=True)
	wrap_task.check_permission("write")
	message = cstr(message).strip()
	if not message:
		frappe.throw(_("Write a gift message."))
	validate_message_length(message)
	wrap_task.message = message
	wrap_task.save()
	return {"name": wrap_task.name, "message": wrap_task.message}


def validate_message_length(message: str):
	if len(message) > MAX_MESSAGE_LENGTH:
		frappe.throw(
			_("Keep the gift message to {0} characters. This one has {1}.").format(
				MAX_MESSAGE_LENGTH, len(message)
			)
		)


@frappe.whitelist(methods=["POST"])
def turn_off_item_gift_wrap(name: str) -> str:
	save_item_wrappable(name, False)
	return _("Gift wrap is off for {0}.").format(frappe.db.get_value("Item", name, "item_name"))


@frappe.whitelist(methods=["POST"])
def turn_on_item_gift_wrap(name: str) -> str:
	save_item_wrappable(name, True)
	return _("Gift wrap is on for {0}.").format(frappe.db.get_value("Item", name, "item_name"))


def save_item_wrappable(item: str, wrappable: bool):
	frappe.has_permission("Item", "write", item, throw=True)
	# The cart checks the variant a shopper picked, so the flag follows the product onto every variant.
	item_codes = [item, *frappe.get_all("Item", filters={"variant_of": item}, pluck="name")]
	frappe.db.set_value(
		"Item", {"name": ["in", item_codes]}, "commera_gift_wrap_not_wrappable", 0 if wrappable else 1
	)


@frappe.whitelist(methods=["GET"])
def get_customer_gift_wrap(customer: str) -> dict:
	frappe.has_permission("Customer", "read", customer, throw=True)
	filters = {"customer": customer}
	orders = frappe.get_list(
		"Gift Wrap Task",
		filters=filters,
		fields=["name", "sales_order", "status", "message", "creation"],
		order_by="creation desc",
		limit=RECENT_CUSTOMER_ORDERS,
	)
	return {
		"orders": orders,
		"total": frappe.db.count("Gift Wrap Task", filters) if orders else 0,
		"default_message": frappe.db.get_value("Customer", customer, "commera_gift_wrap_default_message"),
	}


@frappe.whitelist(methods=["POST"])
def set_customer_default_message(customer: str, message: str | None = None) -> dict:
	frappe.has_permission("Customer", "write", customer, throw=True)
	message = cstr(message).strip()
	validate_message_length(message)
	frappe.db.set_value("Customer", customer, "commera_gift_wrap_default_message", message)
	return {"default_message": message}


@frappe.whitelist(methods=["GET"])
def get_wrap_report() -> dict:
	frappe.has_permission("Gift Wrap Task", "read", throw=True)
	today = getdate(nowdate())
	first_week_start = add_days(today, -today.weekday() - 7 * (REPORT_WEEKS - 1))
	thirty_days_ago = add_days(today, -30)

	tasks = frappe.get_list(
		"Gift Wrap Task",
		filters={"creation": [">=", first_week_start]},
		fields=["status", "item_count", "creation"],
		limit=0,
	)
	weeks = [
		{"week_start": add_days(first_week_start, 7 * week), "orders": 0, "wrapped": 0}
		for week in range(REPORT_WEEKS)
	]
	for task in tasks:
		week = weeks[(getdate(task.creation) - first_week_start).days // 7]
		week["orders"] += 1
		week["wrapped"] += task.status == "Wrapped"

	recent = [task for task in tasks if getdate(task.creation) >= thirty_days_ago]
	return {
		"waiting": frappe.db.count("Gift Wrap Task", {"status": "Open"}),
		"orders_last_30_days": len(recent),
		"items_last_30_days": sum(cint(task.item_count) for task in recent),
		"wrapped_last_30_days": sum(task.status == "Wrapped" for task in recent),
		"weeks": weeks,
		"top_products": get_top_wrapped_products(),
	}


def get_top_wrapped_products() -> list[dict]:
	wrap_task = DocType("Gift Wrap Task")
	order_item = DocType("Sales Order Item")
	item = DocType("Item")
	product = Coalesce(item.variant_of, item.name)
	rows = (
		frappe.qb.from_(wrap_task)
		.join(order_item)
		.on((order_item.parent == wrap_task.sales_order) & (order_item.parenttype == "Sales Order"))
		.join(item)
		.on(item.name == order_item.item_code)
		.groupby(product)
		.select(
			product.as_("item"),
			Count(wrap_task.name).distinct().as_("orders"),
			Sum(order_item.qty).as_("quantity"),
		)
		.orderby(Count(wrap_task.name).distinct(), order=frappe.qb.desc)
		.limit(TOP_PRODUCTS)
		.run(as_dict=True)
	)
	item_names = dict(
		frappe.get_all(
			"Item",
			filters={"name": ["in", [row.item for row in rows]]},
			fields=["name", "item_name"],
			as_list=True,
		)
	)
	for row in rows:
		row.item_name = item_names.get(row.item, row.item)
	return rows
