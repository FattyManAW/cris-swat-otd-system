import { useState } from "react";
import { Bot, Search, RefreshCw, Truck, Shield, Play, Loader2, CheckCircle2, Target, Wrench, BadgeCheck, AlertCircle } from "lucide-react";
import { api } from "../lib/api";

const AGENTS = [
  {
    id: "customer",
    icon: Bot, name: "客服溝通樞紐",
    role: "從詢單接收到出貨通知的全程客戶互動",
    goal: "確保客戶查詢在 30 秒內得到回應，ASN 準確率達 99%",
    tools: ["ATP 查詢", "ASN 生成", "Invoice 寄送", "報關聯繫"],
    steps: ["詢單接收與記錄", "進度追蹤與回覆", "ASN 預出貨通知", "Invoice 寄送", "報關聯繫"],
    simulate: async () => {
      const r = await api.simCustomer();
      return { endpoint: "/api/v1/atp/check", result: r };
    },
  },
  {
    id: "atp",
    icon: Search, name: "ATP/CTP 交期試算",
    role: "接收詢單需求，調用 ERP 進行交期試算",
    goal: "交期回覆準確率 ≥ 95%，CTP 試算 < 2 秒",
    tools: ["ATP 查詢", "CTP 模擬", "庫存檢查", "產能分析"],
    steps: ["ATP 可允諾量檢查", "CTP 產能承諾分析", "交期回覆與建議", "庫存/產能不足警示"],
    simulate: async () => {
      const r = await api.simCustomer();
      return { endpoint: "/api/v1/atp/check", result: r };
    },
  },
  {
    id: "po",
    icon: RefreshCw, name: "PO→SO 訂單轉換",
    role: "接收客戶 PO，自動建立 SO",
    goal: "PO→SO 轉換 < 5 秒，料號對照成功率 ≥ 98%",
    tools: ["PO 解析", "料號對照", "SO 建立", "異常回報"],
    steps: ["PO 接收與解析", "料號對照與驗證", "SO 單頭單身建立", "問題料號回報"],
    simulate: async () => {
      const poId = await api.simPOtoSO();
      return { endpoint: "/api/v1/po/{po_id}/convert", result: { po_id: poId, status: "converted" } };
    },
  },
  {
    id: "logistics",
    icon: Truck, name: "物流處理專家",
    role: "全程物流流程處理",
    goal: "報關文件生成 < 10 秒，出貨追蹤準確率 100%",
    tools: ["報關文件", "出貨排程", "在途追蹤", "到貨簽收"],
    steps: ["報關文件生成", "出貨排程確認", "在途追蹤", "到貨確認與簽收"],
    simulate: async () => {
      const r = await api.simLogistics();
      return { endpoint: "/api/v1/logistics/arrange", result: r };
    },
  },
  {
    id: "after",
    icon: Shield, name: "售後服務專家",
    role: "客戶聲音與售後支援",
    goal: "退換貨處理 < 24h，客戶滿意度追蹤率 100%",
    tools: ["案件管理", "滿意度追蹤", "退換貨處理", "品質回饋"],
    steps: ["案件追蹤與管理", "客戶滿意度管理", "退換貨處理", "品質回饋收集"],
    simulate: async () => {
      const r = await api.simShipping();
      return { endpoint: "/api/v1/shipping/create", result: r };
    },
  },
];

