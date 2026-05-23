import { GitBranch } from "lucide-react";

const FLOW = [
  { icon: "📋", label: "詢單接收", agent: "客服 Agent" },
  { icon: "🔍", label: "ATP/CTP 試算", agent: "ATP Agent" },
  { icon: "🔄", label: "PO→SO 轉換", agent: "轉單 Agent" },
  { icon: "🚚", label: "物流排程", agent: "物流 Agent" },
  { icon: "📦", label: "出貨追蹤", agent: "物流 Agent" },
  { icon: "🧾", label: "發票與收款", agent: "客服 Agent" },
  { icon: "💬", label: "售後服務", agent: "售後 Agent" },
];

export default function ProcessFlow() {
  return (
    <div className="bg-otd-card border border-otd-border rounded-xl p-5 mb-6">
      <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2">
        <GitBranch className="w-4 h-4 text-otd-accent" />
        AI Agent 全流程協作
      </h2>
      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {FLOW.map(({ icon, label, agent }, i) => (
          <div key={i} className="flex items-center gap-1 flex-shrink-0">
            <div className="bg-otd-surface border border-otd-border rounded-lg px-4 py-3 text-center min-w-[120px]">
              <div className="text-lg">{icon}</div>
              <div className="text-[12px] font-semibold text-otd-text mt-1">{label}</div>
              <div className="text-[10px] bg-otd-agent/15 text-otd-agent rounded px-1.5 py-0.5 mt-1 inline-block">
                {agent}
              </div>
            </div>
            {i < FLOW.length - 1 && (
              <span className="text-otd-muted text-lg flex-shrink-0">→</span>
            )}
          </div>
        ))}
      </div>
      <p className="text-[11px] text-otd-muted mt-4 text-center">
        五個 AI Agent 協同驅動 — 從詢單到售後，端到端自動化供應鏈
      </p>
    </div>
  );
}