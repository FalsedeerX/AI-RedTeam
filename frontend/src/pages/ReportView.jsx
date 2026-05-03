import React from 'react';
import { apiGet } from '../lib/api';

// Severity display config — order determines render priority (highest first).
const SEVERITY_CONFIG = {
  critical: { label: 'Critical', dot: '🔴', borderColor: 'border-red-600',   bg: 'bg-red-50',    headerColor: 'text-red-800',   badgeBg: 'bg-red-600'    },
  high:     { label: 'High',     dot: '🟠', borderColor: 'border-orange-400', bg: 'bg-orange-50', headerColor: 'text-orange-800',badgeBg: 'bg-orange-500' },
  medium:   { label: 'Medium',   dot: '🟡', borderColor: 'border-yellow-400', bg: 'bg-yellow-50', headerColor: 'text-yellow-800',badgeBg: 'bg-yellow-500' },
  low:      { label: 'Low',      dot: '🔵', borderColor: 'border-blue-300',   bg: 'bg-blue-50',   headerColor: 'text-blue-800',  badgeBg: 'bg-blue-500'   },
};
const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low'];

// Derive a letter grade from the worst severity present in findings.
function computeScore(findings) {
  if (findings.some(f => f.severity === 'critical')) return { grade: 'F', label: 'Critical Risk',    color: 'bg-red-600',    border: 'border-red-800',    text: 'text-red-800'    };
  if (findings.some(f => f.severity === 'high'))     return { grade: 'D', label: 'High Risk',       color: 'bg-orange-500', border: 'border-orange-700',  text: 'text-orange-800' };
  if (findings.some(f => f.severity === 'medium'))   return { grade: 'C', label: 'Moderate Risk',   color: 'bg-yellow-500', border: 'border-yellow-700',  text: 'text-yellow-800' };
  if (findings.some(f => f.severity === 'low'))      return { grade: 'B', label: 'Low Risk',        color: 'bg-blue-500',   border: 'border-blue-700',    text: 'text-blue-800'   };
  return                                                     { grade: 'A', label: 'No Issues Found', color: 'bg-green-600',  border: 'border-green-800',   text: 'text-green-800'  };
}

