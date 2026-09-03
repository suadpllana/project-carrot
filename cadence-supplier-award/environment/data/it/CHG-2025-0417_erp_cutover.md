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
purchase order under a PO-45xxx reporting number.

Goods receipts are posted in the system of record for the posting date and
carry that system's purchase order number.

Both number series appear on the mart's 2025 purchase-order reference extract.

INTERFACE NOTE
--------------
The QMS inspection interface receives the lot identifier from the receiving
transaction. It does not receive the supplier name; where a supplier name
appears on an inspection record it was keyed by hand and is not validated
against the vendor master.

ACTIONS
-------
  ACT-1  Migrate open purchase orders ........................ DONE 2025-07-01
  ACT-2  Publish ERP / mart number reference extract ......... DONE 2025-07-02
  ACT-3  Notify Sourcing, Finance, Quality ................... DONE 2025-07-02
  ACT-4  Restore supplier name on the QMS interface .......... DEFERRED (FY2027)
================================================================================
