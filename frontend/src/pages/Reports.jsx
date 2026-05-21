import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { RefreshCw, BarChart3, FileText } from "lucide-react";
import { api } from "../lib/api";

const COLORS = ["#4b8cff", "#3cc97e", "#f0b028", "#f44b55", "#a78bfa", "#38bdf8"];

export default function Reports() {
  const [soData, setSoData] = useState([]);
  const [invData, setInvData] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [sos, invs] = await Promise.all([api.getSOs(), api.getInvoices()]);
      // Group SOs by month
      const byMonth = {};
      sos.forEach(s => {
        const m = (s.order_date || "").slice(0, 7);
        byMonth[m] = (byMonth[m] || 0) + 1;
      });
      setSoData(Object.entries(byMonth).map(([month, count]) => ({ month, count })));

      // Invoice status distribution
      const byStatus = {};
      invs.forEach(i => {
        const s = i.status || "unknown";
        byStatus[s] = (byStatus[s] || 0) + 1;
      });
      setInvData(Object.entries(byStatus).map(([status, count]) => ({ name: status, value: count })));
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="text-xl font-bold text-otd-text">報表匯出</h1><p className="text-sm text-otd-muted mt-0.5">PO / SO / Invoice 分析</p></div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 bg-otd-card border border-otd-border rounded-lg text-sm text-otd-muted hover:bg-otd-border/50"><RefreshCw className="w-3.5 h-3.5" /> 刷新</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-otd-card border border-otd-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2"><FileText className="w-4 h-4 text-otd-accent" />SO 月度趨勢</h2>
          {loading ? <div className="h-64 flex items-center justify-center text-otd-muted">載入中...</div> :
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={soData}>
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#747a8c" }} />
                <YAxis tick={{ fontSize: 11, fill: "#747a8c" }} />
                <Tooltip contentStyle={{ background: "#181b23", border: "1px solid #2e3140", borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" fill="#4b8cff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          }
        </div>

        <div className="bg-otd-card border border-otd-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-otd-text mb-4 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-otd-green" />Invoice 狀態分佈</h2>
          {loading ? <div className="h-64 flex items-center justify-center text-otd-muted">載入中...</div> :
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={invData} cx="50%" cy="50%" outerRadius={90} dataKey="value" label={({ name, value }) => `${name} (${value})`}>
                  {invData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Legend />
                <Tooltip contentStyle={{ background: "#181b23", border: "1px solid #2e3140", borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          }
        </div>
      </div>
    </div>
  );
}