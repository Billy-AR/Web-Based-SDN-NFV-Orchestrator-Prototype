// ── SDN + NFV Orchestrator — main.js ──

// ── Clock ──
function updateClock() {
    document.getElementById('clock').innerText = new Date().toLocaleTimeString('en-GB');
}
setInterval(updateClock, 1000);
updateClock();

// ── Log ──
function addLog(message, type = 'default') {
    const container = document.getElementById('log-container');
    const time = new Date().toLocaleTimeString('en-GB');
    const cls = {
        success: 'log-text-success',
        error:   'log-text-error',
        info:    'log-text-info',
        default: 'log-text-default'
    }[type] || 'log-text-default';

    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `<span class="log-time">[${time}]</span><span class="${cls}"> ${message}</span>`;
    container.prepend(entry);
}

// ── Loading State ──
function setLoading(loading) {
    document.querySelectorAll('.control-btn').forEach(btn => {
        btn.disabled = loading;
        btn.style.opacity = loading ? '0.5' : '1';
    });
}

function setHint(msg) {
    document.getElementById('status-hint').innerText = msg;
}

// ── Button Actions ──
document.getElementById('btn-start-topo').addEventListener('click', async () => {
    setLoading(true);
    setHint('⏳ Starting Mininet topology, please wait...');
    addLog('Requesting topology start...', 'info');
    const res  = await fetch('/api/topology/start', { method: 'POST' });
    const data = await res.json();
    const ok   = data.status === 'success';
    addLog(data.message, ok ? 'success' : 'error');
    setHint(ok ? '✅ Topology running. You can now Deploy Firewall.' : `❌ Error: ${data.message}`);
    await fetchStats();
    setLoading(false);
});

document.getElementById('btn-stop-topo').addEventListener('click', async () => {
    setLoading(true);
    setHint('⏳ Stopping topology...');
    addLog('Requesting topology stop...', 'info');
    const res  = await fetch('/api/topology/stop', { method: 'POST' });
    const data = await res.json();
    addLog(data.message, data.status === 'success' ? 'success' : 'error');
    setHint('Topology stopped. Press Start Topology to restart.');
    await fetchStats();
    setLoading(false);
});

document.getElementById('btn-deploy-fw').addEventListener('click', async () => {
    setLoading(true);
    setHint('⏳ Deploying Firewall VNF container...');
    addLog('Deploying Firewall VNF...', 'info');
    const res  = await fetch('/api/vnf/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'fw', role: 'firewall' })
    });
    const data = await res.json();
    const ok   = data.status === 'success';
    addLog(data.message, ok ? 'success' : 'error');
    setHint(ok ? '✅ Firewall deployed. Install redirect flow to chain traffic.' : `❌ ${data.message}`);
    await fetchStats();
    setLoading(false);
});

document.getElementById('btn-install-flow').addEventListener('click', async () => {
    setLoading(true);
    setHint('⏳ Injecting OpenFlow rules into switches...');
    addLog('Installing redirect flow rules via Ryu REST API...', 'info');
    const res  = await fetch('/api/flow/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'redirect_firewall' })
    });
    const data = await res.json();
    const ok   = data.status === 'success';
    addLog(data.message, ok ? 'success' : 'error');
    setHint(ok ? '✅ Service chaining active. Traffic now routed through Firewall VNF.' : `❌ ${data.message}`);
    setLoading(false);
    await fetchStats();
});

// ── Stats Polling ──
async function fetchStats() {
    try {
        const res  = await fetch('/api/stats');
        const data = await res.json();
        updateUI(data);
    } catch (e) {
        console.warn('Stats fetch failed:', e);
    }
}

