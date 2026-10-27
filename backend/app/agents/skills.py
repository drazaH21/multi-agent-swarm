import sqlite3
import os
import re
from typing import Dict, Any, List, Optional
from app.core.caching import swarm_cache

# Resolve absolute path to data/conglomerate.db dynamically
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_PATH = os.path.join(_root, "data", "conglomerate.db").replace("\\", "/")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def detect_query_target_agent(q: str) -> Optional[str]:
    q_lower = q.lower()
    multi_domain_keywords = ["consolidated", "overview", "executive", "all subsidiaries", "across all", "health", "briefing", "conglomerate"]
    if any(k in q_lower for k in multi_domain_keywords):
        return "supervisor"

    domains_hit = 0
    if any(k in q_lower for k in ["sale", "revenue", "gmv", "orders"]): domains_hit += 1
    if any(k in q_lower for k in ["foam", "stock", "inventory", "shortage", "procure"]): domains_hit += 1
    if any(k in q_lower for k in ["tax", "gst", "leakage"]): domains_hit += 1
    if any(k in q_lower for k in ["attend", "late", "shift", "biometric"]): domains_hit += 1
    if any(k in q_lower for k in ["payroll", "salary", "wage"]): domains_hit += 1
    
    if domains_hit >= 2:
        return "supervisor"

    if re.search(r"(paid|pay|salary|salaries|wage|payroll|earner|earn|compensation|leave|bonus)", q_lower):
        return "hr"
    if re.search(r"(tv|tvs|television|ac|inverter|fridge|refrigerator|washing machine|foam|spring|fabric|pillow|mattress|stock|units left|inventory|procure|deficit)", q_lower):
        if re.search(r"(sold|sell|revenue|sales volume)", q_lower):
            return "sales"
        return "inventory"
    if re.search(r"(sale|sales|revenue|gmv|distribute|breakdown|turnover)", q_lower):
        return "sales"
    if re.search(r"(tax|gst|leak|audit|invoice|discrepancy)", q_lower):
        return "auditor"
    if re.search(r"(attend|absent|late|shift|check in|biometric|punch)", q_lower):
        return "attendance"
    if re.search(r"(logistic|dispatch|fleet|truck|shipment|transit|delivery)", q_lower):
        return "logistics"
    if re.search(r"(support|ticket|warranty|complain|claim|customer|sag)", q_lower):
        return "support"
    if re.search(r"(action|remediation|approve|approval|pending)", q_lower):
        return "supervisor"
        
    return None

def tool_guardrail_check(prompt: str) -> bool:
    unrelated_keywords = ["weather", "cricket score", "movie", "recipe", "pizza", "joke", "sports", "flight"]
    p = prompt.lower()
    return any(k in p for k in unrelated_keywords)

def tool_query_inventory_item(item_keyword: str, tenant_id: str = "ALL") -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT company_id, item_name, current_stock, unit FROM raw_inventory WHERE LOWER(item_name) LIKE ?"
    params = [f"%{item_keyword.lower()}%"]
    if tenant_id != "ALL":
        query += " AND company_id = ?"
        params.append(tenant_id)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"found": False, "total_stock": 0.0, "breakdown": [], "message": f"No inventory matching '{item_keyword}'."}

    total = sum(r["current_stock"] for r in rows)
    breakdown = [f"{r['company_id'].upper()}: {r['item_name']} -> {r['current_stock']} {r['unit']}" for r in rows]
    return {"found": True, "total_stock": total, "breakdown": breakdown}

def tool_query_attendance(tenant_id: str = "ALL") -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT company_id, employee_name, check_in_time, status FROM raw_attendance WHERE 1=1"
    params = []
    if tenant_id != "ALL":
        query += " AND company_id = ?"
        params.append(tenant_id)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    late = [f"[{r['company_id'].upper()}] {r['employee_name']}" for r in rows if r["status"] == "LATE"]
    present = sum(1 for r in rows if r["status"] in ["PRESENT", "LATE"])
    return {
        "total_staff": total,
        "present_count": present,
        "absent_count": total - present,
        "late_count": len(late),
        "late_records": late
    }

def tool_get_sales_distribution() -> Dict[str, Any]:
    cached = swarm_cache.get("sales_agent", {"metric": "sales_distribution"})
    if cached:
        return {"data": cached, "cached": True}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT company_id, company_name, gross_sales, total_orders, avg_ticket_size FROM fct_company_sales_breakdown ORDER BY gross_sales DESC")
    rows = cursor.fetchall()
    conn.close()
    
    total_sales = sum(r["gross_sales"] for r in rows)
    companies = [{"company_id": r["company_id"], "company_name": r["company_name"], "gross_sales": r["gross_sales"], "orders": r["total_orders"], "avg_ticket": r["avg_ticket_size"]} for r in rows]
    res = {"total_group_sales": total_sales, "companies": companies}
    swarm_cache.set("sales_agent", {"metric": "sales_distribution"}, res, ttl=10)
    return {"data": res, "cached": False}

