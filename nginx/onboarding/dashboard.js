// OTD ERP Dashboard — 完整互動式操作引導系統
const API = 'http://localhost:8040';

// ── Navigation ──
document.querySelectorAll('#mainNav a').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    document.querySelectorAll('#mainNav a').forEach(x => x.classList.remove('active'));
    a.classList.add('active');
    const sec = a.dataset.section;
    document.querySelectorAll('main > section').forEach(s => s.style.display = 'none');
    document.getElementById('section-' + sec).style.display = 'block';
    if (sec === 'dashboard') refreshDashboard();
    if (sec === 'wizard') initWizard();
    if (sec === 'api') renderApiRef('items');
    if (sec === 'data') loadData('po');
    if (sec === 'wizard') initWizard();
  });
});

// ── Quick Flow Jump ──
function jumpToWizard(step) {
  // Switch to wizard tab
  document.querySelectorAll('#mainNav a').forEach(x => x.classList.remove('active'));
  document.querySelector('#mainNav a[data-section="wizard"]').classList.add('active');
  document.querySelectorAll('main > section').forEach(s => s.style.display = 'none');
  document.getElementById('section-wizard').style.display = 'block';
  // Mark step as in-progress in quick flow
  markQfStatus(step, 'active');
  showWizardStep(step);
}

function markQfStatus(cardIndex, status) {
  const el = document.getElementById('qf-status-' + cardIndex);
  if (!el) return;
  const card = document.querySelector('.qf-card:nth-child(' + cardIndex + ')');
  if (status === 'active') {
    el.innerHTML = '<span class="qf-dot active"></span>進行中';
    if (card) card.classList.add('active');
  } else if (status === 'done') {
    el.innerHTML = '<span class="qf-dot done"></span>已完成';
    if (card) { card.classList.add('done'); card.classList.remove('active'); }
  }
}

// Track wizard step changes to update quick flow status
const origShowWizardStep = showWizardStep;
showWizardStep = function(n) {
  origShowWizardStep(n);
  // Map wizard steps to quick flow cards (1-indexed)
  // wizard: 1=查詢,2=PO,3=ATP,4=SO,5=Shipping,6=Invoice,7=Logistics
  // qf: 1=PO,2=SO,3=Shipping,4=Invoice
  const qfMap = { 2:1, 4:2, 5:3, 6:4 };
  if (qfMap[n]) markQfStatus(qfMap[n], 'active');
};

// ── L1 Quick Flow Status (real-time from API) ──
async function refreshQuickFlow() {
  try {
    const [po, so, shipping, invoice] = await Promise.all([
      fetch(API + '/api/v1/po/count').then(r=>r.json()),
      fetch(API + '/api/v1/so/count').then(r=>r.json()),
      fetch(API + '/api/v1/shipping/count').then(r=>r.json()),
      fetch(API + '/api/v1/invoice/count').then(r=>r.json()),
    ]);
    if (po.count > 0) markQfStatus(1, 'done');
    if (so.count > 0) markQfStatus(2, 'done');
    if (shipping.count > 0) markQfStatus(3, 'done');
    if (invoice.count > 0) markQfStatus(4, 'done');
  } catch(e) { /* silent */ }
}

// ── Health / Status ──
async function checkHealth() {
  try {
    const r = await fetch(API + '/healthz');
    const d = await r.json();
    document.getElementById('statusText').textContent = `API v${d.version} · ${d.db}`;
    document.getElementById('statusDot').className = 'dot green';
    document.getElementById('apiBase').textContent = `API: localhost:8040 | 版本: ${d.version} | DB: ${d.db}`;
    document.getElementById('sys_health').innerHTML = '<span style="color:var(--success)">✅ OK</span>';
    document.getElementById('sys_db').innerHTML = `<span style="color:var(--success)">✅ ${d.db}</span>`;
    document.getElementById('sys_version').textContent = d.version;
    return true;
  } catch(e) {
    document.getElementById('statusText').textContent = 'API 離線';
    document.getElementById('statusDot').className = 'dot red';
    document.getElementById('sys_health').innerHTML = '<span style="color:var(--danger)">🔴 無法連線</span>';
    return false;
  }
}

