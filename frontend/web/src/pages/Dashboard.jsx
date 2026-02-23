import React from 'react';
import ReportView from './ReportView';
import { apiGet, apiPost } from '../lib/api';

// TODO: pass projectId to POST /start_scan body once the run-start
// endpoint is wired to the new backend (Phase 2).
export default function Dashboard({ username, email, targets, scanType, projectId }) {
  const [logs, setLogs] = React.useState([]);
  const [scanStatus, setScanStatus] = React.useState('IDLE');
  const [pendingAction, setPendingAction] = React.useState(null);
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [scanStarted, setScanStarted] = React.useState(false);
  const [error, setError] = React.useState('');
  const [viewingReport, setViewingReport] = React.useState(false);
  const [reportType, setReportType] = React.useState('sql_injection');
  const terminalRef = React.useRef(null);

  // Auto-scroll terminal to bottom when new logs arrive
  React.useEffect(() => {
      if (terminalRef.current) {
          terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
      }
  }, [logs]);

  // Polling effect - runs every 1 second when scan is started
  React.useEffect(() => {
      if (!scanStarted) return;

      const pollInterval = setInterval(async () => {
          try {
              // TODO: Confirm GET /poll_status returns
              //   { status, logs, pending_action, targets, scan_type, report_type }
              const data = await apiGet('/poll_status');

              setLogs(data.logs || []);
              setScanStatus(data.status);
              setPendingAction(data.pending_action);
              setReportType(data.report_type || 'sql_injection');

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
  }, [scanStarted]);

  const handleBeginRecon = async () => {
      setError('');
      setScanStarted(true);

      try {
          // TODO: Add project_id to body once backend run-start endpoint
          //   accepts it: { targets, scan_type, project_id: projectId }
          const data = await apiPost('/start_scan', {
              targets,
              scan_type: scanType,
          });

          if (!data.success) {
              setError(data.message || 'Failed to start scan');
              setScanStarted(false);
          }
      } catch (err) {
          console.error('Start scan error:', err);
          setError(err.message || 'Could not connect to backend. Is the server running?');
          setScanStarted(false);
      }
  };

  const handleApprove = async () => {
      try {
          const data = await apiPost('/approve_action');
          if (data.success) {
              setIsModalOpen(false);
              setPendingAction(null);
          }
      } catch (err) {
          console.error('Approve action error:', err);
          setError('Failed to approve action');
      }
  };

  const handleDeny = async () => {
      try {
          const data = await apiPost('/deny_action');
          if (data.success) {
              setIsModalOpen(false);
              setPendingAction(null);
          } else {
              setError('Failed to deny action');
          }
      } catch (err) {
          console.error('Deny action error:', err);
          setError('Failed to communicate denial to AI');
      }
  };

  const handleKillSwitch = async () => {
      try {
          const data = await apiPost('/kill_scan');
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

  const handleResetScan = async () => {
      try {
          const data = await apiPost('/reset_scan');
          if (data.success) {
              setLogs([]);
              setScanStatus('IDLE');
              setPendingAction(null);
              setIsModalOpen(false);
              setScanStarted(false);
              setError('');
              setViewingReport(false);
          } else {
              setError('Failed to reset scan');
          }
      } catch (err) {
          console.error('Reset scan error:', err);
          setError('Could not reset scan');
      }
  };

  // Helper function to determine log color based on content
  const getLogColor = (message) => {
      if (message.includes('[ALERT]')) return 'text-yellow-400';
      if (message.includes('[SUCCESS]')) return 'text-cyan-400';
      return 'text-green-400';
  };

  const handleDownloadPDF = () => {
      alert('Downloading comprehensive security report...\n\nReport includes:\n- Executive summary\n- Detailed vulnerability analysis\n- Remediation recommendations\n- CVSS scores and risk assessments');
  };

  // THIS MUST BE BEFORE THE MAIN RETURN
  // If user is viewing report, show ReportView instead of terminal
  if (viewingReport) {
      return (
          <ReportView 
              targets={targets}
              logs={logs}
              reportType={reportType}
              onDownloadPDF={handleDownloadPDF}
              onStartNewScan={handleResetScan}
          />
      );
  }

  return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
          <div className="max-w-4xl w-full mx-4 p-8 bg-gray-800 text-white rounded-lg shadow-xl relative">
              {/* Emergency Kill Switch Button */}
              {(scanStatus === 'RUNNING' || scanStatus === 'NEEDS_APPROVAL') && (
                  <button
                      onClick={handleKillSwitch}
                      className="absolute top-4 right-4 bg-red-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2 border-2 border-red-400 shadow-lg"
                  >
                      <span className="text-xl">🛑</span>
                      <span>Emergency Stop</span>
                  </button>
              )}
              
              <div className="space-y-6">
                  {/* Welcome Header */}
                  <div className="text-center mb-8">
                      <h1 className="text-3xl font-bold mb-2">
                          Welcome, {username}
                      </h1>
                      {email && (
                          <p className="text-gray-400">
                              {email}
                          </p>
                      )}
                  </div>

                  {/* Engagement Target Header */}
                  <div className="mb-6">
                      <h3 className="text-xl font-semibold text-gray-300">
                          Engagement Target: <span className="text-blue-400">{targets.join(', ')}</span>
                      </h3>
                  </div>

                  {/* Status Indicator */}
                  <div className="bg-gray-700 rounded-lg p-4 mb-6">
                      <p className="text-lg text-gray-200">
                          {scanStatus === 'IDLE' && '🟢 AI Agent Online - Waiting for Command'}
                          {scanStatus === 'RUNNING' && '🔵 AI Agent Running - Scanning Target...'}
                          {scanStatus === 'NEEDS_APPROVAL' && '🟡 AI Agent Paused - Awaiting Authorization'}
                          {scanStatus === 'COMPLETED' && '✅ AI Agent Completed - Scan Finished'}
                          {scanStatus === 'TERMINATED' && '🔴 AI Agent TERMINATED - Emergency Stop Activated'}
                      </p>
                  </div>

                  {/* Error Display */}
                  {error && (
                      <div className="bg-red-900 bg-opacity-30 border border-red-500 rounded-lg p-4">
                          <p className="text-red-400">{error}</p>
                      </div>
                  )}

                  {/* Begin Button (shown before scan starts) */}
                  {!scanStarted && (
                      <button
                          onClick={handleBeginRecon}
                          className="w-full bg-blue-600 text-white font-bold py-4 rounded-lg hover:bg-blue-700 transition-colors text-lg"
                      >
                          Begin Reconnaissance
                      </button>
                  )}

                  {/* Terminal Window (shown after scan starts) */}
                  {scanStarted && (
                      <div className="bg-black rounded-lg p-4 border-2 border-green-500">
                          <div className="mb-2 flex items-center justify-between">
                              <span className="text-green-400 font-mono text-sm">
                                  root@ai-redteam:~#
                              </span>
                              <span className="text-green-400 font-mono text-xs">
                                  Status: {scanStatus}
                              </span>
                          </div>
                          <div 
                              ref={terminalRef}
                              className="h-96 overflow-y-auto text-green-400 font-mono text-sm space-y-1"
                          >
                              {logs.length === 0 ? (
                                  <p className="text-green-500 animate-pulse">Initializing AI Agent...</p>
                              ) : (
                                  logs.map((log, index) => (
                                      <div key={index} className="hover:bg-gray-900">
                                          <span className="text-green-600">
                                              [{new Date(log.timestamp).toLocaleTimeString()}]
                                          </span>
                                          {' '}
                                          <span className={getLogColor(log.message)}>
                                              {log.message}
                                          </span>
                                      </div>
                                  ))
                              )}
                              {scanStatus === 'RUNNING' && (
                                  <p className="text-green-500 animate-pulse">▊</p>
                              )}
                          </div>
                      </div>
                  )}

                  {/* View Report Button (shown when scan is completed) */}
                  {scanStatus === 'COMPLETED' && !viewingReport && (
                      <button
                          onClick={() => setViewingReport(true)}
                          className="w-full bg-green-600 text-white font-bold py-4 rounded-lg hover:bg-green-700 transition-colors text-lg mt-6"
                      >
                          📄 View Security Assessment Report
                      </button>
                  )}
              </div>
          </div>

          {/* HITL Modal Overlay */}
          {isModalOpen && (
              <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
                  <div className="bg-gray-800 rounded-lg p-8 max-w-lg w-full mx-4 border-4 border-yellow-500 shadow-2xl">
                      {/* Header */}
                      <div className="text-center mb-6">
                          <h2 className="text-3xl font-bold text-yellow-400 mb-2">
                              ⚠️ CRITICAL SAFETY INTERVENTION REQUIRED
                          </h2>
                          <p className="text-red-400 font-semibold">
                              Human-in-the-Loop Authorization Needed
                          </p>
                      </div>

                      {/* Body */}
                      <div className="bg-gray-900 rounded-lg p-6 mb-6">
                          <p className="text-white text-lg mb-2">
                              <span className="font-bold">Pending Action:</span>
                          </p>
                          <p className="text-yellow-300 text-xl font-mono">
                              {pendingAction}
                          </p>
                      </div>

                      <div className="bg-red-900 bg-opacity-30 border border-red-500 rounded-lg p-4 mb-6">
                          <p className="text-red-300 text-sm">
                              ⚠️ This action could have significant impact. Review carefully before proceeding.
                          </p>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex gap-4">
                          <button
                              onClick={handleDeny}
                              className="flex-1 bg-red-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-red-700 transition-colors"
                          >
                              ❌ DENY
                          </button>
                          <button
                              onClick={handleApprove}
                              className="flex-1 bg-green-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-green-700 transition-colors"
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
