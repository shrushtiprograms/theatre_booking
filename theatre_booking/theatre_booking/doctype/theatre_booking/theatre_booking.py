# Copyright (c) 2026, Shrushti and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

TICKET_ITEM = "Theatre Ticket"


class TheatreBooking(Document):
    def validate(self):
        show = frappe.get_doc("Theatre Show", self.show)
        self.seat_no = (self.seat_no or "").strip().upper()
        self.validate_no_reopen()
        if self.status == "Booked":
            if show.status != "Scheduled":
                frappe.throw(_("Show {0} is not open for booking").format(show.name))
            self.validate_seat_in_hall(show)
            self.validate_not_double_booked()
        self.set_amount_due(show)
        self.booking_key = f"{self.show}-{self.seat_no}" if self.status == "Booked" else None

    def validate_no_reopen(self):
        before = self.get_doc_before_save()
        if before and before.status == "Cancelled" and self.status != "Cancelled":
            frappe.throw(_("A cancelled booking cannot be reopened. Create a new booking."))

    def validate_seat_in_hall(self, show):
        m = re.fullmatch(r"([A-Z])(\d+)", self.seat_no)
        if not m:
            frappe.throw(_("Seat No must look like A5 (row letter + seat number)"))
        hall = frappe.get_doc("Theatre Hall", show.hall)
        row = ord(m.group(1)) - ord("A") + 1
        seat = int(m.group(2))
        if row > hall.total_rows or not (1 <= seat <= hall.seats_per_row):
            frappe.throw(_("Seat {0} does not exist in {1} ({2} rows x {3} seats)").format(
                self.seat_no, hall.name, hall.total_rows, hall.seats_per_row))

    def validate_not_double_booked(self):
        clash = frappe.db.exists("Theatre Booking", {
            "show": self.show, "seat_no": self.seat_no,
            "status": "Booked", "name": ["!=", self.name]})
        if clash:
            frappe.throw(_("Seat {0} is already booked ({1})").format(self.seat_no, clash))

    def set_amount_due(self, show):
        # New booking: snapshot the show's price (client value ignored).
        if self.is_new():
            self.amount_due = flt(show.ticket_price)
            return
        # Existing booking: show price changes must not touch it,
        # and the client cannot change the invoice link or amount.
        before = self.get_doc_before_save()
        self.sales_invoice = before.sales_invoice
        if self.sales_invoice and self.status == "Booked":
            # the invoice is the source of truth once payments happen
            self.amount_due = flt(frappe.db.get_value(
                "Sales Invoice", self.sales_invoice, "outstanding_amount"))
        else:
            self.amount_due = before.amount_due

    def after_insert(self):
        if self.status == "Booked":
            invoice = self.create_sales_invoice()
            self.db_set("sales_invoice", invoice.name)

    def on_update(self):
        if self.status == "Cancelled" and self.has_value_changed("status"):
            self.cancel_sales_invoice()

    def create_sales_invoice(self):
        show = frappe.db.get_value(
            "Theatre Show", self.show, ["title", "show_date"], as_dict=True)
        company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company:
            frappe.throw(_("Default Company is not set in Global Defaults"))

        today = nowdate()
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": self.customer,
            "company": company,
            "posting_date": today,
            "due_date": today,  # ticket is payable at booking time
            "items": [{
                "item_code": get_ticket_item(),
                "qty": 1,
                "rate": self.amount_due,
                "description": f"{show.title} | {show.show_date} | Seat {self.seat_no}",
            }],
        })
        invoice.flags.ignore_permissions = True
        invoice.insert()
        invoice.submit()
        return invoice

    def cancel_sales_invoice(self):
        if not self.sales_invoice:
            return
        invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)
        if invoice.docstatus == 1:
            invoice.flags.ignore_permissions = True
            invoice.cancel()  # if a payment is linked, ERPNext raises a clear error


def get_ticket_item():
    """Generic non-stock item for tickets. Created lazily on first booking,
    so app install never depends on company or wizard state."""
    if not frappe.db.exists("Item", TICKET_ITEM):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": TICKET_ITEM,
            "item_name": TICKET_ITEM,
            "item_group": "Services",
            "stock_uom": "Nos",
            "is_stock_item": 0,
        })
        item.flags.ignore_permissions = True
        item.insert()
    return TICKET_ITEM