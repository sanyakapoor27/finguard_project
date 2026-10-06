"use client";
import { useState, useEffect, useCallback } from "react";
import {
  Shield, Activity, Search, GitBranch, SlidersHorizontal,
  FileText, Network, Zap, Download, Send, RefreshCw,
  AlertTriangle, CheckCircle, ArrowRight,
} from "lucide-react";
import { fetchMetrics, querycopilot, fetchLineage, runStressTest, exportAudit } from "@/lib/api";

type Metrics = { lcr_pct:number; fraud_volume:number; critical_alerts:number; open_alerts:number; ecl:number; total_rwa:number; lcr_sparkline:{date:string;value:number}[] };
const TABS = [
  {icon:Activity,label:"Command Center"},{icon:Search,label:"CoCo Copilot"},
  {icon:GitBranch,label:"Lineage DAG"},{icon:SlidersHorizontal,label:"Stress Test"},
  {icon:FileText,label:"Filing Drafter"},{icon:Network,label:"AML Network"},
  {icon:Zap,label:"MCP Actions"},{icon:Download,label:"Audit Export"},
];
const fmt=(n:number)=>n.toLocaleString("en-US",{maximumFractionDigits:0});

/* ── SVG Charts ── */
function SparkArea({data,color1="#7c3aed",color2="#ec4899",h=80}:{data:{label:string;value:number}[];color1?:string;color2?:string;h?:number}){
  if(!data.length)return null;
  const max=Math.max(...data.map(d=>d.value),1);const w=600;const pad=20;
  const pts=data.map((d,i)=>`${pad+i*((w-2*pad)/(data.length-1))},${h-pad-((d.value/max)*(h-2*pad))}`).join(" ");
  const area=`${pad},${h-pad} ${pts} ${w-pad},${h-pad}`;
  return(
    <svg viewBox={`0 0 ${w} ${h+24}`} className="w-full" preserveAspectRatio="none" style={{height:h+30}}>
      <defs>
        <linearGradient id="sparkGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor={color1}/><stop offset="100%" stopColor={color2}/></linearGradient>
        <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color1} stopOpacity=".25"/><stop offset="100%" stopColor={color1} stopOpacity=".02"/></linearGradient>
      </defs>
      <polygon points={area} fill="url(#sparkFill)"/>
      <polyline points={pts} fill="none" stroke="url(#sparkGrad)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round"/>
      {data.map((d,i)=>{
        const x=pad+i*((w-2*pad)/(data.length-1));const y=h-pad-((d.value/max)*(h-2*pad));
        return(<g key={i}>
          <circle cx={x} cy={y} r="4" fill="#fff" stroke={color1} strokeWidth="2"/>
          <text x={x} y={h+16} textAnchor="middle" fill="#7c6f96" fontSize="10" fontWeight="500">{d.label}</text>
        </g>);
      })}
    </svg>);
}

