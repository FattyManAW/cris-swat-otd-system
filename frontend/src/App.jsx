import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Customers from "./pages/Customers";
import Items from "./pages/Items";
import PO from "./pages/PO";
import SO from "./pages/SO";
import Logistics from "./pages/Logistics";
import Reports from "./pages/Reports";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/items" element={<Items />} />
        <Route path="/po" element={<PO />} />
        <Route path="/so" element={<SO />} />
        <Route path="/logistics" element={<Logistics />} />
        <Route path="/reports" element={<Reports />} />
      </Routes>
    </Layout>
  );
}