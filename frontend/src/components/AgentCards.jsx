import { useState } from "react";
import { Bot, Search, RefreshCw, Truck, Shield, Play, Loader2, CheckCircle2 } from "lucide-react";
import { api } from "../lib/api";

const AGENTS = [
  {
    id: "customer",
    icon: Bot, name: "客服溝通樞紐", role: "從詢單接收到出貨通知的全程客戶互動",
    steps: ["詢單接收與記錄", "進度追蹤與回覆", "ASN 預出貨通知", "Invoice 寄送", "報關聯繫"],
    simulate: async () => {
      const r = await api.simCustomer();
      return { endpoint: "/api/v1/atp/check", result: r };
    },
  },
  {
    id: "atp",
    icon: Search, name: "ATP/CTP 交期試算", role: "接收詢單需求，調用 ERP 進行交期試算",
    steps: ["ATP 可允諾量檢查", "CTP 產能承諾分析", "交期回覆與建議", "庫存/產能不足警示"],
    simulate: async () => {
      const r = await api.simCustomer();
      return { endpoint: "/api/v1/atp/check", result: r };
    },
  },
  {
    id: "po",
    icon: RefreshCw, name: "PO→SO 訂單轉換", role: "接收客戶 PO，自動建立 SO",
    steps: ["PO 接收與解析", "料號對照與驗證", "SO 單頭單身建立", "問題料號回報"],
    simulate: async () => {
      const poId = await api.simPOtoSO();
      return { endpoint: "/api/v1/po/{po_id}/convert", result: { po_id: poId, status: "converted" } };
    },
  },
  {
    id: "logistics",
    icon: Truck, name: "物流處理專家", role: "全程物流流程處理",
    steps: ["報關文件生成", "出貨排程確認", "在途追蹤", "到貨確認與簽收"],
    simulate: async () => {
      const r = await api.simLogistics();
      return { endpoint: "/api/v1/logistics/arrange", result: r };
    },
  },
  {
    id: "after",
    icon: Shield, name: "售後服務專家", role: "客戶聲音與售後支援",
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

  const runSim = async (agent) => {
    setActive(agent.id);
    try {
      const { endpoint, result } = await agent.simulate();
      setResults(prev => ({ ...prev, [agent.id]: { ok: true, endpoint, result } }));
    } catch (e) {
      setResults(prev => ({ ...prev, [agent.id]: { ok: false, error: e.message } }));
    } finally {
      setActive(null);
    }
  };

  const getResult = (id) => results[id];

  return (
    <div className="bg-otd-card border border-otd-border rounded-xl p-5">
      <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2">
        <Bot className="w-4 h-4 text-otd-agent" />五個專職 AI Agent
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {AGENTS.map((agent) => {
          const { id, icon: Icon, name, role, steps } = agent;
          const res = getResult(id);
          return (
            <div
              key={name}
              className="bg-otd-surface border border-otd-border rounded-xl p-4 transition-all hover:border-otd-agent/50 hover:-translate-y-0.5"
            >
              <Icon className="w-6 h-6 text-otd-agent mb-2" />
              <div className="font-semibold text-otd-text text-sm mb-1">{name}</div>
              <div className="text-[11px] text-otd-muted mb-3">{role}</div>
              <ul className="space-y-1">
                {steps.map((s) => (
                  <li key={s} className="text-[11px] text-otd-muted flex items-start gap-1">
                    <span className="text-otd-agent mt-0.5">▸</span>
                    {s}
                  </li>
                ))}
              </ul>
              {/* 模擬按鈕 */}
              <button
                onClick={() => runSim(agent)}
                disabled={active === id}
                className="mt-3 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-otd-agent/10 text-otd-agent border border-otd-agent/30 hover:bg-otd-agent/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {active === id ? (
                  <><Loader2 className="w-3 h-3 animate-spin" />模擬中…</>
                ) : (
                  <><Play className="w-3 h-3" />模擬</>
                )}
              </button>
              {/* 模擬結果 */}
              {res && (
                <div className={`mt-2 text-[11px] rounded-lg p-2 ${res.ok ? "bg-otd-green/10 text-otd-green border border-otd-green/20" : "bg-otd-red/10 text-otd-red border border-otd-red/20"}`}>
                  <div className="flex items-center gap-1 font-medium">
                    {res.ok ? <CheckCircle2 className="w-3 h-3" /> : null}
                    {res.ok ? "模擬完成" : "模擬失敗"}
                  </div>
                  <div className="font-mono mt-1 opacity-70">{res.ok ? res.endpoint : res.error}</div>
                  {res.ok && res.result && (
                    <pre className="mt-1 overflow-auto max-h-20 text-[10px] font-mono opacity-80">
                      {JSON.stringify(res.result).slice(0, 100)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
