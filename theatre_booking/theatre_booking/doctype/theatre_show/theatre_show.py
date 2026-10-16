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
        self.check_hall_overlap()

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
