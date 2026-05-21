import { useState, useEffect } from "react";
import { Search, Package, RefreshCw } from "lucide-react";
import { api } from "../lib/api";

export default function Items() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const load = async () => {
    try { setItems(await api.getItems()); } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const filtered = items.filter(i =>
    i.item_code?.toLowerCase().includes(search.toLowerCase()) ||
    i.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-otd-text">物料管理</h1>
          <p className="text-sm text-otd-muted mt-0.5">{items.length} 項物料</p>
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-otd-muted" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜尋料號..." className="bg-otd-card border border-otd-border rounded-lg pl-9 pr-3 py-1.5 text-sm text-otd-text placeholder:text-otd-muted focus:outline-none focus:ring-1 focus:ring-otd-accent" />
          </div>
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 bg-otd-card border border-otd-border rounded-lg text-sm text-otd-muted hover:bg-otd-border/50"><RefreshCw className="w-3.5 h-3.5" /> 刷新</button>
        </div>
      </div>

      <div className="bg-otd-card border border-otd-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-otd-border">
            <th className="text-left p-3 text-otd-muted font-medium">料號</th>
            <th className="text-left p-3 text-otd-muted font-medium">描述</th>
            <th className="text-right p-3 text-otd-muted font-medium">單價</th>
            <th className="text-right p-3 text-otd-muted font-medium">單位</th>
            <th className="text-left p-3 text-otd-muted font-medium">供應商</th>
          </tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={5} className="p-8 text-center text-otd-muted">載入中...</td></tr> :
             filtered.length === 0 ? <tr><td colSpan={5} className="p-8 text-center text-otd-muted">無物料資料</td></tr> :
             filtered.map((item) => (
              <tr key={item.item_code} className="border-b border-otd-border/50 hover:bg-otd-border/20">
                <td className="p-3 font-mono text-otd-accent">{item.item_code}</td>
                <td className="p-3 text-otd-text">{item.description || "—"}</td>
                <td className="p-3 text-right text-otd-text">{item.unit_price != null ? `$${item.unit_price}` : "—"}</td>
                <td className="p-3 text-right text-otd-muted">{item.unit || "—"}</td>
                <td className="p-3 text-otd-muted">{item.supplier || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}