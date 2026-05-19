"""OTD ERP 模擬層 — Demo 資料產生器 v2

Matches actual model schema:
  ATP/CTP: check_id PK, qty, ATPResult, batch_recommended
  Shipping: shipping_id PK, no address field
  Logistics: tracking_no PK
  PO/SO Lines: qty not quantity
"""
import os, random, sys
from datetime import datetime, timedelta

import uuid as _uuid
from models import SessionLocal, engine, Base
from models import (
    Item, Customer, PurchaseOrder, POLine, SalesOrder, SOLine,
    ATPCheck, CTPCheck, Shipping, Invoice, Logistics,
    POStatus, SOStatus, ShippingStatus, InvoiceStatus, LogisticsStatus, ATPResult,
)

random.seed(42)


def uid(prefix): return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{_uuid.uuid4().hex[:6].upper()}"


def seed_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ═══ Customers (55) ═══
        cust_data = [
            ("CUST-001","ACME Electronics","Net30","buyer@acme.com"),
            ("CUST-002","Globex Semiconductor","Net60","order@globex.com"),
            ("CUST-003","Initech Solutions","Net30","po@initech.com"),
            ("CUST-004","Umbrella Corp","Net45","proc@umbrella.com"),
            ("CUST-005","Cyberdyne Systems","Net30","cyber@cyberdyne.com"),
            ("CUST-006","Stark Industries","Net30","pepper@stark.com"),
            ("CUST-007","Wayne Enterprises","Net60","lucius@wayne.com"),
            ("CUST-008","Oscorp Industries","Net45","harry@oscorp.com"),
            ("CUST-009","Aperture Science","Net30","cave@aperture.com"),
            ("CUST-010","Black Mesa Research","Net60","eli@blackmesa.com"),
            ("CUST-011","Toyota Motor Corp","Net45","supply@toyota.jp"),
            ("CUST-012","Honda Engineering","Net30","parts@honda.jp"),
            ("CUST-013","Siemens AG","Net60","proc@siemens.de"),
            ("CUST-014","Bosch GmbH","Net45","order@bosch.de"),
            ("CUST-015","General Electric","Net60","supply@ge.com"),
            ("CUST-016","Caterpillar Inc","Net45","parts@cat.com"),
            ("CUST-017","John Deere","Net30","supply@johndeere.com"),
            ("CUST-018","Mitsubishi Heavy","Net60","proc@mhi.jp"),
            ("CUST-019","Rolls-Royce PLC","Net60","proc@rolls-royce.com"),
            ("CUST-020","ABB Group","Net45","order@abb.com"),
            ("CUST-021","Google Cloud","Net30","vendor@google.com"),
            ("CUST-022","Microsoft Azure","Net45","supply@microsoft.com"),
            ("CUST-023","Amazon AWS","Net30","proc@amazon.com"),
            ("CUST-024","Meta Platforms","Net60","supply@meta.com"),
            ("CUST-025","Apple Inc","Net30","vendor@apple.com"),
            ("CUST-026","Netflix Inc","Net45","proc@netflix.com"),
            ("CUST-027","Salesforce Inc","Net30","order@salesforce.com"),
            ("CUST-028","Oracle Corp","Net60","supply@oracle.com"),
            ("CUST-029","SAP SE","Net45","proc@sap.de"),
            ("CUST-030","Adobe Systems","Net30","vendor@adobe.com"),
            ("CUST-031","Medtronic PLC","Net60","supply@medtronic.com"),
            ("CUST-032","Johnson & Johnson","Net45","proc@jnj.com"),
            ("CUST-033","Siemens Healthineers","Net60","order@siemens-health.de"),
            ("CUST-034","Roche Diagnostics","Net45","supply@roche-diag.ch"),
            ("CUST-035","Abbott Labs","Net30","proc@abbott.com"),
            ("CUST-036","Stryker Corp","Net60","supply@stryker.com"),
            ("CUST-037","Boston Scientific","Net45","order@bostonsci.com"),
            ("CUST-038","Baxter International","Net30","proc@baxter.com"),
            ("CUST-039","Zimmer Biomet","Net45","supply@zimmer.com"),
            ("CUST-040","Philips Healthcare","Net60","vendor@philips.nl"),
            ("CUST-041","Tesla Inc","Net30","supply@tesla.com"),
            ("CUST-042","BMW Group","Net60","proc@bmw.de"),
            ("CUST-043","Mercedes-Benz AG","Net45","supply@mercedes.de"),
            ("CUST-044","Volkswagen AG","Net60","order@vw.de"),
            ("CUST-045","Ford Motor Co","Net45","parts@ford.com"),
            ("CUST-046","General Motors","Net30","supply@gm.com"),
            ("CUST-047","Hyundai Motor","Net45","proc@hyundai.kr"),
            ("CUST-048","Nissan Motor Co","Net60","supply@nissan.jp"),
            ("CUST-049","Volvo Group","Net45","order@volvo.se"),
            ("CUST-050","BYD Auto","Net30","supply@byd.cn"),
            ("CUST-051","台積電 TSMC","Net30","supplier@tsmc.com"),
            ("CUST-052","鴻海 Foxconn","Net45","proc@foxconn.com"),
            ("CUST-053","聯發科 MediaTek","Net30","vendor@mediatek.com"),
            ("CUST-054","華碩 ASUS","Net45","supply@asus.com"),
            ("CUST-055","廣達 Quanta","Net60","order@quanta.com"),
        ]
        for cid, name, terms, email in cust_data:
            if not db.query(Customer).filter(Customer.customer_id == cid).first():
                db.add(Customer(customer_id=cid, name=name, terms=terms, contact_email=email))
        db.commit()

        # ═══ Items (100) ═══
        cat_cfg = [
            ("electronics", 7, 500, 2000, "PC"),
            ("mechanical",  14, 200, 500, "SET"),
            ("software",    1,  9999, 99999, "LIC"),
            ("packaging",   3,  1000, 5000, "PKG"),
            ("medical",     30, 50,  200, "UNIT"),
        ]
        all_items = []
        for cat, lt, ss, dc, unit in cat_cfg:
            for i in range(1, 21):
                code = f"SKU-{cat[:3].upper()}-{i:03d}"
                desc = f"{cat.title()} Part {i:03d}"
                existing = db.query(Item).filter(Item.item_code == code).first()
                if not existing:
                    db.add(Item(item_code=code, description=desc, unit=unit, category=cat,
                                lead_time_days=lt, safety_stock=ss, daily_capacity=dc))
                    all_items.append(code)
        db.commit()
        all_item_objs = db.query(Item).all()

        # ═══ PO (35) ═══
        base = datetime.now() - timedelta(days=180)
        for i in range(1, 36):
            cust = random.choice(cust_data)[0]
            po_id = f"PO-202{random.randint(3,6)}-{i:05d}"
            if db.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first():
                continue
            status = POStatus.PENDING if i <= 15 else POStatus.CONVERTED
            po = PurchaseOrder(po_id=po_id, customer_id=cust, po_date=base + timedelta(days=i*5), status=status)
            db.add(po)
            db.flush()
            for ln, item in enumerate(random.sample(all_item_objs, min(4, len(all_item_objs))), 1):
                db.add(POLine(
                    po_id=po_id, item_code=item.item_code,
                    qty=random.randint(50, 5000), line_no=ln,
                ))
        db.commit()
        n_po = db.query(PurchaseOrder).count()

        # ═══ SO (25) ═══
        status_cycle = [SOStatus.DRAFT, SOStatus.CONFIRMED, SOStatus.PARTIAL, SOStatus.COMPLETED]
        for i in range(1, 26):
            cust = random.choice(cust_data)[0]
            so_id = f"SO-2026-{i:05d}"
            if db.query(SalesOrder).filter(SalesOrder.so_id == so_id).first():
                continue
            so = SalesOrder(
                so_id=so_id, customer_id=cust,
                so_date=base + timedelta(days=100 + i*3),
                status=status_cycle[i % 4],
            )
            db.add(so)
            db.flush()
            for ln, item in enumerate(random.sample(all_item_objs, min(5, len(all_item_objs))), 1):
                db.add(SOLine(
                    so_id=so_id, item_code=item.item_code,
                    qty=random.randint(10, 20000), line_no=ln,
                ))
        db.commit()
        n_so = db.query(SalesOrder).count()

        # ═══ ATP/CTP checks (per SO) ═══
        all_sos = db.query(SalesOrder).all()
        for so in all_sos:
            lines = db.query(SOLine).filter(SOLine.so_id == so.so_id).all()
            for line in lines[:2]:
                cid = uid("ATP")
                if not db.query(ATPCheck).filter(ATPCheck.check_id == cid).first():
                    db.add(ATPCheck(
                        check_id=cid, item_code=line.item_code, qty=line.qty,
                        request_date=so.so_date,
                        available_qty=line.qty + random.randint(-100, 500),
                        result=ATPResult.ON_TIME if random.random() > 0.15 else ATPResult.INSUFFICIENT,
                        checked_at=datetime.now(),
                    ))
            if so.status != SOStatus.DRAFT:
                cid = uid("CTP")
                if not db.query(CTPCheck).filter(CTPCheck.check_id == cid).first():
                    db.add(CTPCheck(
                        check_id=cid, item_code=lines[0].item_code if lines else "SKU-001",
                        qty=sum(l.qty for l in lines), request_date=so.so_date,
                        available_date=so.so_date + timedelta(days=random.randint(7, 30)),
                        result=ATPResult.ON_TIME,
                        batch_recommended=random.randint(1, 5),
                        checked_at=datetime.now(),
                    ))
        db.commit()

        # ═══ Shipping (per SO, except DRAFT) ═══
        for so in all_sos:
            if so.status == SOStatus.DRAFT:
                continue
            sid = f"SHIP-{so.so_id[-8:]}"
            if db.query(Shipping).filter(Shipping.shipping_id == sid).first():
                continue
            sstat = random.choice(list(ShippingStatus))
            if so.status == SOStatus.COMPLETED and sstat in (ShippingStatus.PENDING, ShippingStatus.PACKING):
                sstat = random.choice([ShippingStatus.SHIPPED, ShippingStatus.DELIVERED])
            db.add(Shipping(
                shipping_id=sid, so_id=so.so_id, status=sstat,
                pallet_count=random.randint(1, 10),
                tracking_no=f"TKN{random.randint(100000,999999)}" if sstat in (ShippingStatus.SHIPPED, ShippingStatus.DELIVERED) else None,
            ))
        db.commit()

        # ═══ Invoice (per SO, mostly COMPLETED) ═══
        for so in all_sos:
            if random.random() < 0.3 and so.status != SOStatus.COMPLETED:
                continue
            iid = f"INV-{so.so_id[-8:]}"
            if db.query(Invoice).filter(Invoice.invoice_id == iid).first():
                continue
            lines = db.query(SOLine).filter(SOLine.so_id == so.so_id).all()
            amount = sum(l.qty * random.randint(5, 200) for l in lines)
            istat = InvoiceStatus.PAID if so.status == SOStatus.COMPLETED else InvoiceStatus.DRAFT if so.status == SOStatus.DRAFT else InvoiceStatus.ISSUED
            shipping = db.query(Shipping).filter(Shipping.so_id == so.so_id).first()
            db.add(Invoice(
                invoice_id=iid, so_id=so.so_id,
                shipping_id=shipping.shipping_id if shipping else None,
                amount=amount, issue_date=so.so_date + timedelta(days=1),
                status=istat,
            ))
        db.commit()

        # ═══ Logistics (per shipped/delivered shipping) ═══
        shippings = db.query(Shipping).filter(Shipping.status.in_([ShippingStatus.SHIPPED, ShippingStatus.DELIVERED])).all()
        for sh in shippings:
            tno = f"LGT{random.randint(200000,999999)}"
            if db.query(Logistics).filter(Logistics.tracking_no == tno).first():
                continue
            so = db.query(SalesOrder).filter(SalesOrder.so_id == sh.so_id).first()
            lstat = LogisticsStatus.DELIVERED if sh.status == ShippingStatus.DELIVERED else random.choice([LogisticsStatus.BOOKED, LogisticsStatus.IN_TRANSIT])
            db.add(Logistics(
                tracking_no=tno, shipping_id=sh.shipping_id,
                status=lstat,
                carrier=random.choice(["DHL","FedEx","UPS","新竹物流","黑貓宅急便","SF Express"]),
                eta=(so.so_date if so else datetime.now()) + timedelta(days=random.randint(3, 14)),
            ))
        db.commit()

        # ═══ Summary ═══
        print("═══════════════════════════════════════")
        print("  🎉 OTD Demo 資料匯入完成！")
        print("═══════════════════════════════════════")
        print(f"  Customers:   {db.query(Customer).count()}")
        print(f"  Items:       {db.query(Item).count()}")
        print(f"  PO:          {n_po}")
        print(f"  SO:          {n_so}")
        print(f"  ATP Checks:  {db.query(ATPCheck).count()}")
        print(f"  CTP Checks:  {db.query(CTPCheck).count()}")
        print(f"  Shipping:    {db.query(Shipping).count()}")
        print(f"  Invoices:    {db.query(Invoice).count()}")
        print(f"  Logistics:   {db.query(Logistics).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()