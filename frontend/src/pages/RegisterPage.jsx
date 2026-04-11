import { useState } from 'react';
import { apiPost } from '../lib/api';
import {
  AuthPageWrapper,
  AuthCard,
  Logo,
  Field,
  BackBtn,
  StepDots,
  ErrorBox,
  PrimaryButton,
  C,
  S,
} from '../components/auth/AuthShared';

export default function RegisterPage({ onBack, onSuccess, onGoLogin }) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm]   = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  const submit = async () => {
    if (!email.trim() || !password.trim() || !confirm.trim()) {
      setError('All fields are required.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await apiPost('/users/register', { email, password });
      const username = email.split('@')[0];
      onSuccess(username, email, data.id);
    } catch (err) {
      if (err.message && err.message.includes('409')) {
        setError('An account with this email already exists. Log in instead?');
      } else {
        setError(err.message || 'Could not connect to the server.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthPageWrapper>
      <AuthCard>
        <BackBtn onClick={onBack} />
        <Logo />

        <StepDots total={3} current={0} />

        <h1 style={S.h1}>Create your account</h1>
        <p style={S.sub}>Use your approved Purdue student email to create an account.</p>

        <ErrorBox message={error} />

        <Field
          label="Email"
          type="email"
          placeholder="you@purdue.edu"
          value={email}
          onChange={e => setEmail(e.target.value)}
          autoComplete="email"
        />
        <Field
          label="Password"
          type="password"
          placeholder="At least 8 characters"
          value={password}
          onChange={e => setPassword(e.target.value)}
          autoComplete="new-password"
        />
        <Field
          label="Confirm password"
          type="password"
          placeholder="••••••••"
          value={confirm}
          onChange={e => setConfirm(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          autoComplete="new-password"
        />

        <PrimaryButton onClick={submit} disabled={loading}>
          {loading ? 'Creating account…' : 'Continue →'}
        </PrimaryButton>

        <p style={{ textAlign: 'center', fontSize: 12.5, color: C.muted, marginTop: 14, lineHeight: 1.5 }}>
          Temporary access is restricted to approved ECE 49595 Purdue email addresses.
        </p>

        <p style={{ textAlign: 'center', fontSize: 13.5, color: C.muted, marginTop: 20 }}>
          Already have an account?{' '}
          <span style={S.link} onClick={onGoLogin}>Log in</span>
        </p>
      </AuthCard>
    </AuthPageWrapper>
  );
}
