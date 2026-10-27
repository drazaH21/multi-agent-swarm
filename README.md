# retail-multi-agent-swarm

> Autonomous, local-first multi-agent office environment designed for multi-subsidiary conglomerate operations. Integrates a supervisor-led agent hierarchy, deterministic SQL analytics, local LLM persona synthesis (`llama3:latest` via Ollama), Human-in-the-Loop (HITL) approval queues, and a 2D pixel-art operational floor with live WebSocket telemetry.

---

## 1. Project Overview

Modern conglomerate enterprises frequently struggle with operational data silos: inventory managers lack direct insight into transit logistics, sales reps lack visibility into warehouse material deficits, and executive leadership must manually aggregate disparate BI reports across separate subsidiaries.

`retail-multi-agent-swarm` solves this by orchestrating eight autonomous, specialized AI agents across four distinct business subsidiaries:
- **Amsa Retail Hub** (Consumer appliances, electronics, retail showroom floor)
- **MVM Wholesale Distributors** (B2B wholesale distributor operations)
- **Dream Sleep Bedding Solutions** (Mattress manufacturing, foam conversion)
- **Amsa Associates & Parts** (Raw material supply chain, Bonnell spring fabrication)

The system enforces strict domain isolation, stateful multi-turn conversational memory, edge guardrails, and deterministic tool verification to eliminate hallucination in critical business decisions.

---

## 2. Architecture

```
                       ┌─────────────────────────────────────────┐
                       │          Operator / Web Client          │
                       │   (Pixel-Art Floor & Agent Terminals)   │
                       └────────────────────┬────────────────────┘
                                            │ HTTP / WebSocket
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │        FastAPI Gateway Router           │
                       │  - Sliding Window Token Bucket Limiter  │
                       │  - Swarm Domain Guardrail Engine        │
                       └────────────────────┬────────────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               │                                                         │
   [ Single-Domain Query ]                                   [ Multi-Domain Query ]
               │                                                         │
               ▼                                                         ▼
┌─────────────────────────────┐                         ┌─────────────────────────────────┐
│ Specialized Floor Agents    │ ──(Domain Mismatch)───► │ Central Executive Supervisor    │
│ - Attendance & Biometrics   │                         │ - Cross-Subsidiary Aggregator   │
│ - Sales & Revenue (dbt)     │ ◄──(Explicit Handoff)── │ - HITL Action Queue Coordinator │
│ - GST & Tax Auditor         │                         │ - Order Debate Arbiter          │
│ - Inventory & Materials     │                         └────────────────┬────────────────┘
│ - Customer Support & SLA    │                                          │
│ - HR & Compensation         │                                          │
│ - Logistics & Fleet         │                                          │
└──────────────┬──────────────┘                                          │
               │                                                         │
               └────────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │       Context & Deterministic Core      │
                       │  - Stateful Bounded Session Memory      │
                       │  - Swarm LRU / TTL Analytical Cache     │
                       └────────────────────┬────────────────────┘
                                            │
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │     Analytical & Storage Layer          │
                       │  - SQLite (Raw Tables + dbt Marts)      │
                       │  - HITL Approval Queue (B-Tree indexed) │
                       └────────────────────┬────────────────────┘
                                            │ Verified Fact Payload
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │        Local Synthesis Engine           │
                       │  - Ollama (`llama3:latest`)             │
                       │  - Persona Guided System Prompts        │
                       │  - Deterministic Direct Fallbacks       │
                       └─────────────────────────────────────────┘
```

---

## 3. Agents & Domain Responsibilities

