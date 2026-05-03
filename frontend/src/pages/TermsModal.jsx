import React from 'react';

export default function TermsModal({ username, email, onAccept, onDecline }) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--rt-bg)' }}>
      <div className="w-full max-w-xl rounded-xl overflow-hidden" style={{ background: 'var(--rt-surface)', border: '1px solid var(--rt-border)' }}>

        {/* Header */}
        <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--rt-border)' }}>
          <p className="text-xs font-mono font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--rt-muted)' }}>
            Legal Agreement
          </p>
          <h1 className="text-lg font-bold" style={{ color: 'var(--rt-text)', letterSpacing: '-0.5px' }}>
            AI RedTeam — End User License &amp; Liability Agreement
          </h1>
          {username && (
            <p className="text-xs mt-1" style={{ color: 'var(--rt-muted)' }}>
              Agreement for: <span style={{ color: 'var(--rt-text)' }}>{username}</span>
              {email && <span> ({email})</span>}
            </p>
          )}
        </div>

        {/* Scrollable Legal Text */}
        <div className="px-6 py-4">
          <div
            className="rounded-lg p-5 space-y-5 overflow-y-auto text-xs leading-relaxed"
            style={{
              background: 'var(--rt-bg)',
              border: '1px solid var(--rt-border)',
              maxHeight: '320px',
              color: 'var(--rt-muted)',
            }}
          >
            <div>
              <p className="font-semibold mb-1" style={{ color: 'var(--rt-text)' }}>1. Authorized Use Only</p>
              <p>
                You acknowledge that this software is a dual-use security tool. You agree to use AI RedTeam
                solely for defensive auditing of systems you own or have explicit written permission to test.
                Unauthorized scanning of third-party networks is a violation of the Computer Fraud and Abuse
                Act (CFAA) (18 U.S.C. § 1030).
              </p>
            </div>

            <div>
              <p className="font-semibold mb-1" style={{ color: 'var(--rt-text)' }}>2. No Warranty &amp; Data Loss</p>
              <p>
                This software utilizes autonomous AI agents to execute active exploits. While safeguards are
                in place, you acknowledge that use of this tool carries inherent risks of service disruption,
                data corruption, or system instability. The developers provide this software "AS IS" without
                warranty of any kind.
              </p>
            </div>

            <div>
              <p className="font-semibold mb-1" style={{ color: 'var(--rt-text)' }}>3. Indemnification</p>
              <p>
                You agree to assume full legal and operational liability for all actions taken by the AI agent
                under your command. You hereby indemnify and hold harmless the AI RedTeam developers and
                Purdue University from any legal claims, damages, or liabilities arising from your use of
                this tool.
              </p>
            </div>

            <div>
              <p className="font-semibold mb-1" style={{ color: 'var(--rt-text)' }}>4. Audit Logging</p>
              <p>
                You acknowledge that all engagement activities, including target scopes and executed commands,
                are cryptographically logged to a local immutable ledger for forensic purposes.
              </p>
            </div>

            <p className="pt-3" style={{ borderTop: '1px solid var(--rt-border)', color: 'var(--rt-dim)' }}>
              By clicking "I Accept" below, you acknowledge that you have read, understood, and agree to be
              bound by this agreement.
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-5 flex gap-3" style={{ borderTop: '1px solid var(--rt-border)' }}>
          <button
            onClick={onDecline}
            className="flex-1 py-2.5 rounded-lg text-sm font-semibold transition-opacity hover:opacity-80"
            style={{ background: 'var(--rt-surface2)', color: 'var(--rt-muted)', border: '1px solid var(--rt-border)' }}
          >
            Decline
          </button>
          <button
            onClick={onAccept}
            className="flex-1 py-2.5 rounded-lg text-sm font-semibold transition-opacity hover:opacity-85"
            style={{ background: 'var(--rt-sky)', color: '#0d1117' }}
          >
            I Accept
          </button>
        </div>

      </div>
    </div>
  );
}