function BarChart({data,colors,h=120}:{data:{label:string;value:number;color?:string}[];colors?:string[];h?:number}){
  const max=Math.max(...data.map(d=>d.value),1);const gap=80;const bw=50;const w=data.length*gap+40;
  const palette=colors||["#7c3aed","#ec4899","#6366f1","#f43f5e","#06b6d4","#f59e0b"];
  return(
    <svg viewBox={`0 0 ${w} ${h+40}`} className="w-full" style={{height:h+50}}>
      <defs>{palette.map((c,i)=>(<linearGradient key={i} id={`bg${i}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={c} stopOpacity=".85"/><stop offset="100%" stopColor={c} stopOpacity=".5"/></linearGradient>))}</defs>
      {data.map((d,i)=>{
        const bh=Math.max(4,(d.value/max)*h);const x=20+i*gap;
        return(<g key={i}>
          <rect x={x} y={h-bh} width={bw} height={bh} rx={6} fill={`url(#bg${i%palette.length})`}/>
          <text x={x+bw/2} y={h-bh-6} textAnchor="middle" fill={palette[i%palette.length]} fontSize="11" fontWeight="700">${fmt(d.value)}</text>
          <text x={x+bw/2} y={h+18} textAnchor="middle" fill="#7c6f96" fontSize="10" fontWeight="500">{d.label}</text>
        </g>);
      })}
    </svg>);
}

function DualLineChart({series,h=160}:{series:{date:string;baseline:number;stressed:number}[];h?:number}){
  if(!series?.length)return null;
  const max=Math.max(...series.map(s=>Math.max(s.baseline,s.stressed)),1);
  const w=640;const pad=20;
  const line=(key:"baseline"|"stressed")=>series.map((s,i)=>`${pad+i*(w-2*pad)/(series.length-1)},${h-pad-(s[key]/max)*(h-2*pad)}`).join(" ");
  return(
    <svg viewBox={`0 0 ${w} ${h+30}`} className="w-full" style={{height:h+40}}>
      <defs>
        <linearGradient id="baseFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7c3aed" stopOpacity=".2"/><stop offset="100%" stopColor="#7c3aed" stopOpacity="0"/></linearGradient>
        <linearGradient id="stressFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f43f5e" stopOpacity=".15"/><stop offset="100%" stopColor="#f43f5e" stopOpacity="0"/></linearGradient>
      </defs>
      {/* grid lines */}
      {[0,.25,.5,.75,1].map(p=>(<line key={p} x1={pad} y1={h-pad-p*(h-2*pad)} x2={w-pad} y2={h-pad-p*(h-2*pad)} stroke="#e9e4f5" strokeWidth="1"/>))}
      <polygon points={`${pad},${h-pad} ${line("baseline")} ${w-pad},${h-pad}`} fill="url(#baseFill)"/>
      <polyline points={line("baseline")} fill="none" stroke="#7c3aed" strokeWidth="2.5" strokeLinejoin="round"/>
      <polygon points={`${pad},${h-pad} ${line("stressed")} ${w-pad},${h-pad}`} fill="url(#stressFill)"/>
      <polyline points={line("stressed")} fill="none" stroke="#f43f5e" strokeWidth="2.5" strokeDasharray="6,4" strokeLinejoin="round"/>
      {series.filter((_,i)=>i%5===0).map((s,idx)=>{
        const i=idx*5;const x=pad+i*(w-2*pad)/(series.length-1);
        return(<text key={i} x={x} y={h+16} textAnchor="middle" fill="#7c6f96" fontSize="9">{s.date.slice(5)}</text>);
      })}
    </svg>);
}

export default function Home(){
  const [tab,setTab]=useState(0);
  const [metrics,setMetrics]=useState<Metrics|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const refresh=useCallback(async()=>{setLoading(true);setError("");try{setMetrics(await fetchMetrics())}catch{setError("Backend offline — run: docker compose up --build")}finally{setLoading(false)}},[]);
  useEffect(()=>{refresh()},[refresh]);

  return(
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white/60 backdrop-blur-md border-b border-violet-100 px-8 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-pink-500 flex items-center justify-center shadow-lg shadow-violet-200">
            <Shield className="w-5 h-5 text-white"/>
          </div>
          <div>
            <span className="text-xl font-extrabold bg-gradient-to-r from-violet-700 to-pink-600 bg-clip-text text-transparent">FinGuard CoCopilot</span>
            <span className="text-[.65rem] text-[var(--dim)] ml-3 font-medium">Snowflake CoCo AI Runtime</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="badge badge-on"><span className="pulse-dot green"/>CoCo ONLINE</span>
          <span className="badge badge-act"><span className="pulse-dot violet"/>Cortex Search</span>
          <span className="badge badge-conn"><span className="pulse-dot pink"/>MCP</span>
          <button onClick={refresh} className="p-2 rounded-lg hover:bg-violet-50 transition ml-2"><RefreshCw className={`w-4 h-4 text-[var(--dim)] ${loading?"animate-spin":""}`}/></button>
        </div>
      </header>

      {error&&<div className="mx-8 mt-4 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-sm font-medium">{error}</div>}

      {/* KPI Row */}
      {metrics&&(
        <div className="grid grid-cols-5 gap-5 px-8 py-6">
          <KPI label="Current LCR" value={`${metrics.lcr_pct.toFixed(1)}%`} color={metrics.lcr_pct>=100?"violet":"rose"}/>
          <KPI label="Fraud At-Risk" value={`$${fmt(metrics.fraud_volume)}`} color="rose"/>
          <KPI label="Critical Alerts" value={String(metrics.critical_alerts)} color="amber"/>
          <KPI label="Expected Credit Loss" value={`$${fmt(metrics.ecl)}`} color="pink"/>
          <KPI label="Total RWA" value={`$${fmt(metrics.total_rwa)}`} color="indigo"/>
        </div>
      )}

      {/* LCR Sparkline — always visible */}
      {metrics && metrics.lcr_sparkline.length > 0 && (
        <div className="px-8 mb-5">
          <div className="gcard">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-[.72rem] font-bold text-[var(--dim)] uppercase tracking-widest">LCR 7-Day Trend</h3>
              <span className="text-xs font-mono text-violet-500">{metrics.lcr_sparkline[0]?.value.toFixed(1)}% latest</span>
            </div>
            <SparkArea
              data={metrics.lcr_sparkline.slice().reverse().map(p => ({ label: p.date.slice(5), value: p.value }))}
              color1="#7c3aed" color2="#ec4899" h={90}
            />
          </div>
        </div>
      )}

      {/* Tab Bar */}
      <div className="px-8 mb-2"><div className="tab-bar overflow-x-auto">{TABS.map((t,i)=>(
        <button key={i} onClick={()=>setTab(i)} className={`tab-btn ${tab===i?"active":""}`}><t.icon className="w-4 h-4"/>{t.label}</button>
      ))}</div></div>

      <main className="px-8 py-5">
        {tab===0&&<CommandCenter metrics={metrics}/>}
        {tab===1&&<CopilotChat/>}
        {tab===2&&<LineageDAG/>}
        {tab===3&&<StressSandbox/>}
        {tab===4&&<FilingDrafter/>}
        {tab===5&&<AMLNetworkTab/>}
        {tab===6&&<MCPActionsTab/>}
        {tab===7&&<AuditExport/>}
      </main>

      <footer className="text-center py-6 text-[.7rem] text-[var(--dim)]">
        Built with Snowflake CoCo · Cortex Search · Cortex Analyst · MCP
      </footer>
    </div>
  );
}

function KPI({label,value,color}:{label:string;value:string;color:string}){return(<div className={`kpi ${color}`}><div className="kpi-label">{label}</div><div className={`kpi-value ${color}`}>{value}</div></div>)}
function Panel({title,children}:{title:string;children:React.ReactNode}){return(<div className="gcard mb-5"><h3 className="text-[.72rem] font-bold text-[var(--dim)] uppercase tracking-widest mb-4">{title}</h3>{children}</div>)}

/* ━━━ Tab 0 ━━━ */
function CommandCenter({metrics}:{metrics:Metrics|null}){
  if(!metrics)return<p className="text-[var(--dim)]">Loading...</p>;
  return(<div className="grid grid-cols-2 gap-5">
    <Panel title="Portfolio Risk Overview">
      <div className="space-y-4">
        {[["Total RWA",`$${fmt(metrics.total_rwa)}`,"text-indigo-600"],["Open Alerts",String(metrics.open_alerts),"text-amber-600"],
          ["Critical Alerts",String(metrics.critical_alerts),"text-rose-600"],["ECL",`$${fmt(metrics.ecl)}`,"text-violet-600"]].map(([l,v,c])=>(
          <div key={l} className="flex justify-between items-center"><span className="text-[var(--dim)] text-sm font-medium">{l}</span><span className={`font-mono font-bold text-sm ${c}`}>{v}</span></div>
        ))}
      </div>
    </Panel>
    <Panel title="System Health">
      <div className="space-y-3">
        {[["CoCo Engine","ONLINE","green"],["Cortex Analyst","READY","violet"],["Cortex Search","ACTIVE","violet"],
          ["MCP Dispatcher","CONNECTED","pink"],["Stream Monitor","LISTENING","green"]].map(([n,s,c])=>(
          <div key={n} className="flex items-center gap-3"><span className={`pulse-dot ${c}`}/><span className="text-sm text-[var(--dim)] flex-1 font-medium">{n}</span><span className="text-[.65rem] font-mono text-violet-400 bg-violet-50 px-2 py-0.5 rounded">{s}</span></div>
        ))}
      </div>
    </Panel>
  </div>);
}

/* ━━━ Tab 1 ━━━ */
function CopilotChat(){
  const [q,setQ]=useState("");const [src,setSrc]=useState<"semantic"|"search">("semantic");const [res,setRes]=useState<any>(null);const [busy,setBusy]=useState(false);
  const ask=async()=>{if(!q.trim())return;setBusy(true);try{setRes(await querycopilot(q,src))}catch{}finally{setBusy(false)}};
  return(<div>
    <div className="flex gap-3 mb-5">
      <select value={src} onChange={e=>setSrc(e.target.value as any)} className="input" style={{width:220}}><option value="semantic">Semantic Model</option><option value="search">Regulatory Search</option></select>
      <input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==="Enter"&&ask()} placeholder="Ask FinGuard anything..." className="input flex-1"/>
      <button onClick={ask} disabled={busy} className="btn-primary"><Send className="w-4 h-4"/>Ask</button>
    </div>
    {res&&(<div className="grid grid-cols-2 gap-5">
      <Panel title="Answer">
        {res.type==="semantic"&&res.data?.length>0?(<div className="overflow-auto max-h-80"><table className="data-table"><thead><tr>{Object.keys(res.data[0]).map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{res.data.slice(0,50).map((r:any,i:number)=><tr key={i}>{Object.values(r).map((v:any,j:number)=><td key={j}>{String(v)}</td>)}</tr>)}</tbody></table></div>)
        :res.type==="search"?(<div className="space-y-3">{res.results?.map((r:any,i:number)=>(<div key={i} className="p-4 rounded-xl bg-violet-50/50 border border-violet-100"><div className="text-violet-700 text-xs font-bold mb-1">{r.SECTION_REF} <span className="text-[var(--dim)]">({r.REGULATION_TYPE})</span></div><div className="text-sm text-[var(--text)]">{r.CLAUSE_TEXT}</div></div>))}</div>)
        :<pre className="text-sm whitespace-pre-wrap text-[var(--dim)]">{JSON.stringify(res,null,2)}</pre>}
      </Panel>
      <Panel title="Query Lineage">
        {res.generated_sql&&<pre className="text-xs p-4 rounded-xl bg-violet-50 border border-violet-100 overflow-auto font-mono text-violet-700">{res.generated_sql}</pre>}
        {res.query_sql&&<pre className="text-xs p-4 rounded-xl bg-pink-50 border border-pink-100 overflow-auto font-mono text-pink-700">{res.query_sql}</pre>}
        <div className="mt-4 flex items-center gap-2 text-emerald-600"><CheckCircle className="w-4 h-4"/><span className="text-xs font-semibold">Verified & logged to AUDIT_TRAIL_LOGS</span></div>
      </Panel>
    </div>)}
  </div>);
}

/* ━━━ Tab 2 ━━━ */
function LineageDAG(){
  const [alertId,setAlertId]=useState("AML-000327");const [data,setData]=useState<any>(null);const [busy,setBusy]=useState(false);
  const load=async()=>{setBusy(true);try{setData(await fetchLineage(alertId))}catch{}finally{setBusy(false)}};
  return(<div>
    <div className="flex gap-3 mb-5"><input value={alertId} onChange={e=>setAlertId(e.target.value)} className="input" style={{width:200}} placeholder="Alert ID"/>
    <button onClick={load} disabled={busy} className="btn-primary"><GitBranch className="w-4 h-4"/>Load Lineage</button></div>
    {data&&(<>
      <div className="flex items-center gap-3 mb-5">
        <DN c="violet" l="ACCOUNT" v={data.alert.ACCOUNT_ID} s={`${data.alert.SEVERITY} • ${data.alert.STATUS}`}/>
        <ArrowRight className="w-5 h-5 text-violet-300 flex-shrink-0"/>
        <DN c="rose" l="SUSPICIOUS TXNS" v={`${data.transactions.length} txns`} s={`Top: ${data.transactions[0]?.FRAUD_SCORE?.toFixed(3)||'N/A'}`}/>
        <ArrowRight className="w-5 h-5 text-violet-300 flex-shrink-0"/>
        <DN c="indigo" l="CLAUSES" v={data.clauses.map((c:any)=>c.SECTION_REF).join(', ')} s={`${data.clauses.length} matched`}/>
        <ArrowRight className="w-5 h-5 text-violet-300 flex-shrink-0"/>
        <DN c="pink" l="ACTIONS" v={data.dispatches.map((d:any)=>d.CHANNEL).join(', ')||'None'} s={data.dispatches[0]?.VERDICT||'Pending'}/>
      </div>
      <div className="grid grid-cols-2 gap-5">
        <Panel title="Transaction Evidence"><div className="overflow-auto max-h-72"><table className="data-table"><thead><tr><th>TXN_ID</th><th>Amount</th><th>Country</th><th>Channel</th><th>Fraud</th><th>Flag</th></tr></thead>
        <tbody>{data.transactions.slice(0,15).map((t:any,i:number)=>(<tr key={i} className={t.FRAUD_SCORE>.65?"bg-rose-50":""}><td>{String(t.TXN_ID).slice(0,10)}</td><td>${Number(t.AMOUNT).toLocaleString()}</td><td>{t.COUNTERPARTY_COUNTRY}</td><td>{t.CHANNEL}</td><td className={t.FRAUD_SCORE>.65?"text-rose-600 font-bold":""}>{Number(t.FRAUD_SCORE).toFixed(4)}</td><td>{t.IS_FLAGGED?'⚠️':'✓'}</td></tr>))}</tbody></table></div></Panel>
        <Panel title="Cited Regulatory Clauses">{data.clauses.map((c:any,i:number)=>(<div key={i} className="p-4 mb-3 rounded-xl bg-indigo-50/50 border border-indigo-100"><div className="text-indigo-700 text-xs font-bold">{c.SECTION_REF} ({c.REGULATION_TYPE})</div><div className="text-sm mt-1">{c.CLAUSE_TEXT?.slice(0,250)}</div></div>))}</Panel>
      </div>
    </>)}
  </div>);
}
function DN({c,l,v,s}:{c:string;l:string;v:string;s:string}){
  const bc={violet:"border-violet-400",rose:"border-rose-400",indigo:"border-indigo-400",pink:"border-pink-400"}[c]||"border-gray-300";
  const tc={violet:"text-violet-600",rose:"text-rose-600",indigo:"text-indigo-600",pink:"text-pink-600"}[c]||"text-gray-600";
  return(<div className={`dag-node ${bc} flex-1`}><div className={`text-[.65rem] font-bold uppercase tracking-wider ${tc}`}>{l}</div><div className="text-sm font-bold mt-1 truncate">{v}</div><div className="text-[.65rem] text-[var(--dim)] mt-1">{s}</div></div>);
}

/* ━━━ Tab 3 ━━━ */
function StressSandbox(){
  const [hc,setHc]=useState(0);const [sp,setSp]=useState(0);const [of,setOf]=useState(0);
  const [res,setRes]=useState<any>(null);const [busy,setBusy]=useState(false);
  const run=async()=>{setBusy(true);try{setRes(await runStressTest({haircut_adjustment_pct:hc,default_rate_spike_pct:sp,outflow_speed_pct:of}))}catch{}finally{setBusy(false)}};
  return(<div>
    <div className="grid grid-cols-3 gap-5 mb-5">
      <Sld label="HQLA Haircut Adj %" min={-50} max={50} value={hc} onChange={setHc}/>
      <Sld label="Default Rate Spike %" min={0} max={200} value={sp} onChange={setSp}/>
      <Sld label="Outflow Speed %" min={-30} max={100} value={of} onChange={setOf}/>
    </div>
    <button onClick={run} disabled={busy} className="btn-primary mb-5">Run Stress Test</button>
    {res&&(<div className="grid grid-cols-2 gap-5">
      <Panel title="LCR: Baseline vs Stressed (30 days)">
        <DualLineChart series={res.lcr_series} h={160}/>
        <div className="flex gap-6 mt-3 text-[.75rem] font-semibold">
          <span className="flex items-center gap-2"><span className="w-3 h-3 rounded bg-violet-500"/>Baseline</span>
          <span className="flex items-center gap-2"><span className="w-3 h-3 rounded bg-rose-500"/>Stressed</span>
        </div>
      </Panel>
      <Panel title="Credit Impact">
        <BarChart data={[{label:"RWA Base",value:res.rwa_baseline},{label:"RWA Stress",value:res.rwa_stressed},{label:"ECL Base",value:res.ecl_baseline},{label:"ECL Stress",value:res.ecl_stressed}]} colors={["#7c3aed","#f43f5e","#6366f1","#ec4899"]} h={110}/>
      </Panel>
    </div>)}
  </div>);
}
function Sld({label,min,max,value,onChange}:{label:string;min:number;max:number;value:number;onChange:(v:number)=>void}){
  return(<div className="gcard"><div className="flex justify-between text-sm mb-3"><span className="text-[var(--dim)] font-medium">{label}</span><span className="font-mono text-violet-600 font-bold">{value}%</span></div><input type="range" min={min} max={max} value={value} onChange={e=>onChange(Number(e.target.value))} className="w-full"/></div>);
}

/* ━━━ Tab 4 ━━━ */
function FilingDrafter(){
  const [type,setType]=useState("FinCEN SAR Filing");const [gen,setGen]=useState("");const [busy,setBusy]=useState(false);
  const generate=async()=>{setBusy(true);try{const r=await querycopilot(`Generate a ${type} report summary for the most critical AML alert`,"search");let d=`# ${type}\n\n**Generated:** ${new Date().toISOString()}\n\n## Regulatory Basis\n\n`;if(r.results){r.results.forEach((c:any,i:number)=>{d+=`### [${i+1}] ${c.SECTION_REF} (${c.REGULATION_TYPE})\n\n> ${c.CLAUSE_TEXT}\n\n`})}setGen(d)}catch{setGen("Error generating.")}finally{setBusy(false)}};
  return(<Panel title="Regulatory Filing Auto-Drafter">
    <div className="flex gap-3 mb-5">
      <select value={type} onChange={e=>setType(e.target.value)} className="input" style={{width:260}}>{["FinCEN SAR Filing","Basel III LCR Memo","IFRS 9 ECL Report","AML Investigation Summary"].map(t=><option key={t}>{t}</option>)}</select>
      <button onClick={generate} disabled={busy} className="btn-primary"><FileText className="w-4 h-4"/>{busy?"Generating...":"Generate Filing"}</button>
    </div>
    {gen&&(<div><div className="p-5 rounded-xl bg-violet-50/50 border border-violet-100 max-h-96 overflow-auto"><pre className="text-sm whitespace-pre-wrap">{gen}</pre></div>
    <button onClick={()=>{const b=new Blob([gen],{type:"text/markdown"});const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=`${type.replace(/ /g,"_")}.md`;a.click()}} className="btn-ghost mt-3"><Download className="w-4 h-4"/>Download .md</button></div>)}
  </Panel>);
}

/* ━━━ Tab 5 ━━━ */
function AMLNetworkTab(){
  const [data,setData]=useState<Metrics|null>(null);
  useEffect(()=>{fetchMetrics().then(setData).catch(()=>{})},[]);
  return(<Panel title="AML Velocity & Network Detection">
    <div className="grid grid-cols-3 gap-5 mb-5">
      <div className="gcard text-center"><AlertTriangle className="w-8 h-8 mx-auto mb-3 text-amber-500"/><div className="text-3xl font-extrabold text-amber-600">{data?data.critical_alerts:"—"}</div><div className="text-[.72rem] text-[var(--dim)] mt-1 font-medium">Critical Alerts (Live)</div></div>
      <div className="gcard text-center"><Network className="w-8 h-8 mx-auto mb-3 text-rose-500"/><div className="text-3xl font-extrabold text-rose-600">{data?data.open_alerts:"—"}</div><div className="text-[.72rem] text-[var(--dim)] mt-1 font-medium">Open Investigations</div></div>
      <div className="gcard text-center"><Zap className="w-8 h-8 mx-auto mb-3 text-violet-500"/><div className="text-3xl font-extrabold text-violet-600">{data?`$${fmt(data.fraud_volume)}`:"—"}</div><div className="text-[.72rem] text-[var(--dim)] mt-1 font-medium">Fraud Volume</div></div>
    </div>
    {data&&data.lcr_sparkline&&<SparkArea data={data.lcr_sparkline.slice().reverse().map(s=>({label:s.date.slice(5),value:s.value}))} color1="#6366f1" color2="#7c3aed" h={80}/>}
  </Panel>);
}

/* ━━━ Tab 6 ━━━ */
function MCPActionsTab(){
  return(<Panel title="Cross-Tool Action Engine (MCP)">
    <div className="grid grid-cols-2 gap-5 mb-5">
      <div className="gcard text-center"><div className="text-[.65rem] text-[var(--dim)] uppercase font-bold mb-2">Slack</div><div className="text-lg font-bold text-violet-600">Active</div><div className="text-xs text-[var(--dim)] mt-1">#risk-compliance-alerts</div></div>
      <div className="gcard text-center"><div className="text-[.65rem] text-[var(--dim)] uppercase font-bold mb-2">Jira</div><div className="text-lg font-bold text-pink-600">Active</div><div className="text-xs text-[var(--dim)] mt-1">Project: COMP</div></div>
    </div>
    <div className="gcard"><div className="text-[.65rem] text-[var(--dim)] uppercase font-bold mb-2">Atlassian MCP Server</div><div className="text-sm font-mono text-violet-600">FINGUARD_DB.PUBLIC.ATLASSIAN_MCP</div><div className="text-xs text-[var(--dim)] mt-1">mcp.atlassian.com/v1/mcp · Dynamic Client Registration OAuth</div></div>
  </Panel>);
}

/* ━━━ Tab 7 ━━━ */
function AuditExport(){
  const [alertId,setAlertId]=useState("AML-000327");const [busy,setBusy]=useState(false);const [done,setDone]=useState(false);
  const dl=async()=>{setBusy(true);setDone(false);try{const blob=await exportAudit(alertId);const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=`audit_${alertId}.zip`;a.click();URL.revokeObjectURL(url);setDone(true)}catch{}finally{setBusy(false)}};
  return(<Panel title="One-Click Signed Audit Export">
    <p className="text-[var(--dim)] text-sm mb-5">ZIP: audit memo, SQL logs, lineage graph JSON, metadata with SHA-256 signature.</p>
    <div className="flex gap-3 items-center">
      <input value={alertId} onChange={e=>setAlertId(e.target.value)} className="input" style={{width:200}}/>
      <button onClick={dl} disabled={busy} className="btn-primary"><Download className="w-4 h-4"/>{busy?"Generating...":"Export Package"}</button>
      {done&&<span className="text-emerald-600 text-sm flex items-center gap-1 font-semibold"><CheckCircle className="w-4 h-4"/>Downloaded</span>}
    </div>
  </Panel>);
}