| Agent | Domain & Scope | Primary Tools & Marts |
|---|---|---|
| **Executive Supervisor** | Conglomerate-wide health, executive overviews, cross-domain escalations, order debate arbitrations | `orchestrate_audit()`, `fct_company_sales_breakdown` |
| **Sales & Revenue** | Gross turnover, ticket size, category-wise volume, dbt sales performance marts | `tool_query_product_sales_volume()`, `fct_product_sales_volume` |
| **Inventory & Materials** | Raw material weights (40D foam), finished goods stock, critical deficit alerts | `tool_query_inventory_item()`, `raw_inventory` |
| **HR & Payroll** | Headcount, monthly payroll liabilities, compensation rankings, leave tracking | `tool_query_hr_payroll()`, `raw_payroll` |
| **Logistics & Fleet** | Active container dispatches, hub-to-hub transit statuses, cargo manifests | `tool_query_logistics_dispatches()`, `raw_logistics_dispatches` |
| **GST & Compliance** | Invoice tax rates (HSN 9404 12% vs 18%), margin leakage audits, remittance flags | `tool_audit_taxes()`, `raw_invoices` |
| **Customer Support** | Warranty sag guarantees, installation delays, transit damages, SLA breaches | `tool_query_customer_support()`, `raw_support_tickets` |
| **Attendance & Shifts** | Warehouse punch-ins, showroom biometric check-ins, late arrival anomalies | `tool_query_attendance()`, `raw_attendance` |

---

## 4. Domain Isolation & Cross-Agent Handoffs

### Why Domain Isolation is Enforced
In an enterprise, granting every user or terminal unrestricted access creates severe compliance and data governance risks. A showroom floor executive or attendance operator should not be able to inspect unredacted executive payroll liabilities, and a dispatch coordinator does not require access to raw tax leakage audits.

### Cross-Domain Redirection Mechanism
When an operator submits a query outside an agent's assigned jurisdiction:
1. **Detection**: Heuristic regex and keyword token matching evaluate the prompt against domain dictionaries.
2. **Cardinality Verification**:
   - If `domains_hit >= 2` or consolidated terms (`"consolidated"`, `"overview"`, `"all subsidiaries"`, `"briefing"`) are detected, the inquiry requires executive clearance.
   - If a single foreign domain is detected (e.g., asking the Attendance Agent about mattress foam stock), the appropriate specialist agent is resolved directly.
3. **Automated Handoff Execution**:
   - The origin agent acknowledges the boundary:
     ```text
     [Attendance Agent]: 'That consolidated inquiry requires cross-domain authority. Transferring you to Executive Supervisor in the cabin.'
     ```
   - The UI canvas programmatically pans focus across the floor to the appropriate workstation or the glass executive cabin.
   - The terminal session switches context to the new agent persona and issues verified query execution.

---

## 5. End-to-End Operational Flow

1. **Intake & Edge Guardrail**: User query arrives via `/api/chat`. Queries containing irrelevant or out-of-scope topics (e.g., movies, recipes, sports scores) are rejected with a standardized Guardrail notice without invoking the LLM.
2. **Contextual Multi-Turn Resolution**: The session memory inspects the rolling dialogue history. If the query is an elliptical follow-up (e.g., *"How many TVs in Retail?"* followed by *"What about AMS Associates?"*), the system extracts the prior entity target (`SKU: TV`) and resolves stock for the newly requested tenant.
3. **Deterministic Data Retrieval**: The agent executes an exact SQL query against `data/conglomerate.db`. If a query pattern is identical to a recent extraction, the Swarm LRU/TTL cache intercepts and serves the pre-calculated payload.
4. **Local LLM Synthesis**: The exact structured facts (e.g., `Total Sales: ₹4,870,000.00`, `Shortage: 380 Kg 40D Foam`) are formatted into a system prompt for Ollama's `llama3:latest`. The LLM synthesizes an operational briefing in character. If Ollama is offline or uninstalled, deterministic template fallbacks trigger seamlessly.
5. **Cross-Agent Collaboration Debate**: For complex logistics feasibility queries (e.g., *"Can we fulfill 60 Orthopedic Mattresses?"*), a 5-step collaborative graph runs sequentially:
   - Sales checks demand velocity $\rightarrow$ Inventory checks foam/spring availability $\rightarrow$ Logistics evaluates fleet schedules $\rightarrow$ Auditor confirms margin and tax compliance $\rightarrow$ Supervisor renders the final executive verdict.
