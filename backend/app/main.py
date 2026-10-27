import asyncio
import os
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.agents.supervisor import AmsavisionSupervisorEngine, limiter
from app.schemas.state import ConglomerateAuditReport
from app.core.caching import swarm_cache
from app.core.memory import session_memory
from app.core.llm import ollama_client
from app.agents.skills import (
    tool_query_inventory_item,
    tool_query_attendance,
    tool_guardrail_check,
    tool_get_sales_distribution,
    tool_query_customer_support,
    tool_query_hr_payroll,
    tool_query_product_sales_volume,
    tool_query_logistics_dispatches,
    tool_get_pending_actions,
    tool_execute_action,
    detect_query_target_agent
)
from app.agents.collaboration import CrossAgentCollaborationEngine

app = FastAPI(title="Amsavision Multi-Agent Conglomerate Swarm", version="2.8.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = AmsavisionSupervisorEngine()

class AuditRequest(BaseModel):
    tenant_id: str = "ALL"

class ChatQueryRequest(BaseModel):
    prompt: str
    tenant_id: Optional[str] = "ALL"
    session_id: Optional[str] = "default_session"
    target_agent_id: Optional[str] = "supervisor"

class ActionDecisionRequest(BaseModel):
    decision: str = "APPROVED"

class CollaborationRequest(BaseModel):
    product: str = "Orthopedic King Mattress"
    quantity: int = 60
    tenant_id: str = "dream_sleep"

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/audit", response_model=ConglomerateAuditReport)
async def trigger_audit(req: AuditRequest):
    return await engine.orchestrate_audit(req.tenant_id)

@app.get("/api/actions")
def get_actions(tenant_id: str = "ALL"):
    return tool_get_pending_actions(tenant_id)

@app.post("/api/actions/{action_id}/execute")
def execute_action(action_id: str, req: ActionDecisionRequest):
    return tool_execute_action(action_id, req.decision)

@app.post("/api/collaborate")
def execute_cross_agent_debate(req: CollaborationRequest):
    return CrossAgentCollaborationEngine.simulate_order_fulfillment_debate(req.product, req.quantity, req.tenant_id)

@app.get("/api/export", response_class=HTMLResponse)
async def export_executive_brief(tenant_id: str = "ALL"):
    report = await engine.orchestrate_audit(tenant_id)
    sales = tool_get_sales_distribution()["data"]
    support = tool_query_customer_support(tenant_id)["data"]
    hr = tool_query_hr_payroll(tenant_id, ranked=True)["data"]
    actions = tool_get_pending_actions(tenant_id)

    sales_rows = "".join(f"<tr><td style='padding:6px;border-bottom:1px solid #e2e8f0'>{c['company_name']}</td><td style='padding:6px;border-bottom:1px solid #e2e8f0;text-align:right'>₹{c['gross_sales']:,.2f}</td><td style='padding:6px;border-bottom:1px solid #e2e8f0;text-align:center'>{c['orders']}</td><td style='padding:6px;border-bottom:1px solid #e2e8f0;text-align:right'>₹{c['avg_ticket']:,.2f}</td></tr>" for c in sales["companies"])
    shortage_rows = "".join(f"<li><b>{s['item_name'] if isinstance(s, dict) and 'item_name' in s else s}</b></li>" for s in report.inventory_summary.critical_shortages)
    action_rows = "".join(f"<li><b>[{a['impact_level']}] {a['action_title']}</b> ({a['origin_agent']}): {a['payload_details']}</li>" for a in actions) or "<li>No pending actions.</li>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='utf-8'>
        <title>Amsavision Conglomerate - Executive Swarm Brief</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; color: #1e293b; }}
            h1 {{ margin-bottom: 4px; color: #0f172a; }}
            .metric-box {{ display: inline-block; width: 22%; margin: 1%; padding: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; box-sizing: border-box; }}
            .metric-title {{ font-size: 11px; color: #64748b; text-transform: uppercase; }}
            .metric-val {{ font-size: 20px; font-weight: bold; color: #0f172a; margin-top: 4px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
            th {{ background: #f1f5f9; padding: 8px; text-align: left; font-size: 12px; }}
            .section {{ margin-top: 30px; }}
            @media print {{ body {{ margin: 0; }} button {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div style='display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #0f172a;padding-bottom:12px;'>
            <div>
                <h1>Amsavision Conglomerate</h1>
                <p style='margin:0;font-size:13px;color:#64748b'>Autonomous Multi-Agent Audit Brief | Scope: <b>{tenant_id.upper()}</b></p>
            </div>
            <button onclick='window.print()' style='background:#4f46e5;color:white;border:none;padding:10px 18px;border-radius:6px;cursor:pointer;font-weight:600;'>Save as PDF / Print</button>
        </div>

        <div style='margin-top:20px;'>
            <div class='metric-box'><div class='metric-title'>Total Group Revenue</div><div class='metric-val'>₹{sales['total_group_sales']:,.2f}</div></div>
            <div class='metric-box'><div class='metric-title'>Flagged Tax Leakage</div><div class='metric-val' style='color:#dc2626'>₹{report.financial_summary.potential_margin_leakage:,.2f}</div></div>
            <div class='metric-box'><div class='metric-title'>Monthly Payroll</div><div class='metric-val'>₹{hr['monthly_payroll_liability']:,.2f}</div></div>
            <div class='metric-box'><div class='metric-title'>Open Support SLAs</div><div class='metric-val'>{support['active_unresolved']} Cases</div></div>
        </div>

        <div class='section'>
            <h3 style='margin-bottom:8px'>Subsidiary Sales Breakdown (dbt Mart)</h3>
            <table>
                <thead><tr><th>Subsidiary</th><th style='text-align:right'>Gross Sales</th><th style='text-align:center'>Orders</th><th style='text-align:right'>Avg Ticket</th></tr></thead>
                <tbody>{sales_rows}</tbody>
            </table>
        </div>

        <div class='section' style='display:flex;gap:40px;'>
            <div style='flex:1'>
                <h3 style='margin-bottom:8px'>Critical Inventory Deficits</h3>
                <ul style='font-size:13px;line-height:1.6;color:#334155'>{shortage_rows}</ul>
            </div>
            <div style='flex:1'>
                <h3 style='margin-bottom:8px'>Pending Human-in-the-Loop Actions</h3>
                <ul style='font-size:13px;line-height:1.6;color:#334155'>{action_rows}</ul>
            </div>
        </div>
    </body>
    </html>
    """

def resolve_tenant_name(text: str) -> Optional[str]:
    t = text.lower()
    if "retail" in t or "ams_retail" in t:
        return "ams_retail"
    if "assoc" in t or "ams_assoc" in t:
        return "ams_assoc"
    if "mvm" in t or "mvm_dist" in t:
        return "mvm_dist"
    if "dream" in t or "sleep" in t or "bedding" in t or "dream_sleep" in t:
        return "dream_sleep"
    return None

AGENT_DISPLAY_NAMES = {
    "supervisor": "Supervisor Agent",
    "attendance": "Attendance Agent",
    "sales": "Sales & GMV Agent",
    "auditor": "GST Auditor Agent",
    "inventory": "Inventory & Foam Agent",
    "support": "Customer Support Agent",
    "hr": "HR & Payroll Agent",
    "logistics": "Logistics Fleet Agent"
}

AGENT_PERSONAS = {
    "supervisor": "You are the Executive Supervisor of Amsavision Conglomerate. You coordinate business operations from your glass office cabin across all 4 subsidiaries.",
    "attendance": "You are the Attendance & Biometrics Agent. You monitor warehouse punch-in machines and showroom staff check-ins.",
    "sales": "You are the Sales & Revenue Agent. You analyze wholesale orders, revenue velocity, and dbt sales performance marts.",
    "auditor": "You are the GST & Compliance Auditor. You scrutinize tax rates (12% vs 18% HSNs) and prevent margin leakage.",
    "inventory": "You are the Inventory & Materials Coordinator. You track foam block weights, finished units, warehouse levels, and urgent procurement needs.",
    "support": "You are the Customer Support & SLA Agent. You triage warranty sag guarantees and delivery complaints.",
    "hr": "You are the HR & Payroll Specialist. You manage executive compensation, salary rosters, and leave pools.",
    "logistics": "You are the Fleet Dispatch Controller. You track cargo container trucks across Salem and Chennai hubs."
}

@app.post("/api/chat")
async def supervisor_chat(req: ChatQueryRequest):
    prompt = req.prompt.strip()
    session_id = req.session_id if req.session_id else "default_session"
    tenant = req.tenant_id if req.tenant_id else "ALL"
    target_agent = req.target_agent_id if req.target_agent_id else "supervisor"
    
    q_clean = re.sub(r"[^\w\s]", "", prompt.lower()).strip()
    q_clean = re.sub(r"\s+", " ", q_clean)

    # 1. Guardrail
    if tool_guardrail_check(prompt):
        return {
            "answer": "Request rejected by Swarm Guardrails: Query is outside the scope of Amsavision Conglomerate business operations.",
            "source": "Swarm Security & Domain Guardrail",
            "redirect_agent": None
        }

    # 2. Break Return / Wake-up
    wake_patterns = [
        "youre up", "your up", "you re up", "you are up", "shift is up", "wake up", 
        "back to work", "break over", "break is over", "return to desk", "desk"
    ]
    if any(p in q_clean for p in wake_patterns):
        agent_name = AGENT_DISPLAY_NAMES.get(target_agent, 'Agent')
        if target_agent == "supervisor":
            reply = f"{agent_name}: 'I am stationed in the executive cabin and actively monitoring swarm telemetry. Ready for your command!'"
        else:
            reply = f"{agent_name} acknowledges: 'Copy that! Ending my break and returning to my workstation desk immediately.'"
        return {
            "answer": reply,
            "source": "Shift Dispatch Routine",
            "redirect_agent": target_agent,
            "wake_up": True
        }

    # 3. Detect Domain Mismatch and Trigger Redirection
    detected_target = detect_query_target_agent(q_clean)
    redirect_notice = ""
    
    if detected_target == "supervisor" and target_agent != "supervisor":
        redirect_notice = f"[{AGENT_DISPLAY_NAMES.get(target_agent)}]: 'That consolidated inquiry requires cross-domain authority. Transferring you to Executive Supervisor in the cabin.'\n\n"
        target_agent = "supervisor"
    elif target_agent != "supervisor" and detected_target and detected_target != target_agent:
        redirect_notice = f"[{AGENT_DISPLAY_NAMES.get(target_agent)}]: 'That topic belongs to {AGENT_DISPLAY_NAMES.get(detected_target)}. Handing you off.'\n\n"
        target_agent = detected_target

    # Multi-Domain Collective Executive Overview
    if detected_target == "supervisor" or (target_agent == "supervisor" and any(k in q_clean for k in ["overview", "consolidated", "all subsidiaries", "revenue", "health"])):
        report = await engine.orchestrate_audit(tenant)
        sales = tool_get_sales_distribution()["data"]
        raw_facts = (
            f"Consolidated Total Sales: ₹{sales['total_group_sales']:,.2f} across all subsidiaries.\n"
            f"Critical Inventory Shortages: {len(report.inventory_summary.critical_shortages)} items (380 Kg 40D Foam deficit from Sheela Foam Ltd).\n"
            f"Tax Leakage: ₹{report.financial_summary.potential_margin_leakage:,.2f} flagged across {len(report.financial_summary.tax_discrepancies)} invoices.\n"
            f"Biometric Attendance Flags: {len(report.attendance_summary.late_anomalies)} late check-ins.\n"
        )
        
        llm_reply = await ollama_client.generate_response(prompt, AGENT_PERSONAS["supervisor"], raw_facts)
        if llm_reply:
            reply = redirect_notice + f"Supervisor Agent [Local Ollama: {ollama_client.model_name}]:\n{llm_reply}"
            source_engine = f"Local Ollama ({ollama_client.model_name}) + Central Supervisor Engine"
        else:
            clean_tenant = tenant if tenant != "ALL" else "CONSOLIDATED"
            reply = redirect_notice + (
                f"Supervisor Agent [Executive Overview - {clean_tenant}]:\n"
                f"- Total Group Sales: ₹{sales['total_group_sales']:,.2f}\n"
                f"- Critical Shortages: {len(report.inventory_summary.critical_shortages)} items (380 Kg 40D Foam deficit)\n"
                f"- GST Discrepancies: {len(report.financial_summary.tax_discrepancies)} flagged invoices (Leakage: ₹{report.financial_summary.potential_margin_leakage:,.2f})\n"
                f"- Biometric Attendance: {len(report.attendance_summary.late_anomalies)} late check-ins"
            )
            source_engine = "Central Supervisor Synthesis"
            
        session_memory.add_turn(session_id, "user", prompt)
        session_memory.add_turn(session_id, "assistant", reply, intent="EXECUTIVE_OVERVIEW")
        return {"answer": reply, "source": source_engine, "redirect_agent": "supervisor"}

    prev_ctx = session_memory.get_context(session_id)

    # 4. Contextual Follow-up Resolution
    is_followup = any(q_clean.startswith(phrase) for phrase in ["what about", "how about", "and in", "check in", "what of", "for"])
    target_tenant = resolve_tenant_name(q_clean)

    if is_followup and target_tenant and prev_ctx.get("active_sku"):
        sku = prev_ctx["active_sku"]
        res = tool_query_inventory_item(sku, target_tenant)
        total_stock = res.get("total_stock", 0)
        breakdown_str = "; ".join(res.get("breakdown", []))
        raw_facts = f"SKU: {sku.upper()}, Subsidiary: {target_tenant.upper()}, Total Stock: {total_stock} units. Breakdown: {breakdown_str}."
        
        header_tag = f"Inventory Agent [Multi-Turn Follow-Up | SKU: '{sku.upper()}']:\n"
        llm_reply = await ollama_client.generate_response(prompt, AGENT_PERSONAS["inventory"], raw_facts)
        
        reply = redirect_notice + header_tag + (llm_reply if llm_reply else (
            f"Found {total_stock} units of {sku.upper()} in [{target_tenant.upper()}].\n"
            f"Details: {breakdown_str if breakdown_str else 'No stock remaining in this subsidiary.'}"
        ))
        engine_source = f"Local Ollama ({ollama_client.model_name}) + Context Memory" if llm_reply else "Conversational Memory Engine"
        session_memory.add_turn(session_id, "user", prompt)
        session_memory.add_turn(session_id, "assistant", reply, intent="INVENTORY_FOLLOWUP", metadata={"active_sku": sku, "active_tenant": target_tenant})
        return {"answer": reply, "source": engine_source, "redirect_agent": "inventory"}

    # 5. Cross-Agent Order Fulfillment Debate
    if ("fulfill" in q_clean or "can we produce" in q_clean or "order of" in q_clean) and ("mattress" in q_clean or "foam" in q_clean or "tv" in q_clean):
        qty_match = re.search(r"\b(\d+)\b", q_clean)
        qty = int(qty_match.group(1)) if qty_match else 50
        debate = CrossAgentCollaborationEngine.simulate_order_fulfillment_debate("Orthopedic King Mattress", qty, "dream_sleep")
        steps_text = "\n".join([f"• [{s['agent']} -> {s['handoff_to']}]: {s['thought']}" for s in debate["chain_steps"][:-1]])
        reply = redirect_notice + (
            f"Cross-Agent Collaborative Reasoning Stream ({qty}x Orthopedic Mattresses):\n"
            f"{steps_text}\n\n"
            f"Central Supervisor Executive Verdict:\n{debate['executive_verdict']}"
        )
        session_memory.add_turn(session_id, "user", prompt)
        session_memory.add_turn(session_id, "assistant", reply, intent="COLLABORATION_DEBATE")
        return {"answer": reply, "source": "Collaboration Graph", "redirect_agent": "supervisor"}

    # 6. Pending Actions
    if re.search(r"(pending action|approval queue|approve|remediation|recommended action)", q_clean):
        acts = tool_get_pending_actions(tenant)
        if not acts:
            return {"answer": f"All remediation actions for [{tenant}] have been executed or reviewed.", "source": "HITL Action Engine", "redirect_agent": "supervisor"}
        lines = [f"- [{a['action_id']}] ({a['impact_level']}) {a['action_title']} proposed by {a['origin_agent']}: {a['payload_details']}" for a in acts]
        return {"answer": f"Human-In-The-Loop Approval Queue ({len(acts)} pending):\n" + "\n".join(lines), "source": "HITL Action Engine", "redirect_agent": "supervisor"}

    # 7. HR & Payroll
    if re.search(r"(paid|pay|salary|salaries|wage|payroll|earner|earn|compensation|leave|bonus)", q_clean):
        is_ranked = any(w in q_clean for w in ["highest", "most", "top", "rank", "manager", "best paid"])
        res = tool_query_hr_payroll(tenant, ranked=is_ranked)
        data = res["data"]
        raw_facts = f"Total Headcount: {data['total_headcount']}, Monthly Payroll Liability: ₹{data['monthly_payroll_liability']:,.2f}, Leaves Taken: {data['leaves_taken_this_month']}, Top Staff: {data['employee_details'][:4]}"
        if data.get("highest_earner"):
            raw_facts += f", Highest Overall Earner: {data['highest_earner']['name']} ({data['highest_earner']['role']}) at ₹{data['highest_earner']['wage']}/mo, Highest Paid Manager: {data['highest_manager']['name']} ({data['highest_manager']['role']}) at ₹{data['highest_manager']['wage']}/mo"

        llm_reply = await ollama_client.generate_response(prompt, AGENT_PERSONAS["hr"], raw_facts)
        if llm_reply:
            reply = redirect_notice + f"HR & Payroll Agent [Local Ollama: {ollama_client.model_name}]:\n{llm_reply}"
            source_engine = f"Local Ollama ({ollama_client.model_name}) + tool_query_hr_payroll"
        else:
            if is_ranked and data.get("highest_earner"):
                earner = data["highest_earner"]
                mgr = data.get("highest_manager")
                reply = redirect_notice + (
                    f"HR & Payroll Agent [Executive Compensation Analysis]:\n"
                    f"- Highest Paid Overall: {earner['name']} ({earner['role']} - {earner['company']}) at ₹{earner['wage']:,.0f}/month.\n"
                    f"- Highest Paid Manager/Lead: {mgr['name']} ({mgr['role']} - {mgr['company']}) at ₹{mgr['wage']:,.0f}/month.\n\n"
                    f"Full Compensation Ranking ({data['total_headcount']} staff):\n" + "\n".join(f"- {e}" for e in data["employee_details"][:4])
                )
            else:
                reply = redirect_notice + (
                    f"HR & Payroll Agent [Scope: {tenant}]:\n"
                    f"Total Workforce Audited: {data['total_headcount']} staff | Total Monthly Wage Liability: ₹{data['monthly_payroll_liability']:,.2f}\n"
                    f"Leaves Taken This Month: {data['leaves_taken_this_month']} days\n"
                    f"Staff Profiles:\n" + "\n".join(f"- {e}" for e in data["employee_details"])
                )
            source_engine = "Skill: tool_query_hr_payroll"

        session_memory.add_turn(session_id, "user", prompt)
        session_memory.add_turn(session_id, "assistant", reply, intent="HR_PAYROLL", metadata={"active_topic": "payroll"})
        return {"answer": reply, "source": source_engine, "redirect_agent": "hr"}

    # 8. Product Sales Volume
    prod_sold_match = re.search(r"(tv|tvs|television|televisions|ac|inverter|refrigerator|fridge|mattress|mattresses|pillow|pillows|bedding)", q_clean)
    if prod_sold_match and any(w in q_clean for w in ["sold", "sell", "sales volume", "units sold", "how many sold", "number of", "till date"]):
        kw = "tv" if "tv" in prod_sold_match.group(1) else prod_sold_match.group(1)
        res = tool_query_product_sales_volume(kw, tenant)
        data = res["data"]
        raw_facts = f"Product: {kw.upper()}, Units Sold: {data.get('total_units_sold', 0)}, Revenue: ₹{data.get('total_revenue', 0)}, Breakdown: {data.get('breakdown', [])}"

        llm_reply = await ollama_client.generate_response(prompt, AGENT_PERSONAS["sales"], raw_facts)
        if llm_reply:
            reply = redirect_notice + f"Sales Volume Agent [Local Ollama: {ollama_client.model_name}]:\n{llm_reply}"
            source_engine = f"Local Ollama ({ollama_client.model_name}) + dbt Mart: fct_product_sales_volume"
        else:
            if data["found"]:
                reply = redirect_notice + (
                    f"Sales Volume Agent [dbt Mart: fct_product_sales_volume]:\n"
                    f"Total '{kw.upper()}' Units Sold Till Date: {data['total_units_sold']} units across [{tenant}] (Gross Product Revenue: ₹{data['total_revenue']:,.2f}).\n"
                    f"Subsidiary Breakdown:\n" + "\n".join(f"- {b}" for b in data["breakdown"])
                )
            else:
                reply = redirect_notice + f"Sales Volume Agent: {data['message']}"
            source_engine = "dbt Mart: fct_product_sales_volume"

        session_memory.add_turn(session_id, "user", prompt)
        session_memory.add_turn(session_id, "assistant", reply, intent="PRODUCT_SALES", metadata={"active_sku": kw, "active_topic": "sales"})
        return {"answer": reply, "source": source_engine, "redirect_agent": "sales"}

    # 9. Logistics & Fleet Dispatches
    if re.search(r"(logistic|dispatch|fleet|truck|shipment|transit|delivery|deliveries)", q_clean):
        res = tool_query_logistics_dispatches(tenant)
        data = res["data"]
        raw_facts = f"Active Trips: {data['active_trips']}, Cargo & Dispatches: {data['dispatches']}"

        llm_reply = await ollama_client.generate_response(prompt, AGENT_PERSONAS["logistics"], raw_facts)
        if llm_reply:
            reply = redirect_notice + f"Logistics Fleet Agent [Local Ollama: {ollama_client.model_name}]:\n{llm_reply}"
            source_engine = f"Local Ollama ({ollama_client.model_name}) + tool_query_logistics_dispatches"
        else:
            reply = redirect_notice + (
                f"Logistics & Dispatch Fleet Agent [Scope: {tenant}]:\n"
                f"Active Cargo Dispatches: {data['active_trips']}.\n"
                f"Fleet Tracking:\n" + "\n".join(f"- {d}" for d in data["dispatches"])
            )
            source_engine = "Skill: tool_query_logistics_dispatches"
        return {"answer": reply, "source": source_engine, "redirect_agent": "logistics"}

    # 10. Inventory Stock, Foam & Procurement Query
    inv_item_match = re.search(r"(foam|spring|fabric|pillow|mattress|tvs|tv|television|ac|inverter|fridge|refrigerator)", q_clean)
    if inv_item_match:
        raw_kw = inv_item_match.group(1)
        item_kw = "tv" if raw_kw in ["tv", "tvs", "television"] else raw_kw
        detected_tenant = resolve_tenant_name(q_clean) or tenant
        res = tool_query_inventory_item(item_kw, detected_tenant)
        
        raw_facts = f"Item: {item_kw.upper()}, Current Available Stock: {res.get('total_stock', 0)}, Breakdown: {res.get('breakdown', [])}."
        if "foam" in item_kw:
            raw_facts += " PROCUREMENT DEFICIT ALERT: Critical shortage of 380.0 Kg 40D Memory Foam Blocks. Emergency reorder PO-FOAM-2026 pending in HITL approval queue."

        llm_reply = await ollama_client.generate_response(prompt, AGENT_PERSONAS["inventory"], raw_facts)
        if llm_reply:
            reply = redirect_notice + f"Inventory & Materials Agent [Local Ollama: {ollama_client.model_name}]:\n{llm_reply}"
            source_engine = f"Local Ollama ({ollama_client.model_name}) + tool_query_inventory_item"
        else:
            procure_note = "\nProcurement Alert: Critical deficit of 380 Kg 40D Memory Foam Blocks (PO-FOAM-2026 pending in HITL Queue)." if "foam" in item_kw else ""
            reply = redirect_notice + (
                f"Inventory Agent [Tool: StockQuery]: Found a total of {res['total_stock']} units for '{item_kw.upper()}' across [{detected_tenant.upper()}].\n"
                f"Entity breakdown: {'; '.join(res['breakdown'])}.{procure_note}"
            )
            source_engine = "Skill: tool_query_inventory_item"

        session_memory.add_turn(session_id, "user", prompt)
        session_memory.add_turn(session_id, "assistant", reply, intent="INVENTORY_STOCK", metadata={"active_sku": item_kw, "active_tenant": detected_tenant})
        return {"answer": reply, "source": source_engine, "redirect_agent": "inventory"}

    # 11. Customer Support
    if re.search(r"(support|ticket|warranty|complain|claim|customer|sag|installation)", q_clean):
        res = tool_query_customer_support(tenant)
        data = res["data"]
        reply = redirect_notice + (
            f"Customer Support Agent [Scope: {tenant}]:\n"
            f"Active Unresolved Tickets: {data['active_unresolved']} of {data['total_tickets']}.\n"
            f"Current Cases:\n" + "\n".join(f"- {t}" for t in data["tickets"])
        )
        return {"answer": reply, "source": "Skill: tool_query_customer_support", "redirect_agent": "support"}

    # 12. Sales Distribution
    if re.search(r"(distribute|breakdown|per company|each company|across companies|by business|compare sales|split)", q_clean) and re.search(r"(sale|revenue|business|company|gmv)", q_clean):
        res = tool_get_sales_distribution()
        data = res["data"]
        lines = [f"- {c['company_name']}: ₹{c['gross_sales']:,.2f} ({c['orders']} orders, Avg: ₹{c['avg_ticket']:,.2f})" for c in data["companies"]]
        reply = redirect_notice + (
            f"Sales Agent [dbt Mart: fct_company_sales_breakdown]:\n"
            f"Total Group Consolidated Revenue: ₹{data['total_group_sales']:,.2f}\n" + "\n".join(lines)
        )
        return {"answer": reply, "source": "dbt Mart: fct_company_sales_breakdown", "redirect_agent": "sales"}

    # 13. Attendance
    if re.search(r"(attend|absent|late|shift|check in|biometric|punch)", q_clean):
        att = tool_query_attendance(tenant)
        reply = redirect_notice + (
            f"Attendance Agent [Tool: ShiftAudit]: Staff Headcount: {att['total_staff']} | Present: {att['present_count']} | Absentees: {att['absent_count']}.\n"
            f"Late Biometric Check-ins: ({att['late_count']}) {', '.join(att['late_records']) if att['late_records'] else 'None'}."
        )
        return {"answer": reply, "source": "Skill: tool_query_attendance", "redirect_agent": "attendance"}

    # 14. Tax Discrepancies
    if re.search(r"(tax|gst|leak|audit|invoice|discrepancy)", q_clean):
        report = await engine.orchestrate_audit(tenant)
        disc = report.financial_summary.tax_discrepancies
        disc_str = ", ".join(disc) if disc else "No tax discrepancies found."
        reply = redirect_notice + (
            f"Financial Auditor Agent [Scope: {tenant}]: Audited {report.financial_summary.total_invoices_audited} invoices. "
            f"Total tax leakage identified: ₹{report.financial_summary.potential_margin_leakage:,.2f}. Details: {disc_str}"
        )
        return {"answer": reply, "source": "Skill: tool_audit_taxes", "redirect_agent": "auditor"}

    # Fallback
    report = await engine.orchestrate_audit(tenant)
    clean_tenant = tenant if tenant != "ALL" else "CONSOLIDATED"
    reply = redirect_notice + (
        f"Conglomerate Executive Overview [{clean_tenant}]: Total Sales ₹{report.sales_summary.total_revenue:,.2f}, "
        f"{len(report.inventory_summary.critical_shortages)} critical inventory shortages, "
        f"{len(report.financial_summary.tax_discrepancies)} GST issue, and "
        f"{len(report.attendance_summary.late_anomalies)} biometric late flag."
    )
    return {"answer": reply, "source": "Central Supervisor Synthesis", "redirect_agent": "supervisor"}

@app.get("/api/limiter")
def get_rate_limiter_status():
    metrics = limiter.get_metrics()
    metrics["cache"] = swarm_cache.stats()
    return metrics

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            telemetry_payload = {
                "timestamp": asyncio.get_event_loop().time(),
                "limiter": limiter.get_metrics(),
                "cache": swarm_cache.stats()
            }
            await websocket.send_json(telemetry_payload)
            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        pass
