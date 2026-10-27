import pytest
from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.abspath('backend'))

from app.main import app

client = TestClient(app)

def test_export_executive_brief():
    response = client.get("/api/export?tenant_id=ALL")
    assert response.status_code == 200
    assert "Amsavision Conglomerate" in response.text
    assert "Total Group Revenue" in response.text

def test_conversational_multi_turn_followup():
    sess = "test_turn_session_101"
    turn1 = client.post("/api/chat", json={
        "prompt": "How many TVs are in stock in Amsavision Retail?",
        "tenant_id": "ams_retail",
        "session_id": sess
    })
    assert turn1.status_code == 200
    assert "tv" in turn1.json()["answer"].lower()

    turn2 = client.post("/api/chat", json={
        "prompt": "What about AMS Associates?",
        "tenant_id": "ALL",
        "session_id": sess
    })
    assert turn2.status_code == 200
    ans2 = turn2.json()["answer"]
    # Validates that multi-turn context resolved to TV stock in AMS Associates
    assert "Multi-Turn Follow-Up" in ans2 or ("tv" in ans2.lower() and "14" in ans2)

def test_cross_agent_debate_simulation():
    response = client.post("/api/collaborate", json={"product": "Orthopedic King Mattress", "quantity": 60, "tenant_id": "dream_sleep"})
    assert response.status_code == 200
    assert len(response.json()["chain_steps"]) == 5

def test_highest_paid_employee_and_manager():
    response = client.post("/api/chat", json={"prompt": "Highest Paid Employee and Manager?", "tenant_id": "ALL"})
    assert response.status_code == 200
    ans = response.json()["answer"]
    assert "HR & Payroll Agent" in ans
    assert ("Highest Paid" in ans or "Suresh" in ans)

def test_product_sales_volume_tv():
    response = client.post("/api/chat", json={"prompt": "Number of TV sold till date?", "tenant_id": "ALL"})
    assert response.status_code == 200
    assert "Sales Volume Agent" in response.json()["answer"]

def test_logistics_fleet_dispatches():
    response = client.post("/api/chat", json={"prompt": "Show me active logistics fleet dispatches", "tenant_id": "ALL"})
    assert response.status_code == 200
    assert "Logistics" in response.json()["answer"]

def test_guardrail_rejection():
    response = client.post("/api/chat", json={"prompt": "Can I get a Pizza?", "tenant_id": "ALL"})
    assert response.status_code == 200
    assert "rejected by Swarm Guardrails" in response.json()["answer"]