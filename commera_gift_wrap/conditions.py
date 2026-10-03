import frappe


def has_gift_wrap_task(doctype: str, name: str) -> bool:
	return bool(frappe.db.exists("Gift Wrap Task", {"sales_order": name}))


def has_open_gift_wrap_task(doctype: str, name: str) -> bool:
	return bool(frappe.db.exists("Gift Wrap Task", {"sales_order": name, "status": "Open"}))


def is_item_wrappable(doctype: str, name: str) -> bool:
	return can_edit("Item", name) and not frappe.db.get_value("Item", name, "commera_gift_wrap_not_wrappable")


def is_item_not_wrappable(doctype: str, name: str) -> bool:
	return can_edit("Item", name) and bool(
		frappe.db.get_value("Item", name, "commera_gift_wrap_not_wrappable")
	)


def can_edit_customer(doctype: str, name: str) -> bool:
	return can_edit("Customer", name)


def can_edit(doctype: str, name: str) -> bool:
	return bool(frappe.has_permission(doctype, "write", name))
