import sqlite3
import random
from datetime import datetime

def seed_amsavision_data(db_path: str = "amsavision.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create tables
    cur.executescript('''
        DROP TABLE IF EXISTS attendance;
        DROP TABLE IF EXISTS sales;
        DROP TABLE IF EXISTS inventory;

        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            employee_name TEXT,
            shift_date TEXT,
            check_in TEXT,
            check_out TEXT,
            status TEXT
        );

        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            invoice_id TEXT,
            client_name TEXT,
            amount REAL,
            tax_rate REAL,
            tax_paid REAL,
            status TEXT,
            created_at TEXT
        );

        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            item_name TEXT,
            category TEXT,
            stock_level REAL,
            reorder_point REAL,
            unit TEXT
        );
    ''')

    tenants = ["ams_retail", "ams_assoc", "mvm_dist", "dream_sleep"]
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Seed Attendance (Staff across 4 entities)
    staff_members = ["Ramesh K", "Karthik V", "Suresh M", "Pooja S", "Vignesh R", "Anand B"]
    for tenant in tenants:
        for name in staff_members:
            # Inject realistic biometric anomaly (late check-in)
            is_late = (tenant == "ams_retail" and name == "Karthik V") or (tenant == "mvm_dist" and name == "Anand B")
            check_in = "10:45 AM" if is_late else "09:15 AM"
            status = "LATE_ANOMALY" if is_late else "PRESENT"
            cur.execute(
                "INSERT INTO attendance (tenant_id, employee_name, shift_date, check_in, check_out, status) VALUES (?,?,?,?,?,?)",
                (tenant, name, today, check_in, "07:30 PM", status)
            )

    # 2. Seed Sales & GST Invoices
    for tenant in tenants:
        for i in range(1, 11):
            inv_code = f"INV-2026-{tenant.upper()}-{1000 + i}"
            base_amt = random.randint(25000, 320000)
            gst_rate = 0.18
            # Injected anomaly: MVM Distribution invoice has tax underpaid at 12% instead of 18%
            if tenant == "mvm_dist" and i == 4:
                tax_paid = round(base_amt * 0.12, 2)
            else:
                tax_paid = round(base_amt * gst_rate, 2)

            cur.execute(
                "INSERT INTO sales (tenant_id, invoice_id, client_name, amount, tax_rate, tax_paid, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (tenant, inv_code, f"Dealer {chr(64 + i)} Trade Partners", base_amt, gst_rate, tax_paid, "SETTLED", today)
            )

    # 3. Seed Inventory
    # Electronics items for retail & distribution arms
    electronics = [
        ("55-inch 4K UHD Smart TV", "Television", 14, 20, "Units"),
        ("1.5 Ton 5-Star Inverter AC", "Air Conditioners", 3, 15, "Units"), # Anomaly: Low stock
        ("Double Door 340L Refrigerator", "Refrigerators", 28, 10, "Units"),
        ("Front Load 8Kg Washing Machine", "Washing Machines", 12, 8, "Units")
    ]
    for tenant in ["ams_retail", "ams_assoc", "mvm_dist"]:
        for item, cat, stock, reorder, unit in electronics:
            cur.execute(
                "INSERT INTO inventory (tenant_id, item_name, category, stock_level, reorder_point, unit) VALUES (?,?,?,?,?,?)",
                (tenant, item, cat, stock, reorder, unit)
            )

    # Raw materials & finished goods for Dream & Sleep bedding factory
    bedding_items = [
        ("40-Density Memory Foam Blocks", "Raw Material", 120, 500, "Kg"), # Anomaly: Critical deficit!
        ("High-Tensile Pocketed Spring Coils", "Raw Material", 1400, 800, "Pcs"),
        ("Organic Quilted Jacquard Fabric", "Raw Material", 280, 400, "Meters"), # Anomaly: Below reorder
        ("Orthopedic King Mattress 8-inch", "Finished Goods", 18, 10, "Units"),
        ("Ergonomic Memory Foam Pillow", "Finished Goods", 65, 30, "Units")
    ]
    for item, cat, stock, reorder, unit in bedding_items:
        cur.execute(
            "INSERT INTO inventory (tenant_id, item_name, category, stock_level, reorder_point, unit) VALUES (?,?,?,?,?,?)",
            ("dream_sleep", item, cat, stock, reorder, unit)
        )

    conn.commit()
    conn.close()
    print("Database successfully seeded: amsavision.db")

if __name__ == "__main__":
    seed_amsavision_data()
