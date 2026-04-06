import { useCallback, useEffect, useState } from 'react';
import { C } from './auth/AuthShared';

const AUTO_DISMISS_MS = 7000;

export default function WelcomeBanner({ onDismiss }) {
  const [visible, setVisible] = useState(false);
  const [leaving, setLeaving] = useState(false);

  const dismiss = useCallback(() => {
    setLeaving(true);
    setTimeout(onDismiss, 320);
  }, [onDismiss]);

  useEffect(() => {
    // Slight delay so the dashboard renders first, then banner slides in
    const enterTimer = setTimeout(() => setVisible(true), 120);
    const exitTimer  = setTimeout(() => dismiss(), AUTO_DISMISS_MS);
    return () => {
      clearTimeout(enterTimer);
      clearTimeout(exitTimer);
    };
  }, [dismiss]);

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 28,
        right: 28,
        zIndex: 9999,
        width: 340,
        fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
        transform: visible && !leaving ? 'translateY(0)' : 'translateY(110%)',
        opacity: visible && !leaving ? 1 : 0,
        transition: 'transform 0.32s cubic-bezier(0.34,1.3,0.64,1), opacity 0.28s ease',
      }}
    >
      <div
        style={{
          background: '#1e1c23',
          border: `1px solid rgba(232,132,90,0.25)`,
          borderRadius: 14,
          padding: '16px 18px',
          boxShadow: '0 16px 48px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.04) inset',
        }}
      >
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: C.success,
              boxShadow: `0 0 8px ${C.success}`,
              flexShrink: 0,
            }} />
            <span style={{ fontSize: 13.5, fontWeight: 600, color: '#f2efe8' }}>
              Account created
            </span>
          </div>
          <button
            onClick={dismiss}
            style={{
              background: 'none',
              border: 'none',
              color: C.muted,
              cursor: 'pointer',
              fontSize: 16,
              lineHeight: 1,
              padding: '0 2px',
              fontFamily: 'inherit',
            }}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <p style={{ fontSize: 13, color: C.muted, lineHeight: 1.65, margin: 0 }}>
          You&apos;re all set. Revisit the walkthrough anytime from the{' '}
          <span style={{ color: C.accent, fontWeight: 500 }}>Guide</span>
          {' '}tab in the nav.
        </p>

        {/* Progress bar */}
        <div style={{ marginTop: 14, height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              borderRadius: 2,
              background: `linear-gradient(90deg, ${C.accent}, #d4714a)`,
              animation: `wb-shrink ${AUTO_DISMISS_MS}ms linear forwards`,
            }}
          />
        </div>
      </div>

      <style>{`
        @keyframes wb-shrink {
          from { width: 100%; }
          to   { width: 0%; }
        }
      `}</style>
    </div>
  );
}
