import { useState, useCallback } from "react";
import { GripVertical, Clock, User, Tag, ArrowRight, Circle, CheckCircle2, AlertCircle } from "lucide-react";

const STATUS_LABELS = {
  todo: "待辦",
  in_progress: "進行中",
  done: "已完成",
};

const STATUS_ICONS = {
  todo: Circle,
  in_progress: Clock,
  done: CheckCircle2,
};

const STATUS_CLASSES = {
  todo: "border-l-amber-400 bg-amber-50/30",
  in_progress: "border-l-blue-400 bg-blue-50/30",
  done: "border-l-emerald-400 bg-emerald-50/30",
};

const INITIAL_TASKS = [
  { id: "t1", title: "客服：處理詢單 #25-102", agent: "客服溝通樞紐", status: "todo", createdAt: "10:00", priority: "high" },
  { id: "t2", title: "ATP：交期試算 #25-103", agent: "ATP/CTP 交期試算", status: "todo", createdAt: "10:15", priority: "medium" },
  { id: "t3", title: "轉單：PO→SO #25-104", agent: "PO→SO 訂單轉換", status: "todo", createdAt: "10:30", priority: "high" },
  { id: "t4", title: "物流：報關文件生成", agent: "物流處理專家", status: "in_progress", createdAt: "09:45", priority: "medium", startedAt: "10:00" },
  { id: "t5", title: "售後：退換貨處理 #25-098", agent: "售後服務專家", status: "in_progress", createdAt: "09:30", priority: "low", startedAt: "09:45" },
  { id: "t6", title: "客服：ASN 預出貨通知", agent: "客服溝通樞紐", status: "done", createdAt: "08:00", priority: "high", startedAt: "08:15", completedAt: "09:00" },
  { id: "t7", title: "ATP：庫存不足警示", agent: "ATP/CTP 交期試算", status: "done", createdAt: "07:30", priority: "medium", startedAt: "08:00", completedAt: "08:45" },
];

const PRIORITY_INDICATOR = {
  high: { color: "bg-otd-red", label: "高" },
  medium: { color: "bg-otd-amber", label: "中" },
  low: { color: "bg-otd-muted", label: "低" },
};

export default function KanbanBoard() {
  const [tasks, setTasks] = useState(INITIAL_TASKS);
  const [dragTask, setDragTask] = useState(null);

  const handleDragStart = useCallback((e, task) => {
    setDragTask(task);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", task.id);
  }, []);

  const handleDrop = useCallback((e, status) => {
    e.preventDefault();
    if (!dragTask) return;
    const now = new Date().toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit" });
    setTasks(prev =>
      prev.map(t => {
        if (t.id !== dragTask.id) return t;
        const update = { ...t, status };
        if (status === "in_progress" && !t.startedAt) update.startedAt = now;
        if (status === "done") update.completedAt = now;
        return update;
      })
    );
    setDragTask(null);
  }, [dragTask]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const getColumnTasks = (status) => tasks.filter(t => t.status === status);

  return (
    <div className="bg-otd-card border border-otd-border rounded-xl p-5">
      <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2">
        <GripVertical className="w-4 h-4 text-otd-agent" />Agent 任務看板
      </h2>
      <div className="grid grid-cols-3 gap-3">
        {Object.entries(STATUS_LABELS).map(([status, label]) => {
          const Icon = STATUS_ICONS[status];
          const colTasks = getColumnTasks(status);
          return (
            <div
              key={status}
              className="bg-otd-surface rounded-lg border border-otd-border min-h-[200px] flex flex-col"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, status)}
            >
              {/* Column header */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-otd-border">
                <div className="flex items-center gap-1.5">
                  <Icon className="w-3.5 h-3.5 text-otd-agent" />
                  <span className="text-xs font-semibold text-otd-text">{label}</span>
                </div>
                <span className="text-[10px] text-otd-muted bg-otd-bg px-1.5 py-0.5 rounded-full">
                  {colTasks.length}
                </span>
              </div>
              {/* Cards */}
              <div className="flex-1 p-2 space-y-2 overflow-y-auto">
                {colTasks.map(task => {
                  const PriorityBadge = PRIORITY_INDICATOR[task.priority];
                  return (
                    <div
                      key={task.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, task)}
                      className={`border-l-2 rounded-lg p-2.5 cursor-grab active:cursor-grabbing transition-shadow hover:shadow-sm bg-white ${STATUS_CLASSES[task.status]}`}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <span className="text-xs font-medium text-otd-text leading-snug">{task.title}</span>
                        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-0.5 ${PriorityBadge.color}`}
                             title={PriorityBadge.label} />
                      </div>
                      <div className="flex items-center gap-2 mt-2 text-[10px] text-otd-muted">
                        <div className="flex items-center gap-0.5">
                          <User className="w-2.5 h-2.5" />
                          <span>{task.agent.split(" ")[0]}</span>
                        </div>
                        <div className="flex items-center gap-0.5">
                          <Clock className="w-2.5 h-2.5" />
                          <span>{task.createdAt}</span>
                        </div>
                      </div>
                      {/* Lifecycle timestamps */}
                      {task.startedAt && (
                        <div className="mt-1 text-[10px] text-otd-muted/70 flex items-center gap-1">
                          <ArrowRight className="w-2.5 h-2.5" />
                          開始 {task.startedAt}
                          {task.completedAt && <> · 完成 {task.completedAt}</>}
                        </div>
                      )}
                    </div>
                  );
                })}
                {colTasks.length === 0 && (
                  <div className="text-[10px] text-otd-muted/50 text-center py-6">
                    拖曳任務至此
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