import { useEffect, useState } from "react";
import { ArrowRight, FileText, Package, Truck, Receipt } from "lucide-react";
import { api } from "../lib/api";

const STEPS = [
  {
    id: 1,
    icon: FileText,
    title: "建立採購單",
    desc: "POST /api/v1/po",
    apiCheck: "po",
    wizardStep: 2,
  },
  {
    id: 2,
    icon: Package,
    title: "PO 轉銷售單",
    desc: "POST /po/{id}/convert",
    apiCheck: "so",
    wizardStep: 4,
  },
  {
    id: 3,
    icon: Truck,
    title: "安排出貨",
    desc: "POST /shipping/create",
    apiCheck: "shipping",
    wizardStep: 5,
  },
  {
    id: 4,
    icon: Receipt,
    title: "開立發票",
    desc: "POST /invoice/create",
    apiCheck: "invoice",
    wizardStep: 6,
  },
];

export default function QuickFlowGuide() {
  const [statuses, setStatuses] = useState({});

  useEffect(() => {
    (async () => {
      try {
        const [po, so, shipping, invoice] = await Promise.all([
          api.countPO(),
          api.countSO(),
          api.countShipping(),
          api.countInvoice(),
        ]);
        setStatuses({
          po: po?.count > 0 ? "done" : "todo",
          so: so?.count > 0 ? "done" : "todo",
          shipping: shipping?.count > 0 ? "done" : "todo",
          invoice: invoice?.count > 0 ? "done" : "todo",
        });
      } catch {}
    })();
  }, []);

  const statusBadge = (s) => {
    if (s === "done") return { dot: "bg-otd-green", text: "已完成", ring: "ring-otd-green/40" };
    if (s === "active") return { dot: "bg-otd-amber animate-pulse", text: "進行中", ring: "ring-otd-amber/40" };
    return { dot: "bg-otd-muted", text: "待開始", ring: "ring-otd-border" };
  };

  return (
    <div className="bg-otd-card border border-otd-border rounded-xl p-5 mb-6">
      <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2">
        <ArrowRight className="w-4 h-4 text-otd-accent" />
        快速開始 — 四步驟完成第一筆訂單
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {STEPS.map(({ id, icon: Icon, title, desc, apiCheck }) => {
          const s = statusBadge(statuses[apiCheck] || "todo");
          return (
            <div
              key={id}
              className={`relative bg-otd-surface border rounded-xl p-4 text-center transition-all hover:-translate-y-0.5 ${
                statuses[apiCheck] === "done"
                  ? "border-otd-green/50 ring-1 ring-otd-green/20"
                  : "border-otd-border hover:border-otd-accent/50"
              }`}
            >
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-otd-accent text-white text-xs font-bold flex items-center justify-center">
                {id}
              </div>
              <Icon className="w-8 h-8 mx-auto mt-2 mb-2 text-otd-accent" />
              <div className="font-semibold text-otd-text text-sm">{title}</div>
              <div className="text-[11px] text-otd-muted font-mono mt-1">{desc}</div>
              <div className={`flex items-center justify-center gap-1 mt-2 text-xs`}>
                <span className={`w-2 h-2 rounded-full ${s.dot}`} />
                <span className={statuses[apiCheck] === "done" ? "text-otd-green" : "text-otd-muted"}>
                  {s.text}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] text-otd-muted mt-4 text-center">
        💡 系統已載入 {statuses.po === "done" ? "全部四步驟" : "部分"}資料 — 點擊側欄模組開始操作
      </p>
    </div>
  );
}