import sqlite3

def run_dbt_transformations(db_path: str = "amsavision.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript('''
        -- 1. Sales Breakdown Mart
        DROP VIEW IF EXISTS fct_company_sales_breakdown;
        CREATE VIEW fct_company_sales_breakdown AS
        SELECT 
            tenant_id,
            COUNT(id) AS total_orders,
            ROUND(SUM(amount), 2) AS gross_sales,
            ROUND(AVG(amount), 2) AS average_ticket_size,
            ROUND(SUM(tax_paid), 2) AS total_gst_remitted,
            ROUND(SUM(amount * tax_rate) - SUM(tax_paid), 2) AS tax_leakage_amount
        FROM sales
        GROUP BY tenant_id;

        -- 2. Line-Item Level Sales Orders
        CREATE TABLE IF NOT EXISTS sales_order_items (
            line_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            product_category TEXT,
            item_name TEXT,
            quantity_sold INTEGER,
            unit_price REAL,
            total_price REAL,
            order_date TEXT
        );

        -- 3. dbt Mart: fct_product_sales_volume
        DROP VIEW IF EXISTS fct_product_sales_volume;
        CREATE VIEW fct_product_sales_volume AS
        SELECT 
            tenant_id,
            product_category,
            item_name,
            SUM(quantity_sold) AS total_units_sold,
            ROUND(SUM(total_price), 2) AS total_product_revenue
        FROM sales_order_items
        GROUP BY tenant_id, product_category, item_name;

        -- 4. Customer Support Tickets
        CREATE TABLE IF NOT EXISTS customer_tickets (
            ticket_id TEXT PRIMARY KEY,
            tenant_id TEXT,
            customer_name TEXT,
            product_category TEXT,
            issue_type TEXT,
            status TEXT,
            created_at TEXT
        );

        -- 5. HR & Payroll Table
        CREATE TABLE IF NOT EXISTS hr_payroll (
            emp_id TEXT PRIMARY KEY,
            tenant_id TEXT,
            employee_name TEXT,
            designation TEXT,
            monthly_base_wage REAL,
            leave_balance_days INTEGER,
            leaves_taken_this_month INTEGER,
            status TEXT
        );

        -- 6. dbt Mart: fct_hr_payroll_summary
        DROP VIEW IF EXISTS fct_hr_payroll_summary;
        CREATE VIEW fct_hr_payroll_summary AS
        SELECT 
            tenant_id,
            COUNT(emp_id) AS total_employees,
            ROUND(SUM(monthly_base_wage), 2) AS total_monthly_payroll,
            ROUND(AVG(monthly_base_wage), 2) AS avg_monthly_wage,
            SUM(leaves_taken_this_month) AS total_leaves_taken,
            SUM(leave_balance_days) AS remaining_leave_pool
        FROM hr_payroll
        GROUP BY tenant_id;

        -- 7. Logistics & Fleet Deliveries
        CREATE TABLE IF NOT EXISTS logistics_dispatches (
            dispatch_id TEXT PRIMARY KEY,
            tenant_id TEXT,
            vehicle_no TEXT,
            destination TEXT,
            cargo_summary TEXT,
            delivery_status TEXT,
            eta TEXT
        );

        -- 8. Human-In-The-Loop Agent Action Execution Queue
        CREATE TABLE IF NOT EXISTS swarm_actions (
            action_id TEXT PRIMARY KEY,
            origin_agent TEXT,
            tenant_id TEXT,
            action_title TEXT,
            payload_details TEXT,
            impact_level TEXT,
            status TEXT,
            created_at TEXT
        );
    ''')

    # Seed Line-Item Sales Records
    items_seed = [
        ("ams_retail", "Television", "55-inch 4K UHD Smart TV", 28, 45000.0, 1260000.0, "2026-10-27"),
        ("ams_retail", "Air Conditioners", "1.5 Ton 5-Star Inverter AC", 16, 38000.0, 608000.0, "2026-10-27"),
        ("ams_retail", "Refrigerators", "Double Door 340L Refrigerator", 12, 32000.0, 384000.0, "2026-10-26"),
        ("ams_assoc", "Television", "55-inch 4K UHD Smart TV", 45, 42000.0, 1890000.0, "2026-10-27"),
        ("ams_assoc", "Air Conditioners", "1.5 Ton 5-Star Inverter AC", 25, 35000.0, 875000.0, "2026-10-25"),
        ("mvm_dist", "Television", "55-inch 4K UHD Smart TV", 36, 42000.0, 1512000.0, "2026-10-27"),
        ("mvm_dist", "Refrigerators", "Double Door 340L Refrigerator", 22, 31000.0, 682000.0, "2026-10-26"),
        ("dream_sleep", "Mattress", "Orthopedic King Mattress 8-inch", 38, 28000.0, 1064000.0, "2026-10-27"),
        ("dream_sleep", "Pillow", "Ergonomic Memory Foam Pillow", 120, 1800.0, 216000.0, "2026-10-27")
    ]
    cur.executemany('''
        INSERT OR REPLACE INTO sales_order_items (tenant_id, product_category, item_name, quantity_sold, unit_price, total_price, order_date)
        VALUES (?,?,?,?,?,?,?)
    ''', items_seed)

    # Seed Logistics Dispatches
    fleet_seed = [
        ("DSP-401", "ams_assoc", "TN-09-CB-1124", "Salem Electronics Hub", "30x 55\" Smart TVs", "IN_TRANSIT", "Today 04:30 PM"),
        ("DSP-402", "dream_sleep", "TN-22-BA-9941", "Chennai Central Showroom", "25x Orthopedic King Mattresses", "DISPATCHED", "Today 06:00 PM"),
        ("DSP-403", "mvm_dist", "TN-07-AL-5512", "Coimbatore Regional Depot", "18x Double Door Refrigerators", "DELIVERED", "Delivered 11:15 AM")
    ]
    cur.executemany("INSERT OR REPLACE INTO logistics_dispatches VALUES (?,?,?,?,?,?,?)", fleet_seed)

    # Seed Customer Support Tickets
    tickets = [
        ("TCK-101", "ams_retail", "Naveen Raj", "Television", "Installation delay for 55-inch QLED", "OPEN", "2026-10-27"),
        ("TCK-102", "dream_sleep", "Arjun Rao", "Mattress", "Warranty claim: 10-year sag guarantee review", "ESCALATED", "2026-10-26"),
        ("TCK-103", "mvm_dist", "Praveen Kumar", "Air Conditioners", "Damaged carton packaging on wholesale pallet", "OPEN", "2026-10-27"),
        ("TCK-104", "ams_assoc", "Siva Electronics", "Electronics", "Invoice credit note request for defective batch", "RESOLVED", "2026-10-25"),
        ("TCK-105", "dream_sleep", "Divya Sundaram", "Bedding", "Memory foam pillow zipper stitch defect", "OPEN", "2026-10-27")
    ]
    cur.executemany("INSERT OR REPLACE INTO customer_tickets VALUES (?,?,?,?,?,?,?)", tickets)

    # Seed HR & Payroll Records
    hr_records = [
        ("EMP-AR-01", "ams_retail", "Karthik V", "Showroom Floor Manager", 38000.0, 14, 2, "ACTIVE"),
        ("EMP-AR-02", "ams_retail", "Pooja S", "Senior Retail Sales Associate", 26000.0, 18, 0, "ACTIVE"),
        ("EMP-AA-01", "ams_assoc", "Ramesh K", "Logistics & Dispatch Lead", 42000.0, 12, 1, "ACTIVE"),
        ("EMP-AA-02", "ams_assoc", "Vignesh R", "B2B Billing Specialist", 30000.0, 16, 0, "ACTIVE"),
        ("EMP-MV-01", "mvm_dist", "Anand B", "Wholesale Warehouse Supervisor", 35000.0, 10, 3, "ACTIVE"),
        ("EMP-MV-02", "mvm_dist", "Suresh M", "Regional Appliance Distributor Rep", 45000.0, 15, 0, "ACTIVE"),
        ("EMP-DS-01", "dream_sleep", "Murugan T", "Foam Cutting Production Incharge", 32000.0, 8, 2, "ACTIVE"),
        ("EMP-DS-02", "dream_sleep", "Lakshmi N", "Quilting & Mattress QC Inspector", 28000.0, 19, 1, "ACTIVE")
    ]
    cur.executemany("INSERT OR REPLACE INTO hr_payroll VALUES (?,?,?,?,?,?,?,?)", hr_records)

    # Seed Actionable Remediations (Human-in-the-Loop)
    actions_seed = [
        ("ACT-PO-901", "Inventory Agent", "dream_sleep", "Issue Emergency Purchase Order (PO-FOAM-2026)", "Procure 380 Kg of 40-Density Memory Foam Blocks from Sheela Foam Ltd at ₹185/Kg (Total: ₹70,300).", "HIGH", "PENDING_APPROVAL", "2026-10-27 12:40"),
        ("ACT-GST-902", "GST Auditor Agent", "mvm_dist", "Post GST Ledger Correction (INV-2026-MVM_DIST-1004)", "Generate debit note of ₹18,295.98 to reconcile wholesale invoice where 12% GST was posted instead of 18%.", "CRITICAL", "PENDING_APPROVAL", "2026-10-27 12:41"),
        ("ACT-HR-903", "HR & Payroll Agent", "ams_retail", "Issue Formal Shift Warning Notice", "Send automated compliance notification to Floor Manager Karthik V regarding consecutive biometric check-in anomalies.", "MEDIUM", "PENDING_APPROVAL", "2026-10-27 12:42")
    ]
    cur.executemany("INSERT OR REPLACE INTO swarm_actions VALUES (?,?,?,?,?,?,?,?)", actions_seed)

    conn.commit()
    conn.close()
    print("SUCCESS: Materialized all dbt marts and created HITL Action Queue table.")

if __name__ == "__main__":
    run_dbt_transformations()