def tool_query_customer_support(tenant_id: str = "ALL") -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT ticket_id, company_id, customer_name, issue_category, priority, status, description FROM raw_support_tickets WHERE 1=1"
    params = []
    if tenant_id != "ALL":
        query += " AND company_id = ?"
        params.append(tenant_id)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    unresolved = [f"[{r['priority']}] {r['company_id'].upper()} #{r['ticket_id']}: {r['description']} ({r['status']})" for r in rows if r["status"] != "RESOLVED"]
    return {"data": {"total_tickets": len(rows), "active_unresolved": len(unresolved), "tickets": unresolved}}

def tool_query_hr_payroll(tenant_id: str = "ALL", ranked: bool = False) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    order_clause = " ORDER BY monthly_wage_inr DESC" if ranked else ""
    query = f"SELECT employee_name, company_id, designation, monthly_wage_inr, leaves_taken_this_month, is_manager FROM raw_payroll WHERE 1=1"
    params = []
    if tenant_id != "ALL":
        query += " AND company_id = ?"
        params.append(tenant_id)
    query += order_clause
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    total_payroll = sum(r["monthly_wage_inr"] for r in rows)
    total_leaves = sum(r["leaves_taken_this_month"] for r in rows)
    staff_details = [f"{r['employee_name']} ({r['designation']} - {r['company_id'].upper()}): ₹{r['monthly_wage_inr']:,.0f}/mo | Leave: {r['leaves_taken_this_month']}d" for r in rows]
    highest_earner = {"name": rows[0]["employee_name"], "role": rows[0]["designation"], "company": rows[0]["company_id"].upper(), "wage": rows[0]["monthly_wage_inr"]} if rows else None
    mgrs = [r for r in rows if r["is_manager"] == 1]
    highest_mgr = {"name": mgrs[0]["employee_name"], "role": mgrs[0]["designation"], "company": mgrs[0]["company_id"].upper(), "wage": mgrs[0]["monthly_wage_inr"]} if mgrs else None
    
    payload = {
        "total_headcount": len(rows),
        "monthly_payroll_liability": total_payroll,
        "leaves_taken_this_month": total_leaves,
        "employee_details": staff_details,
        "highest_earner": highest_earner,
        "highest_manager": highest_mgr
    }
    return {"data": payload}

def tool_query_product_sales_volume(product_kw: str, tenant_id: str = "ALL") -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT company_id, category, total_units_sold, total_revenue FROM fct_product_sales_volume WHERE LOWER(category) LIKE ?"
    params = [f"%{product_kw.lower()}%"]
    if tenant_id != "ALL":
        query += " AND company_id = ?"
        params.append(tenant_id)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"data": {"found": False, "total_units_sold": 0, "total_revenue": 0.0, "breakdown": [], "message": f"No sales volume records found matching '{product_kw}'."}}

    units = sum(r["total_units_sold"] for r in rows)
    rev = sum(r["total_revenue"] for r in rows)
    breakdown = [f"{r['company_id'].upper()}: {r['total_units_sold']} units (₹{r['total_revenue']:,.2f})" for r in rows]
    return {"data": {"found": True, "total_units_sold": units, "total_revenue": rev, "breakdown": breakdown}}

def tool_query_logistics_dispatches(tenant_id: str = "ALL") -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT dispatch_id, origin_company_id, destination_hub, truck_identifier, cargo_manifest, status, estimated_arrival FROM raw_logistics_dispatches WHERE 1=1"
    params = []
    if tenant_id != "ALL":
        query += " AND origin_company_id = ?"
        params.append(tenant_id)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    trips = [f"[{r['origin_company_id'].upper()}] Truck {r['truck_identifier']} -> {r['destination_hub']} ({r['cargo_manifest']}) | Status: {r['status']} (ETA: {r['estimated_arrival']})" for r in rows]
    return {"data": {"active_trips": len(rows), "dispatches": trips}}

def tool_get_pending_actions(tenant_id: str = "ALL") -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT action_id, origin_agent, target_entity, action_title, payload_details, impact_level, status FROM action_approval_queue WHERE status = 'PENDING'"
    params = []
    if tenant_id != "ALL":
        query += " AND target_entity = ?"
        params.append(tenant_id)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [{"action_id": r["action_id"], "origin_agent": r["origin_agent"], "target_entity": r["target_entity"], "action_title": r["action_title"], "payload_details": r["payload_details"], "impact_level": r["impact_level"], "status": r["status"]} for r in rows]

def tool_execute_action(action_id: str, decision: str) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE action_approval_queue SET status = ? WHERE action_id = ?", (decision, action_id))
    conn.commit()
    conn.close()
    return {"action_id": action_id, "status": decision, "message": f"Action {action_id} successfully marked as {decision}."}

