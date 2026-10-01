import frappe
from commera.api.payments import cart_write_lock, save_cart_quotation, validate_cart_is_not_in_checkout
from commera.api.shipping import get_checkout_summary
from commera.checkout_hooks import apply_app_fees
from commera.core import _get_cart_quotation
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils.data import cint, cstr, flt

GIFT_WRAP_FEE_DESCRIPTION = "Gift wrap"
MAX_MESSAGE_LENGTH = 200


# Guests are scoped by Commera's cart cookie inside _get_cart_quotation.
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=100, seconds=60 * 60)
def set_gift_wrap(enabled: bool | int | str, message: str | None = None) -> dict:
	quotation = _get_cart_quotation()
	if quotation.is_new():
		frappe.throw(_("Add something to your cart before choosing gift wrap."))

	with cart_write_lock(quotation):
		validate_cart_is_not_in_checkout(quotation.name)
		quotation.commera_gift_wrap_enabled = cint(enabled)
		quotation.commera_gift_wrap_message = (
			cstr(message).strip() if quotation.commera_gift_wrap_enabled else ""
		)
		apply_app_fees(quotation)
		save_cart_quotation(quotation)
		return {
			"enabled": quotation.commera_gift_wrap_enabled,
			"message": quotation.commera_gift_wrap_message,
			"checkout_summary": get_checkout_summary(quotation),
		}


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
