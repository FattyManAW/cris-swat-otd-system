import { useState, useEffect } from "react";
import { Package, FileText, Truck, BarChart3, RefreshCw, Clock, CheckCircle2 } from "lucide-react";
import { api } from "../lib/api";
import QuickFlowGuide from "../components/QuickFlowGuide";
import AgentCards from "../components/AgentCards";
import KanbanBoard from "../components/KanbanBoard";
import ProcessFlow from "../components/ProcessFlow";

function Badge({ status }) {
  const map = {
    pending:    "bg-otd-amber/15 text-otd-amber",
    confirmed:  "bg-otd-accent/15 text-otd-accent",
    processing: "bg-blue-500/15 text-blue-400",
    shipped:    "bg-otd-green/15 text-otd-green",
    delivered:  "bg-otd-green/15 text-otd-green",
    cancelled:  "bg-otd-red/15 text-otd-red",
    draft:      "bg-otd-muted/15 text-otd-muted",
    completed:  "bg-otd-green/15 text-otd-green",
  };
  const cls = map[status] || "bg-otd-muted/15 text-otd-muted";
  return <span className={`badge px-2 py-0.5 rounded text-[11px] font-medium ${cls}`}>{status}</span>;
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [po, so, inv, ship, log] = await Promise.all([
        api.countPO(),
        api.countSO(),
        api.countInvoice(),
        api.countShipping(),
        api.countLogistics(),
      ]);
      setData({ po, so, inv, ship, log });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const kpis = [
    { label: "採購單 PO",  value: data?.po?.count ?? "—", icon: FileText,  accent: "text-otd-accent" },
    { label: "銷售單 SO",  value: data?.so?.count ?? "—", icon: Package,   accent: "text-otd-green" },
    { label: "物流單",     value: data?.log?.count ?? "—", icon: Truck,     accent: "text-otd-amber" },
    { label: "發票",       value: data?.inv?.count ?? "—", icon: BarChart3, accent: "text-blue-400" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-otd-text">儀表板</h1>
          <p className="text-sm text-otd-muted mt-0.5">OTD 流程全覽</p>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-otd-muted hover:bg-otd-border/50 transition-colors">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          刷新
        </button>
      </div>

      {/* Quick Flow Guide — L1 Onboarding */}
      <QuickFlowGuide />

      {/* Process Flow — Agent Collaboration */}
      <ProcessFlow />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {kpis.map(({ label, value, icon: Icon, accent }) => (
          <div key={label} className="bg-otd-card border border-otd-border rounded-xl p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-otd-muted uppercase tracking-wider">{label}</span>
              <Icon className={`w-4 h-4 ${accent}`} />
            </div>
            <div className="text-2xl font-bold text-otd-text mt-2">{value}</div>
          </div>
        ))}
      </div>

      {/* OTD Flow Overview */}
      <div className="bg-otd-card border border-otd-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-otd-accent" />
          OTD 流程概覽
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-center">
          {[
            { stage: "PO",   desc: "採購單",  color: "from-otd-accent to-blue-600" },
            { stage: "SO",   desc: "銷售單",  color: "from-otd-green to-emerald-600" },
            { stage: "ATP",  desc: "庫存確認", color: "from-violet-500 to-purple-600" },
            { stage: "出貨", desc: "Shipping", color: "from-otd-amber to-orange-500" },
            { stage: "發票", desc: "Invoice",  color: "from-pink-500 to-rose-600" },
          ].map(({ stage, desc, color }) => (
            <div key={stage} className="flex flex-col items-center gap-1">
              <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${color} flex items-center justify-center text-white font-bold text-sm`}>
                {stage.charAt(0)}
              </div>
              <span className="text-[11px] text-otd-muted">{desc}</span>
              <div className="flex items-center gap-0.5 text-otd-green">
                <CheckCircle2 className="w-3 h-3" />
                <span className="text-[10px]">API</span>
              </div>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-otd-muted mt-4 text-center">
          點擊側欄進入各模組 · 五個 AI Agent 協同驅動供應鏈自動化
        </p>
      </div>

      {/* Kanban Board — Agent Task Tracking */}
      <KanbanBoard />

      {/* Agent Cards */}
      <AgentCards />
    </div>
  );
}