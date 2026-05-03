import { useState } from 'react';
import { C, S, noise } from './authTokens';

// Re-export tokens so existing imports from AuthShared still work.
export { C, S };

// ── AuthPageWrapper ───────────────────────────────────────────────────────────
export function AuthPageWrapper({ children }) {
  return (
    <div style={S.page}>
      <div style={{
        position: 'fixed',
        inset: 0,
        backgroundImage: noise,
        pointerEvents: 'none',
        zIndex: 0,
      }} />
      <div style={{
        position: 'fixed',
        width: 700,
        height: 500,
        borderRadius: '50%',
        background: 'radial-gradient(ellipse, rgba(232,132,90,0.055) 0%, transparent 65%)',
        top: '30%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'none',
        zIndex: 0,
      }} />
      {children}
    </div>
  );
}

// ── AuthCard ──────────────────────────────────────────────────────────────────
export function AuthCard({ children }) {
  return <div style={S.card}>{children}</div>;
}

// ── Logo ──────────────────────────────────────────────────────────────────────
export function Logo() {
  return (
    <div style={S.logo}>
      <div style={S.logoMark}>RT</div>
      <span style={S.logoText}>AI RedTeam</span>
    </div>
  );
}

// ── Field ─────────────────────────────────────────────────────────────────────
export function Field({ label, type = 'text', placeholder, value, onChange, onKeyDown, autoComplete }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={S.fieldGroup}>
      <label style={S.label}>{label}</label>
      <input
        style={{
          ...S.input,
          borderColor: focused ? C.borderFocus : C.border,
          boxShadow: focused ? `0 0 0 3px rgba(232,132,90,0.12)` : 'none',
        }}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={onKeyDown}
        autoComplete={autoComplete}
      />
    </div>
  );
}

// ── BackBtn ───────────────────────────────────────────────────────────────────
export function BackBtn({ onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'none',
        border: 'none',
        color: C.muted,
        cursor: 'pointer',
        fontSize: 13,
        padding: '0 0 22px 0',
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
        fontWeight: 500,
      }}
    >
      ← Back
    </button>
  );
}

// ── StepDots ──────────────────────────────────────────────────────────────────
export function StepDots({ total, current }) {
  return (
    <div style={{ display: 'flex', gap: 5, marginBottom: 28, alignItems: 'center' }}>
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          style={{
            width: i === current ? 22 : 6,
            height: 6,
            borderRadius: 3,
            background:
              i === current
                ? C.accent
                : i < current
                ? 'rgba(232,132,90,0.35)'
                : C.border,
            transition: 'width 0.25s ease, background 0.25s ease',
          }}
        />
      ))}
      <span style={{ fontSize: 12, color: C.muted, marginLeft: 6, fontWeight: 500 }}>
        {current + 1} / {total}
      </span>
    </div>
  );
}

// ── PrimaryButton ─────────────────────────────────────────────────────────────
export function PrimaryButton({ children, onClick, disabled = false, type = 'button' }) {
  return (
    <button
      type={type}
      style={{ ...S.btnPrimary, opacity: disabled ? 0.55 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }}
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.opacity = '0.88'; }}
      onMouseLeave={e => { e.currentTarget.style.opacity = disabled ? '0.55' : '1'; }}
    >
      {children}
    </button>
  );
}

// ── SecondaryButton ───────────────────────────────────────────────────────────
export function SecondaryButton({ children, onClick, type = 'button' }) {
  return (
    <button
      type={type}
      style={S.btnSecondary}
      onClick={onClick}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = C.accent;
        e.currentTarget.style.color = C.text;
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = C.border;
        e.currentTarget.style.color = C.mutedLight;
      }}
    >
      {children}
    </button>
  );
}

// ── ErrorBox ──────────────────────────────────────────────────────────────────
export function ErrorBox({ message }) {
  if (!message) return null;
  return <div style={S.errorBox}>{message}</div>;
}