export default function ReportView({ targets, reportId, runId, onStartNewScan }) {
  const [report, setReport] = React.useState(null);
  const [findings, setFindings] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');

  React.useEffect(() => {
    if (!reportId) {
      setError('Report data is unavailable. The scan may not have completed successfully.');
      setLoading(false);
      return;
    }

    async function fetchData() {
      try {
        const reportData = await apiGet(`/reports/${reportId}`);
        setReport(reportData);

        if (reportData.report_format === 'json') {
          try {
            const parsed = JSON.parse(reportData.content);
            const normalized = (Array.isArray(parsed) ? parsed : []).map(f => ({
              ...f,
              severity: (f.severity || '').toLowerCase(),
            }));
            setFindings(normalized);
          } catch {
            setFindings([]);
          }
        } else if (runId) {
          const findingsData = await apiGet(`/scans/${runId}/findings`);
          setFindings(findingsData);
        }
      } catch (err) {
        setError(err.message || 'Failed to load report data.');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [reportId, runId]);

  // Group findings by severity in display order.
  const grouped = React.useMemo(() => {
    const groups = {};
    for (const sev of SEVERITY_ORDER) {
      const matches = findings.filter(f => f.severity === sev);
      if (matches.length > 0) groups[sev] = matches;
    }
    return groups;
  }, [findings]);

  const score = React.useMemo(() => computeScore(findings), [findings]);

  // Build a summary line: "3 findings: 1 high, 1 medium, 1 low"
  const findingSummary = React.useMemo(() => {
    if (findings.length === 0) return 'No findings detected.';
    const parts = SEVERITY_ORDER
      .filter(sev => grouped[sev])
      .map(sev => `${grouped[sev].length} ${sev}`);
    return `${findings.length} finding${findings.length !== 1 ? 's' : ''}: ${parts.join(', ')}.`;
  }, [findings, grouped]);

  // Issue 8 — JSON export via Blob download.
  const handleDownloadJSON = () => {
    const payload = {
      title: report?.title ?? 'Security Assessment Report',
      summary: report?.summary ?? '',
      generated_at: report?.created_at ?? new Date().toISOString(),
      targets: targets ?? [],
      findings,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security-report-${reportId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const targetDisplay = (targets ?? []).join(', ');
  const timestamp = report?.created_at
    ? new Date(report.created_at).toLocaleString()
    : new Date().toLocaleString();

  // --- Loading state ---
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-2xl text-gray-600 animate-pulse">Loading report...</p>
        </div>
      </div>
    );
  }

  // --- Error state ---
  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-8">
        <div className="max-w-xl w-full bg-white rounded-lg shadow-xl p-8 border-2 border-red-300 text-center">
          <p className="text-xl font-bold text-red-700 mb-4">Failed to load report</p>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={onStartNewScan}
            className="bg-purple-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-purple-700 transition-colors"
          >
            Start New Scan
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-8">
      <div className="max-w-4xl w-full bg-white rounded-lg shadow-2xl p-8 border-2 border-gray-300">

        {/* Header */}
        <div className="border-b-2 border-gray-300 pb-6 mb-6">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            {report?.title ?? 'Security Assessment Report'}
          </h1>
          <div className="flex justify-between items-center text-gray-600">
            <div>
              <p className="text-lg">
                <span className="font-semibold">Target:</span> {targetDisplay}
              </p>
              <p className="text-sm mt-1">
                <span className="font-semibold">Generated:</span> {timestamp}
              </p>
              <p className="text-sm mt-1 text-gray-500">{findingSummary}</p>
            </div>
            <div className="text-right">
              <p className="text-sm">AI RedTeam Platform</p>
              <p className="text-xs text-gray-500">Purdue University</p>
            </div>
          </div>
        </div>

        {/* Security Scorecard */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Security Scorecard</h2>
          <div className={`flex items-center gap-8 ${score.color.replace('bg-', 'bg-').replace('600', '50').replace('500', '50')} border-2 ${score.border.replace('border-', 'border-')} rounded-lg p-6`}
               style={{ background: 'var(--scorecard-bg)' }}>
            <div className="flex-shrink-0">
              <div className={`w-32 h-32 rounded-full ${score.color} flex items-center justify-center border-4 ${score.border}`}>
                <span className="text-5xl font-bold text-white">{score.grade}</span>
              </div>
              <p className={`text-center mt-2 font-bold ${score.text}`}>Security Score</p>
            </div>
            <div className="flex-1">
              <p className="text-lg font-semibold text-gray-900 mb-2">{score.label}</p>
              <p className="text-gray-700">
                {report?.summary ?? 'Assessment complete.'}
              </p>
            </div>
          </div>
        </div>

        {/* Findings — grouped by severity */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Vulnerability Findings</h2>

          {findings.length === 0 ? (
            <div className="border-2 border-green-400 rounded-lg p-6 bg-green-50 text-center">
              <p className="text-green-800 font-semibold text-lg">No findings detected.</p>
              <p className="text-gray-600 mt-1 text-sm">The target did not surface any actionable issues during this assessment.</p>
            </div>
          ) : (
            <div className="space-y-8">
              {SEVERITY_ORDER.filter(sev => grouped[sev]).map(sev => {
                const cfg = SEVERITY_CONFIG[sev];
                return (
                  <div key={sev}>
                    {/* Severity group header */}
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xl">{cfg.dot}</span>
                      <h3 className={`text-xl font-bold ${cfg.headerColor}`}>
                        {cfg.label} ({grouped[sev].length})
                      </h3>
                    </div>

                    <div className="space-y-4">
                      {grouped[sev].map((finding, idx) => (
                        <FindingCard key={finding.id ?? idx} finding={finding} cfg={cfg} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 pt-6 border-t-2 border-gray-300">
          <button
            onClick={handleDownloadJSON}
            className="flex-1 bg-blue-600 text-white font-bold py-4 px-6 rounded-lg hover:bg-blue-700 transition-colors text-lg flex items-center justify-center gap-2"
          >
            <span>📥</span>
            <span>Download Report (JSON)</span>
          </button>
          <button
            onClick={onStartNewScan}
            className="flex-1 bg-purple-600 text-white font-bold py-4 px-6 rounded-lg hover:bg-purple-700 transition-colors text-lg flex items-center justify-center gap-2"
          >
            <span>🔄</span>
            <span>Exit & Start New Scan</span>
          </button>
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-gray-200 text-center text-xs text-gray-500">
          <p>This report was generated by AI RedTeam autonomous security assessment platform.</p>
          <p className="mt-1">For questions or support, contact the development team at Purdue University.</p>
        </div>
      </div>
    </div>
  );
}

// Individual finding card — shown within a severity group.
// Handles both full scan findings (title, content, evidence, confidence,
// finding_type) and lightweight agent findings (severity + description).
function FindingCard({ finding, cfg }) {
  const [evidenceOpen, setEvidenceOpen] = React.useState(false);

  const title = finding.title || finding.description || 'Untitled Finding';
  const body = finding.content || finding.description || '';

  return (
    <div className={`border-2 ${cfg.borderColor} rounded-lg p-6 ${cfg.bg}`}>
      <div className="flex items-start gap-3">
        <div className="flex-1">
          {/* Title row */}
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <h4 className={`text-lg font-bold ${cfg.headerColor}`}>{title}</h4>
            <span className={`text-xs font-bold text-white px-2 py-0.5 rounded ${cfg.badgeBg} uppercase`}>
              {finding.severity}
            </span>
            {finding.finding_type && (
              <span className="text-xs text-gray-500 uppercase tracking-wide border border-gray-300 rounded px-2 py-0.5">
                {finding.finding_type}
              </span>
            )}
          </div>

          {/* Description */}
          <p className="text-gray-700 mb-3">{body}</p>

          {/* Confidence */}
          {finding.confidence != null && (
            <p className="text-sm text-gray-500 mb-2">
              <span className="font-semibold">Confidence:</span> {finding.confidence}%
            </p>
          )}

          {/* Evidence — collapsible */}
          {finding.evidence && (
            <>
              <button
                onClick={() => setEvidenceOpen(o => !o)}
                className="text-sm font-semibold text-gray-600 hover:text-gray-900 underline focus:outline-none"
              >
                {evidenceOpen ? 'Hide Evidence ▲' : 'Show Evidence ▼'}
              </button>
              {evidenceOpen && (
                <div className="mt-2 bg-gray-900 text-green-400 font-mono text-sm p-3 rounded">
                  {finding.evidence}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
