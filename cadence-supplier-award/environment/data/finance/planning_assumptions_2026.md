# FY2026 Planning Assumptions — Standing Finance Policy

**Issued by:** Corporate FP&A, Cadence Instruments LLC
**Applies to:** all FY2026 budget submissions, make-vs-buy cases and sourcing
award recommendations
**Revision:** 4 (supersedes revision 3 of 2025-08-02)

These rates are mandatory inputs for FY2026 planning. Do not substitute spot
rates, forward curves, forecasts of your own, or trailing actuals for any
figure in this memo.

---

## 1. Planning exchange rates (mandatory for FY2026)

Every FY2026 submission converts foreign-currency amounts at the rates below.
They are set once per planning cycle by Treasury and are held flat for the
whole contract year.

| Currency | FY2026 planning rate |
| --- | --- |
| Euro | USD 1.0850 per 1 EUR |
| Pound sterling | USD 1.2720 per 1 GBP |
| Mexican peso | USD 0.0545 per 1 MXN |

Historical daily rates are retained in the treasury export
(`fx/fx_daily_2025.csv`) for restating prior-year actuals. They are not to be
used for FY2026 planning.

## 2. Cost of capital

Weighted average cost of capital: **9.0% per annum.**

## 3. Payment terms — working capital valuation

Cadence values supplier payment terms against a **standard baseline of Net
30.** For any supplier, the annual working-capital adjustment is:

```
working_capital_adjustment_usd
    = annual supplier-invoiced material spend (USD, before any rebate)
      x 9.0%
      x (30 - payment_days) / 365
```

Terms longer than Net 30 produce a **negative** number (a benefit to Cadence).
Terms shorter than Net 30 produce a **positive** number (a cost).

Where a supplier offers a cash discount for early settlement, evaluate both the
discounted early-payment date and the standard due date, and plan on whichever
is cheaper to Cadence in total. A cash discount taken is a reduction of spend;
the earlier payment date is then used in the formula above.

Rebates settled as year-end credit notes do not change invoice due dates and
are excluded from the spend base in the formula above.

## 4. Inbound freight

Inbound freight, duty and brokerage for lanes where Cadence is the paying party
are budgeted from the published logistics tariff
(`logistics/freight_tariff_2026.csv`). The tariff is quoted per 1,000 pieces
plus a fixed brokerage charge per inbound shipment. Whether a lane is billed to
Cadence at all is governed by the Incoterm agreed in the relevant supply
contract; where a supplier's price is delivered-duty-paid, no separate freight
is budgeted for that supplier.

## 5. Scrap and disposal

Pieces **scrapped** at incoming inspection are moved to the scrap cage and
disposed of under the Aurora waste contract. The standing burdened rate for
FY2026 is **USD 1.25 per scrapped piece**, covering segregation, handling,
documentation and disposal.

Nonconforming pieces that leave the site on a return authorisation are not
disposed of by Cadence and carry no disposal charge. Return freight and
handling on authorised returns are borne by the supplier under the standing
supply agreements and are not budgeted by Cadence.

## 6. Presentation

**Cadence's fiscal year 2026 runs from 1 April 2026 to 31 March 2027.**

All sourcing award cases are presented in **US dollars**. Do not annualize
from a partial period, and do not present a case in a supplier's invoicing
currency.
