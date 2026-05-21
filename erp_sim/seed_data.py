"""OTD ERP 模擬層 - 預設測試資料"""

from models import Base, Customer, Item, SessionLocal, engine


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Customers ──────────────────────────────────────────────────────
        customers = [
            Customer(customer_id="CUST-001", name="ACME Corp", terms="Net30", contact_email="buyer@acme.com"),
            Customer(customer_id="CUST-002", name="Globex Inc", terms="Net60", contact_email="order@globex.com"),
            Customer(customer_id="CUST-003", name="Initech",  terms="Net30", contact_email="po@initech.com"),
        ]
        for c in customers:
            if not db.query(Customer).filter(Customer.customer_id == c.customer_id).first():
                db.add(c)

        # ── Items ──────────────────────────────────────────────────────────
        items = [
            Item(item_code="SKU-001", description="電子零件 A型", unit="PC", category="electronics",  lead_time_days=7,  safety_stock=500,  daily_capacity=2000),
            Item(item_code="SKU-002", description="電子零件 B型", unit="PC", category="electronics",  lead_time_days=10, safety_stock=300,  daily_capacity=1500),
            Item(item_code="SKU-003", description="外殼組件",     unit="SET", category="mechanical",   lead_time_days=14, safety_stock=200,  daily_capacity=500),
            Item(item_code="SKU-004", description="包裝材料",     unit="PKG", category="packaging",    lead_time_days=3,  safety_stock=1000, daily_capacity=5000),
            Item(item_code="SKU-005", description="軟體授權",     unit="LIC", category="software",    lead_time_days=1,  safety_stock=9999, daily_capacity=99999),
        ]
        for i in items:
            if not db.query(Item).filter(Item.item_code == i.item_code).first():
                db.add(i)

        db.commit()
        print(f"✅ Seed complete: {len(customers)} customers, {len(items)} items")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
