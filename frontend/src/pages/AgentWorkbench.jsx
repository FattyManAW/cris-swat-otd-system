import { useState, useEffect } from "react";
import { api } from "../lib/api";
import { clsx } from "clsx";
import {
  Bot, Search, RefreshCw, Truck, Shield,
  Play, Loader2, CheckCircle2, AlertCircle,
  Target, Wrench, Clock, Zap, ChevronDown, ChevronRight,
  Circle, GitBranch, X, BarChart3, Filter, SlidersHorizontal, ArrowUpDown,
} from "lucide-react";

const COLUMNS = [
  { id: "queue", label: "📥 待處理", color: "text-otd-muted" },
  { id: "active", label: "⚙️ 處理中", color: "text-otd-amber" },
  { id: "done", label: "✅ 已完成", color: "text-otd-green" },
];

const AGENTS = [
  {
    id: "customer", icon: Bot, name: "客服溝通樞紐", emoji: "💬",
    role: "從詢單接收到出貨通知的全程客戶互動",
    goal: "確保客戶查詢在 30 秒內得到回應，ASN 準確率達 99%",
    tools: ["ATP 查詢", "ASN 生成", "Invoice 寄送", "報關聯繫"],
    simulate: async () => {
      const r = await api.simCustomer();
      return { endpoint: "/api/v1/atp/check", phases: ["分析客戶需求", "查詢出貨狀態", "生成 ASN 通知"], result: r };
    },
  },
  {
    id: "atp", icon: Search, name: "ATP/CTP 交期試算", emoji: "🔍",
    role: "接收詢單需求，調用 ERP 進行交期試算",
    goal: "交期回覆準確率 ≥ 95%，CTP 試算 < 2 秒",
    tools: ["ATP 查詢", "CTP 模擬", "庫存檢查", "產能分析"],
    simulate: async () => {
      const r = await api.simCustomer();
      return { endpoint: "/api/v1/atp/check", phases: ["檢查可允諾庫存", "模擬產能承諾", "計算交期回覆"], result: r };
    },
  },
  {
    id: "po", icon: RefreshCw, name: "PO→SO 訂單轉換", emoji: "🔄",
    role: "接收客戶 PO，自動建立 SO",
    goal: "PO→SO 轉換 < 5 秒，料號對照成功率 ≥ 98%",
    tools: ["PO 解析", "料號對照", "SO 建立", "異常回報"],
    simulate: async () => {
      const poId = await api.simPOtoSO();
      return { endpoint: "/api/v1/po/{po_id}/convert", phases: ["解析 PO 內容", "料號對照驗證", "建立 SO 單據"], result: { po_id: poId, status: "converted" } };
    },
  },
  {
    id: "logistics", icon: Truck, name: "物流處理專家", emoji: "🚚",
    role: "全程物流流程處理",
    goal: "報關文件生成 < 10 秒，出貨追蹤準確率 100%",
    tools: ["報關文件", "出貨排程", "在途追蹤", "到貨簽收"],
    simulate: async () => {
      const r = await api.simLogistics();
      return { endpoint: "/api/v1/logistics/arrange", phases: ["生成報關文件", "安排出貨排程", "開始在途追蹤"], result: r };
    },
  },
  {
    id: "after", icon: Shield, name: "售後服務專家", emoji: "🛡️",
    role: "客戶聲音與售後支援",
    goal: "退換貨處理 < 24h，客戶滿意度追蹤率 100%",
    tools: ["案件管理", "滿意度追蹤", "退換貨處理", "品質回饋"],
    simulate: async () => {
      const r = await api.simShipping();
      return { endpoint: "/api/v1/shipping/create", phases: ["建立售後案件", "追蹤客戶回饋", "更新滿意度"], result: r };
    },
  },
];