6. **Human-in-the-Loop (HITL) Queue**: High-impact recommendations (e.g., emergency purchase order `PO-FOAM-2026` for ₹1,33,000 or GST remittance differential adjustments) are written to `action_approval_queue` with status `PENDING`, awaiting manual administrative execution via `/api/actions/{action_id}/execute`.

---

## 6. Algorithms and Data Structures (DSA)

- **Heuristic NLP & Keyword Token Scoring (Algorithms)**: Evaluates query intent without requiring heavy classifier inference, tracking multi-domain hit cardinality.
- **LRU / TTL Cache Expiry (Algorithms)**: Evicts expired entries based on a 30-second TTL window to keep real-time metrics fresh while preventing redundant database hits.
- **Sliding Window Token Bucket (Algorithms)**: Rate limits concurrent inbound requests to prevent local LLM resource starvation.
- **Sequential Finite State Machine (Algorithms)**: Orchestrates deterministic progression across the 5-node cross-agent collaboration debate chain.
- **Hash Maps / Dictionaries (`Dict[str, Any]`) (Data Structures)**: Used for O(1) persona lookups, tool routing dictionaries, and composite string-serialized cache keys (`f"{tool_name}:{sorted(params.items())}"`).
- **Bounded Queues / Circular Deque (`collections.deque`) (Data Structures)**: Enforces a sliding rolling window of conversational turns per session ID, mitigating memory bloat over prolonged chat interactions.
- **FIFO Priority Approval Queue (Data Structures)**: Ranks pending HITL administrative interventions ordered by operational criticality (`CRITICAL` $\rightarrow$ `HIGH` $\rightarrow$ `MEDIUM`).
- **Relational B-Tree Indices (Data Structures)**: Indexes key SQLite foreign keys and filter columns (`company_id`, `category`, `status`) to ensure sub-millisecond analytical aggregations.

---

## 7. Test Suite & Validation

The test suite (`tests/test_agent_system.py`) evaluates the system end-to-end using `pytest`:

```bash
pytest tests/test_agent_system.py -v
```

### Verified Test Cases:
1. `test_export_executive_brief`: Validates generation of the consolidated HTML executive briefing, dbt subsidiary sales marts, and handling of mixed string/dict inventory deficit lists.
2. `test_conversational_multi_turn_followup`: Confirms that context memory preserves active entity SKUs across sequential dialogue turns without explicit re-mention.
3. `test_cross_agent_debate_simulation`: Verifies the 5-step collaborative reasoning stream across Sales, Inventory, Logistics, Auditor, and Supervisor.
4. `test_highest_paid_employee_and_manager`: Evaluates HR payroll query sorting to differentiate the top individual earner from the highest-paid manager/lead.
5. `test_product_sales_volume_tv`: Validates aggregate unit sales and revenue calculations from the `fct_product_sales_volume` dbt analytical mart.
6. `test_logistics_fleet_dispatches`: Verifies fleet tracking data retrieval across transit routes and container manifests.
7. `test_guardrail_rejection`: Asserts that out-of-scope non-business queries are intercepted and rejected at the gateway.

---

## 8. Setup & Installation

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) with `llama3:latest` installed:
  ```bash
  ollama pull llama3:latest
  ```

### Installation
```bash
# Clone the repository
git clone https://github.com/your-username/retail-multi-agent-swarm.git
cd retail-multi-agent-swarm

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate      # Windows
source venv/bin/activate    # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Seed the database
python seed_db.py

# Run the test suite
pytest tests/test_agent_system.py -v

# Start the application
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Access the interactive dashboard at: `http://127.0.0.1:8000/dashboard`
