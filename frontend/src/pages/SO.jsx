import { useState, useEffect } from "react";
import { RefreshCw, FileCheck, Calendar, User, DollarSign, Search } from "lucide-react";
import { api } from "../lib/api";

export default function SO() {
  const [sos, setSOs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState(null);
  const [lines, setLines] = useState([]);

  const load = async () => {
    try { setSOs(await api.getSOs()); } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const viewDetail = async (so) => {
    setDetail(so);
    try { setLines(await api.getSOLines(so.so_id)); } catch (e) { setLines([]); }
  };

  const filtered = sos.filter(s =>
    s.so_id?.toLowerCase().includes(search.toLowerCase()) ||
    s.customer_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="text-xl font-bold text-otd-text">銷售單 SO</h1><p className="text-sm text-otd-muted mt-0.5">{sos.length} 張銷售單</p></div>
        <div className="flex gap-2">
          <div className="relative"><Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-otd-muted" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜尋 SO..." className="bg-otd-card border border-otd-border rounded-lg pl-9 pr-3 py-1.5 text-sm text-otd-text placeholder:text-otd-muted focus:outline-none focus:ring-1 focus:ring-otd-accent" />
          </div>
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 bg-otd-card border border-otd-border rounded-lg text-sm text-otd-muted hover:bg-otd-border/50"><RefreshCw className="w-3.5 h-3.5" /> 刷新</button>
        </div>
      </div>

      <div className="bg-otd-card border border-otd-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-otd-border">
            <th className="text-left p-3 text-otd-muted font-medium">SO 編號</th>
            <th className="text-left p-3 text-otd-muted font-medium">客戶</th>
            <th className="text-left p-3 text-otd-muted font-medium">狀態</th>
            <th className="text-right p-3 text-otd-muted font-medium">總額</th>
            <th className="text-left p-3 text-otd-muted font-medium">訂單日期</th>
            <th className="text-left p-3 text-otd-muted font-medium">預計交期</th>
          </tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={6} className="p-8 text-center text-otd-muted">載入中...</td></tr> :
             filtered.length === 0 ? <tr><td colSpan={6} className="p-8 text-center text-otd-muted">無 SO 資料</td></tr> :
             filtered.map((so) => (
              <tr key={so.so_id} className="border-b border-otd-border/50 hover:bg-otd-border/20 cursor-pointer" onClick={() => viewDetail(so)}>
                <td className="p-3 font-mono text-otd-green">{so.so_id}</td>
                <td className="p-3 text-otd-text">{so.customer_name || "—"}</td>
                <td className="p-3"><span className="badge px-2 py-0.5 rounded text-[11px] font-medium bg-otd-green/15 text-otd-green">{so.status || "draft"}</span></td>
                <td className="p-3 text-right text-otd-text">{so.total_amount != null ? `$${so.total_amount.toLocaleString()}` : "—"}</td>
                <td className="p-3 text-otd-muted">{so.order_date?.split("T")[0] || "—"}</td>
                <td className="p-3 text-otd-muted">{so.estimated_delivery?.split("T")[0] || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setDetail(null)}>
          <div className="bg-otd-card border border-otd-border rounded-xl w-full max-w-2xl max-h-[80vh] overflow-y-auto m-4" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b border-otd-border flex items-center justify-between">
              <div><h2 className="text-lg font-bold text-otd-text">{detail.so_id}</h2><p className="text-sm text-otd-muted">客戶: {detail.customer_name || "—"}</p></div>
              <button onClick={() => setDetail(null)} className="p-1.5 hover:bg-otd-border/50 rounded-lg"><Search className="w-4 h-4 text-otd-muted" /></button>
            </div>
            <div className="p-5">
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div><p className="text-xs text-otd-muted mb-1">狀態</p><p className="text-sm font-medium text-otd-text">{detail.status}</p></div>
                <div><p className="text-xs text-otd-muted mb-1">總額</p><p className="text-sm font-medium text-otd-text">{detail.total_amount != null ? `$${detail.total_amount.toLocaleString()}` : "—"}</p></div>
                <div><p className="text-xs text-otd-muted mb-1">交期</p><p className="text-sm font-medium text-otd-text">{detail.estimated_delivery?.split("T")[0] || "—"}</p></div>
              </div>
              <h3 className="text-sm font-semibold text-otd-text mb-2">明細</h3>
              {lines.length === 0 ? <p className="text-otd-muted text-sm">無明細</p> :
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-otd-border">
                    <th className="text-left p-2 text-otd-muted font-medium">料號</th>
                    <th className="text-right p-2 text-otd-muted font-medium">數量</th>
                    <th className="text-right p-2 text-otd-muted font-medium">單價</th>
                    <th className="text-right p-2 text-otd-muted font-medium">小計</th>
                  </tr></thead>
                  <tbody>{lines.map((l, i) => (
                    <tr key={i} className="border-b border-otd-border/50">
                      <td className="p-2 font-mono text-otd-accent">{l.item_code}</td>
                      <td className="p-2 text-right text-otd-text">{l.quantity}</td>
                      <td className="p-2 text-right text-otd-text">{l.unit_price != null ? `$${l.unit_price}` : "—"}</td>
                      <td className="p-2 text-right text-otd-text">{l.line_total != null ? `$${l.line_total.toLocaleString()}` : "—"}</td>
                    </tr>
                  ))}</tbody>
                </table>
              }
            </div>
          </div>
        </div>
      )}
    </div>
  );
}