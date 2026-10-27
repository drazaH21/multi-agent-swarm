from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class TenantID(str, Enum):
    AMS_RETAIL = "ams_retail"
    AMS_ASSOC = "ams_assoc"
    MVM_DIST = "mvm_dist"
    DREAM_SLEEP = "dream_sleep"
    CONSOLIDATED = "ALL"

class AgentStatus(str, Enum):
    IDLE = "IDLE"
    SCANNING = "SCANNING"
    ANALYZING = "ANALYZING"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    DISPATCHING = "DISPATCHING"

class AgentTelemetry(BaseModel):
    agent_id: str
    tenant_id: TenantID
    status: AgentStatus
    current_action: str
    rpm_used: int = 0
    tpm_used: int = 0
    latency_ms: float = 0.0
    last_finding: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    pos_x: float = 0.0
    pos_y: float = 0.0
    target_node: str = "Central Supervisor"

class AttendanceAuditResult(BaseModel):
    tenant_id: str
    total_staff: int
    present_count: int
    late_anomalies: List[str]

class SalesAuditResult(BaseModel):
    tenant_id: str
    total_revenue: float
    total_invoices: int
    avg_invoice_value: float

class FinancialAuditResult(BaseModel):
    tenant_id: str
    total_invoices_audited: int
    tax_discrepancies: List[str]
    potential_margin_leakage: float

class InventoryAuditResult(BaseModel):
    tenant_id: str
    total_skus_tracked: int
    critical_shortages: List[Dict[str, Any]]

class ConglomerateAuditReport(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: TenantID
    attendance_summary: AttendanceAuditResult
    sales_summary: SalesAuditResult
    financial_summary: FinancialAuditResult
    inventory_summary: InventoryAuditResult
    synthesis_summary: str
    recommendations: List[str]