// ── Dashboard ──
async function refreshDashboard() {
  checkHealth();
  const endpoints = [
    { id: 'kpi_po', url: '/api/v1/po/count', key: 'count' },
    { id: 'kpi_so', url: '/api/v1/so/count', key: 'count' },
    { id: 'kpi_shipping', url: '/api/v1/shipping/count', key: 'count' },
    { id: 'kpi_invoice', url: '/api/v1/invoice/count', key: 'count' },
    { id: 'kpi_items', url: '/api/v1/items', key: null },
  ];
  for (const ep of endpoints) {
    try {
      const r = await fetch(API + ep.url);
      const d = await r.json();
      document.getElementById(ep.id).textContent = ep.key ? d[ep.key] : d.length;
    } catch(e) {
      document.getElementById(ep.id).textContent = '—';
    }
  }
}

// ── Wizard ──
const wizardData = {
  1: {
    title: '步驟 1：查詢可用品項',
    desc: '先確認系統中有哪些品項可以用。所有品項都可以用 GET 查詢。',
    api: '<span class="method get">GET</span> /api/v1/items',
    code: `curl http://localhost:8040/api/v1/items\n\n# 回應範例：\n[\n  {"item_code":"SKU-ELE-001","description":"Electronics Part 001","unit":"PC"},\n  ...\n]`,
  },
  2: {
    title: '步驟 2：建立採購單 (PO)',
    desc: '建立一張新採購單。需要指定 customer_id 和至少一條 line（item_code + qty）。',
    api: '<span class="method post">POST</span> /api/v1/po',
    code: `curl -X POST http://localhost:8040/api/v1/po \\\n  -H "Content-Type: application/json" \\\n  -d '{\n    "po_id": "PO-2024-001",\n    "customer_id": "CUST-001",\n    "lines": [\n      {"item_code":"SKU-ELE-001","qty":500,"unit_price":12.5}\n    ]\n  }'`,
  },
  3: {
    title: '步驟 3：ATP 可允諾量檢查',
    desc: '在接單前，先用 ATP (Available-To-Promise) 檢查庫存是否能滿足需求。回傳 on_time（可準時）/ delayed（延遲）/ insufficient（不足）。',
    api: '<span class="method post">POST</span> /api/v1/atp/check',
    code: `curl -X POST http://localhost:8040/api/v1/atp/check \\\n  -H "Content-Type: application/json" \\\n  -d '{\n    "item_code": "SKU-ELE-001",\n    "qty": 500,\n    "request_date": "2026-06-01T00:00:00"\n  }'\n\n# 回傳 on_time | delayed | insufficient`,
  },
  4: {
    title: '步驟 4：PO 轉 SO（採購轉銷售）',
    desc: '將已確認的採購單轉換為銷售單。系統自動複製所有 lines。',
    api: '<span class="method post">POST</span> /api/v1/po/{po_id}/convert',
    code: `curl -X POST "http://localhost:8040/api/v1/po/PO-2024-001/convert?so_id=SO-2024-001"\n\n# SO 會自動建立，lines 從 PO 複製`,
  },
  5: {
    title: '步驟 5：安排出貨 (Shipping)',
    desc: '建立出貨單、打包、寄出。三步操作：create → pack → ship。',
    api: '<span class="method post">POST</span> /api/v1/shipping/create',
    code: `# 1. 建立出貨單\ncurl -X POST http://localhost:8040/api/v1/shipping/create \\\n  -H "Content-Type: application/json" \\\n  -d '{"shipping_id":"SHIP-001","so_id":"SO-2024-001","pallet_count":5}'\n\n# 2. 打包\ncurl -X PATCH "http://localhost:8040/api/v1/shipping/SHIP-001/pack?pallet_count=5"\n\n# 3. 寄出\ncurl -X PATCH "http://localhost:8040/api/v1/shipping/SHIP-001/ship?tracking_no=TN123456"`,
  },
  6: {
    title: '步驟 6：開立發票 (Invoice)',
    desc: '出貨完成後開立發票。需連結到 SO 並指定金額。',
    api: '<span class="method post">POST</span> /api/v1/invoice/create',
    code: `curl -X POST http://localhost:8040/api/v1/invoice/create \\\n  -H "Content-Type: application/json" \\\n  -d '{\n    "invoice_id":"INV-001",\n    "so_id":"SO-2024-001",\n    "shipping_id":"SHIP-001",\n    "amount":6250.00\n  }'`,
  },
  7: {
    title: '步驟 7：物流追蹤 (Logistics)',
    desc: '安排物流並追蹤配送狀態。從 booked → in_transit → arrived → delivered。',
    api: '<span class="method post">POST</span> /api/v1/logistics/arrange',
    code: `# 安排物流\ncurl -X POST http://localhost:8040/api/v1/logistics/arrange \\\n  -H "Content-Type: application/json" \\\n  -d '{"tracking_no":"TN123456","shipping_id":"SHIP-001","carrier":"DHL"}'\n\n# 確認到貨\ncurl -X POST http://localhost:8040/api/v1/logistics/TN123456/arrive`,
  },
};

