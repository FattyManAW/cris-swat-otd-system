import { Bot, Search, RefreshCw, Truck, Shield } from "lucide-react";

const AGENTS = [
  {
    icon: Bot, name: "客服溝通樞紐", role: "從詢單接收到出貨通知的全程客戶互動",
    steps: ["詢單接收與記錄", "進度追蹤與回覆", "ASN 預出貨通知", "Invoice 寄送", "報關聯繫"],
  },
  {
    icon: Search, name: "ATP/CTP 交期試算", role: "接收詢單需求，調用 ERP 進行交期試算",
    steps: ["ATP 可允諾量檢查", "CTP 產能承諾分析", "交期回覆與建議", "庫存/產能不足警示"],
  },
  {
    icon: RefreshCw, name: "PO→SO 訂單轉換", role: "接收客戶 PO，自動建立 SO",
    steps: ["PO 接收與解析", "料號對照與驗證", "SO 單頭單身建立", "問題料號回報"],
  },
  {
    icon: Truck, name: "物流處理專家", role: "全程物流流程處理",
    steps: ["報關文件生成", "出貨排程確認", "在途追蹤", "到貨確認與簽收"],
  },
  {
    icon: Shield, name: "售後服務專家", role: "客戶聲音與售後支援",
    steps: ["案件追蹤與管理", "客戶滿意度管理", "退換貨處理", "品質回饋收集"],
  },
];

export default function AgentCards() {
  return (
    <div className="bg-otd-card border border-otd-border rounded-xl p-5">
      <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2">
        <Bot className="w-4 h-4 text-otd-agent" />五個專職 AI Agent
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {AGENTS.map(({ icon: Icon, name, role, steps }) => (
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
          </div>
        ))}
      </div>
    </div>
  );
}