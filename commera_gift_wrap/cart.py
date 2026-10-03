import frappe
from commera.sdk import cart
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils.data import cint, cstr, flt

GIFT_WRAP_FEE_DESCRIPTION = "Gift wrap"
MAX_MESSAGE_LENGTH = 200


# Guests are scoped by Commera's cart cookie inside cart.get_cart.
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=100, seconds=60 * 60)
def set_gift_wrap(enabled: bool | int | str, message: str | None = None) -> dict:
	current_cart = cart.get_cart()
	if not current_cart:
		frappe.throw(_("Add something to your cart before choosing gift wrap."))

	enabled = cint(enabled)
	message = (cstr(message).strip() or get_default_message(current_cart["customer"])) if enabled else ""
	checkout_summary = cart.set_cart_fields(
		{"commera_gift_wrap_enabled": enabled, "commera_gift_wrap_message": message}
	)
	return {"enabled": enabled, "message": message, "checkout_summary": checkout_summary}


def get_default_message(customer: str | None) -> str:
	if not customer:
		return ""
	return cstr(frappe.db.get_value("Customer", customer, "commera_gift_wrap_default_message"))


def get_gift_wrap_fees(quotation) -> list[dict]:
	settings = frappe.get_cached_doc("Gift Wrap Settings")
	if settings.simulate_failure:
		raise RuntimeError("Gift Wrap Settings: simulated fee hook failure")
	if not quotation.get("commera_gift_wrap_enabled"):
		return []

	total_qty = sum(flt(item.qty) for item in quotation.items)
	amount = flt(settings.price_per_item) * total_qty
	# Commera refuses a zero fee as an app error, so an unpriced wrap must charge nothing at all.
	if amount <= 0:
		return []
	return [
		{
			"description": GIFT_WRAP_FEE_DESCRIPTION,
			"amount": amount,
			"account_head": settings.fee_account or None,
		}
	]


def get_gift_wrap_refusal(quotation) -> str | None:
	if not quotation.get("commera_gift_wrap_enabled"):
		return None

	if len(cstr(quotation.get("commera_gift_wrap_message"))) > MAX_MESSAGE_LENGTH:
		return _("Your gift message is too long. Please keep it to {0} characters.").format(
			MAX_MESSAGE_LENGTH
		)

	item_codes = [item.item_code for item in quotation.items]
	not_wrappable = frappe.get_all(
		"Item",
		filters={"name": ["in", item_codes], "commera_gift_wrap_not_wrappable": 1},
		pluck="name",
	)
	for item in quotation.items:
		if item.item_code in not_wrappable:
			return _("{0} can't be gift wrapped.").format(item.item_name)
	return None
