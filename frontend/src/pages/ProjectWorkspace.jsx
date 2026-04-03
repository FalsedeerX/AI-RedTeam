import React from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { apiGet, apiPost, apiDelete } from '../lib/api';

// Infer target type from its value string.
function inferTargetType(value) {
  if (!value) return 'URL';
  const v = value.trim();
  if (/\/\d+$/.test(v)) return 'CIDR';
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(v)) return 'IP';
  if (/^https?:\/\//i.test(v) || v.includes('/')) return 'URL';
  return 'DOMAIN';
}

// Derive a security grade + color from a findings array.
function computeGrade(findings) {
  if (!findings || findings.length === 0) return { grade: 'A', color: 'var(--rt-leaf)', label: 'No issues found' };
  if (findings.some(f => f.severity === 'critical')) return { grade: 'F', color: 'var(--rt-ember)', label: 'Critical risk' };
  if (findings.some(f => f.severity === 'high')) return { grade: 'D', color: 'var(--rt-amber)', label: 'High risk' };
  if (findings.some(f => f.severity === 'medium')) return { grade: 'C', color: 'var(--rt-amber)', label: 'Moderate risk' };
  return { grade: 'B', color: 'var(--rt-sky)', label: 'Low risk' };
}

function relativeTime(isoStr) {
  if (!isoStr) return null;
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// ── Severity badge styles ──────────────────────────────────────────────────────
const SEV_STYLE = {
  critical: { color: 'var(--rt-ember)', bg: 'rgba(248,81,73,0.15)', border: 'rgba(248,81,73,0.3)', leftBorder: 'var(--rt-ember)' },
  high:     { color: 'var(--rt-amber)', bg: 'rgba(210,153,34,0.15)',  border: 'rgba(210,153,34,0.3)',  leftBorder: 'var(--rt-amber)' },
  medium:   { color: 'var(--rt-sky)',   bg: 'rgba(121,192,255,0.12)', border: 'rgba(121,192,255,0.3)', leftBorder: 'var(--rt-sky)' },
  low:      { color: 'var(--rt-leaf)',  bg: 'rgba(63,185,80,0.12)',   border: 'rgba(63,185,80,0.3)',   leftBorder: 'var(--rt-leaf)' },
};
const SEV_ORDER = ['critical', 'high', 'medium', 'low'];

export default function ProjectWorkspace({ username }) {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Tab state — honours ?tab= query param (e.g. returning from terminal)
  const initialTab = searchParams.get('tab') || 'targets';
  const [activeTab, setActiveTab] = React.useState(initialTab);

  // Project + target state
  const [project, setProject] = React.useState(null);
  const [targets, setTargets] = React.useState([]);
  const [allProjects, setAllProjects] = React.useState([]);
  const [loadingProject, setLoadingProject] = React.useState(true);
  //const [loadingTargets, setLoadingTargets] = React.useState(false);
  const [projectError, setProjectError] = React.useState('');

  // Add target form state
  const [showAddTarget, setShowAddTarget] = React.useState(false);
  const [newTargetValue, setNewTargetValue] = React.useState('');
  const [addingTarget, setAddingTarget] = React.useState(false);

  // Scan tab state
  const [selectedTargetId, setSelectedTargetId] = React.useState('');
  const [scanMode, setScanMode] = React.useState('passive');
  const [scanType, setScanType] = React.useState('web');
  const [authorization, setAuthorization] = React.useState('');
  const [scanLaunching, setScanLaunching] = React.useState(false);
  const [scanError, setScanError] = React.useState('');

  // Findings tab state
  const [findings, setFindings] = React.useState([]);
  const [loadingFindings, setLoadingFindings] = React.useState(false);
  const [_findingsError, setFindingsError] = React.useState('');
  const [_latestRunId, setLatestRunId] = React.useState(null);

  // Reports tab state
  const [reports, setReports] = React.useState([]);
  const [loadingReports, setLoadingReports] = React.useState(false);

  // Project switcher
  const [switcherOpen, setSwitcherOpen] = React.useState(false);
  const switcherRef = React.useRef(null);

  // Delete project
  const [confirmDelete, setConfirmDelete] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);

  // Global error banner
  const [error, setError] = React.useState('');

  // ── Load project + targets + all-projects on mount ──────────────────────────
  React.useEffect(() => {
    async function init() {
      setLoadingProject(true);
      setProjectError('');
      try {
        const [projectsData, targetsData] = await Promise.all([
          apiGet('/projects'),
          apiGet(`/projects/${projectId}/targets`),
        ]);
        const found = projectsData.find(p => String(p.id) === String(projectId));
        if (!found) { setProjectError('Project not found.'); return; }
        setProject(found);
        setAllProjects(projectsData);
        setTargets(targetsData);
        if (targetsData.length > 0) setSelectedTargetId(String(targetsData[0].id));
      } catch (err) {
        setProjectError(`Could not load project: ${err.message}`);
      } finally {
        setLoadingProject(false);
      }
    }
    init();
  }, [projectId]);

  // ── Load findings when switching to findings tab ─────────────────────────────
  React.useEffect(() => {
    if (activeTab === 'findings' && !loadingFindings) {
      loadFindings();
    }
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Load reports when switching to reports tab ───────────────────────────────
  React.useEffect(() => {
    if (activeTab === 'reports' && !loadingReports) {
      loadReports();
    }
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Close switcher on outside click ─────────────────────────────────────────
  React.useEffect(() => {
    function handle(e) {
      if (switcherRef.current && !switcherRef.current.contains(e.target)) setSwitcherOpen(false);
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  async function loadFindings() {
    setLoadingFindings(true);
    setFindingsError('');
    try {
      // Try project-level findings endpoint first.
      // Falls back to empty array if the endpoint doesn't exist yet.
      const data = await apiGet(`/projects/${projectId}/findings`).catch(() => null);
      if (data) {
        setFindings(data.findings || data);
        if (data.run_id) setLatestRunId(data.run_id);
      }
    } catch {
      // Findings endpoint not yet available — silently degrade
    } finally {
      setLoadingFindings(false);
    }
  }

  async function loadReports() {
    setLoadingReports(true);
    try {
      const data = await apiGet(`/projects/${projectId}/reports`).catch(() => []);
      setReports(Array.isArray(data) ? data : []);
    } finally {
      setLoadingReports(false);
    }
  }

  // ── Target CRUD ──────────────────────────────────────────────────────────────
  async function handleAddTarget() {
    const value = newTargetValue.trim();
    if (!value || addingTarget) return;
    setAddingTarget(true);
    const temp = { id: `temp-${Date.now()}`, value };
    setTargets(prev => [...prev, temp]);
    setNewTargetValue('');
    setShowAddTarget(false);
    try {
      const created = await apiPost(`/projects/${projectId}/targets`, { value });
      setTargets(prev => prev.map(t => (t.id === temp.id ? created : t)));
      if (!selectedTargetId) setSelectedTargetId(String(created.id));
    } catch (err) {
      setTargets(prev => prev.filter(t => t.id !== temp.id));
      setError(`Failed to add target: ${err.message}`);
    } finally {
      setAddingTarget(false);
    }
  }

  async function handleRemoveTarget(target) {
    setTargets(prev => prev.filter(t => t.id !== target.id));
    if (String(target.id).startsWith('temp-')) return;
    try {
      await apiDelete(`/projects/${projectId}/targets/${target.id}`);
    } catch (err) {
      setTargets(prev => [...prev, target]);
      setError(`Failed to remove target: ${err.message}`);
    }
  }

  // ── Scan launch ──────────────────────────────────────────────────────────────
  async function handleStartScan() {
    if (authorization !== 'I AUTHORIZE' || !selectedTargetId || scanLaunching) return;
    setScanLaunching(true);
    setScanError('');

    const selectedTarget = targets.find(t => String(t.id) === String(selectedTargetId));
    const targetValue = selectedTarget ? selectedTarget.value : targets[0]?.value;

    try {
      const data = await apiPost('/agent/start', {
        project_id: projectId,
        target: targetValue,
      });
      navigate(`/projects/${projectId}/runs/${data.run_id}`, {
        state: { targets: [targetValue], scanType, username },
      });
    } catch (err) {
      setScanError(`Failed to start scan: ${err.message}`);
      setScanLaunching(false);
    }
  }

  // ── Delete project ──────────────────────────────────────────────────────────
  async function handleDeleteProject() {
    setDeleting(true);
    try {
      await apiDelete(`/projects/${projectId}`);
      navigate('/dashboard');
    } catch (err) {
      setError(`Failed to delete project: ${err.message}`);
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  // ── JSON export ──────────────────────────────────────────────────────────────
  function handleExportJSON(report) {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report-${report.id || 'export'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── Loading / error screens ──────────────────────────────────────────────────
  if (loadingProject) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--rt-bg)' }}>
        <p className="text-sm animate-pulse" style={{ color: 'var(--rt-muted)' }}>Loading project…</p>
      </div>
    );
  }

  if (projectError) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ background: 'var(--rt-bg)' }}>
        <p className="text-sm" style={{ color: 'var(--rt-ember)' }}>{projectError}</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="text-sm underline"
          style={{ color: 'var(--rt-sky)' }}
        >
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  const grade = computeGrade(findings);
  const canLaunch = authorization === 'I AUTHORIZE' && selectedTargetId && !scanLaunching;

  return (
    <div className="flex flex-col min-h-screen" style={{ background: 'var(--rt-bg)' }}>

      {/* ── Project topbar ───────────────────────────────────────────────────── */}
      <div
        className="flex items-center gap-4 px-7 py-3"
        style={{ background: 'var(--rt-surface)', borderBottom: '1px solid var(--rt-border)' }}
      >
        <nav className="flex items-center gap-2 text-sm" style={{ color: 'var(--rt-muted)' }}>
          <button
            onClick={() => navigate('/dashboard')}
            className="transition-colors hover:underline"
            style={{ color: 'var(--rt-sky)' }}
          >
            ← Dashboard
          </button>
          <span style={{ color: 'var(--rt-dim)' }}>/</span>
          <span className="font-semibold" style={{ color: 'var(--rt-text)' }}>{project?.name}</span>
        </nav>

        <div className="flex-1" />

        {/* Project switcher */}
        <div className="relative" ref={switcherRef}>
          <button
            onClick={() => setSwitcherOpen(o => !o)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors"
            style={{ background: 'var(--rt-surface2)', border: '1px solid var(--rt-border)', color: 'var(--rt-text)' }}
          >
            <span className="max-w-[160px] truncate">{project?.name}</span>
            <span className="text-xs" style={{ color: 'var(--rt-muted)' }}>▾</span>
          </button>
          {switcherOpen && (
            <div
              className="absolute right-0 top-9 w-56 rounded-lg overflow-hidden shadow-2xl z-50"
              style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
            >
              <p className="px-3 py-2 text-xs font-mono font-semibold uppercase tracking-widest" style={{ color: 'var(--rt-dim)' }}>
                Switch Project
              </p>
              {allProjects.map(p => (
                <button
                  key={p.id}
                  onClick={() => { setSwitcherOpen(false); navigate(`/projects/${p.id}`); }}
                  className="w-full text-left px-3 py-2 text-sm transition-colors"
                  style={{
                    background: String(p.id) === String(projectId) ? 'rgba(121,192,255,0.08)' : 'transparent',
                    color: String(p.id) === String(projectId) ? 'var(--rt-sky)' : 'var(--rt-text)',
                  }}
                >
                  {p.name}
                  {String(p.id) === String(projectId) && <span className="ml-2 text-xs" style={{ color: 'var(--rt-sky)' }}>✓</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Workspace tab bar ────────────────────────────────────────────────── */}
      <div
        className="flex items-center px-7"
        style={{ background: 'var(--rt-surface)', borderBottom: '1px solid var(--rt-border)' }}
      >
        {[
          { id: 'targets',  label: 'Targets',  count: targets.length },
          { id: 'scan',     label: 'Scan' },
          { id: 'findings', label: 'Findings', count: findings.length || null },
          { id: 'reports',  label: 'Reports',  count: reports.length || null },
        ].map(tab => (
          <WsTab
            key={tab.id}
            label={tab.label}
            count={tab.count}
            active={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
          />
        ))}
      </div>

      {/* ── Global error banner ───────────────────────────────────────────────── */}
      {error && (
        <div
          className="mx-7 mt-4 flex items-start justify-between gap-3 px-4 py-3 rounded-lg text-sm"
          style={{ background: 'rgba(248,81,73,0.08)', border: '1px solid rgba(248,81,73,0.3)', color: 'var(--rt-ember)' }}
        >
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-xs underline flex-shrink-0">Dismiss</button>
        </div>
      )}

      {/* ── Body: main + sidebar ─────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Main content */}
        <div className="flex-1 overflow-y-auto px-7 py-7" style={{ background: 'var(--rt-bg)' }}>

          {/* ────────────────────── TARGETS TAB ─────────────────────────────── */}
          {activeTab === 'targets' && (
            <div>
              <div className="flex items-start justify-between mb-5">
                <div>
                  <h2 className="text-sm font-semibold" style={{ color: 'var(--rt-text)' }}>Targets</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--rt-muted)' }}>
                    URLs, IPs, or CIDR ranges in scope for this project
                  </p>
                </div>
                <button
                  onClick={() => setShowAddTarget(t => !t)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-opacity hover:opacity-85"
                  style={{ background: 'var(--rt-sky)', color: '#0d1117' }}
                >
                  + Add Target
                </button>
              </div>

              {targets.length === 0 ? (
                <div
                  className="rounded-lg py-16 text-center"
                  style={{ border: '1px dashed var(--rt-border)' }}
                >
                  <p className="text-2xl mb-2 opacity-30">🎯</p>
                  <p className="text-sm font-medium mb-1" style={{ color: 'var(--rt-muted)' }}>No targets yet</p>
                  <p className="text-xs" style={{ color: 'var(--rt-dim)' }}>Add a URL, IP, or CIDR range to begin.</p>
                </div>
              ) : (
                <div className="flex flex-col gap-2 mb-4">
                  {targets.map(target => (
                    <TargetRow
                      key={target.id}
                      target={target}
                      onScan={() => { setSelectedTargetId(String(target.id)); setActiveTab('scan'); }}
                      onRemove={() => handleRemoveTarget(target)}
                    />
                  ))}
                </div>
              )}

              {/* Add target inline form */}
              {showAddTarget && (
                <div
                  className="rounded-lg p-4 mt-3"
                  style={{ background: 'var(--rt-surface2)', border: '1px dashed var(--rt-border-bright)' }}
                >
                  <p className="text-xs font-semibold mb-3" style={{ color: 'var(--rt-muted)' }}>Add new target</p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      autoFocus
                      value={newTargetValue}
                      onChange={e => setNewTargetValue(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleAddTarget()}
                      placeholder="e.g. https://example.com or 192.168.1.1"
                      className="flex-1 px-3 py-2 rounded text-xs font-mono outline-none"
                      style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)', color: 'var(--rt-text)' }}
                      onFocus={e => { e.target.style.borderColor = 'var(--rt-sky)'; }}
                      onBlur={e => { e.target.style.borderColor = 'var(--rt-border)'; }}
                    />
                    <button
                      onClick={handleAddTarget}
                      disabled={!newTargetValue.trim() || addingTarget}
                      className="px-3 py-2 rounded text-xs font-semibold transition-opacity hover:opacity-85 disabled:opacity-40"
                      style={{ background: 'var(--rt-sky)', color: '#0d1117' }}
                    >
                      Add
                    </button>
                    <button
                      onClick={() => { setShowAddTarget(false); setNewTargetValue(''); }}
                      className="px-3 py-2 rounded text-xs"
                      style={{ background: 'transparent', border: '1px solid var(--rt-border)', color: 'var(--rt-muted)' }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ────────────────────── SCAN TAB ────────────────────────────────── */}
          {activeTab === 'scan' && (
            <div>
              <div className="mb-5">
                <h2 className="text-sm font-semibold" style={{ color: 'var(--rt-text)' }}>Launch Scan</h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--rt-muted)' }}>Configure and start a new assessment run</p>
              </div>

              <div
                className="rounded-lg p-6 max-w-xl"
                style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
              >
                {targets.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-sm mb-2" style={{ color: 'var(--rt-muted)' }}>No targets configured</p>
                    <button
                      onClick={() => setActiveTab('targets')}
                      className="text-sm underline"
                      style={{ color: 'var(--rt-sky)' }}
                    >
                      Add targets first →
                    </button>
                  </div>
                ) : (
                  <>
                    {/* Target selector */}
                    <label className="block text-xs font-medium mb-2" style={{ color: 'var(--rt-muted)' }}>Select Target</label>
                    <select
                      value={selectedTargetId}
                      onChange={e => setSelectedTargetId(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg text-xs font-mono mb-5 outline-none cursor-pointer"
                      style={{ background: 'var(--rt-surface2)', border: '1px solid var(--rt-border)', color: 'var(--rt-text)' }}
                    >
                      {targets.map(t => (
                        <option key={t.id} value={String(t.id)}>{t.value}</option>
                      ))}
                    </select>

                    {/* Scan mode */}
                    <label className="block text-xs font-medium mb-2" style={{ color: 'var(--rt-muted)' }}>Scan Mode</label>
                    <div className="grid grid-cols-2 gap-2 mb-5">
                      <ModeOption
                        selected={scanMode === 'passive'}
                        onClick={() => setScanMode('passive')}
                        label="🔍 Passive"
                        sub="Non-intrusive · default"
                      />
                      <ModeOption
                        selected={scanMode === 'active'}
                        onClick={() => setScanMode('active')}
                        label="⚡ Active"
                        sub="May trigger alerts"
                      />
                    </div>

                    {/* Scan type */}
                    <label className="block text-xs font-medium mb-2" style={{ color: 'var(--rt-muted)' }}>Scan Type</label>
                    <div className="grid grid-cols-2 gap-2 mb-5">
                      <ModeOption
                        selected={scanType === 'web'}
                        onClick={() => setScanType('web')}
                        label="🌐 Web (URL)"
                        sub="Nikto / HTTP"
                      />
                      <ModeOption
                        selected={scanType === 'network'}
                        onClick={() => setScanType('network')}
                        label="🖥 Network (IP)"
                        sub="nmap"
                      />
                    </div>

                    {/* Auth gate */}
                    <div
                      className="rounded-lg p-3 mb-5"
                      style={{ background: 'rgba(248,81,73,0.06)', border: '1px solid rgba(248,81,73,0.25)' }}
                    >
                      <p className="text-xs font-semibold mb-2 flex items-center gap-1" style={{ color: 'var(--rt-ember)' }}>
                        ⚠ Unauthorized testing is a violation of the CFAA
                      </p>
                      <input
                        type="text"
                        value={authorization}
                        onChange={e => setAuthorization(e.target.value)}
                        placeholder='Type "I AUTHORIZE" to confirm permission'
                        className="w-full px-3 py-2 rounded text-xs font-mono outline-none"
                        style={{
                          background: 'var(--rt-surface)',
                          border: '1px solid rgba(248,81,73,0.3)',
                          color: 'var(--rt-text)',
                        }}
                        onFocus={e => { e.target.style.borderColor = 'var(--rt-ember)'; }}
                        onBlur={e => { e.target.style.borderColor = 'rgba(248,81,73,0.3)'; }}
                      />
                    </div>

                    {/* Scan error */}
                    {scanError && (
                      <p className="text-xs mb-3 px-3 py-2 rounded" style={{ background: 'rgba(248,81,73,0.1)', color: 'var(--rt-ember)' }}>
                        {scanError}
                      </p>
                    )}

                    {/* Start Scan button */}
                    <button
                      onClick={handleStartScan}
                      disabled={!canLaunch}
                      className="w-full py-2.5 rounded-lg text-sm font-bold transition-opacity hover:opacity-85 disabled:opacity-40 disabled:cursor-not-allowed"
                      style={{ background: 'var(--rt-leaf)', color: '#0d1117', letterSpacing: '0.02em' }}
                    >
                      {scanLaunching ? 'Launching…' : '▶ Start Scan'}
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          {/* ────────────────────── FINDINGS TAB ────────────────────────────── */}
          {activeTab === 'findings' && (
            <div>
              <div className="flex items-start justify-between mb-5">
                <div>
                  <h2 className="text-sm font-semibold" style={{ color: 'var(--rt-text)' }}>Findings</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--rt-muted)' }}>
                    {findings.length > 0 ? `${findings.length} issues found` : 'Vulnerabilities discovered during scans'}
                  </p>
                </div>
              </div>

              {loadingFindings ? (
                <div className="py-12 text-center">
                  <p className="text-sm animate-pulse" style={{ color: 'var(--rt-muted)' }}>Loading findings…</p>
                </div>
              ) : findings.length === 0 ? (
                <div className="py-16 text-center" style={{ border: '1px dashed var(--rt-border)', borderRadius: '8px' }}>
                  <p className="text-3xl mb-3 opacity-20">🔍</p>
                  <p className="text-sm font-medium mb-1" style={{ color: 'var(--rt-muted)' }}>No findings yet</p>
                  <p className="text-xs mb-5" style={{ color: 'var(--rt-dim)' }}>Run a scan to discover vulnerabilities in your targets.</p>
                  <button
                    onClick={() => setActiveTab('scan')}
                    className="px-4 py-2 rounded-lg text-xs font-semibold transition-opacity hover:opacity-85"
                    style={{ background: 'var(--rt-sky)', color: '#0d1117' }}
                  >
                    Go to Scan →
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {SEV_ORDER.filter(sev => findings.some(f => f.severity === sev)).map(sev => (
                    <React.Fragment key={sev}>
                      {findings.filter(f => f.severity === sev).map(finding => (
                        <FindingCard key={finding.id} finding={finding} />
                      ))}
                    </React.Fragment>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ────────────────────── REPORTS TAB ─────────────────────────────── */}
          {activeTab === 'reports' && (
            <div>
              <div className="mb-5">
                <h2 className="text-sm font-semibold" style={{ color: 'var(--rt-text)' }}>Reports</h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--rt-muted)' }}>Generated assessment reports for this project</p>
              </div>

              {loadingReports ? (
                <p className="text-sm animate-pulse" style={{ color: 'var(--rt-muted)' }}>Loading reports…</p>
              ) : reports.length === 0 ? (
                <div className="py-16 text-center" style={{ border: '1px dashed var(--rt-border)', borderRadius: '8px' }}>
                  <p className="text-3xl mb-3 opacity-20">📄</p>
                  <p className="text-sm font-medium mb-1" style={{ color: 'var(--rt-muted)' }}>No reports yet</p>
                  <p className="text-xs" style={{ color: 'var(--rt-dim)' }}>Complete a scan to generate a report.</p>
                </div>
              ) : (
                <div className="flex flex-col gap-3 max-w-xl">
                  {reports.map((report, i) => (
                    <div
                      key={report.id || i}
                      className="flex items-center gap-4 px-4 py-4 rounded-lg"
                      style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
                    >
                      <span className="text-3xl">📄</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold truncate" style={{ color: 'var(--rt-text)' }}>
                          {report.title || `Scan Report — Run #${i + 1}`}
                        </p>
                        <p className="font-mono text-xs mt-0.5" style={{ color: 'var(--rt-muted)' }}>
                          {report.created_at ? `Generated ${relativeTime(report.created_at)}` : ''}{report.summary ? ` · ${report.summary.slice(0, 40)}` : ''}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleExportJSON(report)}
                          className="px-2 py-1 rounded text-xs transition-colors"
                          style={{ border: '1px solid var(--rt-border)', color: 'var(--rt-muted)' }}
                          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--rt-border-bright)'; e.currentTarget.style.color = 'var(--rt-text)'; }}
                          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--rt-border)'; e.currentTarget.style.color = 'var(--rt-muted)'; }}
                        >
                          JSON
                        </button>
                        <button
                          className="px-2 py-1 rounded text-xs opacity-40 cursor-not-allowed"
                          style={{ border: '1px solid var(--rt-border)', color: 'var(--rt-muted)' }}
                          title="PDF export coming soon"
                          disabled
                        >
                          PDF
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>

        {/* ── Right sidebar ─────────────────────────────────────────────────── */}
        <aside
          className="w-80 flex-shrink-0 overflow-y-auto flex flex-col gap-6 p-6"
          style={{ borderLeft: '1px solid var(--rt-border)', background: 'var(--rt-surface)' }}
        >
          {/* Project info */}
          <div>
            <p className="text-xs font-mono font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--rt-muted)' }}>
              Project Info
            </p>
            <div className="flex flex-col gap-2">
              <InfoRow label="Created" value={project?.created_at ? new Date(project.created_at).toLocaleDateString() : '—'} />
              <InfoRow label="Owner" value={username || '—'} mono />
              <InfoRow label="Targets" value={String(targets.length)} mono />
            </div>
          </div>

          {/* Security grade */}
          <div>
            <p className="text-xs font-mono font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--rt-muted)' }}>
              Security Grade
            </p>
            <div
              className="rounded-lg p-4 text-center mb-3"
              style={{ background: 'var(--rt-surface2)', border: '1px solid var(--rt-border)' }}
            >
              <p className="font-mono text-5xl font-bold leading-none mb-1" style={{ color: grade.color }}>
                {findings.length > 0 ? grade.grade : '—'}
              </p>
              <p className="text-xs" style={{ color: 'var(--rt-muted)' }}>
                {findings.length > 0 ? grade.label : 'Run a scan to get a grade'}
              </p>
            </div>
            {findings.length > 0 && (
              <p className="text-xs leading-relaxed" style={{ color: 'var(--rt-muted)' }}>
                Grade is calculated from severity distribution across all findings in the latest scan.
              </p>
            )}
          </div>

          {/* Quick actions */}
          <div>
            <p className="text-xs font-mono font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--rt-muted)' }}>
              Quick Actions
            </p>
            <div className="flex flex-col gap-2">
              <SidebarBtn onClick={() => setActiveTab('scan')}>▶ New Scan Run</SidebarBtn>
              <SidebarBtn onClick={() => setActiveTab('reports')}>⬇ Reports</SidebarBtn>
              <SidebarBtn
                onClick={() => setConfirmDelete(true)}
                danger
              >
                ✕ Delete Project
              </SidebarBtn>
            </div>
          </div>
        </aside>
      </div>

      {/* ── Delete confirmation modal ──────────────────────────────────────── */}
      {confirmDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.7)' }}
        >
          <div
            className="w-full max-w-sm rounded-xl p-6 shadow-2xl"
            style={{ background: 'var(--rt-surface)', border: '1px solid rgba(248,81,73,0.4)' }}
          >
            <h2 className="text-base font-bold mb-2" style={{ color: 'var(--rt-text)' }}>Delete Project?</h2>
            <p className="text-sm mb-5" style={{ color: 'var(--rt-muted)' }}>
              This will permanently delete <strong style={{ color: 'var(--rt-text)' }}>{project?.name}</strong> and all its
              data. This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="flex-1 py-2 rounded-lg text-sm font-medium"
                style={{ background: 'var(--rt-surface2)', border: '1px solid var(--rt-border)', color: 'var(--rt-muted)' }}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteProject}
                disabled={deleting}
                className="flex-1 py-2 rounded-lg text-sm font-semibold disabled:opacity-60"
                style={{ background: 'var(--rt-ember)', color: 'white' }}
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function WsTab({ label, count, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors"
      style={{
        color: active ? 'var(--rt-sky)' : 'var(--rt-muted)',
        background: 'transparent',
        borderTop: 'none',
        borderLeft: 'none',
        borderRight: 'none',
        borderBottom: active ? '2px solid var(--rt-sky)' : '2px solid transparent',
        cursor: 'pointer',
      }}
    >
      {label}
      {count != null && count > 0 && (
        <span
          className="font-mono text-xs px-1.5 py-0.5 rounded-full"
          style={{
            background: active ? 'rgba(121,192,255,0.12)' : 'var(--rt-surface2)',
            border: `1px solid ${active ? 'rgba(121,192,255,0.3)' : 'var(--rt-border)'}`,
            color: active ? 'var(--rt-sky)' : 'var(--rt-muted)',
          }}
        >
          {count}
        </span>
      )}
    </button>
  );
}

function TargetRow({ target, onScan, onRemove }) {
  const type = inferTargetType(target.value);
  const isTemp = String(target.id).startsWith('temp-');
  const typeColor = type === 'IP' || type === 'CIDR' ? 'var(--rt-orchid)' : 'var(--rt-sky)';
  const typeBorder = type === 'IP' || type === 'CIDR' ? 'rgba(188,140,255,0.25)' : 'rgba(121,192,255,0.25)';
  const typeBg = type === 'IP' || type === 'CIDR' ? 'rgba(188,140,255,0.1)' : 'rgba(121,192,255,0.1)';

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors"
      style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--rt-border-bright)'; e.currentTarget.style.background = 'var(--rt-surface2)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--rt-border)'; e.currentTarget.style.background = 'var(--rt-surface)'; }}
    >
      <span
        className="font-mono text-xs font-bold px-2 py-0.5 rounded flex-shrink-0"
        style={{ color: typeColor, border: `1px solid ${typeBorder}`, background: typeBg, textTransform: 'uppercase' }}
      >
        {type}
      </span>
      <span className="font-mono text-xs flex-1 truncate" style={{ color: 'var(--rt-text)' }}>
        {target.value}
      </span>
      {isTemp && <span className="text-xs opacity-50" style={{ color: 'var(--rt-sky)' }}>saving…</span>}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <button
          onClick={onScan}
          className="px-2 py-1 rounded text-xs transition-colors"
          style={{ border: '1px solid var(--rt-border)', color: 'var(--rt-muted)' }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--rt-text)'; e.currentTarget.style.borderColor = 'var(--rt-border-bright)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--rt-muted)'; e.currentTarget.style.borderColor = 'var(--rt-border)'; }}
        >
          Scan
        </button>
        <button
          onClick={onRemove}
          className="px-2 py-1 rounded text-xs transition-colors"
          style={{ border: '1px solid var(--rt-border)', color: 'var(--rt-muted)' }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--rt-ember)'; e.currentTarget.style.borderColor = 'rgba(248,81,73,0.4)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--rt-muted)'; e.currentTarget.style.borderColor = 'var(--rt-border)'; }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}

function ModeOption({ selected, onClick, label, sub }) {
  return (
    <button
      onClick={onClick}
      className="rounded-lg px-3 py-3 text-left transition-colors"
      style={{
        background: selected ? 'rgba(121,192,255,0.08)' : 'var(--rt-surface2)',
        border: `1px solid ${selected ? 'var(--rt-sky)' : 'var(--rt-border)'}`,
      }}
    >
      <span className="block text-xs font-semibold" style={{ color: selected ? 'var(--rt-sky)' : 'var(--rt-muted)' }}>
        {label}
      </span>
      <span className="block font-mono text-xs mt-0.5" style={{ color: 'var(--rt-dim)' }}>{sub}</span>
    </button>
  );
}

function FindingCard({ finding }) {
  const sev = finding.severity?.toLowerCase() || 'low';
  const style = SEV_STYLE[sev] || SEV_STYLE.low;
  const [open, setOpen] = React.useState(false);

  return (
    <div
      className="rounded-lg px-4 py-4 cursor-pointer transition-colors"
      style={{
        background: 'var(--rt-surface)',
        border: `1px solid var(--rt-border)`,
        borderLeft: `3px solid ${style.leftBorder}`,
      }}
      onMouseEnter={e => { e.currentTarget.style.background = 'var(--rt-surface2)'; }}
      onMouseLeave={e => { e.currentTarget.style.background = 'var(--rt-surface)'; }}
      onClick={() => setOpen(o => !o)}
    >
      <div className="flex items-start justify-between gap-3 mb-1">
        <p className="text-sm font-semibold" style={{ color: 'var(--rt-text)' }}>{finding.title}</p>
        <span
          className="font-mono text-xs font-bold px-2 py-0.5 rounded flex-shrink-0"
          style={{ background: style.bg, color: style.color, textTransform: 'uppercase' }}
        >
          {sev}
        </span>
      </div>
      <p className="text-xs mb-2" style={{ color: 'var(--rt-muted)' }}>{finding.content}</p>
      <div className="flex items-center gap-3 font-mono text-xs" style={{ color: 'var(--rt-dim)' }}>
        {finding.finding_type && <span>{finding.finding_type}</span>}
        {finding.confidence && <span>· {finding.confidence}% confidence</span>}
      </div>
      {open && finding.evidence && (
        <div className="mt-3 px-3 py-2 rounded font-mono text-xs" style={{ background: '#000', color: '#3fb950' }}>
          {finding.evidence}
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value, mono }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span style={{ color: 'var(--rt-muted)' }}>{label}</span>
      <span className={mono ? 'font-mono font-medium' : 'font-medium'} style={{ color: 'var(--rt-text)' }}>
        {value}
      </span>
    </div>
  );
}

function SidebarBtn({ children, onClick, danger }) {
  return (
    <button
      onClick={onClick}
      className="w-full px-3 py-2 rounded-lg text-sm text-center font-medium transition-colors"
      style={{
        background: 'var(--rt-surface2)',
        border: `1px solid ${danger ? 'rgba(248,81,73,0.3)' : 'var(--rt-border)'}`,
        color: danger ? 'var(--rt-ember)' : 'var(--rt-text)',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = danger ? 'rgba(248,81,73,0.6)' : 'var(--rt-border-bright)'; e.currentTarget.style.background = 'var(--rt-surface)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = danger ? 'rgba(248,81,73,0.3)' : 'var(--rt-border)'; e.currentTarget.style.background = 'var(--rt-surface2)'; }}
    >
      {children}
    </button>
  );
}
