import React from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import ReportView from './ReportView';
import { apiGet, apiPost } from '../lib/api';

export default function Dashboard() {
  const { projectId, runId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // Scan config comes from navigation state set by ProjectWorkspace
  const { targets = [], username = '' } = location.state || {};

  const [logs, setLogs] = React.useState([]);
  const [scanStatus, setScanStatus] = React.useState('running');
  const [pendingHitl, setPendingHitl] = React.useState(null);
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [error, setError] = React.useState('');
  const [viewingReport, setViewingReport] = React.useState(false);
  const [reportId, setReportId] = React.useState(null);
  const [currentPhase, setCurrentPhase] = React.useState('recon');
  const [stepCount, setStepCount] = React.useState(0);
  const [phaseHistory, setPhaseHistory] = React.useState([]);
  const [findings, setFindings] = React.useState([]);
  const terminalRef = React.useRef(null);

  // Auto-scroll terminal to bottom when new logs arrive
  React.useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  // Polling — starts immediately because the scan was already launched in the workspace.
  React.useEffect(() => {
    if (!runId) return;

    const pollInterval = setInterval(async () => {
      try {
        const data = await apiGet(`/agent/${runId}/status`);

        setLogs(data.logs || []);
        setScanStatus(data.status);
        setCurrentPhase(data.current_phase || 'recon');
        setStepCount(data.step_count || 0);
        setPhaseHistory(data.phase_history || []);
        setFindings(data.findings || []);
        setPendingHitl(data.pending_hitl || null);

        if (data.status === 'hitl_pending' && data.pending_hitl) {
          setIsModalOpen(true);
        }

        if (data.status === 'completed' || data.status === 'killed' || data.status === 'error') {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Polling error:', err);
        setError('Lost connection to backend');
      }
    }, 1000);

    return () => clearInterval(pollInterval);
  }, [runId]);

  const handleApprove = async () => {
    try {
      const data = await apiPost(`/agent/${runId}/approve`);
      if (data.success) {
        setIsModalOpen(false);
        setPendingHitl(null);
      }
    } catch (err) {
      console.error('Approve error:', err);
      setError('Failed to approve action');
    }
  };

  const handleDeny = async () => {
    try {
      const data = await apiPost(`/agent/${runId}/deny`);
      if (data.success) {
        setIsModalOpen(false);
        setPendingHitl(null);
      } else {
        setError('Failed to deny action');
      }
    } catch (err) {
      console.error('Deny error:', err);
      setError('Failed to communicate denial to AI');
    }
  };

  const handleKillSwitch = async () => {
    try {
      const data = await apiPost(`/agent/${runId}/kill`);
      if (data.success) {
        setScanStatus('killed');
        setIsModalOpen(false);
        setPendingHitl(null);
        setError('⚠️ Session Terminated by Emergency Switch');
      } else {
        setError('Failed to activate kill switch');
      }
    } catch (err) {
      console.error('Kill switch error:', err);
      setError('Failed to activate emergency stop');
    }
  };

  // Return to the workspace's findings tab after a scan completes.
  const handleReturnToWorkspace = () => {
    navigate(`/projects/${projectId}?tab=findings`);
  };

  const getLogColor = (message, node) => {
    if (node === 'risk_gate_node') return '#d29922';
    if (node === 'system') return '#79c0ff';
    if (message.includes('[ALERT]') || message.includes('HITL')) return '#d29922';
    if (message.includes('[SUCCESS]') || message.includes('completed')) return '#79c0ff';
    if (message.includes('failed') || message.includes('error')) return '#f85149';
    return '#3fb950';
  };

  const PHASE_LABELS = {
    recon: '🔍 Recon',
    enumeration: '📡 Enumeration',
    exploitation: '⚡ Exploitation',
    complete: '📄 Complete',
  };
  const PHASE_ORDER = ['recon', 'enumeration', 'exploitation', 'complete'];

  if (viewingReport) {
    return (
      <ReportView
        targets={targets}
        reportId={reportId}
        runId={runId}
        onStartNewScan={handleReturnToWorkspace}
      />
    );
  }

  const isActive = scanStatus === 'running' || scanStatus === 'hitl_pending';

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: '#0d1117' }}>
      <div
        className="w-full max-w-4xl mx-4 p-8 rounded-lg shadow-xl relative"
        style={{ background: '#161b22', border: '1px solid #30363d' }}
      >
        {/* Emergency Kill Switch */}
        {isActive && (
          <button
            onClick={handleKillSwitch}
            className="absolute top-4 right-4 font-bold py-2 px-4 rounded-lg flex items-center gap-2 border-2 shadow-lg transition-opacity hover:opacity-85"
            style={{ background: '#f85149', color: 'white', borderColor: 'rgba(248,81,73,0.6)' }}
          >
            <span className="text-xl">🛑</span>
            <span>Emergency Stop</span>
          </button>
        )}

        <div className="space-y-6">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold mb-1" style={{ color: '#e6edf3' }}>
              Scan in Progress
            </h1>
            {username && (
              <p className="text-sm" style={{ color: '#7d8590' }}>Running as {username}</p>
            )}
          </div>

          {/* Target display */}
          <div className="mb-4">
            <p className="text-sm font-semibold" style={{ color: '#7d8590' }}>
              Target{targets.length > 1 ? 's' : ''}:{' '}
              <span style={{ color: '#79c0ff', fontFamily: 'monospace' }}>{targets.join(', ')}</span>
            </p>
          </div>

          {/* Phase progress bar */}
          <div
            className="rounded-lg p-4"
            style={{ background: '#1c2333', border: '1px solid #30363d' }}
          >
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm" style={{ color: '#e6edf3' }}>
                {scanStatus === 'running' && '🔵 AI Agent Running — Scanning Target…'}
                {scanStatus === 'hitl_pending' && '🟡 AI Agent Paused — Awaiting Your Authorization'}
                {scanStatus === 'completed' && '✅ Scan Complete — Review your findings below'}
                {scanStatus === 'killed' && '🔴 Scan Terminated — Emergency Stop Activated'}
                {scanStatus === 'error' && '❌ Agent Error — Something went wrong'}
              </p>
              <span className="font-mono text-xs" style={{ color: '#7d8590' }}>
                Step {stepCount}
              </span>
            </div>
            {/* Phase indicator */}
            <div className="flex items-center gap-1">
              {PHASE_ORDER.map((phase, i) => {
                const inHistory = phaseHistory.includes(phase);
                const isCurrent = phase === currentPhase;
                const isCompleted = inHistory && !isCurrent;
                // While running, highlight the current phase in blue; after finishing,
                // show every visited phase (including the last current) as green.
                const active = isCurrent && isActive;
                const done = isCompleted || (isCurrent && !isActive && inHistory);
                return (
                  <React.Fragment key={phase}>
                    <div
                      className="flex-1 rounded-full text-center text-xs py-1 font-semibold transition-all"
                      style={{
                        background: active ? 'rgba(121,192,255,0.15)' : done ? 'rgba(63,185,80,0.12)' : 'rgba(110,118,129,0.1)',
                        border: `1px solid ${active ? '#79c0ff' : done ? '#3fb950' : '#30363d'}`,
                        color: active ? '#79c0ff' : done ? '#3fb950' : '#484f58',
                      }}
                    >
                      {PHASE_LABELS[phase] || phase}
                    </div>
                    {i < PHASE_ORDER.length - 1 && (
                      <span style={{ color: '#30363d' }}>›</span>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div
              className="rounded-lg p-4 text-sm"
              style={{ background: 'rgba(248,81,73,0.08)', border: '1px solid rgba(248,81,73,0.3)', color: '#f85149' }}
            >
              {error}
            </div>
          )}

          {/* Terminal window */}
          <div
            className="rounded-lg p-4 border-2"
            style={{ background: '#000', borderColor: '#3fb950' }}
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-sm" style={{ color: '#3fb950' }}>
                root@ai-redteam:~#
              </span>
              <span className="font-mono text-xs" style={{ color: '#3fb950' }}>
                {scanStatus}
              </span>
            </div>
            <div
              ref={terminalRef}
              className="h-96 overflow-y-auto font-mono text-sm space-y-1"
            >
              {logs.length === 0 ? (
                <p className="animate-pulse" style={{ color: '#3fb950' }}>Initializing AI Agent…</p>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="hover:bg-gray-900">
                    <span style={{ color: '#237a37' }}>
                      [{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '...'}]
                    </span>{' '}
                    {log.node && (
                      <span className="font-bold" style={{ color: '#bc8cff' }}>
                        [{log.node}]{' '}
                      </span>
                    )}
                    <span style={{ color: getLogColor(log.message || '', log.node) }}>
                      {log.message || ''}
                    </span>
                    {log.tool_calls && log.tool_calls.length > 0 && (
                      <span style={{ color: '#7d8590' }}>
                        {' '}→ {log.tool_calls.map(tc => tc.name).join(', ')}
                      </span>
                    )}
                  </div>
                ))
              )}
              {scanStatus === 'running' && (
                <p className="animate-pulse" style={{ color: '#3fb950' }}>▊</p>
              )}
            </div>
          </div>

          {/* Post-scan actions */}
          {scanStatus === 'completed' && !viewingReport && (
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setViewingReport(true)}
                className="flex-1 font-bold py-3 rounded-lg transition-opacity hover:opacity-85"
                style={{ background: '#3fb950', color: '#0d1117' }}
              >
                📄 View Full Report
              </button>
              <button
                onClick={handleReturnToWorkspace}
                className="flex-1 font-bold py-3 rounded-lg transition-colors"
                style={{ background: '#1c2333', border: '1px solid #30363d', color: '#79c0ff' }}
              >
                💾 Save & View Report
              </button>
            </div>
          )}

          {(scanStatus === 'killed' || scanStatus === 'error') && (
            <button
              onClick={handleReturnToWorkspace}
              className="w-full font-bold py-3 rounded-lg transition-colors"
              style={{ background: '#1c2333', border: '1px solid #30363d', color: '#79c0ff' }}
            >
              ← Return to Project
            </button>
          )}
        </div>
      </div>

      {/* HITL Modal */}
      {isModalOpen && pendingHitl && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: 'rgba(0,0,0,0.75)' }}
        >
          <div
            className="rounded-lg p-8 w-full max-w-lg mx-4 shadow-2xl border-4"
            style={{
              background: '#161b22',
              borderColor: pendingHitl.risk_level === 'HIGH' ? '#f85149'
                         : pendingHitl.risk_level === 'MEDIUM' ? '#d29922'
                         : '#3fb950',
            }}
          >
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-2" style={{ color: '#d29922' }}>
                ⚠️ HUMAN-IN-THE-LOOP AUTHORIZATION
              </h2>
              {/* Risk level badge */}
              <span
                className="inline-block font-mono text-xs font-bold px-3 py-1 rounded-full"
                style={{
                  background: pendingHitl.risk_level === 'HIGH' ? 'rgba(248,81,73,0.15)'
                             : pendingHitl.risk_level === 'MEDIUM' ? 'rgba(210,153,34,0.15)'
                             : 'rgba(63,185,80,0.15)',
                  color: pendingHitl.risk_level === 'HIGH' ? '#f85149'
                        : pendingHitl.risk_level === 'MEDIUM' ? '#d29922'
                        : '#3fb950',
                  border: `1px solid ${pendingHitl.risk_level === 'HIGH' ? 'rgba(248,81,73,0.4)'
                          : pendingHitl.risk_level === 'MEDIUM' ? 'rgba(210,153,34,0.4)'
                          : 'rgba(63,185,80,0.4)'}`,
                }}
              >
                RISK: {pendingHitl.risk_level || 'HIGH'}
              </span>
            </div>

            {/* Description */}
            <div
              className="rounded-lg p-4 mb-4"
              style={{ background: '#0d1117', border: '1px solid #30363d' }}
            >
              <p className="text-sm font-bold mb-2" style={{ color: '#e6edf3' }}>Description:</p>
              <p className="text-sm" style={{ color: '#d29922' }}>{pendingHitl.description}</p>
            </div>

            {/* Proposed actions */}
            {pendingHitl.proposed_actions && pendingHitl.proposed_actions.length > 0 && (
              <div
                className="rounded-lg p-4 mb-4"
                style={{ background: '#0d1117', border: '1px solid #30363d' }}
              >
                <p className="text-sm font-bold mb-3" style={{ color: '#e6edf3' }}>Proposed Actions:</p>
                <div className="space-y-3">
                  {pendingHitl.proposed_actions.map((action, i) => (
                    <div
                      key={i}
                      className="rounded p-3"
                      style={{ background: 'rgba(121,192,255,0.05)', border: '1px solid #21262d' }}
                    >
                      <p className="font-mono text-xs font-bold mb-1" style={{ color: '#79c0ff' }}>
                        {action.tool || 'unknown'}
                      </p>
                      {action.args && Object.keys(action.args).length > 0 && (
                        <pre className="text-xs mb-1 overflow-x-auto" style={{ color: '#7d8590' }}>
                          {JSON.stringify(action.args, null, 2)}
                        </pre>
                      )}
                      {action.reason && (
                        <p className="text-xs" style={{ color: '#8b949e' }}>💡 {action.reason}</p>
                      )}
                      {action.raw && (
                        <p className="text-xs font-mono" style={{ color: '#8b949e' }}>{action.raw}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div
              className="rounded-lg p-4 mb-6 text-sm"
              style={{ background: 'rgba(248,81,73,0.08)', border: '1px solid rgba(248,81,73,0.3)', color: '#f85149' }}
            >
              ⚠️ This action could have significant impact. Review carefully before proceeding.
            </div>

            <div className="flex gap-4">
              <button
                onClick={handleDeny}
                className="flex-1 font-bold py-3 px-6 rounded-lg transition-opacity hover:opacity-85"
                style={{ background: '#f85149', color: 'white' }}
              >
                ❌ DENY
              </button>
              <button
                onClick={handleApprove}
                className="flex-1 font-bold py-3 px-6 rounded-lg transition-opacity hover:opacity-85"
                style={{ background: '#3fb950', color: '#0d1117' }}
              >
                ✓ APPROVE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
