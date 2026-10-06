"""FinGuard CoCopilot v4 — Light Violet Theme"""

import os, json, hashlib, datetime
import streamlit as st
import pandas as pd

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))

@st.cache_data(ttl=90)
def q(sql):
    return conn.query(sql)

def ql(sql):
    return conn.query(sql)

def safe(s):
    return str(s).replace("'", "''")

st.set_page_config(page_title="FinGuard CoCopilot", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""<style>
.block-container{padding:1.2rem 2.5rem 2rem 2.5rem;max-width:1200px}
[data-testid="stAppViewContainer"]{background:#faf8ff}
[data-testid="stHeader"]{background:rgba(250,248,255,.85);backdrop-filter:blur(12px)}

.kpi-row{display:flex;gap:16px;margin-bottom:8px}
.kc{flex:1;background:#fff;border:1px solid #ede9fe;border-radius:14px;padding:18px 22px;
    position:relative;overflow:hidden;box-shadow:0 1px 4px rgba(124,58,237,.04)}
.kc::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.kc.violet::before{background:linear-gradient(90deg,#7c3aed,#a78bfa)}
.kc.rose::before{background:linear-gradient(90deg,#e11d48,#fb7185)}
.kc.amber::before{background:linear-gradient(90deg,#d97706,#fbbf24)}
.kc.pink::before{background:linear-gradient(90deg,#db2777,#f472b6)}
.kc.indigo::before{background:linear-gradient(90deg,#4f46e5,#818cf8)}
.kc .kl{color:#7c6f96;font-size:.68rem;text-transform:uppercase;letter-spacing:.12em;font-weight:700}
.kc .kv{font-size:1.6rem;font-weight:800;margin-top:4px}
.kc .kv.violet{color:#7c3aed}.kc .kv.rose{color:#e11d48}.kc .kv.amber{color:#d97706}
.kc .kv.pink{color:#db2777}.kc .kv.indigo{color:#4f46e5}

.badge{display:inline-flex;align-items:center;gap:5px;padding:4px 12px;border-radius:99px;
       font-size:.62rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.badge.on{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.badge.act{background:#f3f0ff;color:#7c3aed;border:1px solid #ddd6fe}
.badge.conn{background:#fdf2f8;color:#db2777;border:1px solid #fbcfe8}

.stTabs [data-baseweb="tab-list"]{gap:3px;background:#f3f0ff;border-radius:10px;padding:4px}
.stTabs [data-baseweb="tab"]{border-radius:8px;color:#7c6f96;font-weight:600;font-size:.8rem}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#7c3aed,#6366f1)!important;color:#fff!important;
    box-shadow:0 2px 8px rgba(124,58,237,.2)}

.node{border-radius:12px;padding:16px;text-align:center;border:2px solid;background:#fff;
      box-shadow:0 2px 8px rgba(0,0,0,.04);transition:.2s}

button[data-testid="stBaseButton-primary"]{background:linear-gradient(135deg,#7c3aed,#6366f1)!important;
    border:none!important;box-shadow:0 2px 8px rgba(124,58,237,.2)}
button[data-testid="stBaseButton-primary"]:hover{box-shadow:0 4px 16px rgba(124,58,237,.3)!important}

div[data-testid="stMetricValue"]{font-size:1.25rem;font-weight:700}
div[data-testid="stMetricDelta"]{font-size:.72rem}
section[data-testid="stExpander"]{border:1px solid #ede9fe;border-radius:12px;background:#fff}
div[data-testid="stExpander"] summary{font-weight:600;color:#7c3aed}
</style>""", unsafe_allow_html=True)

# ── Header ──
h1, h2 = st.columns([3, 2])
with h1:
    st.markdown("## 🛡️ FinGuard CoCopilot")
    st.caption("AI-Driven Risk, Liquidity & AML Command Center · Powered by Snowflake Cortex")
with h2:
    st.markdown(
        '<div style="text-align:right;padding-top:10px">'
        '<span class="badge on">● CoCo ONLINE</span> '
        '<span class="badge act">● Cortex Search</span> '
        '<span class="badge conn">● MCP</span></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# KPI ROW
# ═══════════════════════════════════════════════
lcr_v = q("""SELECT ROUND(((HQLA_LEVEL_1+(HQLA_LEVEL_2A*0.85)+(HQLA_LEVEL_2B*0.50))
    / NULLIF(EXPECTED_CASH_OUTFLOWS_30D-LEAST(EXPECTED_CASH_INFLOWS_30D,
    EXPECTED_CASH_OUTFLOWS_30D*0.75),0))*100,1) AS V
    FROM FINGUARD_DB.PUBLIC.LIQUIDITY_POSITIONS ORDER BY SNAPSHOT_DATE DESC LIMIT 1""").iloc[0,0]
fraud_v = q("SELECT ROUND(SUM(AMOUNT),0) FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE FRAUD_SCORE>0.85").iloc[0,0]
crit_v = q("SELECT COUNT(*) FROM FINGUARD_DB.PUBLIC.AML_ALERTS WHERE SEVERITY='CRITICAL' AND STATUS!='CLOSED'").iloc[0,0]
ecl_v = q("SELECT ROUND(SUM(EXPOSURE_AT_DEFAULT*PROBABILITY_OF_DEFAULT*LOSS_GIVEN_DEFAULT),0) FROM FINGUARD_DB.PUBLIC.CREDIT_EXPOSURES").iloc[0,0]
rwa_v = q("SELECT ROUND(SUM(RISK_WEIGHTED_ASSETS),0) FROM FINGUARD_DB.PUBLIC.CREDIT_EXPOSURES").iloc[0,0]

def kpi(label, value, color):
    st.markdown(f'<div class="kc {color}"><div class="kl">{label}</div><div class="kv {color}">{value}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
c1,c2,c3,c4,c5 = st.columns(5)
with c1: kpi("Current LCR", f"{lcr_v}%", "violet" if lcr_v>=100 else "rose")
with c2: kpi("Fraud At-Risk", f"${fraud_v:,.0f}", "rose")
with c3: kpi("Critical Alerts", str(int(crit_v)), "amber")
with c4: kpi("ECL", f"${ecl_v:,.0f}", "pink")
with c5: kpi("Total RWA", f"${rwa_v:,.0f}", "indigo")
st.markdown('</div>', unsafe_allow_html=True)

with st.expander("📊 LCR Sparkline & Channel Volume"):
    e1, e2 = st.columns(2)
    with e1:
        spark = q("SELECT SNAPSHOT_DATE, ROUND(LCR_RATIO*100,1) AS LCR FROM FINGUARD_DB.PUBLIC.LIQUIDITY_POSITIONS ORDER BY SNAPSHOT_DATE DESC LIMIT 14")
        st.area_chart(spark.set_index("SNAPSHOT_DATE")["LCR"], color="#7c3aed", height=150)
    with e2:
        ch = q("SELECT CHANNEL, ROUND(SUM(AMOUNT),0) AS VOL FROM FINGUARD_DB.PUBLIC.TRANSACTIONS GROUP BY CHANNEL ORDER BY VOL DESC")
        st.bar_chart(ch.set_index("CHANNEL")["VOL"], color="#ec4899", height=150)

st.markdown("")

# ═══════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════
adf = q("SELECT ALERT_ID,ACCOUNT_ID,RULE_TRIGGERED,SEVERITY,STATUS FROM FINGUARD_DB.PUBLIC.AML_ALERTS WHERE SEVERITY IN ('HIGH','CRITICAL') ORDER BY ALERT_ID LIMIT 200")

t1,t2,t3,t4,t5,t6,t7,t8 = st.tabs([
    "🤖 Dual-Verifier","🔗 Lineage DAG","📉 Stress Test",
    "📋 Filing Drafter","🕸️ AML Network","⚡ MCP Actions",
    "📦 Audit Export","⚙️ System"])

# ═══════ TAB 1: Dual-Verifier ═══════
with t1:
    st.markdown("### 🤖 Dual-Verifier Copilot")
    st.caption("Runs BOTH Cortex Analyst SQL and Cortex Search policy retrieval, then cross-checks.")
    question = st.text_input("Ask anything about FinGuard data or regulations", key="q1",
                             placeholder="e.g. What are the SAR filing thresholds?")
    if question:
        sq = safe(question); dq = sq.replace('"','\\"')
        left, right = st.columns(2)
        sql_ok, search_ok, top_score = False, False, 0.0

        with left:
            st.markdown("##### 💎 SQL Path (Cortex Analyst)")
            try:
                with st.spinner("Generating SQL..."):
                    r = ql(f"""SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet',
                        'Tables in FINGUARD_DB.PUBLIC: TRANSACTIONS(TXN_ID,ACCOUNT_ID,TIMESTAMP,AMOUNT,CURRENCY,COUNTERPARTY_COUNTRY,CHANNEL,FRAUD_SCORE,IS_FLAGGED), LIQUIDITY_POSITIONS(SNAPSHOT_DATE,HQLA_LEVEL_1,HQLA_LEVEL_2A,HQLA_LEVEL_2B,EXPECTED_CASH_OUTFLOWS_30D,EXPECTED_CASH_INFLOWS_30D,LCR_RATIO), CREDIT_EXPOSURES(OBLIGOR_ID,SECTOR,EXPOSURE_AT_DEFAULT,PROBABILITY_OF_DEFAULT,LOSS_GIVEN_DEFAULT,RISK_WEIGHTED_ASSETS,RATING), AML_ALERTS(ALERT_ID,ACCOUNT_ID,RULE_TRIGGERED,SEVERITY,STATUS). Write ONLY one valid Snowflake SELECT. Question: {sq}') AS S""")
                    gsql = r.iloc[0,0].strip().replace("```sql","").replace("```","").strip()
                    st.code(gsql, language="sql")
                    if gsql.upper().startswith("SELECT"):
                        df = ql(gsql)
                        st.dataframe(df, use_container_width=True, height=200)
                        sql_ok = True
                    else:
                        st.info(gsql[:500])
            except Exception as e:
                st.error(f"SQL error: {str(e)[:300]}")

        with right:
            st.markdown("##### 📜 Policy Path (Cortex Search)")
            try:
                with st.spinner("Searching policies..."):
                    sr = ql(f"""SELECT PARSE_JSON(SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                        'FINGUARD_DB.PUBLIC.REG_POLICY_SEARCH_SERVICE',
                        '{{"query":"{dq}","columns":["CHUNK_ID","REGULATION_TYPE","SECTION_REF","CLAUSE_TEXT"],"limit":3}}'
                    ))['results'] AS R""")
                    res = json.loads(sr.iloc[0,0])
                    if res:
                        top_score = res[0].get("@scores",{}).get("cosine_similarity",0)
                        search_ok = top_score > 0.25
                    for r in res:
                        sc = r.get("@scores",{}).get("cosine_similarity",0)
                        st.markdown(f"**{r['SECTION_REF']}** `{r['REGULATION_TYPE']}` — sim: `{sc:.3f}`")
                        st.caption(r["CLAUSE_TEXT"][:250])
                        st.divider()
            except Exception as e:
                st.error(f"Search error: {str(e)[:300]}")

        st.divider()
        v1,v2,v3 = st.columns(3)
        v1.metric("SQL Path", "✓ PASS" if sql_ok else "✗ FAIL")
        v2.metric("Policy Path", f"✓ {top_score:.2f}" if search_ok else "✗ FAIL")
        both = sql_ok and search_ok
        v3.metric("Dual-Verify", "✓ VERIFIED" if both else ("⚠ PARTIAL" if sql_ok or search_ok else "✗ FAILED"))
        if both: st.success("Both paths verified.")
        elif sql_ok or search_ok: st.warning("One path succeeded. Manual review recommended.")
        else: st.error("Both paths failed.")
        try:
            ql(f"""INSERT INTO FINGUARD_DB.PUBLIC.AUDIT_TRAIL_LOGS(LOG_ID,USER_ID,QUERY_TEXT,CORTEX_SEARCH_SCORE,DETERMINISTIC_VERIFICATION_STATUS)
                SELECT UUID_STRING(),CURRENT_USER(),'{sq[:400]}',{top_score},'{("VERIFIED" if both else "MANUAL_REVIEW")}'""")
        except Exception: pass

# ═══════ TAB 2: Lineage DAG ═══════
with t2:
    st.markdown("### 🔗 Causal Lineage DAG")
    sel = st.selectbox("Alert ID", adf["ALERT_ID"].tolist(), key="dag_sel")
    if sel:
        ar = adf[adf["ALERT_ID"]==sel].iloc[0]; acct = ar["ACCOUNT_ID"]
        txs = q(f"SELECT TXN_ID,AMOUNT,COUNTERPARTY_COUNTRY,CHANNEL,FRAUD_SCORE,IS_FLAGGED FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE ACCOUNT_ID='{acct}' ORDER BY FRAUD_SCORE DESC LIMIT 10")
        rmap={"Structuring":"structuring detection","Rapid Velocity":"SAR filing requirements","High Risk Country":"high risk jurisdiction","Offshore Loop":"offshore circular transfer"}
        try:
            cr=ql(f"""SELECT PARSE_JSON(SNOWFLAKE.CORTEX.SEARCH_PREVIEW('FINGUARD_DB.PUBLIC.REG_POLICY_SEARCH_SERVICE',
                '{{"query":"{rmap.get(ar["RULE_TRIGGERED"],ar["RULE_TRIGGERED"])}","columns":["SECTION_REF","CLAUSE_TEXT","REGULATION_TYPE"],"limit":2}}'))['results'] AS R""")
            cls=json.loads(cr.iloc[0,0])
        except Exception: cls=[]
        try: dsp=q(f"SELECT CHANNEL,STATUS,PAYLOAD:verdict::VARCHAR AS VERDICT FROM FINGUARD_DB.PUBLIC.MCP_DISPATCH_LOG WHERE ALERT_ID='{safe(sel)}'")
        except Exception: dsp=pd.DataFrame()

        st.markdown("#### Signal Flow")
        n1,a1,n2,a2,n3,a3,n4 = st.columns([2,1,2,1,2,1,2])
        with n1:
            st.markdown(f'<div class="node" style="border-color:#7c3aed"><div style="color:#7c3aed;font-size:.7rem;font-weight:700">ACCOUNT</div><div style="font-weight:800;font-size:1rem">{acct}</div><div style="color:#7c6f96;font-size:.7rem">{ar["SEVERITY"]} · {ar["STATUS"]}</div></div>', unsafe_allow_html=True)
        with a1: st.markdown('<p style="text-align:center;padding-top:16px;color:#c4b5fd;font-size:1.5rem">→</p>', unsafe_allow_html=True)
        with n2:
            mf=txs.iloc[0]["FRAUD_SCORE"] if len(txs)>0 else 0
            st.markdown(f'<div class="node" style="border-color:#e11d48"><div style="color:#e11d48;font-size:.7rem;font-weight:700">SUSPICIOUS TXNS</div><div style="font-weight:800">{len(txs)} transactions</div><div style="color:#7c6f96;font-size:.7rem">Max fraud: {mf:.4f}</div></div>', unsafe_allow_html=True)
        with a2: st.markdown('<p style="text-align:center;padding-top:16px;color:#c4b5fd;font-size:1.5rem">→</p>', unsafe_allow_html=True)
        with n3:
            crefs=", ".join(c["SECTION_REF"] for c in cls) if cls else "None"
            st.markdown(f'<div class="node" style="border-color:#4f46e5"><div style="color:#4f46e5;font-size:.7rem;font-weight:700">REGULATORY CLAUSES</div><div style="font-weight:800;font-size:.85rem">{crefs}</div><div style="color:#7c6f96;font-size:.7rem">{len(cls)} matched</div></div>', unsafe_allow_html=True)
        with a3: st.markdown('<p style="text-align:center;padding-top:16px;color:#c4b5fd;font-size:1.5rem">→</p>', unsafe_allow_html=True)
        with n4:
            if len(dsp)>0:
                chs=", ".join(dsp["CHANNEL"].unique()); vrd=dsp.iloc[0].get("VERDICT","N/A")
                st.markdown(f'<div class="node" style="border-color:#db2777"><div style="color:#db2777;font-size:.7rem;font-weight:700">MCP ACTIONS</div><div style="font-weight:800">{chs}</div><div style="color:#7c6f96;font-size:.7rem">{vrd}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="node" style="border-color:#d4d4d8"><div style="color:#71717a;font-size:.7rem;font-weight:700">MCP ACTIONS</div><div style="color:#a1a1aa">No dispatches</div></div>', unsafe_allow_html=True)

        e1,e2 = st.columns(2)
        with e1:
            st.markdown("**Transaction Evidence**")
            st.dataframe(txs, use_container_width=True, height=250)
        with e2:
            st.markdown("**Cited Clauses**")
            for c in cls:
                st.info(f"**{c['SECTION_REF']}** ({c['REGULATION_TYPE']})\n\n{c['CLAUSE_TEXT'][:250]}")

# ═══════ TAB 3: Stress Test ═══════
with t3:
    st.markdown("### 📉 What-If Stress Sandbox")
    s1,s2,s3=st.columns(3)
    hc=s1.slider("HQLA Haircut Adj %",-50,50,0,5)
    sp=s2.slider("Default Rate Spike %",0,200,0,10)
    of=s3.slider("Outflow Speed %",-30,100,0,5)

    bd=q("SELECT SNAPSHOT_DATE,HQLA_LEVEL_1,HQLA_LEVEL_2A,HQLA_LEVEL_2B,EXPECTED_CASH_OUTFLOWS_30D,EXPECTED_CASH_INFLOWS_30D FROM FINGUARD_DB.PUBLIC.LIQUIDITY_POSITIONS ORDER BY SNAPSHOT_DATE DESC LIMIT 30")
    d=bd.copy()
    h2as,h2bs=max(0,0.85-hc/100),max(0,0.50-hc/100); om=1+of/100
    d["Baseline"]=((d["HQLA_LEVEL_1"]+d["HQLA_LEVEL_2A"]*0.85+d["HQLA_LEVEL_2B"]*0.50)/(d["EXPECTED_CASH_OUTFLOWS_30D"]-d["EXPECTED_CASH_INFLOWS_30D"].clip(upper=d["EXPECTED_CASH_OUTFLOWS_30D"]*0.75)).clip(lower=1))*100
    d["Stressed"]=((d["HQLA_LEVEL_1"]+d["HQLA_LEVEL_2A"]*h2as+d["HQLA_LEVEL_2B"]*h2bs)/(d["EXPECTED_CASH_OUTFLOWS_30D"]*om-d["EXPECTED_CASH_INFLOWS_30D"].clip(upper=d["EXPECTED_CASH_OUTFLOWS_30D"]*om*0.75)).clip(lower=1))*100

    re=q("SELECT SUM(RISK_WEIGHTED_ASSETS) AS RWA,SUM(EXPOSURE_AT_DEFAULT*PROBABILITY_OF_DEFAULT*LOSS_GIVEN_DEFAULT) AS ECL FROM FINGUARD_DB.PUBLIC.CREDIT_EXPOSURES")
    rb,eb=float(re.iloc[0]["RWA"]),float(re.iloc[0]["ECL"]); es,rs=eb*(1+sp/100),rb*(1+sp/200)

    x1,x2=st.columns(2)
    with x1:
        st.caption("LCR: Baseline vs Stressed (30d)")
        st.line_chart(d.set_index("SNAPSHOT_DATE")[["Baseline","Stressed"]], color=["#7c3aed","#e11d48"], height=250)
        mn=d["Stressed"].min()
        if mn<100: st.error(f"⚠ LCR breaches 100% (min: {mn:.1f}%)")
        else: st.success(f"LCR stays above 100% (min: {mn:.1f}%)")
    with x2:
        st.caption("Credit Impact")
        cp=pd.DataFrame({"Metric":["RWA","RWA","ECL","ECL"],"Scenario":["Baseline","Stressed","Baseline","Stressed"],"Value":[rb,rs,eb,es]})
        st.bar_chart(cp.pivot(index="Metric",columns="Scenario",values="Value"), color=["#7c3aed","#e11d48"], height=250)

    m1,m2,m3,m4=st.columns(4)
    m1.metric("Baseline LCR",f"{d['Baseline'].iloc[0]:.1f}%")
    m2.metric("Stressed LCR",f"{d['Stressed'].iloc[0]:.1f}%",delta=f"{d['Stressed'].iloc[0]-d['Baseline'].iloc[0]:.1f}%")
    m3.metric("Baseline ECL",f"${eb:,.0f}")
    m4.metric("Stressed ECL",f"${es:,.0f}",delta=f"+${es-eb:,.0f}")

# ═══════ TAB 4: Filing Drafter ═══════
with t4:
    st.markdown("### 📋 Regulatory Filing Auto-Drafter")
    ft=st.selectbox("Filing Type",["FinCEN SAR Filing","Basel III LCR Memo","IFRS 9 ECL Report"],key="ft")
    fa=st.selectbox("Reference Alert",adf["ALERT_ID"].tolist(),key="fa")
    if st.button("Generate Filing",type="primary",key="gf"):
        with st.spinner("Drafting..."):
            ar2=adf[adf["ALERT_ID"]==fa].iloc[0]; ac2=ar2["ACCOUNT_ID"]
            st2=ql(f"SELECT COUNT(*) AS T,ROUND(SUM(AMOUNT),2) AS V,SUM(CASE WHEN IS_FLAGGED THEN 1 ELSE 0 END) AS F,ROUND(MAX(FRAUD_SCORE),4) AS MF FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE ACCOUNT_ID='{ac2}'").iloc[0]
            fqm={"FinCEN SAR Filing":"SAR filing requirements","Basel III LCR Memo":"LCR HQLA haircut","IFRS 9 ECL Report":"expected credit loss IFRS 9"}
            try:
                fcr=ql(f"""SELECT PARSE_JSON(SNOWFLAKE.CORTEX.SEARCH_PREVIEW('FINGUARD_DB.PUBLIC.REG_POLICY_SEARCH_SERVICE',
                    '{{"query":"{fqm[ft]}","columns":["SECTION_REF","CLAUSE_TEXT","REGULATION_TYPE"],"limit":3}}'))['results'] AS R""")
                fcs=json.loads(fcr.iloc[0,0])
            except Exception: fcs=[]
            now=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            doc=f"# {ft}\n\n**Date:** {now} | **Alert:** {fa} | **Account:** {ac2}\n\n"
            doc+=f"## Summary\n| Field | Value |\n|---|---|\n| Transactions | {int(st2['T'])} |\n| Volume | ${float(st2['V']):,.2f} |\n| Flagged | {int(st2['F'])} |\n| Max Fraud | {st2['MF']} |\n\n"
            doc+="## Regulatory Basis\n\n"
            for i,c in enumerate(fcs,1):
                doc+=f"### [{i}] {c['SECTION_REF']} ({c['REGULATION_TYPE']})\n\n> {c['CLAUSE_TEXT']}\n\n*Source: Cortex Search*[^{i}]\n\n"
            doc+="## Footnotes\n\n"
            for i,c in enumerate(fcs,1): doc+=f"[^{i}]: {c['SECTION_REF']} — retrieved {now}\n"
            doc+=f"\nSHA-256: `{hashlib.sha256(doc.encode()).hexdigest()}`\n"
            st.markdown(doc)
            st.download_button("Download Filing",doc,file_name=f"{ft.replace(' ','_')}_{fa}.md",mime="text/markdown")

# ═══════ TAB 5: AML Network ═══════
with t5:
    st.markdown("### 🕸️ AML Velocity & Network Detection")
    sv=q("SELECT COUNT(*) AS V FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE AMOUNT BETWEEN 9000 AND 9999").iloc[0,0]
    va=q("SELECT COUNT(*) FROM (SELECT ACCOUNT_ID FROM FINGUARD_DB.PUBLIC.TRANSACTIONS GROUP BY ACCOUNT_ID HAVING COUNT(*)>15)").iloc[0,0]
    la=q("SELECT COUNT(*) FROM FINGUARD_DB.PUBLIC.AML_ALERTS WHERE RULE_TRIGGERED='Offshore Loop'").iloc[0,0]

    a1,a2,a3=st.columns(3)
    a1.metric("Structuring Txns ($9K-$9.9K)",f"{int(sv):,}")
    a2.metric("High-Velocity Accounts",f"{int(va):,}")
    a3.metric("Offshore Loop Alerts",f"{int(la):,}")

    st.caption("Transaction Distribution Near $10K Threshold")
    hd=q("""SELECT WIDTH_BUCKET(AMOUNT,8000,10500,25) AS BKT,COUNT(*) AS CNT
        FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE AMOUNT BETWEEN 8000 AND 10500
        GROUP BY BKT ORDER BY BKT""")
    st.bar_chart(hd.set_index("BKT")["CNT"], color="#e11d48", height=180)

    st.caption("Top Rapid-Velocity Accounts")
    vd=q("""SELECT t.ACCOUNT_ID,COUNT(*) AS TXNS,ROUND(SUM(t.AMOUNT),0) AS VOL,
        ROUND(MAX(t.FRAUD_SCORE),4) AS MAX_FRAUD,COUNT(DISTINCT t.COUNTERPARTY_COUNTRY) AS COUNTRIES,
        COALESCE(a.AC,0) AS ALERTS
        FROM FINGUARD_DB.PUBLIC.TRANSACTIONS t
        LEFT JOIN (SELECT ACCOUNT_ID,COUNT(*) AS AC FROM FINGUARD_DB.PUBLIC.AML_ALERTS GROUP BY ACCOUNT_ID) a ON t.ACCOUNT_ID=a.ACCOUNT_ID
        GROUP BY t.ACCOUNT_ID,a.AC HAVING COUNT(*)>20 ORDER BY TXNS DESC LIMIT 15""")
    st.dataframe(vd, use_container_width=True, height=280)

    st.caption("Alert Severity × Rule")
    rd=q("SELECT RULE_TRIGGERED,SEVERITY,COUNT(*) AS N FROM FINGUARD_DB.PUBLIC.AML_ALERTS GROUP BY 1,2")
    st.bar_chart(rd.pivot(index="RULE_TRIGGERED",columns="SEVERITY",values="N").fillna(0), height=200)

# ═══════ TAB 6: MCP Actions ═══════
with t6:
    st.markdown("### ⚡ MCP Cross-Tool Action Engine")
    try:
        dl=q("""SELECT DISPATCH_ID,ALERT_ID,CHANNEL,STATUS,
            TO_VARCHAR(DISPATCHED_AT,'YYYY-MM-DD HH24:MI:SS') AS DISPATCH_TIME,
            PAYLOAD:verdict::VARCHAR AS VERDICT,PAYLOAD:account_id::VARCHAR AS ACCOUNT
            FROM FINGUARD_DB.PUBLIC.MCP_DISPATCH_LOG ORDER BY DISPATCHED_AT DESC LIMIT 20""")
        if len(dl)>0: st.dataframe(dl, use_container_width=True, height=250)
        else: st.info("No MCP dispatches yet.")
    except Exception as e: st.warning(f"Could not load log: {str(e)[:200]}")

    st.markdown("#### Trigger Dispatch")
    crit_alerts = adf[adf["SEVERITY"]=="CRITICAL"]
    if len(crit_alerts)==0: st.info("No CRITICAL alerts.")
    else:
        da=st.selectbox("Alert",crit_alerts["ALERT_ID"].tolist()[:20],key="mcp_da")
        da_row=crit_alerts[crit_alerts["ALERT_ID"]==da].iloc[0]
        bc1,bc2=st.columns(2)
        if bc1.button("📢 Slack",key="mcp_s"):
            try:
                ql(f"""INSERT INTO FINGUARD_DB.PUBLIC.MCP_DISPATCH_LOG(DISPATCH_ID,ALERT_ID,CHANNEL,PAYLOAD,DISPATCHED_AT,STATUS)
                    SELECT 'SLK-'||UUID_STRING(),'{safe(da)}','SLACK',
                    OBJECT_CONSTRUCT('channel','#risk-compliance-alerts','account_id','{safe(da_row["ACCOUNT_ID"])}','rule','{safe(da_row["RULE_TRIGGERED"])}','verdict','DISPATCHED VIA UI'),
                    CURRENT_TIMESTAMP(),'DISPATCHED'""")
                st.success(f"Slack dispatch logged for {da}"); st.rerun()
            except Exception as e: st.error(str(e)[:200])
        if bc2.button("🎫 Jira",key="mcp_j"):
            try:
                ql(f"""INSERT INTO FINGUARD_DB.PUBLIC.MCP_DISPATCH_LOG(DISPATCH_ID,ALERT_ID,CHANNEL,PAYLOAD,DISPATCHED_AT,STATUS)
                    SELECT 'JRA-'||UUID_STRING(),'{safe(da)}','JIRA',
                    OBJECT_CONSTRUCT('project','COMP','summary','Critical AML: '||'{safe(da_row["ACCOUNT_ID"])}','account_id','{safe(da_row["ACCOUNT_ID"])}','rule','{safe(da_row["RULE_TRIGGERED"])}','verdict','TICKET VIA UI'),
                    CURRENT_TIMESTAMP(),'DISPATCHED'""")
                st.success(f"Jira ticket logged for {da}"); st.rerun()
            except Exception as e: st.error(str(e)[:200])

# ═══════ TAB 7: Audit Export ═══════
with t7:
    st.markdown("### 📦 One-Click Audit Export")
    ea=st.selectbox("Alert",adf["ALERT_ID"].tolist(),key="ea")
    if st.button("Generate Audit Package",type="primary",key="ep"):
        with st.spinner("Building..."):
            er=adf[adf["ALERT_ID"]==ea].iloc[0]; eac=er["ACCOUNT_ID"]
            es2=ql(f"""SELECT COUNT(*) AS T,ROUND(SUM(AMOUNT),2) AS V,
                SUM(CASE WHEN IS_FLAGGED THEN 1 ELSE 0 END) AS F,ROUND(MAX(FRAUD_SCORE),4) AS MF,
                SUM(CASE WHEN COUNTERPARTY_COUNTRY IN ('IR','KP','RU','AF','KY','NG','PA','PK') THEN 1 ELSE 0 END) AS G,
                SUM(CASE WHEN AMOUNT>10000 THEN 1 ELSE 0 END) AS O
                FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE ACCOUNT_ID='{eac}'""").iloc[0]
            ck=[("CHK-001","CTR Filing","FAIL" if es2["O"]>0 else "PASS",f'{int(es2["O"])} over $10K'),
                ("CHK-004","High-Risk Geo","FAIL" if es2["G"]>0 else "PASS",f'{int(es2["G"])} high-risk'),
                ("CHK-005","Fraud Exposure","FAIL" if es2["MF"]>0.65 else "PASS",f'Score: {es2["MF"]}')]
            fc=sum(1 for c in ck if c[2]=="FAIL")
            vd2="COMPLIANT" if fc==0 else ("REVIEW REQUIRED" if fc<=2 else "ESCALATE")
            now=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            rpt=f"# Audit Defense Package\n**{now}** | Alert: {ea} | Account: {eac} | **Verdict: {vd2}**\n\n"
            rpt+="## Checks\n| ID | Rule | Result | Evidence |\n|---|---|---|---|\n"
            for c in ck: rpt+=f"| {c[0]} | {c[1]} | **{c[2]}** | {c[3]} |\n"
            etx=ql(f"SELECT TXN_ID,AMOUNT,COUNTERPARTY_COUNTRY,CHANNEL,FRAUD_SCORE,IS_FLAGGED FROM FINGUARD_DB.PUBLIC.TRANSACTIONS WHERE ACCOUNT_ID='{eac}' ORDER BY TIMESTAMP DESC LIMIT 25")
            rpt+=f"\n## Transactions ({int(es2['T'])} total, ${float(es2['V']):,.2f})\n| TXN_ID | AMOUNT | COUNTRY | CHANNEL | FRAUD | FLAG |\n|---|---|---|---|---|---|\n"
            for _,t in etx.iterrows(): rpt+=f"| {t['TXN_ID'][:12]} | {t['AMOUNT']:,.2f} | {t['COUNTERPARTY_COUNTRY']} | {t['CHANNEL']} | {t['FRAUD_SCORE']:.4f} | {t['IS_FLAGGED']} |\n"
            sig=hashlib.sha256(rpt.encode()).hexdigest()
            rpt+=f"\n## Signature\nSHA-256: `{sig}` | {now}\n"
            st.success(f"**{vd2}** — {fc}/3 checks failed")
            st.download_button("Download (.md)",rpt,file_name=f"audit_{ea}.md",mime="text/markdown")
            with st.expander("Preview"): st.markdown(rpt)

# ═══════ TAB 8: System ═══════
with t8:
    st.markdown("### ⚙️ System Status")
    oc=q("""SELECT 'TRANSACTIONS' AS TBL,COUNT(*) AS ROW_CNT FROM FINGUARD_DB.PUBLIC.TRANSACTIONS
        UNION ALL SELECT 'LIQUIDITY_POSITIONS',COUNT(*) FROM FINGUARD_DB.PUBLIC.LIQUIDITY_POSITIONS
        UNION ALL SELECT 'CREDIT_EXPOSURES',COUNT(*) FROM FINGUARD_DB.PUBLIC.CREDIT_EXPOSURES
        UNION ALL SELECT 'AML_ALERTS',COUNT(*) FROM FINGUARD_DB.PUBLIC.AML_ALERTS
        UNION ALL SELECT 'PARSED_REGULATORY_TEXT',COUNT(*) FROM FINGUARD_DB.PUBLIC.PARSED_REGULATORY_TEXT
        UNION ALL SELECT 'AUDIT_TRAIL_LOGS',COUNT(*) FROM FINGUARD_DB.PUBLIC.AUDIT_TRAIL_LOGS
        UNION ALL SELECT 'MCP_DISPATCH_LOG',COUNT(*) FROM FINGUARD_DB.PUBLIC.MCP_DISPATCH_LOG""")
    st.dataframe(oc, use_container_width=True)
    st.markdown("#### Cortex Services")
    ss1,ss2,ss3=st.columns(3)
    ss1.metric("Search Service","REG_POLICY_SEARCH")
    ss2.metric("Semantic View","FINGUARD_ONTOLOGY")
    ss3.metric("MCP Server","ATLASSIAN_MCP")
    st.markdown("#### Recent Audit Trail")
    try:
        al=q("SELECT * FROM FINGUARD_DB.PUBLIC.AUDIT_TRAIL_LOGS ORDER BY EXECUTION_TIMESTAMP DESC LIMIT 10")
        st.dataframe(al, use_container_width=True)
    except Exception: st.info("No entries yet.")
