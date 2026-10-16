# Copyright (c) 2026, Shrushti and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document


class TheatreBooking(Document):
    def validate(self):
        show = frappe.get_doc("Theatre Show", self.show)
        self.seat_no = (self.seat_no or "").strip().upper()
        if self.status == "Booked":
            if show.status != "Scheduled":
                frappe.throw(_("Show {0} is not open for booking").format(show.name))
            self.validate_seat_in_hall(show)
            self.validate_not_double_booked()
        self.amount_due = show.ticket_price
        self.booking_key = f"{self.show}-{self.seat_no}" if self.status == "Booked" else None

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
