from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import or_

from .db import SessionLocal
from .models import AdvocateProfile, Escalation


router = APIRouter(tags=["escalation-dashboard"])


def _status(esc: Escalation) -> str:
    if esc.resolved_at:
        return "resolved"
    if esc.acknowledgement_received_at:
        return "acknowledged"
    return "open"


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _serialize(esc: Escalation, lawyer_name: Optional[str]) -> dict:
    return {
        "escalation_id": esc.escalation_id,
        "case_id": esc.case_id,
        "event_type": esc.event_type,
        "urgency": esc.urgency_level,
        "status": _status(esc),
        "brief": esc.brief,
        "advocate_id": esc.advocate_id,
        "lawyer_name": lawyer_name or esc.advocate_id,
        "client_id": esc.client_id,
        "client_name": esc.client_name,
        "created_at": _iso(esc.brief_prepared_at),
        "acknowledged_at": _iso(esc.acknowledgement_received_at),
        "acknowledged_by": esc.acknowledged_by,
        "resolved_at": _iso(esc.resolved_at),
        "resolution_notes": esc.resolution_notes,
        "alerts_sent": esc.total_alerts_sent or 0,
    }


@router.get("/dashboard/summary")
def dashboard_summary():
    db = SessionLocal()
    try:
        escalations = db.query(Escalation).all()
        return {
            "total": len(escalations),
            "open": sum(_status(item) == "open" for item in escalations),
            "acknowledged": sum(
                _status(item) == "acknowledged" for item in escalations
            ),
            "resolved": sum(
                _status(item) == "resolved" for item in escalations
            ),
            "critical_open": sum(
                _status(item) == "open"
                and (item.urgency_level or "").upper() == "CRITICAL"
                for item in escalations
            ),
        }
    finally:
        db.close()


