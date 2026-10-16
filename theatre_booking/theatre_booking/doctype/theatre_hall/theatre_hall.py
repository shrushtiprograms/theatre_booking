# Copyright (c) 2026, Shrushti and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

MAX_ROWS = 26  # seat letters A-Z


class TheatreHall(Document):
    def validate(self):
        if not self.total_rows or not (1 <= self.total_rows <= MAX_ROWS):
            frappe.throw(_("Total rows must be between 1 and {0}").format(MAX_ROWS))
        if not self.seats_per_row or self.seats_per_row < 1:
            frappe.throw(_("Seats per row must be at least 1"))
        if not self.is_new():
            self.validate_resize()

    def validate_resize(self):
        before = self.get_doc_before_save()
        if not before:
            return
        shrunk = (self.total_rows < before.total_rows
                  or self.seats_per_row < before.seats_per_row)
        if not shrunk:
            return
        shows = frappe.get_all("Theatre Show", filters={"hall": self.name}, pluck="name")
        if shows and frappe.db.exists(
                "Theatre Booking", {"show": ["in", shows], "status": "Booked"}):
            frappe.throw(_("Cannot shrink {0}: it has active bookings").format(self.name))