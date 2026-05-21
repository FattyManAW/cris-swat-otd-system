import { useState, useEffect } from "react";
import { RefreshCw, Truck, MapPin, CheckCircle2, Clock, Package, Plus } from "lucide-react";
import { api } from "../lib/api";

export default function Logistics() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => { try { setLogs(await api.getLogistics()); } catch (e) { console.error(e); } finally { setLoading(false); } };
  useEffect(() => { load(); }, []);

  const statusBadge = (status) => {
    const map = { in_transit: "bg-otd-accent/15 text-otd-accent", delivered: "bg-otd-green/15 text-otd-green", pending: "bg-otd-amber/15 text-otd-amber", cancelled: "bg-otd-red/15 text-otd-red" };
    return <span className={`badge px-2 py-0.5 rounded text-[11px] font-medium ${map[status] || "bg-otd-muted/15 text-otd-muted"}`}>{status || "pending"}</span>;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="text-xl font-bold text-otd-text">物流追蹤</h1><p className="text-sm text-otd-muted mt-0.5">{logs.length} 筆物流記錄</p></div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 bg-otd-card border border-otd-border rounded-lg text-sm text-otd-muted hover:bg-otd-border/50"><RefreshCw className="w-3.5 h-3.5" /> 刷新</button>
      </div>

      <div className="bg-otd-card border border-otd-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-otd-border">
            <th className="text-left p-3 text-otd-muted font-medium">追蹤號</th>
            <th className="text-left p-3 text-otd-muted font-medium">SO</th>
            <th className="text-left p-3 text-otd-muted font-medium">物流商</th>
            <th className="text-left p-3 text-otd-muted font-medium">狀態</th>
            <th className="text-left p-3 text-otd-muted font-medium">出貨日</th>
            <th className="text-left p-3 text-otd-muted font-medium">預計到貨</th>
          </tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={6} className="p-8 text-center text-otd-muted">載入中...</td></tr> :
             logs.length === 0 ? <tr><td colSpan={6} className="p-8 text-center text-otd-muted">無物流資料</td></tr> :
             logs.map((l) => (
              <tr key={l.tracking_no} className="border-b border-otd-border/50 hover:bg-otd-border/20">
                <td className="p-3 font-mono text-otd-accent">{l.tracking_no}</td>
                <td className="p-3 text-otd-text">{l.so_id || "—"}</td>
                <td className="p-3 text-otd-text">{l.carrier || "—"}</td>
                <td className="p-3">{statusBadge(l.status)}</td>
                <td className="p-3 text-otd-muted">{l.ship_date?.split("T")[0] || "—"}</td>
                <td className="p-3 text-otd-muted">{l.estimated_arrival?.split("T")[0] || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}