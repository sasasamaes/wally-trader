// Wally Trader Dashboard — vanilla JS, polling 5s

const POLL_MS = 5000;

async function fetchJson(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error(`Fetch ${url} failed:`, e);
        return null;
    }
}

function fmtPct(v) {
    return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
}

function fmtUsd(v) {
    return (v >= 0 ? '+' : '') + '$' + v.toFixed(2);
}

function severityClass(sev) {
    return { OK: 'ok', WARN: 'warn', ALERT: 'alert', HIGH: 'alert', CALM: 'ok', ELEVATED: 'warn' }[sev] || '';
}

async function refreshHealth() {
    const data = await fetchJson('/api/health');
    const el = document.getElementById('health-status');
    if (data && data.status === 'ok') {
        el.innerHTML = 'Online';
    } else {
        el.innerHTML = 'Offline';
    }
    document.getElementById('last-updated').textContent = `Updated: ${new Date().toLocaleTimeString()}`;
}

async function refreshProfiles() {
    const data = await fetchJson('/api/profiles');
    const el = document.getElementById('profiles-grid');
    if (!data) { el.innerHTML = 'Error'; return; }
    el.innerHTML = data.profiles.map(p => `
        <div class="profile-card">
            <h3>${p.name}</h3>
            <div>Open: ${p.open_count}</div>
            <div>Today: ${p.today_count}</div>
        </div>
    `).join('');
}

async function refreshPortfolioHeat() {
    const data = await fetchJson('/api/portfolio/heat');
    const el = document.getElementById('portfolio-heat');
    if (!data) { el.innerHTML = 'Error'; return; }
    const cls = data.breach ? 'alert' : (data.total_heat_pct > 10 ? 'warn' : 'ok');
    el.innerHTML = `
        <div class="metric ${cls}">
            <div class="big">${data.total_heat_pct.toFixed(2)}%</div>
            <div>${data.n_positions} positions</div>
            ${data.breach ? '<div class="alert-tag">BREACH</div>' : ''}
        </div>
    `;
}

async function refreshPositions() {
    const data = await fetchJson('/api/positions');
    const el = document.getElementById('positions-table');
    if (!data) { el.innerHTML = 'Error'; return; }
    if (!data.positions.length) {
        el.innerHTML = '<div class="muted">No open positions</div>';
        return;
    }
    el.innerHTML = `
        <table>
            <thead><tr><th>Profile</th><th>Symbol</th><th>Side</th><th>Entry</th><th>SL</th><th>TP</th><th>Lev</th></tr></thead>
            <tbody>
                ${data.positions.map(p => `
                    <tr>
                        <td>${p.profile}</td>
                        <td>${p.symbol}</td>
                        <td class="${p.side === 'LONG' ? 'long' : 'short'}">${p.side}</td>
                        <td>${p.entry || '-'}</td>
                        <td>${p.sl || '-'}</td>
                        <td>${p.tp || '-'}</td>
                        <td>${p.leverage || '-'}x</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

async function refreshDiscipline() {
    const data = await fetchJson('/api/discipline/tilt/bitunix');
    const el = document.getElementById('discipline-info');
    if (!data) { el.innerHTML = 'Error'; return; }
    const cls = severityClass(data.level);
    el.innerHTML = `
        <div class="metric ${cls}">
            <div class="big">${data.score}/100</div>
            <div>${data.level}</div>
            ${data.cooldown_active ? `<div class="alert-tag">COOLDOWN ${data.cooldown_minutes_remaining}min</div>` : ''}
        </div>
        ${data.flags.length ? '<ul>' + data.flags.map(f => `<li>${f}</li>`).join('') + '</ul>' : ''}
    `;
}

async function refreshCalibration() {
    const data = await fetchJson('/api/calibration/divergence/bitunix?window_days=30');
    const el = document.getElementById('calibration-info');
    if (!data) { el.innerHTML = 'Error'; return; }
    if (data.info) {
        el.innerHTML = `<div class="muted">${data.info}: live n=${data.live_n || 0}</div>`;
        return;
    }
    const cls = severityClass(data.severity);
    el.innerHTML = `
        <div class="metric ${cls}">
            <div>${data.severity}</div>
            <div>WR drift: ${fmtPct(data.wr_drift_pct)}</div>
            <div>PF drift: ${fmtPct(data.pf_drift_pct)}</div>
        </div>
    `;
}

async function refreshAll() {
    await Promise.all([
        refreshHealth(),
        refreshProfiles(),
        refreshPortfolioHeat(),
        refreshPositions(),
        refreshDiscipline(),
        refreshCalibration(),
    ]);
}

refreshAll();
setInterval(refreshAll, POLL_MS);
