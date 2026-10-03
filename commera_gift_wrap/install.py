from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "Commera Gift Wrap"


def add_custom_fields():
	order_fields = [
		{
			"fieldname": "commera_gift_wrap_enabled",
			"label": "Gift Wrap",
			"fieldtype": "Check",
			"insert_after": "order_type",
			"module": MODULE,
		},
		{
			"fieldname": "commera_gift_wrap_message",
			"label": "Gift Message",
			"fieldtype": "Small Text",
			"insert_after": "commera_gift_wrap_enabled",
			"depends_on": "commera_gift_wrap_enabled",
			"module": MODULE,
		},
	]
	create_custom_fields(
		{
			"Quotation": order_fields,
			# Same fieldnames on both: ERPNext's Quotation to Sales Order mapper copies them across.
			"Sales Order": order_fields,
			"Item": [
				{
					"fieldname": "commera_gift_wrap_not_wrappable",
					"label": "Can't Be Gift Wrapped",
					"fieldtype": "Check",
					"insert_after": "is_stock_item",
					"module": MODULE,
				}
			],
			"Customer": [
				{
					"fieldname": "commera_gift_wrap_default_message",
					"label": "Default Gift Message",
					"fieldtype": "Small Text",
					"insert_after": "territory",
					"module": MODULE,
				}
			],
		},
		update=True,
	)