@router.get("/dashboard/escalations")
def dashboard_escalations(
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    db = SessionLocal()
    try:
        query = (
            db.query(Escalation, AdvocateProfile.name)
            .outerjoin(
                AdvocateProfile,
                AdvocateProfile.advocate_id == Escalation.advocate_id,
            )
            .order_by(Escalation.brief_prepared_at.desc())
        )

        if urgency:
            query = query.filter(
                Escalation.urgency_level == urgency.strip().upper()
            )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Escalation.case_id.ilike(pattern),
                    Escalation.event_type.ilike(pattern),
                    Escalation.advocate_id.ilike(pattern),
                    Escalation.client_name.ilike(pattern),
                )
            )

        records = [
            _serialize(escalation, lawyer_name)
            for escalation, lawyer_name in query.limit(limit).all()
        ]
        if status:
            requested_status = status.strip().lower()
            records = [
                record
                for record in records
                if record["status"] == requested_status
            ]
        return {"items": records, "count": len(records)}
    finally:
        db.close()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Escalation Dashboard</title>
  <style>
    :root {
      --ink: #14213d; --muted: #667085; --paper: #f5f7fb;
      --card: #fff; --line: #e4e7ec; --critical: #b42318;
      --high: #b54708; --normal: #175cd3; --ok: #067647;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; color: var(--ink);
      background: radial-gradient(circle at top right, #e8efff, transparent 32rem), var(--paper);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
    }
    main { width: min(1400px, 94vw); margin: 0 auto; padding: 32px 0 56px; }
    header { display: flex; justify-content: space-between; gap: 24px; align-items: end; }
    h1 { margin: 0; font-size: clamp(28px, 4vw, 44px); letter-spacing: -.04em; }
    header p { margin: 8px 0 0; color: var(--muted); }
    button, input, select, textarea { font: inherit; }
    button { cursor: pointer; }
    .refresh {
      border: 1px solid var(--line); background: var(--card); color: var(--ink);
      border-radius: 10px; padding: 10px 14px; font-weight: 700;
    }
    .stats {
      display: grid; grid-template-columns: repeat(5, minmax(130px, 1fr));
      gap: 14px; margin: 28px 0 18px;
    }
    .stat {
      background: var(--card); border: 1px solid var(--line);
      border-radius: 16px; padding: 18px; box-shadow: 0 8px 24px #14213d0d;
    }
    .stat span { color: var(--muted); font-size: 13px; font-weight: 700; text-transform: uppercase; }
    .stat strong { display: block; margin-top: 8px; font-size: 30px; }
    .filters {
      display: grid; grid-template-columns: minmax(220px, 2fr) 1fr 1fr;
      gap: 12px; background: var(--card); border: 1px solid var(--line);
      border-radius: 16px; padding: 14px; margin-bottom: 18px;
    }
    input, select, textarea {
      width: 100%; border: 1px solid var(--line); border-radius: 10px;
      padding: 11px 12px; color: var(--ink); background: white;
    }
    .table-wrap {
      overflow-x: auto; background: var(--card); border: 1px solid var(--line);
      border-radius: 16px; box-shadow: 0 10px 30px #14213d0d;
    }
    table { width: 100%; border-collapse: collapse; min-width: 1050px; }
    th, td { padding: 15px 14px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }
    th { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
    tr:last-child td { border-bottom: 0; }
    .case { font-weight: 800; }
    .secondary { margin-top: 4px; color: var(--muted); font-size: 13px; }
    .pill {
      display: inline-flex; border-radius: 999px; padding: 5px 9px;
      font-size: 12px; font-weight: 800; text-transform: capitalize; background: #eef2f6;
    }
    .urgency-critical { color: var(--critical); background: #fee4e2; }
    .urgency-high { color: var(--high); background: #fffaeb; }
    .urgency-normal { color: var(--normal); background: #eff8ff; }
    .status-resolved { color: var(--ok); background: #ecfdf3; }
    .actions { display: flex; gap: 8px; }
    .action {
      border: 0; border-radius: 8px; padding: 8px 10px;
      background: var(--ink); color: white; font-weight: 700;
    }
    .action.resolve { background: var(--ok); }
    .action:disabled { opacity: .4; cursor: default; }
    .empty { padding: 48px; text-align: center; color: var(--muted); }
    dialog { border: 0; border-radius: 16px; width: min(480px, 90vw); padding: 24px; box-shadow: 0 24px 70px #14213d33; }
    dialog::backdrop { background: #14213d88; }
    dialog h2 { margin-top: 0; }
    dialog menu { display: flex; justify-content: flex-end; gap: 10px; padding: 0; margin: 18px 0 0; }
    .error { color: var(--critical); margin: 16px 0 0; }
    @media (max-width: 800px) {
      header { align-items: flex-start; flex-direction: column; }
      .stats { grid-template-columns: repeat(2, 1fr); }
      .filters { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Escalation command center</h1>
      <p>Track urgent case events, delivery attempts, acknowledgements, and resolutions.</p>
    </div>
    <button class="refresh" onclick="loadDashboard()">Refresh</button>
  </header>

  <section class="stats">
    <div class="stat"><span>Total</span><strong id="total">0</strong></div>
    <div class="stat"><span>Open</span><strong id="open">0</strong></div>
    <div class="stat"><span>Critical open</span><strong id="critical_open">0</strong></div>
    <div class="stat"><span>Acknowledged</span><strong id="acknowledged">0</strong></div>
    <div class="stat"><span>Resolved</span><strong id="resolved">0</strong></div>
  </section>

  <section class="filters">
    <input id="search" placeholder="Search case, event, lawyer, or client">
    <select id="status">
      <option value="">All statuses</option><option value="open">Open</option>
      <option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option>
    </select>
    <select id="urgency">
      <option value="">All urgency levels</option><option value="CRITICAL">Critical</option>
      <option value="HIGH">High</option><option value="NORMAL">Normal</option>
    </select>
  </section>

  <div class="table-wrap">
    <table>
      <thead><tr><th>Case</th><th>Urgency</th><th>Status</th><th>People</th>
      <th>Created</th><th>Alerts</th><th>Actions</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <div id="empty" class="empty" hidden>No escalations match these filters.</div>
  </div>
  <p id="error" class="error"></p>
</main>

<dialog id="actionDialog">
  <form method="dialog" id="actionForm">
    <h2 id="dialogTitle">Update escalation</h2>
    <input type="hidden" id="actionId"><input type="hidden" id="actionType">
    <label id="actionLabel" for="actionText">Details</label>
    <textarea id="actionText" rows="4"></textarea>
    <menu>
      <button value="cancel" class="refresh">Cancel</button>
      <button value="default" class="action">Confirm</button>
    </menu>
  </form>
</dialog>

<script>
  const apiBase = window.location.pathname.replace(/\\/dashboard\\/?$/, "");
  const rows = document.getElementById("rows");
  const dialog = document.getElementById("actionDialog");
  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[char]);

  function formatDate(value) {
    if (!value) return "-";
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium", timeStyle: "short"
    }).format(new Date(value));
  }

  async function getJson(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed: ${response.status}`);
    }
    return response.json();
  }

  function renderRows(items) {
    document.getElementById("empty").hidden = items.length !== 0;
    rows.innerHTML = items.map(item => {
      const canAck = item.status === "open";
      const canResolve = item.status !== "resolved";
      return `<tr>
        <td><div class="case">${escapeHtml(item.case_id)}</div>
        <div class="secondary">${escapeHtml(item.event_type)}</div></td>
        <td><span class="pill urgency-${escapeHtml(item.urgency.toLowerCase())}">${escapeHtml(item.urgency)}</span></td>
        <td><span class="pill status-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
        <td><div>${escapeHtml(item.lawyer_name)}</div>
        <div class="secondary">${escapeHtml(item.client_name || "No client name")}</div></td>
        <td>${escapeHtml(formatDate(item.created_at))}</td>
        <td>${escapeHtml(item.alerts_sent)}</td>
        <td><div class="actions">
          <button class="action" ${canAck ? "" : "disabled"} onclick="openAction(${item.escalation_id}, 'ack')">Acknowledge</button>
          <button class="action resolve" ${canResolve ? "" : "disabled"} onclick="openAction(${item.escalation_id}, 'resolve')">Resolve</button>
        </div></td>
      </tr>`;
    }).join("");
  }

  async function loadDashboard() {
    document.getElementById("error").textContent = "";
    const params = new URLSearchParams();
    for (const key of ["search", "status", "urgency"]) {
      const value = document.getElementById(key).value.trim();
      if (value) params.set(key, value);
    }
    try {
      const [summary, data] = await Promise.all([
        getJson(`${apiBase}/dashboard/summary`),
        getJson(`${apiBase}/dashboard/escalations?${params}`)
      ]);
      for (const key of ["total", "open", "critical_open", "acknowledged", "resolved"]) {
        document.getElementById(key).textContent = summary[key];
      }
      renderRows(data.items);
    } catch (error) {
      document.getElementById("error").textContent = error.message;
    }
  }

  function openAction(id, type) {
    document.getElementById("actionId").value = id;
    document.getElementById("actionType").value = type;
    document.getElementById("actionText").value = "";
    document.getElementById("dialogTitle").textContent =
      type === "ack" ? "Acknowledge escalation" : "Resolve escalation";
    document.getElementById("actionLabel").textContent =
      type === "ack" ? "Acknowledged by" : "Resolution notes";
    dialog.showModal();
  }

  document.getElementById("actionForm").addEventListener("submit", async event => {
    event.preventDefault();
    const id = document.getElementById("actionId").value;
    const type = document.getElementById("actionType").value;
    const text = document.getElementById("actionText").value.trim();
    if (type === "ack" && !text) return;
    const body = type === "ack"
      ? { acknowledged_by: text }
      : { resolution_notes: text || null };
    try {
      await getJson(`${apiBase}/escalation/${id}/${type}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      dialog.close();
      await loadDashboard();
    } catch (error) {
      document.getElementById("error").textContent = error.message;
      dialog.close();
    }
  });

  let searchTimer;
  document.getElementById("search").addEventListener("input", () => {
    clearTimeout(searchTimer); searchTimer = setTimeout(loadDashboard, 250);
  });
  document.getElementById("status").addEventListener("change", loadDashboard);
  document.getElementById("urgency").addEventListener("change", loadDashboard);
  loadDashboard();
  setInterval(loadDashboard, 30000);
</script>
</body>
</html>
"""
