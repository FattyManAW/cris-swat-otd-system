import Sidebar from "./Sidebar";

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-otd-bg text-otd-text font-sans">
      <div className="flex">
        <Sidebar />
        <main className="ml-[var(--c-sidebar-width)] flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}