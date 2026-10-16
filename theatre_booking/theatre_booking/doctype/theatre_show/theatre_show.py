# Copyright (c) 2026, Shrushti and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, get_time


class TheatreShow(Document):
    def validate(self):
        if self.ticket_price is None or self.ticket_price < 0:
            frappe.throw(_("Ticket price cannot be negative"))
        if get_time(self.end_time) <= get_time(self.start_time):
            frappe.throw(_("End time must be after start time"))
        if (self.is_new() or self.has_value_changed("show_date")) and getdate(self.show_date) < getdate(nowdate()):
            frappe.throw(_("Cannot schedule a show in the past"))
        self.validate_hall_change()
        self.check_hall_overlap()

    def validate_hall_change(self):
        # seats only mean something relative to a hall, so do not move a show
        # that already has active bookings
        if self.is_new() or not self.has_value_changed("hall"):
            return
        if frappe.db.exists("Theatre Booking", {"show": self.name, "status": "Booked"}):
            frappe.throw(_("Cannot change the hall: this show has active bookings"))

    def check_hall_overlap(self):
        if self.status == "Cancelled":
            return
        clash = frappe.db.exists("Theatre Show", {
            "hall": self.hall,
            "show_date": self.show_date,
            "status": ["!=", "Cancelled"],
            "name": ["!=", self.name],
            "start_time": ["<", self.end_time],
            "end_time": [">", self.start_time],
        })
        if clash:
            frappe.throw(_("Hall {0} is already booked at this time by {1}").format(self.hall, clash))

    def on_update(self):
        if self.status == "Cancelled" and self.has_value_changed("status"):
            self.cancel_bookings()

    def cancel_bookings(self):
        # Saving each booking runs its own rules, which also cancels its Sales Invoice.
        # If an invoice cannot be cancelled (e.g. a payment is linked), the error
        # propagates and the show stays un-cancelled.
        for name in frappe.get_all(
                "Theatre Booking", filters={"show": self.name, "status": "Booked"}, pluck="name"):
            booking = frappe.get_doc("Theatre Booking", name)
            booking.status = "Cancelled"
            booking.save(ignore_permissions=True)


@frappe.whitelist()
def get_shows(date=None, hall=None, status="Scheduled"):
    filters = {"show_date": date or nowdate()}
    if hall:
        filters["hall"] = hall
    if status:
        filters["status"] = status
    return frappe.get_list(
        "Theatre Show",
        filters=filters,
        fields=["name", "title", "hall", "show_date", "start_time", "end_time", "ticket_price", "status"],
        order_by="start_time asc",
    )