/** OTD API client — fetch + error handling */
const API_BASE = window.location.hostname === "localhost" ? "http://localhost:8004" : "";

async function req(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  // ── Dashboard ──
  getDashboard: () => req("/api/v1/po/count").then(() => Promise.all([
    req("/api/v1/po/count"),
    req("/api/v1/so/count"),
    req("/api/v1/invoice/count"),
    req("/api/v1/shipping/count"),
    req("/api/v1/logistics/count"),
  ])),

  // ── Customers ──
  getCustomers: () => req("/api/v1/customers"),
  getCustomer: (id) => req(`/api/v1/customers/${id}`),

  // ── Items ──
  getItems: () => req("/api/v1/items"),
  getItem: (code) => req(`/api/v1/items/${code}`),

  // ── PO ──
  getPOs: () => req("/api/v1/po"),
  getPO: (id) => req(`/api/v1/po/${id}`),
  getPOLines: (id) => req(`/api/v1/po/${id}/lines`),
  convertPO: (id) => req(`/api/v1/po/${id}/convert`, { method: "POST" }),
  countPO: () => req("/api/v1/po/count"),

  // ── SO ──
  getSOs: () => req("/api/v1/so"),
  getSO: (id) => req(`/api/v1/so/${id}`),
  getSOLines: (id) => req(`/api/v1/so/${id}/lines`),
  countSO: () => req("/api/v1/so/count"),

  // ── Logistics ──
  getLogistics: () => req("/api/v1/logistics"),
  getLogistic: (trackingNo) => req(`/api/v1/logistics/${trackingNo}`),
  arrangeLogistics: (data) => req("/api/v1/logistics/arrange", { method: "POST", body: JSON.stringify(data) }),
  markArrived: (trackingNo) => req(`/api/v1/logistics/${trackingNo}/arrive`, { method: "POST" }),
  countLogistics: () => req("/api/v1/logistics/count"),

  // ── Shipping ──
  getShipping: () => req("/api/v1/shipping"),
  getShippingById: (id) => req(`/api/v1/shipping/${id}`),
  createShipping: (data) => req("/api/v1/shipping/create", { method: "POST", body: JSON.stringify(data) }),
  packShipping: (id) => req(`/api/v1/shipping/${id}/pack`, { method: "POST" }),
  shipShipping: (id) => req(`/api/v1/shipping/${id}/ship`, { method: "POST" }),
  countShipping: () => req("/api/v1/shipping/count"),

  // ── Invoice ──
  getInvoices: () => req("/api/v1/invoice"),
  getInvoice: (id) => req(`/api/v1/invoice/${id}`),
  createInvoice: (data) => req("/api/v1/invoice/create", { method: "POST", body: JSON.stringify(data) }),
  countInvoice: () => req("/api/v1/invoice/count"),

  // ── ATP / CTP ──
  checkATP: (itemCode, qty) => req(`/api/v1/atp/check?item_code=${encodeURIComponent(itemCode)}&quantity=${qty}`),
  checkCTP: (itemCode, qty, days) => req(`/api/v1/ctp/check?item_code=${encodeURIComponent(itemCode)}&quantity=${qty}&days=${days}`),
};