# FY2026 Demand Plan — Handover Note

**From:** Demand Planning
**To:** Strategic Sourcing
**Date:** 2025-11-24

The attached extract (`forecast_2026.csv`) is the S&OP-approved FY2026 build
plan as frozen at the November cycle. A few notes for whoever picks this up:

- The extract is a **direct dump from the planning cube**, so it carries the
  cube's own subtotal rows as well as the monthly detail. It has not been
  cleaned.
- Two parts share the extract because they run on the same cell. **SP-40** is
  the stainless valve seat that goes into the FM-200 series. **SP-22** is the
  brass orifice plate for the legacy FM-90 line; it is sourced on a separate
  agreement and is not part of the current valve-seat sourcing exercise.
- The `good_units_required` column is stated in **finished good pieces that
  must pass incoming inspection and reach the line** — it is net demand, not a
  purchase quantity, and it makes no allowance for supplier quality losses,
  safety stock or in-process scrap.
- The plan is frozen for FY2026. Do not re-forecast it.
- The cube keeps the last two S&OP cycles side by side and the dump is not
  filtered to one of them; the `plan_cycle` column says which cycle a row
  belongs to.

Ping me if the cube export looks off and I will re-run it.
