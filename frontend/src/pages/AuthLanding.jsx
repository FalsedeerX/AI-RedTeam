import { useNavigate } from 'react-router-dom'
import {
  AuthPageWrapper,
  AuthCard,
  Logo,
  C,
  S,
  PrimaryButton,
  SecondaryButton,
} from '../components/auth/AuthShared'

export default function AuthLanding() {
  const navigate = useNavigate()

  return (
    <AuthPageWrapper>
      <AuthCard>
        <Logo />

        <h1 style={{ ...S.h1, fontSize: 26, marginBottom: 12 }}>
          AI RedTeam —<br />Your personal pentesting assistant.
        </h1>

        <p style={S.sub}>
          Automated security testing with human oversight. Define your target,
          review AI-generated findings, and stay in control at every step.
        </p>

        <div style={S.divider} />

        <PrimaryButton onClick={() => navigate('/sign-in')}>Log in</PrimaryButton>
        <SecondaryButton onClick={() => navigate('/sign-up')}>Create account</SecondaryButton>

        <p style={{
          textAlign: 'center',
          fontSize: 12,
          color: C.muted,
          marginTop: 24,
          lineHeight: 1.6,
        }}>
          For authorized security testing only.
        </p>
      </AuthCard>
    </AuthPageWrapper>
  )
}
