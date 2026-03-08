import { useState } from 'react';
import { apiPost } from '../lib/api';
import {
  AuthPageWrapper,
  AuthCard,
  Logo,
  Field,
  BackBtn,
  ErrorBox,
  PrimaryButton,
  C,
  S,
} from '../components/auth/AuthShared';

export default function LoginPage({ onBack, onSuccess, onGoRegister }) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  const submit = async () => {
    if (!email.trim() || !password.trim()) {
      setError('Please fill in both fields.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await apiPost('/users/auth', { email, password });
      const username = email.split('@')[0];
      onSuccess(username, email, data.user_id);
    } catch {
      setError("That email or password doesn't match our records.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthPageWrapper>
      <AuthCard>
        <BackBtn onClick={onBack} />
        <Logo />

        <h1 style={S.h1}>Welcome back</h1>
        <p style={S.sub}>Log in to your account to continue.</p>

        <ErrorBox message={error} />

        <Field
          label="Email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={e => setEmail(e.target.value)}
          autoComplete="email"
        />
        <Field
          label="Password"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={e => setPassword(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          autoComplete="current-password"
        />

        <PrimaryButton onClick={submit} disabled={loading}>
          {loading ? 'Signing in…' : 'Log in →'}
        </PrimaryButton>

        <p style={{ textAlign: 'center', fontSize: 13.5, color: C.muted, marginTop: 20 }}>
          Don&apos;t have an account?{' '}
          <span style={S.link} onClick={onGoRegister}>Sign up</span>
        </p>
      </AuthCard>
    </AuthPageWrapper>
  );
}
