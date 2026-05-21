import { useState, useEffect } from "react";
import { Plus, RefreshCw, User, Mail, Phone, Search, X } from "lucide-react";
import { api } from "../lib/api";

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "", company: "" });
  const [search, setSearch] = useState("");

  const load = async () => {
    try { setCustomers(await api.getCustomers()); } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.createCustomer(form);
      setForm({ name: "", email: "", phone: "", company: "" });
      setShowForm(false);
      load();
    } catch (e) { console.error(e); }
  };

  const filtered = customers.filter(c =>
    c.name?.toLowerCase().includes(search.toLowerCase()) ||
    c.company?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-otd-text">客戶管理</h1>
          <p className="text-sm text-otd-muted mt-0.5">{customers.length} 位客戶</p>
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-otd-muted" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="搜尋客戶..."
              className="bg-otd-card border border-otd-border rounded-lg pl-9 pr-3 py-1.5 text-sm text-otd-text placeholder:text-otd-muted focus:outline-none focus:ring-1 focus:ring-otd-accent"
            />
          </div>
          <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1.5 px-3 py-1.5 bg-otd-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition">
            <Plus className="w-4 h-4" /> 新增
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-otd-card border border-otd-border rounded-xl p-4 mb-4 grid grid-cols-2 md:grid-cols-5 gap-3">
          <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="客戶名稱 *" required className="bg-otd-bg border border-otd-border rounded-lg px-3 py-2 text-sm text-otd-text focus:outline-none focus:ring-1 focus:ring-otd-accent" />
          <input value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} placeholder="公司名稱" className="bg-otd-bg border border-otd-border rounded-lg px-3 py-2 text-sm text-otd-text focus:outline-none focus:ring-1 focus:ring-otd-accent" />
          <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="Email" type="email" className="bg-otd-bg border border-otd-border rounded-lg px-3 py-2 text-sm text-otd-text focus:outline-none focus:ring-1 focus:ring-otd-accent" />
          <input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="電話" className="bg-otd-bg border border-otd-border rounded-lg px-3 py-2 text-sm text-otd-text focus:outline-none focus:ring-1 focus:ring-otd-accent" />
          <div className="flex gap-2">
            <button type="submit" className="flex-1 px-3 py-2 bg-otd-accent text-white rounded-lg text-sm font-medium hover:opacity-90">儲存</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-2 bg-otd-border text-otd-muted rounded-lg text-sm hover:bg-otd-border/70">取消</button>
          </div>
        </form>
      )}

      <div className="bg-otd-card border border-otd-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-otd-border">
            <th className="text-left p-3 text-otd-muted font-medium">客戶名稱</th>
            <th className="text-left p-3 text-otd-muted font-medium">公司</th>
            <th className="text-left p-3 text-otd-muted font-medium">Email</th>
            <th className="text-left p-3 text-otd-muted font-medium">電話</th>
            <th className="text-left p-3 text-otd-muted font-medium">ID</th>
          </tr></thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="p-8 text-center text-otd-muted">載入中...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={5} className="p-8 text-center text-otd-muted">無客戶資料</td></tr>
            ) : filtered.map((c) => (
              <tr key={c.customer_id} className="border-b border-otd-border/50 hover:bg-otd-border/20">
                <td className="p-3 text-otd-text font-medium">{c.name}</td>
                <td className="p-3 text-otd-muted">{c.company || "—"}</td>
                <td className="p-3 text-otd-muted">{c.email || "—"}</td>
                <td className="p-3 text-otd-muted">{c.phone || "—"}</td>
                <td className="p-3 text-otd-muted font-mono text-[11px]">{c.customer_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}