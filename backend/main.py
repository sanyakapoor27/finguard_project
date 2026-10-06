"""
FinGuard CoCopilot — FastAPI Backend Server
Exposes Snowflake CoCo functionality to custom web frontends.
"""

import os
import io
import json
import hashlib
import zipfile
import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from snowflake.snowpark import Session

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
app = FastAPI(title="FinGuard CoCopilot API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Snowflake session (lazy singleton)
# ---------------------------------------------------------------------------
_session: Optional[Session] = None

def get_session() -> Session:
    global _session
    if _session is None:
        # Priority 1: Explicit env vars (Render/AWS/Docker with env set)
        if os.getenv("SNOWFLAKE_ACCOUNT"):
            _session = Session.builder.configs({
                "account": os.environ["SNOWFLAKE_ACCOUNT"],
                "user": os.environ["SNOWFLAKE_USER"],
                "password": os.environ["SNOWFLAKE_PASSWORD"],
                "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
                "database": os.getenv("SNOWFLAKE_DATABASE", "FINGUARD_DB"),
                "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
            }).create()
        else:
            # Priority 2: Try named connections from connections.toml
            conn_name = os.getenv("SNOWFLAKE_CONNECTION_NAME", "finguard")
            try:
                _session = Session.builder.config("connection_name", conn_name).create()
            except Exception:
                # Fallback: try "default"
                _session = Session.builder.config("connection_name", "default").create()
        _session.sql("USE SCHEMA FINGUARD_DB.PUBLIC").collect()
    return _session

def query(sql: str) -> list[dict]:
    return [r.as_dict() for r in get_session().sql(sql).collect()]

def query_scalar(sql: str):
    return get_session().sql(sql).collect()[0][0]


# =========================================================================
# 1. GET /api/v1/metrics/executive
# =========================================================================
@app.get("/api/v1/metrics/executive")
def executive_metrics():
    lcr = query_scalar("""
        SELECT ROUND(((HQLA_LEVEL_1 + (HQLA_LEVEL_2A * 0.85) + (HQLA_LEVEL_2B * 0.50))
            / NULLIF(EXPECTED_CASH_OUTFLOWS_30D - LEAST(EXPECTED_CASH_INFLOWS_30D,
                EXPECTED_CASH_OUTFLOWS_30D * 0.75), 0)) * 100, 2) AS LCR_PCT
        FROM FINGUARD_DB.PUBLIC.LIQUIDITY_POSITIONS
        ORDER BY SNAPSHOT_DATE DESC LIMIT 1
    """)
    fraud_vol = query_scalar("""
        SELECT ROUND(SUM(AMOUNT), 2)
        FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE FRAUD_SCORE > 0.85
    """)
    critical_alerts = query_scalar("""
        SELECT COUNT(*)
        FROM FINGUARD_DB.PUBLIC.AML_ALERTS
        WHERE SEVERITY = 'CRITICAL' AND STATUS != 'CLOSED'
    """)
    ecl = query_scalar("""
        SELECT ROUND(SUM(EXPOSURE_AT_DEFAULT * PROBABILITY_OF_DEFAULT * LOSS_GIVEN_DEFAULT), 2)
        FROM FINGUARD_DB.PUBLIC.CREDIT_EXPOSURES
    """)
    total_rwa = query_scalar("""
        SELECT ROUND(SUM(RISK_WEIGHTED_ASSETS), 2)
        FROM FINGUARD_DB.PUBLIC.CREDIT_EXPOSURES
    """)
    open_alerts = query_scalar("""
        SELECT COUNT(*) FROM FINGUARD_DB.PUBLIC.AML_ALERTS WHERE STATUS = 'OPEN'
    """)

    # 7-day LCR sparkline
    sparkline = query("""
        SELECT SNAPSHOT_DATE, ROUND(LCR_RATIO * 100, 2) AS LCR_PCT
        FROM FINGUARD_DB.PUBLIC.LIQUIDITY_POSITIONS
        ORDER BY SNAPSHOT_DATE DESC LIMIT 7
    """)

    return {
        "lcr_pct": float(lcr),
        "fraud_volume": float(fraud_vol),
        "critical_alerts": int(critical_alerts),
        "open_alerts": int(open_alerts),
        "ecl": float(ecl),
        "total_rwa": float(total_rwa),
        "lcr_sparkline": [{"date": str(r["SNAPSHOT_DATE"]), "value": float(r["LCR_PCT"])} for r in sparkline],
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }


# =========================================================================
# 2. POST /api/v1/copilot/query
# =========================================================================
class CopilotRequest(BaseModel):
    question: str
    source: str = "semantic"  # "semantic" or "search"

@app.post("/api/v1/copilot/query")
def copilot_query(req: CopilotRequest):
    session = get_session()

    if req.source == "search":
        safe_q = req.question.replace("'", "''").replace('"', '\\"')
        search_sql = f"""
            SELECT PARSE_JSON(
                SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    'FINGUARD_DB.PUBLIC.REG_POLICY_SEARCH_SERVICE',
                    '{{"query": "{safe_q}",
                      "columns": ["CHUNK_ID","REGULATION_TYPE","SECTION_REF","CLAUSE_TEXT"],
                      "limit": 5}}'
                )
            )['results'] AS RESULTS
        """
        raw = session.sql(search_sql).collect()
        results = json.loads(raw[0]["RESULTS"])

        # Log to audit trail
        session.sql(f"""
            INSERT INTO FINGUARD_DB.PUBLIC.AUDIT_TRAIL_LOGS
                (LOG_ID, USER_ID, QUERY_TEXT, CORTEX_SEARCH_SCORE, DETERMINISTIC_VERIFICATION_STATUS)
            SELECT UUID_STRING(), CURRENT_USER(), '{safe_q[:500]}',
                   {results[0].get('@scores', {}).get('cosine_similarity', 0) if results else 0},
                   'VERIFIED'
        """).collect()

        return {
            "type": "search",
            "results": results,
            "query_sql": search_sql.strip(),
            "results_count": len(results),
        }

    else:  # semantic — generate SQL via Cortex COMPLETE
        safe_q = req.question.replace("'", "''")
        gen_result = session.sql(f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet',
                'You are a Snowflake SQL expert. Tables in FINGUARD_DB.PUBLIC:
                TRANSACTIONS(TXN_ID,ACCOUNT_ID,TIMESTAMP,AMOUNT,CURRENCY,COUNTERPARTY_COUNTRY,CHANNEL,FRAUD_SCORE,IS_FLAGGED),
                LIQUIDITY_POSITIONS(SNAPSHOT_DATE,HQLA_LEVEL_1,HQLA_LEVEL_2A,HQLA_LEVEL_2B,EXPECTED_CASH_OUTFLOWS_30D,EXPECTED_CASH_INFLOWS_30D,LCR_RATIO),
                CREDIT_EXPOSURES(OBLIGOR_ID,SECTOR,EXPOSURE_AT_DEFAULT,PROBABILITY_OF_DEFAULT,LOSS_GIVEN_DEFAULT,RISK_WEIGHTED_ASSETS,RATING),
                AML_ALERTS(ALERT_ID,ACCOUNT_ID,RULE_TRIGGERED,SEVERITY,STATUS).
                Write ONLY a valid Snowflake SQL query to answer: {safe_q}') AS SQL
        """).collect()
        gen_sql = gen_result[0]["SQL"].strip().strip("`").strip()
        if gen_sql.lower().startswith("sql"):
            gen_sql = gen_sql[3:].strip()

        data = []
        error = None
        if gen_sql.upper().startswith("SELECT"):
            try:
                data = [r.as_dict() for r in session.sql(gen_sql).limit(100).collect()]
            except Exception as e:
                error = str(e)

        session.sql(f"""
            INSERT INTO FINGUARD_DB.PUBLIC.AUDIT_TRAIL_LOGS
                (LOG_ID, USER_ID, QUERY_TEXT, DETERMINISTIC_VERIFICATION_STATUS)
            SELECT UUID_STRING(), CURRENT_USER(), '{gen_sql[:500].replace("'","''")}',
                   '{"VERIFIED" if not error else "MANUAL_REVIEW"}'
        """).collect()

        return {
            "type": "semantic",
            "generated_sql": gen_sql,
            "data": data,
            "row_count": len(data),
            "error": error,
        }


# =========================================================================
# 3. GET /api/v1/lineage/{alert_id}
# =========================================================================
@app.get("/api/v1/lineage/{alert_id}")
def lineage_graph(alert_id: str):
    alerts = query(f"""
        SELECT ALERT_ID, ACCOUNT_ID, RULE_TRIGGERED, SEVERITY, STATUS
        FROM FINGUARD_DB.PUBLIC.AML_ALERTS WHERE ALERT_ID = '{alert_id}'
    """)
    if not alerts:
        raise HTTPException(404, f"Alert {alert_id} not found")

    alert = alerts[0]
    account_id = alert["ACCOUNT_ID"]

    txns = query(f"""
        SELECT TXN_ID, TIMESTAMP::VARCHAR AS TIMESTAMP, AMOUNT, CURRENCY,
               COUNTERPARTY_COUNTRY, CHANNEL, FRAUD_SCORE, IS_FLAGGED
        FROM FINGUARD_DB.PUBLIC.TRANSACTIONS
        WHERE ACCOUNT_ID = '{account_id}'
        ORDER BY FRAUD_SCORE DESC LIMIT 20
    """)

    rule_search = {
        "Structuring": "structuring detection currency transaction",
        "Rapid Velocity": "suspicious activity report SAR filing",
        "High Risk Country": "high risk jurisdiction enhanced due diligence",
        "Offshore Loop": "offshore circular transfer detection",
    }
    sq = rule_search.get(alert["RULE_TRIGGERED"], alert["RULE_TRIGGERED"])
    clauses_raw = get_session().sql(f"""
        SELECT PARSE_JSON(SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
            'FINGUARD_DB.PUBLIC.REG_POLICY_SEARCH_SERVICE',
            '{{"query": "{sq}", "columns": ["CHUNK_ID","SECTION_REF","CLAUSE_TEXT","REGULATION_TYPE"], "limit": 3}}'
        ))['results'] AS R
    """).collect()
    clauses = json.loads(clauses_raw[0]["R"])

    dispatches = query(f"""
        SELECT DISPATCH_ID, CHANNEL, STATUS, DISPATCHED_AT::VARCHAR AS DISPATCHED_AT,
               PAYLOAD:verdict::VARCHAR AS VERDICT
        FROM FINGUARD_DB.PUBLIC.MCP_DISPATCH_LOG
        WHERE ALERT_ID = '{alert_id}' ORDER BY DISPATCHED_AT DESC
    """)

    # Build React Flow nodes and edges
    nodes = [
        {"id": "account", "type": "custom", "position": {"x": 0, "y": 200},
         "data": {"label": account_id, "category": "account", "severity": alert["SEVERITY"],
                  "status": alert["STATUS"]}},
    ]
    edges = []

    for i, t in enumerate(txns[:8]):
        nid = f"txn-{i}"
        nodes.append({
            "id": nid, "type": "custom", "position": {"x": 300, "y": i * 80},
            "data": {"label": t["TXN_ID"][:12], "category": "transaction",
                     "amount": float(t["AMOUNT"]), "fraud_score": float(t["FRAUD_SCORE"]),
                     "flagged": t["IS_FLAGGED"], "country": t["COUNTERPARTY_COUNTRY"]},
        })
        edges.append({"id": f"e-acct-{nid}", "source": "account", "target": nid, "animated": True})

    for i, c in enumerate(clauses):
        nid = f"clause-{i}"
        nodes.append({
            "id": nid, "type": "custom", "position": {"x": 650, "y": i * 120 + 100},
            "data": {"label": c["SECTION_REF"], "category": "clause",
                     "text": c["CLAUSE_TEXT"][:200], "framework": c["REGULATION_TYPE"]},
        })
        for ti in range(min(len(txns), 8)):
            edges.append({"id": f"e-txn{ti}-{nid}", "source": f"txn-{ti}", "target": nid,
                          "style": {"strokeDasharray": "5,5"}})

    for i, d in enumerate(dispatches):
        nid = f"action-{i}"
        nodes.append({
            "id": nid, "type": "custom", "position": {"x": 1000, "y": i * 100 + 150},
            "data": {"label": f"{d['CHANNEL']}: {d.get('VERDICT','N/A')}",
                     "category": "action", "channel": d["CHANNEL"],
                     "dispatch_id": d["DISPATCH_ID"]},
        })
        for ci in range(len(clauses)):
            edges.append({"id": f"e-clause{ci}-{nid}", "source": f"clause-{ci}", "target": nid})

    return {
        "alert": alert,
        "nodes": nodes,
        "edges": edges,
        "transactions": txns,
        "clauses": clauses,
        "dispatches": dispatches,
    }


# =========================================================================
# 4. POST /api/v1/sandbox/stress-test
# =========================================================================
class StressTestRequest(BaseModel):
    haircut_adjustment_pct: float = 0
    default_rate_spike_pct: float = 0
    outflow_speed_pct: float = 0

@app.post("/api/v1/sandbox/stress-test")
def stress_test(req: StressTestRequest):
    rows = query("""
        SELECT SNAPSHOT_DATE::VARCHAR AS SNAPSHOT_DATE,
            HQLA_LEVEL_1, HQLA_LEVEL_2A, HQLA_LEVEL_2B,
            EXPECTED_CASH_OUTFLOWS_30D, EXPECTED_CASH_INFLOWS_30D
        FROM FINGUARD_DB.PUBLIC.LIQUIDITY_POSITIONS
        ORDER BY SNAPSHOT_DATE DESC LIMIT 30
    """)

    h2a_base, h2b_base = 0.85, 0.50
    h2a_s = max(0, h2a_base - req.haircut_adjustment_pct / 100)
    h2b_s = max(0, h2b_base - req.haircut_adjustment_pct / 100)
    out_mult = 1 + req.outflow_speed_pct / 100

    lcr_series = []
    for r in rows:
        l1, l2a, l2b = float(r["HQLA_LEVEL_1"]), float(r["HQLA_LEVEL_2A"]), float(r["HQLA_LEVEL_2B"])
        out, inf = float(r["EXPECTED_CASH_OUTFLOWS_30D"]), float(r["EXPECTED_CASH_INFLOWS_30D"])
        net_base = max(out - min(inf, out * 0.75), 1)
        net_stress = max(out * out_mult - min(inf, out * out_mult * 0.75), 1)
        baseline_lcr = (l1 + l2a * h2a_base + l2b * h2b_base) / net_base * 100
        stressed_lcr = (l1 + l2a * h2a_s + l2b * h2b_s) / net_stress * 100
        lcr_series.append({
            "date": r["SNAPSHOT_DATE"], "baseline": round(baseline_lcr, 2),
            "stressed": round(stressed_lcr, 2),
        })

    rwa_row = query("""
        SELECT SUM(RISK_WEIGHTED_ASSETS) AS RWA,
               SUM(EXPOSURE_AT_DEFAULT * PROBABILITY_OF_DEFAULT * LOSS_GIVEN_DEFAULT) AS ECL
        FROM FINGUARD_DB.PUBLIC.CREDIT_EXPOSURES
    """)[0]
    pd_mult = 1 + req.default_rate_spike_pct / 100

    return {
        "lcr_series": lcr_series,
        "rwa_baseline": float(rwa_row["RWA"]),
        "rwa_stressed": float(rwa_row["RWA"]) * (1 + req.default_rate_spike_pct / 200),
        "ecl_baseline": float(rwa_row["ECL"]),
        "ecl_stressed": float(rwa_row["ECL"]) * pd_mult,
        "params": req.model_dump(),
    }


# =========================================================================
# 5. POST /api/v1/audit/export
# =========================================================================
class AuditExportRequest(BaseModel):
    alert_id: str

@app.post("/api/v1/audit/export")
def audit_export(req: AuditExportRequest):
    lineage = lineage_graph(req.alert_id)
    alert = lineage["alert"]
    account_id = alert["ACCOUNT_ID"]

    stats = query(f"""
        SELECT COUNT(*) AS TOTAL_TXNS, ROUND(SUM(AMOUNT),2) AS TOTAL_VOL,
            SUM(CASE WHEN IS_FLAGGED THEN 1 ELSE 0 END) AS FLAGGED,
            ROUND(MAX(FRAUD_SCORE),4) AS MAX_FRAUD,
            SUM(CASE WHEN COUNTERPARTY_COUNTRY IN ('IR','KP','RU','AF','KY','NG','PA','PK') THEN 1 ELSE 0 END) AS HIGH_RISK_GEO,
            SUM(CASE WHEN AMOUNT > 10000 THEN 1 ELSE 0 END) AS OVER_10K
        FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE ACCOUNT_ID = '{account_id}'
    """)[0]

    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    memo = f"""# FinGuard Audit Defense Package
**Generated:** {now}
**Alert:** {req.alert_id} | **Account:** {account_id}
**Rule:** {alert['RULE_TRIGGERED']} | **Severity:** {alert['SEVERITY']}

## Executive Summary
| Metric | Value |
|--------|-------|
| Total Transactions | {stats['TOTAL_TXNS']} |
| Total Volume | ${float(stats['TOTAL_VOL']):,.2f} |
| Flagged | {stats['FLAGGED']} |
| Max Fraud Score | {stats['MAX_FRAUD']} |
| High-Risk Geo | {stats['HIGH_RISK_GEO']} |

## Regulatory Citations
"""
    for c in lineage["clauses"]:
        memo += f"### {c['SECTION_REF']}\n{c['CLAUSE_TEXT']}\n\n"

    content_hash = hashlib.sha256(memo.encode()).hexdigest()
    memo += f"\n## Digital Signature\nSHA-256: `{content_hash}`\nTimestamp: {now}\n"

    sql_log = f"-- Transaction pull\nSELECT * FROM TRANSACTIONS WHERE ACCOUNT_ID = '{account_id}';\n"
    lineage_json = json.dumps({"nodes": lineage["nodes"], "edges": lineage["edges"]}, indent=2)

    # Build ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("audit_memo.md", memo)
        zf.writestr("sql_query_log.sql", sql_log)
        zf.writestr("lineage_graph.json", lineage_json)
        zf.writestr("execution_metadata.json", json.dumps({
            "alert_id": req.alert_id, "account_id": account_id,
            "generated_at": now, "sha256": content_hash,
            "stats": {k: float(v) if isinstance(v, (int, float)) else str(v) for k, v in stats.items()},
        }, indent=2))
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=audit_package_{req.alert_id}.zip"},
    )


# =========================================================================
# Health check
# =========================================================================
@app.get("/api/v1/health")
def health():
    return {"status": "ok", "engine": "FinGuard CoCopilot", "version": "1.0.0"}