let currentStep = 1;
function initWizard() { showWizardStep(1); }

function showWizardStep(n) {
  currentStep = n;
  const d = wizardData[n];
  document.getElementById('wizardContent').innerHTML = `
    <h3>${d.title}</h3>
    <p>${d.desc}</p>
    <div class="api-path">${d.api}</div>
    <div class="code-block">${d.code}</div>
  `;
  document.querySelectorAll('.wizard-step-btn').forEach((b, i) => {
    b.classList.remove('active', 'done');
    if (i + 1 === n) b.classList.add('active');
    else if (i + 1 < n) b.classList.add('done');
  });
}

document.getElementById('wizardSteps').addEventListener('click', e => {
  if (e.target.classList.contains('wizard-step-btn')) {
    showWizardStep(parseInt(e.target.dataset.step));
  }
});

// ── API Reference ──
const apiModules = {
  items: [
    { m:'GET', path:'/api/v1/items', desc:'列出所有品項' },
    { m:'POST', path:'/api/v1/items', desc:'建立新品項' },
    { m:'GET', path:'/api/v1/items/{item_code}', desc:'查詢單一品項' },
    { m:'GET', path:'/api/v1/customers', desc:'列出所有客戶' },
    { m:'POST', path:'/api/v1/customers', desc:'建立新客戶' },
    { m:'GET', path:'/api/v1/customers/{customer_id}', desc:'查詢單一客戶' },
  ],
  po: [
    { m:'GET', path:'/api/v1/po', desc:'列出所有採購單' },
    { m:'POST', path:'/api/v1/po', desc:'建立採購單' },
    { m:'GET', path:'/api/v1/po/count', desc:'PO 總數統計' },
    { m:'GET', path:'/api/v1/po/{po_id}', desc:'查詢單一 PO' },
    { m:'GET', path:'/api/v1/po/{po_id}/lines', desc:'查詢 PO 明細' },
    { m:'POST', path:'/api/v1/po/{po_id}/convert', desc:'PO 轉 SO' },
  ],
  so: [
    { m:'GET', path:'/api/v1/so', desc:'列出所有銷售單' },
    { m:'POST', path:'/api/v1/so', desc:'建立銷售單' },
    { m:'GET', path:'/api/v1/so/count', desc:'SO 總數統計' },
    { m:'GET', path:'/api/v1/so/{so_id}', desc:'查詢單一 SO' },
    { m:'GET', path:'/api/v1/so/{so_id}/lines', desc:'查詢 SO 明細' },
    { m:'PATCH', path:'/api/v1/so/{so_id}', desc:'更新 SO 狀態' },
  ],
  shipping: [
    { m:'GET', path:'/api/v1/shipping', desc:'列出所有出貨單' },
    { m:'POST', path:'/api/v1/shipping/create', desc:'建立出貨單' },
    { m:'GET', path:'/api/v1/shipping/count', desc:'出貨總數統計' },
    { m:'GET', path:'/api/v1/shipping/{id}', desc:'查詢出貨單' },
    { m:'PATCH', path:'/api/v1/shipping/{id}/pack', desc:'打包' },
    { m:'PATCH', path:'/api/v1/shipping/{id}/ship', desc:'寄出' },
  ],
  invoice: [
    { m:'GET', path:'/api/v1/invoice', desc:'列出所有發票' },
    { m:'POST', path:'/api/v1/invoice/create', desc:'開立發票' },
    { m:'GET', path:'/api/v1/invoice/count', desc:'發票總數統計' },
    { m:'GET', path:'/api/v1/invoice/{id}', desc:'查詢發票' },
  ],
  atp: [
    { m:'POST', path:'/api/v1/atp/check', desc:'ATP 可允諾量檢查' },
    { m:'POST', path:'/api/v1/ctp/check', desc:'CTP 產能承諾檢查' },
  ],
  logistics: [
    { m:'GET', path:'/api/v1/logistics', desc:'列出所有物流' },
    { m:'POST', path:'/api/v1/logistics/arrange', desc:'安排物流' },
    { m:'GET', path:'/api/v1/logistics/count', desc:'物流總數統計' },
    { m:'GET', path:'/api/v1/logistics/{tracking_no}', desc:'查詢物流' },
    { m:'POST', path:'/api/v1/logistics/{tracking_no}/arrive', desc:'確認到貨' },
  ],
};

