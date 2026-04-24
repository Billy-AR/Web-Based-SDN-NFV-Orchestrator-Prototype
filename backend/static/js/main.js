let lastServerEventId = 0;

function byId(id) {
    return document.getElementById(id);
}

function setText(id, value) {
    const el = byId(id);
    if (el) el.innerText = value;
    return el;
}

function setHtml(id, value) {
    const el = byId(id);
    if (el) el.innerHTML = value;
    return el;
}

function bindIfPresent(id, eventName, handler) {
    const el = byId(id);
    if (el) el.addEventListener(eventName, handler);
}

function initTooltips() {
    if (typeof bootstrap === 'undefined') return;
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        bootstrap.Tooltip.getOrCreateInstance(el);
    });
}

function updateClock() {
    const clock = byId('clock');
    if (clock) clock.innerText = new Date().toLocaleTimeString('en-GB');
}

if (byId('clock')) {
    setInterval(updateClock, 1000);
    updateClock();
}

function addLog(message, type = 'default', timeOverride = null) {
    const container = byId('log-container');
    if (!container) return;

    const time = timeOverride || new Date().toLocaleTimeString('en-GB');
    const cls = {
        success: 'log-text-success',
        error: 'log-text-error',
        warning: 'log-text-error',
        info: 'log-text-info',
        default: 'log-text-default'
    }[type] || 'log-text-default';

    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `<span class="log-time">[${time}]</span><span class="${cls}"> ${message}</span>`;
    container.prepend(entry);
}

function syncServerEvents(events = []) {
    const newEvents = [...events]
        .filter(event => event.id > lastServerEventId)
        .sort((a, b) => a.id - b.id);

    newEvents.forEach(event => {
        addLog(event.message, event.level || 'info', event.time_label);
        lastServerEventId = Math.max(lastServerEventId, event.id);
    });
}

function setLoading(loading) {
    document.querySelectorAll('.control-btn').forEach(btn => {
        btn.disabled = loading;
        btn.style.opacity = loading ? '0.5' : '1';
    });
}

function setHint(msg) {
    setText('status-hint', msg);
}

function formatBytes(value) {
    const bytes = Number(value || 0);
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

async function postJson(url, payload = {}) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    return res.json();
}

function renderPathPills(path = []) {
    const container = byId('path-pill-list');
    if (!container) return;

    if (!path.length) {
        container.innerHTML = '<span class="path-pill">No active path</span>';
        return;
    }

    container.innerHTML = path.map((hop, index) => `
        <span class="path-pill active">${index + 1}. ${hop.toUpperCase()}</span>
    `).join('');
}

function updateTopologySelection(running, path = [], nodeStatus = {}) {
    const baseNodes = ['node-h1', 'node-s1', 'node-s2', 'node-h2'];
    baseNodes.forEach(id => {
        const el = byId(id);
        if (el) {
            el.classList.toggle('active', running);
            el.classList.remove('selected');
        }
    });

    ['link-1', 'link-2', 'link-3'].forEach(id => {
        const el = byId(id);
        if (el) el.classList.toggle('active', running);
    });

    ['fw', 'ids', 'lb'].forEach(name => {
        const node = byId(`node-${name}`);
        const branch = byId(`branch-${name}`);
        const isRunning = nodeStatus[name]?.status === 'running';
        const inPath = path.includes(name);

        if (node) {
            node.classList.toggle('active', isRunning);
            node.classList.toggle('selected', inPath);
        }

        if (branch) {
            branch.classList.toggle('active', inPath || isRunning);
        }
    });

    path.forEach(hop => {
        const node = byId(`node-${hop}`);
        if (node) node.classList.add('selected');
    });

    const playbackTrack = byId('playback-track');
    if (playbackTrack) playbackTrack.classList.toggle('active', running && path.length > 0);
}

function updateIncidents(incidents = []) {
    const container = byId('incident-list');
    if (!container) return;

    if (!incidents.length) {
        container.innerHTML = '<div class="text-muted small">No incidents detected yet.</div>';
        return;
    }

    container.innerHTML = incidents.slice(0, 5).map(incident => `
        <div class="incident-item ${incident.severity}">
            <div class="incident-title">${incident.title}</div>
            <div class="incident-time">${incident.time_label} · ${incident.severity}</div>
        </div>
    `).join('');
}