export default function AgentCards() {
  const [active, setActive] = useState(null);
  const [results, setResults] = useState({});
  const [expandedId, setExpandedId] = useState(null);

  const runSim = async (agent) => {
    setActive(agent.id);
    try {
      const { endpoint, result } = await agent.simulate();
      const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setResults(function (prev) {
        var copy = {};
        for (var k in prev) { copy[k] = prev[k]; }
        copy[agent.id] = { ok: true, endpoint: endpoint, result: result, time: ts };
        return copy;
      });
    } catch (e) {
      setResults(function (prev) {
        var copy = {};
        for (var k in prev) { copy[k] = prev[k]; }
        copy[agent.id] = { ok: false, error: e.message };
        return copy;
      });
    } finally {
      setActive(null);
    }
  };

  const getResult = function (id) { return results[id]; };

  return (
    <div className="bg-otd-card border border-otd-border rounded-xl p-5">
      <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2">
        <Bot className="w-4 h-4 text-otd-agent" />五個專職 AI Agent
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {AGENTS.map(function (agent) {
          var id = agent.id;
          var Icon = agent.icon;
          var name = agent.name;
          var role = agent.role;
          var goal = agent.goal;
          var tools = agent.tools;
          var steps = agent.steps;
          var isExpanded = expandedId === id;
          var res = getResult(id);
          return (
            <div
              key={id}
              className={"bg-otd-surface border rounded-xl transition-all " + (isExpanded ? "border-otd-agent shadow-md ring-1 ring-otd-agent/20" : "border-otd-border hover:border-otd-agent/50")}
            >
              <div className="p-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-otd-agent/10 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-4 h-4 text-otd-agent" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-semibold text-otd-text text-sm truncate">{name}</div>
                      <div className="text-[10px] text-otd-muted truncate">{role}</div>
                    </div>
                  </div>
                  <span className="flex-shrink-0 flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-600 border border-emerald-200">
                    <BadgeCheck className="w-2.5 h-2.5" />
                    在線
                  </span>
                </div>

                <div className="mt-2 flex items-start gap-1.5 text-[10px] text-otd-muted">
                  <Target className="w-3 h-3 text-otd-agent flex-shrink-0 mt-0.5" />
                  <span className="leading-snug">{goal}</span>
                </div>

                <div className="mt-2 flex flex-wrap gap-1">
                  {tools.map(function (t) {
                    return (
                      <span key={t} className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] bg-otd-bg border border-otd-border text-otd-muted">
                        <Wrench className="w-2 h-2" />
                        {t}
                      </span>
                    );
                  })}
                </div>

                {isExpanded && (
                  <ul className="mt-2 space-y-0.5 border-t border-otd-border pt-2">
                    {steps.map(function (s) {
                      return (
                        <li key={s} className="text-[10px] text-otd-muted flex items-start gap-1">
                          <span className="text-otd-agent mt-0.5">▸</span>
                          {s}
                        </li>
                      );
                    })}
                  </ul>
                )}
                <button
                  onClick={function () { setExpandedId(isExpanded ? null : id); }}
                  className="mt-1 text-[9px] text-otd-agent/70 hover:text-otd-agent"
                >
                  {isExpanded ? "收起" : "展開步驟 →"}
                </button>
              </div>

              <div className="px-3 pb-3">
                <button
                  onClick={function () { runSim(agent); }}
                  disabled={active === id}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-otd-agent/10 text-otd-agent border border-otd-agent/30 hover:bg-otd-agent/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {active === id ? (
                    <><Loader2 className="w-3 h-3 animate-spin" />模擬中…</>
                  ) : (
                    <><Play className="w-3 h-3" />模擬</>
                  )}
                </button>
                {res && (
                  <div className={"mt-2 text-[10px] rounded-lg p-2 " + (res.ok ? "bg-otd-green/10 text-otd-green border border-otd-green/20" : "bg-otd-red/10 text-otd-red border border-otd-red/20")}>
                    <div className="flex items-center gap-1 font-medium">
                      {res.ok ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                      {res.ok ? "模擬完成" : "模擬失敗"}
                      {res.time && <span className="ml-auto text-[9px] opacity-60">{res.time}</span>}
                    </div>
                    <div className="font-mono mt-1 opacity-70">{res.ok ? res.endpoint : res.error}</div>
                    {res.ok && res.result && (
                      <pre className="mt-1 overflow-auto max-h-16 text-[9px] font-mono opacity-80">
                        {JSON.stringify(res.result).slice(0, 100)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}