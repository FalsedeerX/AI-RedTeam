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
  const [scanStatus, setScanStatus] = React.useState('RUNNING');
  const [pendingAction, setPendingAction] = React.useState(null);
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [error, setError] = React.useState('');
  const [viewingReport, setViewingReport] = React.useState(false);
  const [reportId, setReportId] = React.useState(null);
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
        const data = await apiGet(`/scans/${runId}/status`);

        setLogs(data.logs || []);
        setScanStatus(data.status);
        setPendingAction(data.pending_action);
        if (data.report_id) setReportId(data.report_id);

        if (data.status === 'NEEDS_APPROVAL' && data.pending_action) {
          setIsModalOpen(true);
        }

        if (data.status === 'COMPLETED' || data.status === 'TERMINATED') {
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
      const data = await apiPost(`/scans/${runId}/approve`);
      if (data.success) {
        setIsModalOpen(false);
        setPendingAction(null);
      }
    } catch (err) {
      console.error('Approve error:', err);
      setError('Failed to approve action');
    }
  };

  const handleDeny = async () => {
    try {
      const data = await apiPost(`/scans/${runId}/deny`);
      if (data.success) {
        setIsModalOpen(false);
        setPendingAction(null);
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
      const data = await apiPost(`/scans/${runId}/kill`);
      if (data.success) {
        setScanStatus('TERMINATED');
        setIsModalOpen(false);
        setPendingAction(null);
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

  const getLogColor = (message) => {
    if (message.includes('[ALERT]')) return '#d29922';
    if (message.includes('[SUCCESS]')) return '#79c0ff';
    return '#3fb950';
  };

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

  const isActive = scanStatus === 'RUNNING' || scanStatus === 'NEEDS_APPROVAL';

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

          {/* Status indicator */}
          <div
            className="rounded-lg p-4"
            style={{ background: '#1c2333', border: '1px solid #30363d' }}
          >
            <p className="text-sm" style={{ color: '#e6edf3' }}>
              {scanStatus === 'RUNNING' && '🔵 AI Agent Running — Scanning Target…'}
              {scanStatus === 'NEEDS_APPROVAL' && '🟡 AI Agent Paused — Awaiting Your Authorization'}
              {scanStatus === 'COMPLETED' && '✅ Scan Complete — Review your findings below'}
              {scanStatus === 'TERMINATED' && '🔴 Scan Terminated — Emergency Stop Activated'}
            </p>
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
                      [{new Date(log.timestamp).toLocaleTimeString()}]
                    </span>{' '}
                    <span style={{ color: getLogColor(log.message) }}>{log.message}</span>
                  </div>
                ))
              )}
              {scanStatus === 'RUNNING' && (
                <p className="animate-pulse" style={{ color: '#3fb950' }}>▊</p>
              )}
            </div>
          </div>

          {/* Post-scan actions */}
          {scanStatus === 'COMPLETED' && !viewingReport && (
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

          {scanStatus === 'TERMINATED' && (
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
      {isModalOpen && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: 'rgba(0,0,0,0.75)' }}
        >
          <div
            className="rounded-lg p-8 w-full max-w-lg mx-4 shadow-2xl border-4"
            style={{ background: '#161b22', borderColor: '#d29922' }}
          >
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-2" style={{ color: '#d29922' }}>
                ⚠️ CRITICAL SAFETY INTERVENTION REQUIRED
              </h2>
              <p className="font-semibold" style={{ color: '#f85149' }}>
                Human-in-the-Loop Authorization Needed
              </p>
            </div>

            <div
              className="rounded-lg p-6 mb-6"
              style={{ background: '#0d1117', border: '1px solid #30363d' }}
            >
              <p className="text-sm font-bold mb-2" style={{ color: '#e6edf3' }}>Pending Action:</p>
              <p className="text-lg font-mono" style={{ color: '#d29922' }}>{pendingAction}</p>
            </div>

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