function updateLoadBalancerSimulation(simulation) {
    const badge = byId('lb-simulation-badge');
    const panel = byId('lb-simulation-panel');
    if (!badge && !panel) return;

    if (!simulation) {
        if (badge) {
            badge.className = 'badge-pill badge-stopped';
            badge.innerHTML = '<span class="pulse pulse-red"></span> Idle';
        }
        if (panel) {
            panel.className = 'empty-state-copy';
            panel.innerHTML = 'Run "Simulate LB Request Spike" to apply the load-balancer policy and distribute synthetic requests across backend servers.';
        }
        return;
    }

    if (badge) {
        badge.className = simulation.active ? 'badge-pill badge-running' : 'badge-pill badge-info';
        badge.innerHTML = simulation.active
            ? '<span class="pulse pulse-green"></span> Active'
            : '<span class="pulse pulse-yellow"></span> Last Run';
    }

    if (!panel) return;

    const backends = simulation.backend_pool || [];
    panel.className = 'lb-simulation';
    panel.innerHTML = `
        <div class="lb-simulation-summary">
            <div class="metric-card">
                <span class="metric-label">Requests</span>
                <span class="metric-value">${simulation.total_requests || 0}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Clients</span>
                <span class="metric-value">${simulation.client_count || 0}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Peak RPS</span>
                <span class="metric-value">${simulation.peak_rps || 0}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Dropped</span>
                <span class="metric-value">${simulation.dropped_requests || 0}</span>
            </div>
        </div>
        <div class="lb-simulation-meta">
            <span>Algorithm: ${(simulation.algorithm || 'round_robin').replace(/_/g, ' ')}</span>
            <span>VIP: ${simulation.virtual_ip || '10.0.0.252'}</span>
            <span>Generated: ${simulation.generated_label || '—'}</span>
        </div>
        <div class="lb-backend-list">
            ${backends.map(backend => `
                <div class="lb-backend-row">
                    <div class="lb-backend-head">
                        <div>
                            <div class="lb-backend-name">${backend.name}</div>
                            <div class="lb-backend-ip">${backend.ip} · ${backend.status}</div>
                        </div>
                        <div class="lb-backend-count">${backend.requests} req · ${backend.share_percent}%</div>
                    </div>
                    <div class="lb-share-track">
                        <div class="lb-share-fill" style="width:${backend.share_percent}%;"></div>
                    </div>
                    <div class="lb-backend-latency">${backend.latency_ms} ms estimated latency</div>
                </div>
            `).join('')}
        </div>
    `;
}

function updatePolicyBadge(activePolicy) {
    const badge = byId('policy-status-badge');
    if (!badge) return;

    if (!activePolicy) {
        badge.className = 'badge-pill badge-stopped';
        badge.innerHTML = '<span class="pulse pulse-red"></span> Idle';
        return;
    }

    if (activePolicy.status === 'fallback') {
        badge.className = 'badge-pill badge-info';
        badge.innerHTML = '<span class="pulse pulse-yellow"></span> Fallback';
        return;
    }

    badge.className = 'badge-pill badge-running';
    badge.innerHTML = '<span class="pulse pulse-green"></span> Active';
}

