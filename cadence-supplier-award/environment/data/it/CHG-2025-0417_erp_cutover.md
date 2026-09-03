================================================================================
CADENCE INSTRUMENTS LLC - IT CHANGE RECORD
================================================================================
Change          : CHG-2025-0417
Title           : Purchasing and receiving go-live on the new ERP
Requested by    : D. Okafor, Supply Chain Systems
Go-live         : 2025-07-01 06:00 CT
Status          : Closed - complete
Affected systems: ERP (purchasing, receiving), purchasing reporting mart,
                  QMS incoming-inspection interface
================================================================================

SUMMARY
-------
Purchase order entry and goods receiving moved from the legacy system to the
new ERP at 06:00 on 2025-07-01. Open purchase orders were migrated into the
ERP that morning. The ERP numbers purchase orders in its own ten-digit range
(4500xxxxxx); the legacy PO-45xxx numbers do not exist in the ERP.

The purchasing reporting mart, which produces the purchase-order extract used
by Sourcing and Finance, was NOT re-platformed. It continues to key every
purchase order under a PO-45xxx reporting number, assigning one to each order
raised in the ERP after go-live so that reporting has one continuous series.

Goods receipts posted in the ERP from go-live onward reference the ERP purchase
order number. Receipts posted before go-live reference the legacy number, and
the receipts extract carries whichever number the posting system used.

A crosswalk between the two number series is published with the purchasing
extracts (purchasing/po_crosswalk_erp_cutover.csv) and covers every purchase
order in the mart, whether it was raised before or after go-live.

KNOWN SIDE EFFECT
-----------------
The QMS incoming-inspection interface receives the lot identifier from the
receiving transaction but no longer receives the supplier name, which the
legacy interface had populated. Inspectors may key the supplier name by hand
on the inspection record; the field is free text and is not validated against
the vendor master. This has been the case on some records since before go-live
and is not scheduled to be fixed.

ACTIONS
-------
  ACT-1  Migrate open purchase orders ........................ DONE 2025-07-01
  ACT-2  Publish PO number crosswalk to the mart ............. DONE 2025-07-02
  ACT-3  Notify Sourcing, Finance, Quality ................... DONE 2025-07-02
  ACT-4  Restore supplier name on the QMS interface .......... DEFERRED (FY2027)
================================================================================