function updateUI(data) {
    // ── KPI Boxes ──
    const running = data.topology.status === 'Running';
    document.getElementById('kpi-topo-status').innerText = running ? 'ON' : 'OFF';
    document.getElementById('kpi-topo-status').style.color = running ? 'var(--green)' : 'var(--red)';
    document.getElementById('kpi-topo-detail').innerText = running
        ? `Hosts: ${data.topology.details?.Hosts || 3}, Switches: ${data.topology.details?.Switches || 2}`
        : 'Stopped';

    const ctrlActive = data.sdn_controller.active;
    document.getElementById('kpi-ctrl-value').innerText = ctrlActive
        ? `${data.sdn_controller.switches_connected} SW`
        : '—';
    document.getElementById('kpi-ctrl-sub').innerText = ctrlActive
        ? `${data.sdn_controller.switches_connected} switch(es) connected`
        : 'Controller offline';

    const totalFlows = data.sdn_controller.total_flows;
    document.getElementById('kpi-flows').innerText = totalFlows;
    const runningVnfs = data.vnfs.filter(v => v.status === 'running').length;
    document.getElementById('kpi-vnfs').innerText = runningVnfs;

    // ── Topology Badge ──
    const badgeTopo = document.getElementById('badge-topo');
    const dotTopo   = document.getElementById('dot-topo');
    const badgeText = document.getElementById('badge-topo-text');
    if (running) {
        badgeTopo.className = 'badge-pill badge-running';
        dotTopo.className = 'pulse pulse-green';
        badgeText.innerText = 'Running';
    } else {
        badgeTopo.className = 'badge-pill badge-stopped';
        dotTopo.className = 'pulse pulse-red';
        badgeText.innerText = 'Stopped';
    }

    // ── Topology Nodes ──
    ['node-h1','node-s1','node-s2','node-h2'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('active', running);
    });
    ['link-1','link-2','link-3'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('active', running);
    });
    
    // VNF Node and Line
    const fwRunning = runningVnfs > 0;
    const fwNode = document.getElementById('node-fw');
    if (fwNode) fwNode.classList.toggle('active', fwRunning);
    
    const vnfLine = document.getElementById('vnf-line');
    if (vnfLine) vnfLine.classList.toggle('active', fwRunning);

    // Flow path indicator
    const flowInd = document.getElementById('flow-path-indicator');
    if (flowInd) flowInd.style.display = (running && totalFlows > 0) ? 'block' : 'none';

    // ── Controller Card ──
    const ctrlBadge = document.getElementById('ctrl-live-badge');
    if (ctrlActive) {
        ctrlBadge.className = 'badge-pill badge-running';
        ctrlBadge.innerHTML = '<span class="pulse pulse-green"></span> Online';
    } else {
        ctrlBadge.className = 'badge-pill badge-stopped';
        ctrlBadge.innerHTML = '<span class="pulse pulse-red"></span> Offline';
    }
    document.getElementById('ctrl-switches').innerText = ctrlActive
        ? `${data.sdn_controller.switches_connected} connected` : '0 connected';
    document.getElementById('ctrl-flows').innerText = totalFlows;

    // ── VNF List ──
    const vnfList   = document.getElementById('vnf-list');
    const vnfBadge  = document.getElementById('vnf-badge');
    if (runningVnfs > 0) {
        vnfBadge.className = 'badge-pill badge-running';
        vnfBadge.innerHTML = `<span class="pulse pulse-green"></span> ${runningVnfs} Active`;
        vnfList.innerHTML = data.vnfs
            .filter(v => v.status === 'running')
            .map(v => `
            <div class="info-row">
                <div>
                    <div style="font-size:.8rem; font-weight:600;">🐳 ${v.name || v.id}</div>
                    <div style="font-size:.68rem; color:var(--muted); font-family:'JetBrains Mono',monospace;">ID: ${v.short_id || v.id}</div>
                </div>
                <span class="badge-pill badge-running" style="font-size:.62rem;">Running</span>
            </div>`).join('');
    } else {
        vnfBadge.className = 'badge-pill badge-stopped';
        vnfBadge.innerHTML = '<span class="pulse pulse-red"></span> None';
        vnfList.innerHTML = '<div style="color:var(--muted);font-size:.8rem;text-align:center;padding:.5rem 0;">No containers deployed yet.</div>';
    }

    // ── System Resources ──
    if (data.system) {
        const cpu = data.system.cpu_percent;
        const ram = data.system.memory_percent;

        document.getElementById('cpu-bar').style.width = cpu + '%';
        document.getElementById('cpu-bar').style.background = cpu > 80 ? 'var(--red)' : cpu > 50 ? 'var(--yellow)' : 'var(--accent)';
        document.getElementById('cpu-text').innerText = cpu.toFixed(1) + '%';

        document.getElementById('ram-bar').style.width = ram + '%';
        document.getElementById('ram-bar').style.background = ram > 85 ? 'var(--red)' : 'var(--yellow)';
        document.getElementById('ram-text').innerText = `${ram.toFixed(1)}%  (${data.system.memory_used_mb} MB / ${data.system.memory_total_mb} MB)`;
    }
}

