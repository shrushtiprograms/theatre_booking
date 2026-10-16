# Theatre Booking

A Frappe app (on top of ERPNext) to schedule theatre shows and book seats.

## What it does
- Admin creates **Theatre Halls** (rows x seats per row) and schedules **Theatre Shows** (hall, date, start/end time, ticket price).
- Admin books a seat (e.g. `A5`) for a show against an ERPNext **Customer**. Each booking creates an ERPNext **Sales Invoice**, and the booking carries the **amount due**.
- Today's shows are visible and filterable: the Theatre Show list opens with `show_date = today`, and `get_shows(date, hall, status)` is a whitelisted API (defaults to today, Scheduled).

## Data model
| DocType | Purpose | Key fields |
|---|---|---|
| Theatre Hall | Master for a screen/hall | hall_name (unique, used as name), total_rows, seats_per_row |
| Theatre Show | A scheduled show | title, hall (Link), show_date, start_time, end_time, ticket_price, status |
| Theatre Booking | One seat for one show | show (Link), seat_no, customer (Link to ERPNext Customer), amount_due, sales_invoice (Link), status, booking_key |

Decisions:
- **Price lives on the Show**, because it is an attribute of the show. A booking takes `amount_due` from the show once, when it is created, so later price changes do not rewrite old bookings. It is set on the server and is read-only.
- **Money lives in the Sales Invoice.** The booking links to its invoice and, once the invoice exists, `amount_due` follows the invoice's outstanding amount. The booking does not keep its own payment records.
- **No Seat DocType.** Seats are implied by the hall size and validated from `seat_no`. A seat table would create hundreds of rows per hall with no extra rule it enables here.
- **Double booking** is blocked twice: an application check for a friendly error, and a unique `booking_key` (`show-seat`, empty when cancelled) so the database refuses it even under a race. Cancelled bookings free the seat.

## Server-side rules (all in controllers, not JavaScript)
- Show: price cannot be negative; end time after start time; no new shows in the past; no overlapping non-cancelled show in the same hall (back-to-back is allowed).
- Booking: show must be Scheduled; seat must look like `A5` and exist in the hall (rows x seats); seat not already booked for that show. `amount_due` is set from the show's price only when the booking is created; later price changes do not touch it. A cancelled booking cannot be reopened (a new booking is created instead).
- If the invoice cannot be created, the whole booking is rolled back, so there is never a booking without an invoice.

## ERPNext functionality used
- **Customer** (Link field): contact details, address and permissions come for free instead of a custom customer table.
- **Sales Invoice**: every booking creates and submits a Sales Invoice for the seat. Receivables, outstanding amount, payments and the ledger come from ERPNext instead of a custom payment table. Cancelling a booking cancels its invoice.
- **Item**: one generic non-stock service item, `Theatre Ticket`, created on the first booking (not at install, so install never depends on company setup). The rate on each invoice line is the booking's price.
- ERPNext is declared in `required_apps` so installation fails clearly without it.
- Frappe features: naming series, Link validation, role permissions, list-view filters, `frappe.whitelist`.

Looked at and not used:
- **Event** (calendar doctype): models a calendar entry, not seats or bookings.
- **Serial No per seat**: needs stock and Item machinery for a hall that has no inventory.
- **Item Price**: price differs per show, so it lives on Theatre Show.
- **Payment Entry / gateway**: out of scope; payments can be recorded against the Sales Invoice in ERPNext.

The invoice is created with `ignore_permissions` so a user who may create bookings does not also need Accounts permissions.

## Install
```
bench get-app https://github.com/shrushtiprograms/theatre_booking
bench --site <site> install-app theatre_booking   # site must have erpnext
```
The site needs a default Company (Global Defaults) with its default income and receivable accounts, which the ERPNext setup wizard creates.

## Known limitations
- Cancelling a Show does not auto-cancel its bookings.
- Resizing a Hall after bookings exist is not re-validated.