/** Mini task card inside a lane */
function TaskCard({ task, agentId }) {
  const statusColors = {
    idle: "bg-otd-bg border-otd-border",
    working: "bg-otd-amber/5 border-otd-amber/30",
    done: "bg-otd-green/5 border-otd-green/30",
    blocked: "bg-otd-red/5 border-otd-red/30",
  };
  const statusDots = {
    idle: "🟢",
    working: "🟡",
    done: "🔵",
    blocked: "🔴",
  };

  return (
    <div className={clsx(
      "border rounded-lg p-2.5 text-xs transition-all hover:shadow-sm",
      statusColors[task.status] || statusColors.idle
    )}>
      <div className="flex items-center gap-1.5 mb-1">
        <span>{statusDots[task.status] || "🟢"}</span>
        <span className="font-semibold text-otd-text truncate">{task.title}</span>
      </div>
      {task.desc && <p className="text-[10px] text-otd-muted mb-1.5">{task.desc}</p>}
      {task.time && (
        <div className="flex items-center gap-1 text-[9px] text-otd-muted">
          <Clock className="w-2.5 h-2.5" />
          {task.time}
        </div>
      )}
      {task.phases && (
        <div className="mt-1.5 space-y-0.5">
          {task.phases.map((p, i) => (
            <div key={i} className="flex items-start gap-1 text-[9px] text-otd-muted">
              <span className="text-otd-agent mt-0.5">{i + 1 === task.currentPhase ? "▶" : "·"}</span>
              {p}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Single Agent column: identity card + 3 lanes */
function AgentColumn({ agent, tasks, onSimulate, simulating, simResult }) {
  const [expanded, setExpanded] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const Icon = agent.icon;

  // Calculate per-column stats
  const activeTasks = tasks.filter(t => t.status === "working");
  const isActive = activeTasks.length > 0;
  const doneCount = tasks.filter(t => t.status === "done").length;

  return (
    <div className="flex flex-col min-w-[260px] max-w-[320px] flex-shrink-0">
      {/* Agent Identity Card */}
      <div className={clsx(
        "bg-otd-card border rounded-xl p-3.5 mb-2 transition-all",
        isActive ? "border-otd-agent/50 ring-1 ring-otd-agent/20" : "border-otd-border"
      )}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-otd-agent/10 flex items-center justify-center">
              <Icon className="w-4 h-4 text-otd-agent" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1">
                <span className="text-xs">{agent.emoji}</span>
                <span className="font-semibold text-otd-text text-xs truncate">{agent.name}</span>
              </div>
              <div className="text-[10px] text-otd-muted truncate">{agent.role}</div>
            </div>
          </div>
          <span className={clsx(
            "flex-shrink-0 w-2 h-2 rounded-full",
            isActive ? "bg-otd-amber animate-pulse" : doneCount > 0 ? "bg-otd-green" : "bg-otd-muted"
          )} />
        </div>

        <div className="flex items-start gap-1 text-[10px] text-otd-muted mb-2">
          <Target className="w-3 h-3 text-otd-agent flex-shrink-0 mt-0.5" />
          <span className="leading-snug">{agent.goal}</span>
        </div>

        <div className="flex flex-wrap gap-1 mb-2">
          {agent.tools.map(t => (
            <span key={t} className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] bg-otd-bg border border-otd-border text-otd-muted">
              <Wrench className="w-2 h-2" />{t}
            </span>
          ))}
        </div>

        <div className="flex gap-1.5">
          <button
            onClick={() => onSimulate(agent)}
            disabled={simulating === agent.id}
            className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-medium bg-otd-agent/10 text-otd-agent border border-otd-agent/30 hover:bg-otd-agent/20 disabled:opacity-50 transition-colors"
          >
            {simulating === agent.id ? (
              <><Loader2 className="w-3 h-3 animate-spin" />模擬中…</>
            ) : (
              <><Play className="w-3 h-3" />觸發模擬</>
            )}
          </button>
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="px-2 py-1.5 rounded-lg text-[10px] text-otd-muted border border-otd-border hover:bg-otd-bg"
          >
            <Clock className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* TAO: Thought→Action→Observation Streaming Panel */}
      {simResult && (
        <div className={clsx(
          "mb-2 text-[10px] rounded-lg border overflow-hidden transition-all",
          simResult.ok
            ? "bg-otd-card border-otd-agent/30"
            : "bg-otd-red/5 border-otd-red/20"
        )}>
          {/* Header */}
          <div className={clsx(
            "px-2.5 py-1.5 flex items-center justify-between text-[9px] font-semibold",
            simResult.ok ? "bg-otd-agent/10 text-otd-agent" : "bg-otd-red/10 text-otd-red"
          )}>
            <span>{simResult.ok ? "🧠 Agent 思考過程" : "❌ 模擬失敗"}</span>
            {simResult.time && <span className="opacity-60">{simResult.time}</span>}
          </div>

          {/* TAO Phases */}
          <div className="p-2 space-y-1.5">
            {/* Thought */}
            <div className={clsx(
              "flex items-start gap-1.5 transition-opacity",
              simResult.taoPhases ? "opacity-100" : "opacity-60"
            )}>
              <span className="flex-shrink-0 mt-0.5">
                {simResult.taoPhases?.thought?.done
                  ? <CheckCircle2 className="w-3 h-3 text-otd-green" />
                  : simResult.phase === "thought"
                    ? <Loader2 className="w-3 h-3 text-otd-amber animate-spin" />
                    : <span className="w-3 h-3 flex items-center justify-center text-[8px]">💭</span>
                }
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[9px] font-semibold text-otd-text">Thought</div>
                <div className="text-[9px] text-otd-muted leading-snug">
                  {simResult.taoPhases?.thought?.text || "等待中…"}
                </div>
                {simResult.taoPhases?.thought?.time && (
                  <div className="text-[8px] text-otd-muted/50 mt-0.5">{simResult.taoPhases.thought.time}</div>
                )}
              </div>
            </div>

            {/* Action */}
            <div className={clsx(
              "flex items-start gap-1.5 transition-opacity",
              simResult.taoPhases?.action ? "opacity-100" : "opacity-40"
            )}>
              <span className="flex-shrink-0 mt-0.5">
                {simResult.taoPhases?.action?.done
                  ? <CheckCircle2 className="w-3 h-3 text-otd-green" />
                  : simResult.phase === "action"
                    ? <Loader2 className="w-3 h-3 text-otd-amber animate-spin" />
                    : <span className="w-3 h-3 flex items-center justify-center text-[8px]">🎯</span>
                }
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[9px] font-semibold text-otd-text">Action</div>
                <div className="text-[9px] text-otd-muted font-mono leading-snug">
                  {simResult.taoPhases?.action?.text || "等待 Thought 完成…"}
                </div>
                {simResult.taoPhases?.action?.time && (
                  <div className="text-[8px] text-otd-muted/50 mt-0.5">{simResult.taoPhases.action.time}</div>
                )}
              </div>
            </div>

            {/* Observation */}
            <div className={clsx(
              "flex items-start gap-1.5 transition-opacity",
              simResult.taoPhases?.observation ? "opacity-100" : "opacity-30"
            )}>
              <span className="flex-shrink-0 mt-0.5">
                {simResult.taoPhases?.observation?.done
                  ? <CheckCircle2 className="w-3 h-3 text-otd-green" />
                  : simResult.phase === "observation"
                    ? <Loader2 className="w-3 h-3 text-otd-amber animate-spin" />
                    : <span className="w-3 h-3 flex items-center justify-center text-[8px]">👁️</span>
                }
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[9px] font-semibold text-otd-text">Observation</div>
                <div className="text-[9px] text-otd-muted leading-snug">
                  {simResult.taoPhases?.observation?.text || "等待 Action 完成…"}
                </div>
                {simResult.taoPhases?.observation?.time && (
                  <div className="text-[8px] text-otd-muted/50 mt-0.5">{simResult.taoPhases.observation.time}</div>
                )}
              </div>
            </div>
          </div>

          {/* Result summary */}
          {simResult.ok && simResult.endpoint && (
            <div className="px-2 pb-2">
              <div className="text-[8px] text-otd-muted/60 font-mono truncate">
                {simResult.endpoint}
              </div>
            </div>
          )}
          {!simResult.ok && simResult.error && (
            <div className="px-2 pb-2 text-[9px] text-otd-red">{simResult.error}</div>
          )}
        </div>
      )}

      {/* Show history toggle */}
      {showHistory && (
        <div className="mb-2 text-[10px] bg-otd-card border border-otd-border rounded-lg p-2.5 max-h-32 overflow-auto">
          <div className="font-semibold mb-1 text-otd-muted">📋 模擬記錄</div>
          <div className="text-otd-muted">尚無記錄</div>
        </div>
      )}

      {/* 3 Lanes */}
      <div className="flex-1 space-y-2">
        {COLUMNS.map(col => {
          const laneTasks = tasks.filter(t => t.lane === col.id);
          return (
            <div key={col.id} className="bg-otd-surface/30 border border-otd-border rounded-lg p-2">
              <div className="flex items-center justify-between mb-1.5">
                <span className={clsx("text-[10px] font-semibold", col.color)}>
                  {col.label}
                </span>
                {laneTasks.length > 0 && (
                  <span className="text-[9px] bg-otd-muted/10 text-otd-muted px-1.5 py-0.5 rounded-full">
                    {laneTasks.length}
                  </span>
                )}
              </div>
              <div className="space-y-1.5 min-h-[40px]">
                {laneTasks.map(task => (
                  <TaskCard key={task.id} task={task} agentId={agent.id} />
                ))}
                {laneTasks.length === 0 && (
                  <div className="text-[9px] text-otd-muted/40 italic text-center py-2">
                    暫無任務
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

/** Activity Feed sidebar — with lifecycle timestamps */
function ActivityFeed({ events }) {
  const typeConfig = {
    thought: { dot: "bg-otd-violet", label: "💭 思考" },
    action: { dot: "bg-otd-amber", label: "🎯 執行" },
    observation: { dot: "bg-otd-agent", label: "👁️ 觀察" },
    done: { dot: "bg-otd-green", label: "✅ 完成" },
    active: { dot: "bg-otd-amber", label: "⚡ 進行中" },
    error: { dot: "bg-otd-red", label: "❌ 錯誤" },
    idle: { dot: "bg-otd-muted", label: "⏸️ 待命" },
  };

  // Calculate lifecycle duration from timestamps
  const getDuration = (events, idx) => {
    if (idx === events.length - 1) return null;
    // Simple heuristic: time between this and next event
    return null; // Not parseable without real timestamps
  };

  return (
    <div className="w-72 flex-shrink-0 bg-otd-card border-l border-otd-border flex flex-col">
      <div className="p-4 border-b border-otd-border">
        <h3 className="text-xs font-semibold text-otd-text flex items-center gap-1.5">
          <GitBranch className="w-3.5 h-3.5 text-otd-agent" />
          即時活動串流
        </h3>
        <div className="flex items-center gap-2 mt-2">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-otd-green animate-pulse" />
            <span className="text-[9px] text-otd-muted">Live</span>
          </span>
          <span className="text-[9px] text-otd-muted/50">
            {events.length} 筆記錄
          </span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {events.map((ev, i) => {
          const cfg = typeConfig[ev.type] || { dot: "bg-otd-muted", label: ev.type };
          return (
            <div key={i} className={clsx(
              "border-l-2 pl-2.5 py-1 transition-all",
              ev.type === "error" ? "border-otd-red/30" :
              ev.type === "done" ? "border-otd-green/30" :
              ev.type === "thought" || ev.type === "observation" ? "border-otd-agent/30" :
              "border-otd-border/50"
            )}>
              <div className="flex items-center gap-1.5">
                <span className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0", cfg.dot)} />
                <span className="text-[9px] font-semibold text-otd-text">{ev.agent}</span>
                <span className="text-[8px] text-otd-muted ml-auto">{ev.time}</span>
              </div>
              <div className="flex items-center gap-1 mt-0.5">
                <span className="text-[8px] text-otd-muted/60">{cfg.label}</span>
                <span className="text-[9px] text-otd-muted truncate">{ev.detail}</span>
              </div>
            </div>
          );
        })}
        {events.length === 0 && (
          <p className="text-[10px] text-otd-muted/40 italic text-center py-4">尚無活動記錄 — 點擊 Agent 模擬開始</p>
        )}
      </div>
      {/* Summary footer */}
      {events.length > 0 && (
        <div className="p-3 border-t border-otd-border">
          <div className="grid grid-cols-3 gap-1 text-center">
            {[
              { label: "完成", count: events.filter(e => e.type === "done").length, color: "text-otd-green" },
              { label: "錯誤", count: events.filter(e => e.type === "error").length, color: "text-otd-red" },
              { label: "總活動", count: events.length, color: "text-otd-muted" },
            ].map(({ label, count, color }) => (
              <div key={label} className="bg-otd-bg/50 rounded py-1">
                <div className={clsx("text-xs font-bold", color)}>{count}</div>
                <div className="text-[8px] text-otd-muted">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** ── Agent Detail Panel (slide-out) ────────────────────────────── */
function DetailPanel({ agent, onClose }) {
  const Icon = agent.icon;
  const statusDot = agent._isActive ? "bg-otd-amber animate-pulse" : agent._doneCount > 0 ? "bg-otd-green" : "bg-otd-muted";
  const statusLabel = agent._isActive ? "處理中" : agent._doneCount > 0 ? "已完成任務" : "待命中";

  return (
    <div className="fixed inset-0 z-40 flex justify-end" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 animate-fade-in" />
      {/* Panel */}
      <div
        className="relative z-50 w-[420px] max-w-[90vw] h-full bg-otd-card border-l border-otd-border overflow-y-auto animate-slide-in-right shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-otd-card/95 backdrop-blur border-b border-otd-border p-5 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-otd-agent/10 flex items-center justify-center">
              <Icon className="w-6 h-6 text-otd-agent" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg">{agent.emoji}</span>
                <h2 className="text-base font-bold text-otd-text">{agent.name}</h2>
              </div>
              <p className="text-xs text-otd-muted mt-0.5">{agent.role}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-otd-bg text-otd-muted hover:text-otd-text transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* Identity */}
          <section>
            <h3 className="text-[11px] font-semibold text-otd-muted uppercase tracking-wider mb-3">Identity</h3>
            <div className="bg-otd-bg border border-otd-border rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className={clsx("w-3 h-3 rounded-full flex-shrink-0", statusDot)} />
                <span className="text-sm font-semibold text-otd-text">{statusLabel}</span>
              </div>
              <div className="flex items-start gap-2">
                <Target className="w-4 h-4 text-otd-agent flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-[10px] font-semibold text-otd-muted mb-0.5">Goal</div>
                  <p className="text-xs text-otd-text leading-relaxed">{agent.goal}</p>
                </div>
              </div>
            </div>
          </section>

          {/* Capability */}
          <section>
            <h3 className="text-[11px] font-semibold text-otd-muted uppercase tracking-wider mb-3">Capability</h3>
            <div className="flex flex-wrap gap-2">
              {agent.tools.map(t => (
                <span key={t} className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs bg-otd-bg border border-otd-border text-otd-text">
                  <Wrench className="w-3 h-3 text-otd-agent" />
                  {t}
                </span>
              ))}
            </div>
          </section>

          {/* Stats */}
          <section>
            <h3 className="text-[11px] font-semibold text-otd-muted uppercase tracking-wider mb-3">
              <BarChart3 className="w-3.5 h-3.5 inline mr-1.5" />
              Statistics
            </h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "待處理", value: agent._queueCount || 0, color: "text-otd-muted" },
                { label: "處理中", value: agent._activeCount || 0, color: "text-otd-amber" },
                { label: "已完成", value: agent._doneCount || 0, color: "text-otd-green" },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center bg-otd-bg border border-otd-border rounded-lg py-3">
                  <div className={clsx("text-xl font-bold", color)}>{value}</div>
                  <div className="text-[10px] text-otd-muted mt-1">{label}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Recent Activity */}
          <section>
            <h3 className="text-[11px] font-semibold text-otd-muted uppercase tracking-wider mb-3">Recent Activity</h3>
            <div className="bg-otd-bg border border-otd-border rounded-lg p-3 max-h-48 overflow-y-auto">
              {(agent._recentEvents || []).length === 0 ? (
                <p className="text-xs text-otd-muted/50 italic text-center py-3">尚無活動記錄</p>
              ) : (
                <div className="space-y-2">
                  {(agent._recentEvents || []).slice(0, 10).map((ev, i) => (
                    <div key={i} className="flex items-center gap-2 text-[10px]">
                      <span className="text-[8px] text-otd-muted/50 flex-shrink-0 w-12">{ev.time}</span>
                      <span className="text-otd-muted truncate">{ev.detail}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
export default function AgentWorkbench() {
  const [simulating, setSimulating] = useState(null);
  const [simResults, setSimResults] = useState({});
  const [events, setEvents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("default"); // default | name | active | done

  // Demo tasks — in production these come from API
  const [agentTasks] = useState(() => {
    const demos = {
      customer: [
        { id: "c1", title: "詢單 #BH26001", desc: "ATP 查詢進行中", status: "working", lane: "active", time: "14:32", phases: ["分析客戶需求", "查詢出貨狀態", "生成 ASN 通知"], currentPhase: 2 },
        { id: "c2", title: "ASN 通知 #BH26002", desc: "Invoice 寄送完成", status: "done", lane: "done", time: "14:28" },
      ],
      atp: [
        { id: "a1", title: "交期試算 #26-007", desc: "檢查 ATP 庫存", status: "working", lane: "active", time: "14:33", phases: ["檢查可允諾庫存", "模擬產能承諾", "計算交期回覆"], currentPhase: 1 },
      ],
      po: [
        { id: "p1", title: "PO #PO26001 轉換", desc: "料號對照完成", status: "done", lane: "done", time: "14:25" },
      ],
      logistics: [
        { id: "l1", title: "報關 #E26001", desc: "等待出貨排程確認", status: "idle", lane: "queue", time: "14:20" },
      ],
      after: [
        { id: "s1", title: "案件 #CS26001", desc: "客戶回饋追蹤", status: "idle", lane: "queue", time: "14:18" },
      ],
    };
    return demos;
  });

  const addEvent = (agent, type, detail) => {
    const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setEvents(prev => [{ agent, type, detail, time: ts }, ...prev].slice(0, 30));
  };

  const handleSimulate = async (agent) => {
    setSimulating(agent.id);
    const ts = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const delay = (ms) => new Promise(r => setTimeout(r, ms));

    addEvent(agent.name, "active", "💭 開始思考…");

    try {
      // ── Phase: Thought ──
      setSimResults(prev => ({
        ...prev,
        [agent.id]: { phase: "thought", ok: true, taoPhases: { thought: { text: "分析當前狀態與任務參數…", time: ts() } } },
      }));
      await delay(800);

      setSimResults(prev => ({
        ...prev,
        [agent.id]: {
          ...prev[agent.id],
          taoPhases: {
            ...prev[agent.id].taoPhases,
            thought: { text: `Role: ${agent.role} → 準備執行 ${agent.name}`, done: true, time: ts() },
          },
        },
      }));
      addEvent(agent.name, "active", "💭 Thought 完成");
      await delay(400);

      // ── Phase: Action ──
      setSimResults(prev => ({
        ...prev,
        [agent.id]: {
          ...prev[agent.id],
          phase: "action",
          taoPhases: {
            ...prev[agent.id].taoPhases,
            action: { text: `觸發模擬…`, time: ts() },
          },
        },
      }));
      await delay(600);

      // Run actual simulation
      const { endpoint, phases, result } = await agent.simulate();

      setSimResults(prev => ({
        ...prev,
        [agent.id]: {
          ...prev[agent.id],
          taoPhases: {
            ...prev[agent.id].taoPhases,
            action: { text: `POST ${endpoint} → ${phases ? phases[0] : "執行完畢"}`, done: true, time: ts() },
          },
        },
      }));
      addEvent(agent.name, "active", "🎯 Action 完成");
      await delay(400);

      // ── Phase: Observation ──
      setSimResults(prev => ({
        ...prev,
        [agent.id]: {
          phase: "observation",
          ok: true,
          endpoint,
          taoPhases: {
            ...prev[agent.id].taoPhases,
            observation: { text: "分析執行結果…", time: ts() },
          },
        },
      }));
      await delay(600);

      const resultSummary = result
        ? typeof result === "string" ? result.slice(0, 80) : JSON.stringify(result).slice(0, 80)
        : "執行完成";

      setSimResults(prev => ({
        ...prev,
        [agent.id]: {
          ...prev[agent.id],
          endpoint,
          time: ts(),
          taoPhases: {
            ...prev[agent.id].taoPhases,
            observation: { text: resultSummary, done: true, time: ts() },
          },
        },
      }));
      addEvent(agent.name, "done", `✅ 模擬完成 → ${endpoint}`);
    } catch (e) {
      setSimResults(prev => ({ ...prev, [agent.id]: { ok: false, error: e.message, time: ts() } }));
      addEvent(agent.name, "error", `❌ 模擬失敗: ${e.message}`);
    } finally {
      setSimulating(null);
    }
  };

  // Filter & sort agents
  const filteredAgents = AGENTS
    .filter(a => !searchTerm || a.name.includes(searchTerm) || a.role.includes(searchTerm) || a.tools.some(t => t.includes(searchTerm)))
    .sort((a, b) => {
      const ta = agentTasks[a.id] || [];
      const tb = agentTasks[b.id] || [];
      if (sortBy === "active") return tb.filter(t => t.status === "working").length - ta.filter(t => t.status === "working").length;
      if (sortBy === "done") return tb.filter(t => t.status === "done").length - ta.filter(t => t.status === "done").length;
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return 0;
    });

  // Build enhanced agent data for detail panel
  const getAgentMeta = (agentId) => {
    const tasks = agentTasks[agentId] || [];
    return {
      _isActive: tasks.some(t => t.status === "working"),
      _queueCount: tasks.filter(t => t.status === "idle" || t.lane === "queue").length,
      _activeCount: tasks.filter(t => t.status === "working").length,
      _doneCount: tasks.filter(t => t.status === "done").length,
      _recentEvents: events.filter(e => e.agent === AGENTS.find(a => a.id === agentId)?.name).slice(0, 10),
    };
  };

  return (
    <div className="flex h-full">
      {/* Main Kanban area */}
      <div className="flex-1 overflow-x-auto">
        {/* Header */}
        <div className="px-6 pt-5 pb-3 border-b border-otd-border">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-otd-text flex items-center gap-2">
                <Bot className="w-5 h-5 text-otd-agent" />
                Agent 工作台
              </h1>
              <p className="text-xs text-otd-muted mt-0.5">
                五個專職 AI Agent · Linear 三欄看板 · CrewAI 思考過程
              </p>
            </div>
            <div className="flex items-center gap-3 text-[10px] text-otd-muted">
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-otd-green" /> 在線</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-otd-amber" /> 處理中</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-otd-muted" /> 待命中</span>
            </div>
          </div>

          {/* ── Filter/Sort Bar ── */}
          <div className="flex items-center gap-3 mt-3">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-otd-muted" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="搜尋 Agent 名稱 / 角色 / 工具…"
                className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-otd-border bg-otd-bg text-xs text-otd-text placeholder:text-otd-muted/50 focus:outline-none focus:border-otd-agent/50 transition-colors"
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-otd-muted hover:text-otd-text">
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-[10px]">
              <Filter className="w-3 h-3 text-otd-muted" />
              <span className="text-otd-muted">排序:</span>
              {[
                { value: "default", label: "預設" },
                { value: "active", label: "處理中" },
                { value: "done", label: "已完成" },
                { value: "name", label: "名稱" },
              ].map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => setSortBy(value)}
                  className={clsx(
                    "px-2 py-0.5 rounded transition-colors",
                    sortBy === value ? "bg-otd-agent/15 text-otd-agent font-semibold" : "text-otd-muted hover:text-otd-text"
                  )}
                >{label}</button>
              ))}
            </div>
            {searchTerm && (
              <span className="text-[10px] text-otd-muted">{filteredAgents.length} / {AGENTS.length} 個 Agent</span>
            )}
          </div>
        </div>

        {/* 5 Column Kanban */}
        <div className="p-4 flex gap-3 overflow-x-auto pb-6" style={{ minHeight: "calc(100vh - 160px)" }}>
          {filteredAgents.map(agent => (
            <div key={agent.id} onClick={() => setSelectedAgent({ ...agent, ...getAgentMeta(agent.id) })} className="cursor-pointer">
              <AgentColumn
                agent={agent}
                tasks={agentTasks[agent.id] || []}
                onSimulate={handleSimulate}
                simulating={simulating}
                simResult={simResults[agent.id]}
              />
            </div>
          ))}
          {filteredAgents.length === 0 && (
            <div className="flex-1 text-center py-12 text-xs text-otd-muted">
              <Search className="w-6 h-6 mx-auto mb-2 opacity-30" />
              無符合條件的 Agent
            </div>
          )}
        </div>
      </div>

      {/* Activity Feed sidebar */}
      <ActivityFeed events={events} />

      {/* ── Detail Panel Overlay ── */}
      {selectedAgent && (
        <DetailPanel agent={selectedAgent} onClose={() => setSelectedAgent(null)} />
      )}
    </div>
  );
}