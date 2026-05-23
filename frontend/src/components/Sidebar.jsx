import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Users, Package, FileText,
  FileCheck, Truck, BarChart3, Boxes,
} from "lucide-react";
import ThemeToggle from "./ThemeToggle";

const nav = [
  { to: "/",          icon: LayoutDashboard, label: "儀表板" },
  { to: "/customers", icon: Users,            label: "客戶管理" },
  { to: "/items",     icon: Package,          label: "物料管理" },
  { to: "/po",        icon: FileText,         label: "採購單 PO" },
  { to: "/so",        icon: FileCheck,        label: "銷售單 SO" },
  { to: "/logistics", icon: Truck,            label: "物流追蹤" },
  { to: "/reports",   icon: BarChart3,        label: "報表匯出" },
];

export default function Sidebar() {
  const { pathname } = useLocation();

  return (
    <aside className="fixed left-0 top-0 h-screen w-[var(--c-sidebar-width)] bg-otd-card border-r border-otd-border flex flex-col z-50">
      {/* Logo */}
      <div className="p-5 border-b border-otd-border">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-otd-accent to-otd-green flex items-center justify-center">
            <Boxes className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-otd-text leading-tight">OTD ERP</h1>
            <p className="text-[10px] text-otd-muted">Order-to-Delivery</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-all",
                isActive
                  ? "bg-otd-accent/15 text-otd-accent font-semibold"
                  : "text-otd-muted hover:bg-otd-border/50 hover:text-otd-text",
              )
            }
          >
            <Icon className="w-[18px] h-[18px]" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-otd-border space-y-2">
        <ThemeToggle />
        <p className="text-[10px] text-otd-muted text-center">
          OTD ERP v1.0
        </p>
      </div>
    </aside>
  );
}

function clsx(...args) {
  return args.filter(Boolean).join(" ");
}