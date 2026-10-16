# Theatre Booking

A Frappe app (on top of ERPNext) to schedule theatre shows and book seats.

## What it does
- Admin creates **Theatre Halls** (rows x seats per row) and schedules **Theatre Shows** (hall, date, start/end time, ticket price).
- Admin books a seat (e.g. `A5`) for a show against an ERPNext **Customer**. The booking carries the **amount due**, copied from the show's ticket price.
- Today's shows are visible and filterable: the Theatre Show list opens with `show_date = today`, and `get_shows(date, hall, status)` is a whitelisted API (defaults to today, Scheduled).

## Data model
| DocType | Purpose | Key fields |
|---|---|---|
| Theatre Hall | Master for a screen/hall | hall_name (unique, used as name), total_rows, seats_per_row |
| Theatre Show | A scheduled show | title, hall (Link), show_date, start_time, end_time, ticket_price, status |
| Theatre Booking | One seat for one show | show (Link), seat_no, customer (Link to ERPNext Customer), amount_due, status, booking_key |

Decisions:
- **Price lives on the Show**, because it is an attribute of the show. A booking stores `amount_due` as a snapshot, so later price changes do not rewrite old bookings. It is set on the server and is read-only.
- **No Seat DocType.** Seats are implied by the hall size and validated from `seat_no`. A seat table would create hundreds of rows per hall with no extra rule it enables here.
- **Double booking** is blocked twice: an application check for a friendly error, and a unique `booking_key` (`show-seat`, empty when cancelled) so the database refuses it even under a race. Cancelled bookings free the seat.

## Server-side rules (all in controllers, not JavaScript)
- Show: price cannot be negative; end time after start time; no new shows in the past; no overlapping non-cancelled show in the same hall (back-to-back is allowed).
- Booking: show must be Scheduled; seat must look like `A5` and exist in the hall (rows x seats); seat not already booked for that show; `amount_due` always taken from the show.

## ERPNext functionality used
- **Customer** (Link field): contact details, address and permissions come for free instead of a custom customer table.
- **Company / currency** setup from the ERPNext setup wizard: the Currency field uses the company currency.
- ERPNext is declared in `required_apps` so installation fails clearly without it.
- Frappe features: naming series, Link validation, role permissions, list-view filters, `frappe.whitelist`.

Looked at but not used in this version: **Sales Invoice / Item**. They would make `amount_due` the invoice's outstanding amount and give payments and ledger entries for free. Here `amount_due` is a stored snapshot; payments are out of scope.

## Install
bench get-app <repo-url>
bench --site <site> install-app theatre_booking # site must have erpnext

## Known limitations
- Cancelling a Show does not auto-cancel its bookings.
- Resizing a Hall after bookings exist is not re-validated.