function updateVnfs(vnfs = []) {
    const running = vnfs.filter(v => v.status === 'running');
    const vnfBadge = byId('vnf-badge');
    const vnfList = byId('vnf-list');

    if (vnfBadge) {
        if (running.length) {
            vnfBadge.className = 'badge-pill badge-running';
            vnfBadge.innerHTML = `<span class="pulse pulse-green"></span> ${running.length} Active`;
        } else {
            vnfBadge.className = 'badge-pill badge-stopped';
            vnfBadge.innerHTML = '<span class="pulse pulse-red"></span> None';
        }
    }

    if (vnfList) {
        if (running.length) {
            vnfList.innerHTML = running.map(v => `
                <div class="info-row">
                    <div>
                        <div style="font-size:.8rem; font-weight:600;">${v.label || v.name}</div>
                        <div style="font-size:.68rem; color:var(--muted); font-family:'IBM Plex Mono',monospace;">
                            ${v.name} · ${v.ip || 'unknown'} · ${v.role || 'vnf'}
                        </div>
                    </div>
                    <div class="vnf-row-actions">
                        <span class="badge-pill badge-running" style="font-size:.62rem;">Running</span>
                        <button class="btn-ctrl btn-ctrl-danger btn-ctrl-mini control-btn" data-stop-vnf="${v.name}" data-stop-vnf-label="${v.label || v.name}">
                            Stop
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            vnfList.innerHTML = '<div class="empty-state-copy">No containers deployed yet.</div>';
        }
    }

    setText('sidebar-vnf-count', `${running.length}`);
}

function updateController(data) {
    const controllerName = data.sdn_controller.name || 'Ryu OpenFlow 1.3';
    const controllerMode = data.sdn_controller.mode_label || 'Local';
    const controllerRestApi = data.sdn_controller.rest_api || '127.0.0.1:8080';
    const controllerOpenFlow = data.sdn_controller.openflow_endpoint || '127.0.0.1:6653';
    const ctrlActive = data.sdn_controller.active;
    const ctrlBadge = byId('ctrl-live-badge');

    setText('kpi-ctrl-value', ctrlActive ? `${data.sdn_controller.switches_connected} SW` : '—');
    setText(
        'kpi-ctrl-sub',
        ctrlActive
            ? `${controllerMode} · ${data.sdn_controller.switches_connected} switch(es) connected`
            : `${controllerMode} mode · controller offline`
    );

    if (ctrlBadge) {
        if (ctrlActive) {
            ctrlBadge.className = 'badge-pill badge-running';
            ctrlBadge.innerHTML = '<span class="pulse pulse-green"></span> Online';
        } else {
            ctrlBadge.className = 'badge-pill badge-stopped';
            ctrlBadge.innerHTML = '<span class="pulse pulse-red"></span> Offline';
        }
    }

    setText('ctrl-switches', ctrlActive ? `${data.sdn_controller.switches_connected} connected` : '0 connected');
    setText('ctrl-flows', data.sdn_controller.total_flows);
    setText('ctrl-controller-name', controllerName);
    setText('ctrl-mode', `${controllerMode} mode`);
    setText('ctrl-rest-api', controllerRestApi);
    setText('ctrl-openflow', controllerOpenFlow);
    setText('sidebar-controller-status', ctrlActive ? 'Online' : 'Offline');
}

function updateSystem(system) {
    if (!system) return;

    const cpuBar = byId('cpu-bar');
    if (cpuBar) {
        cpuBar.style.width = `${system.cpu_percent}%`;
        cpuBar.style.background = system.cpu_percent > 80
            ? 'var(--red)'
            : system.cpu_percent > 50
                ? 'var(--yellow)'
                : 'var(--accent)';
    }
    setText('cpu-text', `${system.cpu_percent.toFixed(1)}%`);

    const ramBar = byId('ram-bar');
    if (ramBar) {
        ramBar.style.width = `${system.memory_percent}%`;
        ramBar.style.background = system.memory_percent > 85 ? 'var(--red)' : 'var(--yellow)';
    }
    setText('ram-text', `${system.memory_percent.toFixed(1)}%  (${system.memory_used_mb} MB / ${system.memory_total_mb} MB)`);
}

function updateUI(data) {
    const running = data.topology.status === 'Running';
    const orchestrator = data.orchestrator || {};
    const activePolicy = orchestrator.active_policy;
    const telemetry = orchestrator.telemetry || {};
    const traffic = telemetry.traffic || {};
    const nodeStatus = telemetry.node_status || {};
    const loadBalancerSimulation = telemetry.load_balancer_simulation;
    const runningVnfs = (data.vnfs || []).filter(v => v.status === 'running').length;

    const topoStatus = byId('kpi-topo-status');
    if (topoStatus) {
        topoStatus.innerText = running ? 'ON' : 'OFF';
        topoStatus.style.color = running ? 'var(--green)' : 'var(--red)';
    }

    setText(
        'kpi-topo-detail',
        running
            ? `Hosts: ${data.topology.details?.Hosts || 5}, Switches: ${data.topology.details?.Switches || 2}`
            : 'Stopped'
    );
    setText('kpi-flows', data.sdn_controller.total_flows);
    setText('kpi-vnfs', runningVnfs);

    const badgeTopo = byId('badge-topo');
    const dotTopo = byId('dot-topo');
    const badgeText = byId('badge-topo-text');
    if (badgeTopo && dotTopo && badgeText) {
        if (running) {
            badgeTopo.className = 'badge-pill badge-running';
            dotTopo.className = 'pulse pulse-green';
            badgeText.innerText = 'Running';
        } else {
            badgeTopo.className = 'badge-pill badge-stopped';
            dotTopo.className = 'pulse pulse-red';
            badgeText.innerText = 'Stopped';
        }
    }

    updateController(data);
    updateVnfs(data.vnfs || []);
    updateSystem(data.system);
    updatePolicyBadge(activePolicy);

    setText('active-policy-label', activePolicy ? activePolicy.label : 'None');
    setText('observed-packets', traffic.packets || 0);
    setText('observed-bytes', formatBytes(traffic.bytes || 0));
    setText('observed-rules', traffic.rule_count || 0);
    setText(
        'kpi-flow-caption',
        activePolicy
            ? `${activePolicy.label} active · ${traffic.source || 'openflow'}`
            : 'Policy flow rules installed'
    );
    setText(
        'kpi-vnfs-caption',
        activePolicy ? `${(activePolicy.chain || []).length} service hop(s)` : 'Containers active'
    );

    const path = traffic.active_path || activePolicy?.path || [];
    renderPathPills(path);
    updateTopologySelection(running, path, nodeStatus);
    updateIncidents(orchestrator.incidents || []);
    updateLoadBalancerSimulation(loadBalancerSimulation);
    syncServerEvents(orchestrator.events || []);

    setText(
        'flow-path-text',
        path.length ? `Active path: ${path.join(' → ')}` : 'Waiting for active policy...'
    );
    setText(
        'observatory-footnote',
        activePolicy
            ? `Status: ${activePolicy.status} · Installed at ${activePolicy.installed_label}`
            : 'Packet playback is synced with the currently selected service path.'
    );

    setText('sidebar-topology-status', running ? 'Running' : 'Stopped');
    setText('sidebar-policy-status', activePolicy ? activePolicy.label : 'Idle');
}

async function fetchPolicies() {
    const select = byId('policy-select');
    if (!select) return;

    try {
        const res = await fetch('/api/policies');
        const policies = await res.json();
        select.innerHTML = policies.map(policy => `
            <option value="${policy.key}">${policy.label}</option>
        `).join('');
    } catch (error) {
        console.warn('Policy fetch failed:', error);
    }
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        updateUI(data);
    } catch (error) {
        console.warn('Stats fetch failed:', error);
    }
}

async function deployVnf(name, role, label) {
    setLoading(true);
    setHint(`Deploying ${label} VNF...`);
    addLog(`Deploying ${label} VNF...`, 'info');

    try {
        const data = await postJson('/api/vnf/deploy', { name, role });
        addLog(data.message, data.status === 'success' ? 'success' : 'error');
        setHint(data.status === 'success' ? `${label} VNF ready.` : data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
}

async function stopVnf(name, label) {
    setLoading(true);
    setHint(`Stopping ${label} VNF...`);
    addLog(`Stopping ${label} VNF...`, 'warning');

    try {
        const data = await postJson('/api/vnf/stop', { name });
        addLog(data.message, data.status === 'success' ? 'success' : 'error');
        setHint(data.status === 'success' ? `${label} VNF stopped.` : data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
}

bindIfPresent('btn-start-topo', 'click', async () => {
    setLoading(true);
    setHint('Starting Mininet topology, please wait...');
    addLog('Requesting topology start...', 'info');

    try {
        const data = await postJson('/api/topology/start');
        addLog(data.message, data.status === 'success' ? 'success' : 'error');
        setHint(data.status === 'success'
            ? 'Topology running. Compose a policy and observe the service path.'
            : data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
});

bindIfPresent('btn-stop-topo', 'click', async () => {
    setLoading(true);
    setHint('Stopping topology...');
    addLog('Requesting topology stop...', 'info');

    try {
        const data = await postJson('/api/topology/stop');
        addLog(data.message, data.status === 'success' ? 'success' : 'error');
        setHint(data.status === 'success' ? 'Topology stopped. Press Start Topology to restart.' : data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
});

bindIfPresent('btn-deploy-fw', 'click', () => deployVnf('fw', 'firewall', 'Firewall'));
bindIfPresent('btn-deploy-ids', 'click', () => deployVnf('ids', 'ids', 'IDS'));
bindIfPresent('btn-deploy-lb', 'click', () => deployVnf('lb', 'load_balancer', 'Load Balancer'));
bindIfPresent('btn-stop-fw', 'click', () => stopVnf('fw', 'Firewall'));
bindIfPresent('btn-stop-ids', 'click', () => stopVnf('ids', 'IDS'));
bindIfPresent('btn-stop-lb', 'click', () => stopVnf('lb', 'Load Balancer'));

document.addEventListener('click', event => {
    const button = event.target.closest('[data-stop-vnf]');
    if (!button) return;
    stopVnf(button.dataset.stopVnf, button.dataset.stopVnfLabel || button.dataset.stopVnf);
});

bindIfPresent('btn-scenario-lb-spike', 'click', async () => {
    setLoading(true);
    setHint('Simulating a request spike through the load balancer...');
    addLog('Triggering scenario: load balancer request spike.', 'info');

    try {
        const data = await postJson('/api/scenario/trigger', {
            scenario: 'load_balancer_spike',
            requests: 240,
            clients: 24
        });
        addLog(data.message, data.status === 'success' ? 'success' : 'error');
        setText('scenario-note', data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
});

bindIfPresent('btn-apply-policy', 'click', async () => {
    const policy = byId('policy-select')?.value;
    if (!policy) return;

    setLoading(true);
    setHint('Applying selected service chain...');
    addLog(`Applying policy '${policy}'...`, 'info');

    try {
        const data = await postJson('/api/policy/apply', { policy, auto_deploy: true });
        addLog(data.message, data.status === 'success' ? 'success' : 'error');
        setHint(data.status === 'success'
            ? `Policy ${data.policy.label} active.`
            : data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
});

bindIfPresent('btn-scenario-kill', 'click', async () => {
    setLoading(true);
    setHint('Injecting VNF failure scenario...');
    addLog('Triggering scenario: kill active VNF.', 'info');

    try {
        const data = await postJson('/api/scenario/trigger', { scenario: 'kill_active_vnf' });
        addLog(data.message, data.status === 'success' ? 'warning' : 'error');
        setText('scenario-note', data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
});

bindIfPresent('btn-scenario-fallback', 'click', async () => {
    setLoading(true);
    setHint('Forcing direct fallback...');
    addLog('Triggering scenario: direct fallback.', 'info');

    try {
        const data = await postJson('/api/scenario/trigger', { scenario: 'fallback_direct' });
        addLog(data.message, data.status === 'success' ? 'warning' : 'error');
        setText('scenario-note', data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
});

bindIfPresent('btn-scenario-recover', 'click', async () => {
    setLoading(true);
    setHint('Recovering last chained policy...');
    addLog('Triggering scenario: recover last policy.', 'info');

    try {
        const data = await postJson('/api/scenario/trigger', { scenario: 'recover_policy' });
        addLog(data.message, data.status === 'success' ? 'success' : 'error');
        setText('scenario-note', data.message);
        await fetchStats();
    } finally {
        setLoading(false);
    }
});

async function fetchFlowDetails() {
    const container = byId('flow-table-container');
    if (!container) return;

    container.innerHTML = '<div class="text-center py-5 text-muted">Fetching rules from SDN controller…</div>';

    try {
        const res = await fetch('/api/flow/details');
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
                const matchStr = Object.entries(flow.match)
                    .map(([k, v]) => `<span style="color:var(--yellow);">${k}</span>=<span style="color:#f8fafc;">${v}</span>`)
                    .join(' · ') || '<em>ANY</em>';
                const actionStr = (flow.actions || []).join(', ') || '<span style="color:var(--red);">DROP</span>';

                html += `<tr style="border-color:var(--border);">
                    <td><span class="badge-pill badge-info" style="font-size:.65rem;">${flow.priority}</span></td>
                    <td style="font-family:'IBM Plex Mono',monospace; font-size:.72rem; max-width: 280px; word-break:break-all;">${matchStr}</td>
                    <td style="color:var(--green); font-family:'IBM Plex Mono',monospace; font-size:.72rem;">${actionStr}</td>
                    <td>${flow.packet_count ?? '—'}</td>
                    <td>${flow.byte_count ?? '—'}</td>
                </tr>`;
            });

            html += '</tbody></table></div>';
        }

        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger m-3">Error fetching flows: ${error.message}</div>`;
    }
}

bindIfPresent('flowModal', 'show.bs.modal', fetchFlowDetails);
bindIfPresent('btn-refresh-flows', 'click', fetchFlowDetails);

initTooltips();
setInterval(fetchStats, 3000);
fetchPolicies();
fetchStats();
addLog('Workspace initialized. Polling every 3 seconds.', 'info');