function renderApiRef(module) {
  const items = apiModules[module] || [];
  document.getElementById('apiGrid').innerHTML = items.map(i => `
    <div class="api-item">
      <span class="m" style="color:${i.m==='GET'?'var(--success)':i.m==='POST'?'var(--accent)':'var(--warning)'}">${i.m}</span>
      <span class="path">${i.path}</span>
      <span class="desc">${i.desc}</span>
    </div>
  `).join('');
}

document.getElementById('apiTabs').addEventListener('click', e => {
  if (e.target.classList.contains('section-tab')) {
    document.querySelectorAll('#apiTabs .section-tab').forEach(t => t.classList.remove('active'));
    e.target.classList.add('active');
    renderApiRef(e.target.dataset.module);
  }
});

// ── Data Overview ──
async function loadData(type) {
  const map = {
    'po': { url: '/api/v1/po', cols: ['po_id','customer_id','po_date','status'], badge: 'status' },
    'so': { url: '/api/v1/so', cols: ['so_id','customer_id','so_date','status'], badge: 'status' },
    'shipping': { url: '/api/v1/shipping', cols: ['shipping_id','so_id','status','tracking_no'], badge: 'status' },
    'invoice': { url: '/api/v1/invoice', cols: ['invoice_id','so_id','amount','status'], badge: 'status' },
    'items': { url: '/api/v1/items', cols: ['item_code','description','unit','category','lead_time_days'], badge: null },
  };
  const cfg = map[type];
  if (!cfg) return;
  const target = document.getElementById('dataTable');
  target.innerHTML = '<div class="loading">載入中…</div>';
  try {
    const r = await fetch(API + cfg.url);
    const data = await r.json();
    const items = Array.isArray(data) ? data : [];
    let html = `<table class="data-table"><tr>${cfg.cols.map(c => `<th>${c}</th>`).join('')}</tr>`;
    for (const row of items.slice(0, 20)) {
      html += '<tr>';
      for (const col of cfg.cols) {
        let val = row[col] ?? '—';
        if (typeof val === 'number') val = val.toLocaleString();
        if (col === 'po_date' || col === 'so_date') val = val ? new Date(val).toLocaleDateString('zh-TW') : '—';
        if (cfg.badge && col === cfg.badge) {
          val = `<span class="badge ${val}">${val}</span>`;
        }
        html += `<td>${val}</td>`;
      }
      html += '</tr>';
    }
    html += '</table>';
    if (items.length > 20) html += `<p style="color:var(--text-muted);margin-top:8px;font-size:12px">顯示前 20 筆，共 ${items.length} 筆</p>`;
    target.innerHTML = html;
  } catch(e) {
    target.innerHTML = `<div class="error">載入失敗：${e.message}</div>`;
  }
}

document.getElementById('dataTabs').addEventListener('click', e => {
  if (e.target.classList.contains('section-tab')) {
    document.querySelectorAll('#dataTabs .section-tab').forEach(t => t.classList.remove('active'));
    e.target.classList.add('active');
    loadData(e.target.dataset.module.replace('-data', ''));
  }
});

// ── Init ──
checkHealth();
refreshDashboard();
refreshQuickFlow();