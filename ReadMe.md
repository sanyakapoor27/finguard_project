# FinGuard CoCopilot

**AI-Driven Real-Time Risk, Liquidity & AML Reporting System Built on Snowflake**

> Built with the help of **Snowflake CoCo (Cortex Code)** — from database design to semantic models, Cortex Search indexing, custom skills, MCP integrations, and full-stack deployment.

![FinGuard Dashboard](https://github.com/user-attachments/assets/34dbc9e7-2570-4201-9ea2-75e70f79800c)

---

## Live Demo Links

| Surface | URL |
|---------|-----|
| **Streamlit Cloud** | [finguard-copilot.streamlit.app](https://app.snowflake.com/streamlit/xlagkiw/qo59602/#/apps/qyse2rgpsw5k2ubn5hm2) |
---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [The 8 Core Features](#the-8-core-features)
3. [Tech Stack](#tech-stack)
4. [How We Used CoCo CLI](#how-we-used-coco-cli)
5. [Database Schema](#database-schema)
6. [Setup & Installation](#setup--installation)
7. [Deploy to Streamlit Cloud](#deploy-to-streamlit-cloud)
8. [Deploy to Render](#deploy-to-render)
9. [Run Locally](#run-locally)
10. [Project Structure](#project-structure)
11. [Screenshots](#screenshots)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FinGuard CoCopilot                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  Streamlit   │  │   Next.js    │  │   Snowsight Workspace │ │
│  │  (Cloud/     │  │  (Render/    │  │   (Native Snowflake)  │ │
│  │   Local)     │  │   Local)     │  │                       │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
│         │                 │                       │             │
│         │          ┌──────┴───────┐               │             │
│         │          │   FastAPI    │               │             │
│         │          │   Backend    │               │             │
│         │          └──────┬───────┘               │             │
│         │                 │                       │             │
│  ┌──────┴─────────────────┴───────────────────────┴──────────┐ │
│  │                    Snowflake                               │ │
│  │  ┌────────────┐ ┌──────────────┐ ┌──────────────────────┐ │ │
│  │  │ FINGUARD_DB│ │Cortex Search │ │  Semantic View       │ │ │
│  │  │ 7 Tables   │ │REG_POLICY_   │ │  FINGUARD_ONTOLOGY   │ │ │
│  │  │ 100K+ rows │ │SEARCH_SERVICE│ │  (Cortex Analyst)    │ │ │
│  │  └────────────┘ └──────────────┘ └──────────────────────┘ │ │
│  │  ┌────────────┐ ┌──────────────┐ ┌──────────────────────┐ │ │
│  │  │ Stream +   │ │ Atlassian    │ │  CoCo Custom Skill   │ │ │
│  │  │ Task       │ │ MCP Server   │ │  audit_evidence_     │ │ │
│  │  │ (CDC)      │ │ (Jira)       │ │  builder             │ │ │
│  │  └────────────┘ └──────────────┘ └──────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

![Architecture Diagram](https://github.com/user-attachments/assets/50567341-b280-4566-b2bc-cd2ff8612885)

---

## The 8 Core Features

### 1. Executive Risk & Liquidity Command Center
Live KPI dashboard with Current LCR %, Fraud At-Risk Volume, Critical AML Alerts, Expected Credit Loss (ECL), and Total RWA. Includes a 14-day LCR sparkline and transaction volume breakdown by channel (WIRE/ACH/SWIFT/CRYPTO).

![Command Center](<img width="1466" height="527" alt="image" src="https://github.com/user-attachments/assets/5353147a-8b80-4c9f-be05-8e45b998b96e" />
)

### 2. Deterministic Dual-Verifier Copilot
Natural language query interface that runs **both** Cortex Analyst (SQL generation) and Cortex Search (policy retrieval) simultaneously. Results are cross-checked with a real-time VERIFIED / PARTIAL / FAILED variance badge. All queries are logged to `AUDIT_TRAIL_LOGS` with verification status.

![Dual Verifier](https://github.com/user-attachments/assets/077f664c-29df-4f82-a201-6622183212c6)

### 3. Interactive Visual Lineage DAG
Select any HIGH/CRITICAL AML alert to visualize the full causal chain: **Account** → **Suspicious Transactions** → **Violated Regulatory Clauses** (via Cortex Search) → **MCP Action Status** (Slack/Jira dispatches). Transaction evidence table highlights rows with fraud scores above 0.65.

![Lineage DAG](https://github.com/user-attachments/assets/4484f981-5d29-4eec-8e94-81349c00b084)

### 4. What-If Liquidity & Credit Stress Sandbox
Three interactive sliders for HQLA Haircut Adjustment, Credit Default Rate Spike, and Outflow Run-Off Speed. Produces real-time SVG line charts (Baseline vs Stressed LCR over 30 days) and bar charts (RWA/ECL impact) using live Snowpark calculations against `LIQUIDITY_POSITIONS` and `CREDIT_EXPOSURES`.

![Stress Test](https://github.com/user-attachments/assets/71502cda-5f05-4328-8bf6-7ac298a3a285)

### 5. Regulatory "Filing-Ready" Auto-Drafter
One-click generation of FinCEN SAR Filings, Basel III LCR Memos, and IFRS 9 ECL Provision Reports. Each filing includes regulatory clause citations retrieved via Cortex Search with `[^footnote]` references linking back to specific `SECTION_REF` identifiers. Downloadable as Markdown.

![Filing Drafter](https://github.com/user-attachments/assets/2fa3c7e2-a21d-47cd-b1bd-06ce519ade07)

### 6. AML Velocity & Network Loop Detection
Live detection metrics: structuring transactions ($9K–$9.9K range), high-velocity accounts (>15 txns in 90 days), and offshore loop alerts. Includes a transaction distribution histogram near the $10K CTR threshold, top velocity accounts table, and alert severity × rule heatmap.

![AML Network](https://github.com/user-attachments/assets/ba0ac9c9-9af8-4e9a-9549-4c73db2fda31
)

### 7. Autonomous Cross-Tool Action Engine (MCP)
Dispatch buttons to trigger Slack alerts and Jira tickets for CRITICAL AML alerts. Dispatches are logged to `MCP_DISPATCH_LOG` with structured VARIANT payloads. Integrated with Snowflake's Atlassian MCP Server (`FINGUARD_DB.PUBLIC.ATLASSIAN_MCP`) via Dynamic Client Registration OAuth.

![MCP Actions](https://github.com/user-attachments/assets/beddcffd-1df1-42ee-95e3-b695021c27a5
)

### 8. One-Click Signed Audit Export Package
Generates a complete audit defense package containing: executive summary, deterministic breach-threshold checks (CTR/High-Risk Geo/Fraud Exposure), itemized transaction evidence table, and a SHA-256 digital signature. Available as Markdown download (Streamlit) or ZIP bundle (API).

![Audit Export](https://github.com/user-attachments/assets/5bb9e02a-4be2-4c73-8adc-8ee6099f123a
)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Database** | Snowflake (FINGUARD_DB, 7 tables, 100K+ rows) |
| **AI / Search** | Cortex Search Service, Cortex Analyst, Cortex COMPLETE (LLM) |
| **Semantic Layer** | Snowflake Semantic View (FINGUARD_ONTOLOGY) with 5 verified queries |
| **Event Processing** | Snowflake Stream (CRITICAL_AML_STREAM) + Task + Python Stored Procedure |
| **MCP Integration** | Atlassian External MCP Server (Jira), Slack webhook scaffolding |
| **Custom Skill** | CoCo audit_evidence_builder skill (.coco/skills/) |
| **Streamlit Frontend** | Streamlit in Snowflake (Workspace) + Streamlit Cloud (external) |
| **Web Frontend** | Next.js 14, TypeScript, Tailwind CSS, Lucide Icons, custom SVG charts |
| **API Backend** | FastAPI (Python), Snowpark session management |
| **Deployment** | Docker Compose, Render, Streamlit Cloud, Snowsight Workspace |

---

## How We Used CoCo CLI

 FinGuard was built using help of **Snowflake CoCo (Cortex Code)** :

| Step | CoCo Action | What It Built |
|------|-------------|---------------|
| 1 | `cortex "...create database schema and synthetic data..."` | FINGUARD_DB with 7 tables, 100K+ referentially consistent rows |
| 2 | `cortex "...ingest regulatory text into Cortex Search..."` | 20 regulatory clauses, REG_POLICY_SEARCH_SERVICE |
| 3 | `cortex "...create semantic model YAML..."` | FINGUARD_ONTOLOGY semantic view with 5 VQRs |
| 4 | `cortex "...create custom CoCo skill..."` | `.coco/skills/audit_evidence_builder/` with full SKILL.md |
| 5 | `cortex "...MCP action dispatcher..."` | Stream + Task + Python stored procedure + dispatch logging |
| 6 | `cortex "...FastAPI backend..."` | `backend/main.py` with 5 REST endpoints |
| 7 | `cortex "...Next.js frontend..."` | 8-tab enterprise terminal with SVG charts |
| 8 | `cortex "...Docker deployment..."` | docker-compose.yml, Dockerfiles, render.yaml |

CoCo also:
- Deployed the semantic view to Snowflake via `cortex agent-studio sv-deploy`
- Created the Atlassian MCP integration via `CREATE EXTERNAL MCP SERVER`
- Debugged connection issues and iteratively improved the UI
- Generated audit reports end-to-end against live data

---

## Database Schema

```
FINGUARD_DB.PUBLIC
├── TRANSACTIONS          (100,000 rows) — TXN_ID, ACCOUNT_ID, AMOUNT, FRAUD_SCORE, IS_FLAGGED...
├── LIQUIDITY_POSITIONS   (365 rows)     — Daily LCR snapshots with HQLA levels
├── CREDIT_EXPOSURES      (10,000 rows)  — Obligor-level EAD, PD, LGD, RWA
├── AML_ALERTS            (2,001 rows)   — Alert triggers: Structuring, Rapid Velocity, Offshore Loop
├── PARSED_REGULATORY_TEXT (20 rows)      — Basel III, AML/BSA, IFRS 9/CECL clauses
├── AUDIT_TRAIL_LOGS      (dynamic)      — Query execution audit trail
└── MCP_DISPATCH_LOG      (dynamic)      — Slack/Jira dispatch records

Cortex Services:
├── REG_POLICY_SEARCH_SERVICE  — Cortex Search on CLAUSE_TEXT
├── FINGUARD_ONTOLOGY          — Semantic View for Cortex Analyst
├── ATLASSIAN_MCP              — External MCP Server (Jira)
├── CRITICAL_AML_STREAM        — CDC stream on AML_ALERTS
└── CRITICAL_AML_DISPATCHER_TASK — Automated dispatch on CRITICAL alerts
```

---

## Setup & Installation

### Prerequisites

- Snowflake account with ACCOUNTADMIN role
- Python 3.11+
- Node.js 18+ (for Next.js frontend)
- Docker (optional, for containerized deployment)

### 1. Initialize the Database

Run the data generator against your Snowflake account:

```bash
cd backend
pip install snowflake-snowpark-python
python ../finguard_data_gen.py
```

This creates FINGUARD_DB with all 7 tables and 100K+ rows.

### 2. Configure Snowflake Connection

Edit `~/.snowflake/connections.toml`:

```toml
[finguard]
account = "YOUR_ORG-YOUR_ACCOUNT"
user = "YOUR_USER"
authenticator = "externalbrowser"
database = "FINGUARD_DB"
schema = "PUBLIC"
warehouse = "COMPUTE_WH"
role = "ACCOUNTADMIN"
```

## Run Locally

### Option A: Streamlit Only

```bash
cd finguard-copilot
pip install streamlit snowflake-snowpark-python snowflake-connector-python
streamlit run streamlit_app.py
```

Create `.streamlit/secrets.toml` with your Snowflake credentials (see Streamlit Cloud section above).

Open: `http://localhost:8501`

### Option B: Full Stack (FastAPI + Next.js)

**Terminal 1 — Backend:**
```bash
cd backend
pip install fastapi uvicorn snowflake-snowpark-python
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000` (frontend) | `http://localhost:8000/docs` (API)

### Option C: Docker

```bash
# Create .env file with Snowflake credentials
echo "SNOWFLAKE_ACCOUNT=YOUR_ORG-YOUR_ACCOUNT" > .env
echo "SNOWFLAKE_USER=YOUR_USER" >> .env
echo "SNOWFLAKE_PASSWORD=YOUR_PASSWORD" >> .env

docker compose up --build
```

Open: `http://localhost:3000` (frontend) | `http://localhost:8000/docs` (API)

---

## Project Structure

```
finguard-copilot/
│
├── finguard-copilot/                # Streamlit app (Snowsight + Cloud)
│   ├── streamlit_app.py             # 8-tab dashboard (461 lines)
│   ├── snowflake.yml                # Snowflake Workspace config
│   ├── pyproject.toml               # Dependencies
│   └── .streamlit/config.toml       # Theme (pink/violet dark)
│
├── backend/                         # FastAPI server
│   ├── main.py                      # 5 API endpoints (423 lines)
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/                        # Next.js 14 app
│   ├── src/app/
│   │   ├── page.tsx                 # 8-tab terminal UI (334 lines)
│   │   ├── globals.css              # Pink/violet theme
│   │   └── layout.tsx
│   ├── src/lib/api.ts               # API client
│   ├── package.json
│   └── tailwind.config.js
│
├── scripts/
│   └── mcp_action_dispatcher.py     # MCP dispatch automation (617 lines)
│
├── .coco/skills/
│   └── audit_evidence_builder/      # Custom CoCo skill
│       ├── SKILL.md                 # Skill workflow (241 lines)
│       └── skill.yaml               # Metadata + triggers
│
├── semantic_models/
│   └── finguard_ontology.yaml       # Semantic view YAML
│
├── finguard_data_gen.py             # Snowpark data generator
├── docker-compose.yml               # Docker orchestration
├── Dockerfile.backend
├── Dockerfile.frontend
├── render.yaml                      # Render deployment config
├── aws-deploy.yaml                  # AWS CloudFormation template
└── start_finguard.sh                # Linux/Mac deploy script
```