// ── OpenFlow Table Modal ──
async function fetchFlowDetails() {
    const container = document.getElementById('flow-table-container');
    container.innerHTML = '<div class="text-center py-5 text-muted">Fetching rules from Ryu controller…</div>';
    try {
        const res  = await fetch('/api/flow/details');
        const data = await res.json();

        if (Object.keys(data).length === 0) {
            container.innerHTML = '<div class="alert alert-warning m-3">No controller connected or no switches found.</div>';
            return;
        }

        let html = '';
        for (const [switchName, flows] of Object.entries(data)) {
            html += `<div class="d-flex align-items-center justify-content-between px-1 mb-2">
                <h6 class="m-0" style="color:var(--cyan);">${switchName}</h6>
                <span class="badge-pill badge-info">${flows.length} rules</span>
            </div>`;

            if (flows.length === 0) {
                html += `<p class="text-muted small px-1 mb-3">No flows installed on this switch.</p>`;
                continue;
            }

            html += `<div class="table-responsive mb-4"><table class="table table-sm" style="font-size:.78rem; color:var(--text);">
                <thead style="color:var(--muted); border-color:var(--border);">
                    <tr>
                        <th style="font-weight:500;">Priority</th>
                        <th style="font-weight:500;">Match Conditions</th>
                        <th style="font-weight:500;">Actions</th>
                        <th style="font-weight:500;">Packets</th>
                        <th style="font-weight:500;">Bytes</th>
                    </tr>
                </thead>
                <tbody style="border-color:var(--border);">`;

            flows.sort((a, b) => b.priority - a.priority).forEach(flow => {
                const matchStr = Object.entries(flow.match).map(([k, v]) => `<span style="color:var(--yellow);">${k}</span>=<span style="color:#f8fafc;">${v}</span>`).join(' · ') || '<em>ANY</em>';
                const actionStr = (flow.actions || []).join(', ') || '<span style="color:var(--red);">DROP</span>';
                html += `<tr style="border-color:var(--border);">
                    <td><span class="badge-pill badge-info" style="font-size:.65rem;">${flow.priority}</span></td>
                    <td style="font-family:'JetBrains Mono',monospace; font-size:.72rem; max-width: 280px; word-break:break-all;">${matchStr}</td>
                    <td style="color:var(--green); font-family:'JetBrains Mono',monospace; font-size:.72rem;">${actionStr}</td>
                    <td>${flow.packet_count ?? '—'}</td>
                    <td>${flow.byte_count ?? '—'}</td>
                </tr>`;
            });
            html += `</tbody></table></div>`;
        }
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<div class="alert alert-danger m-3">Error fetching flows: ${e.message}</div>`;
    }
}

document.getElementById('flowModal').addEventListener('show.bs.modal', fetchFlowDetails);
document.getElementById('btn-refresh-flows').addEventListener('click', fetchFlowDetails);

// ── Init ──
setInterval(fetchStats, 3000);
fetchStats();
addLog('Dashboard initialized. Polling every 3 seconds.', 'info');
