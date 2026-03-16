import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import AuthLanding     from './pages/AuthLanding'
import LoginPage       from './pages/LoginPage'
import RegisterPage    from './pages/RegisterPage'
import TermsModal      from './pages/TermsModal'
import HowItWorks      from './pages/HowItWorks'
import DashboardHome   from './pages/DashboardHome'
import ProjectWorkspace from './pages/ProjectWorkspace'
import Dashboard       from './pages/Dashboard'
import TopNav          from './components/TopNav'
import WelcomeBanner   from './components/WelcomeBanner'
import { setAuthUserId } from './lib/api'

// Auth flow:
//   landing → login  → app
//   landing → register → terms → guide → app (isNewUser = true)
//
// Pre-auth states are managed with useState (transient; page refresh resets to landing).
function App() {
  const [authState, setAuthState]   = useState('landing')
  const [username, setUsername]     = useState('')
  const [email, setEmail]           = useState('')
  const [showWelcome, setShowWelcome] = useState(false)

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleLoginSuccess = (name, userEmail, userId) => {
    setAuthUserId(userId)
    setUsername(name)
    setEmail(userEmail)
    setShowWelcome(false)
    setAuthState('app')
  }

  const handleRegisterSuccess = (name, userEmail, userId) => {
    setAuthUserId(userId)
    setUsername(name)
    setEmail(userEmail)
    setAuthState('terms')
  }

  const handleTermsAccepted = () => setAuthState('guide')

  // Declining terms sends back to credentials, not all the way to landing
  const handleTermsDeclined = () => {
    setAuthState('register')
    setUsername('')
    setEmail('')
    setAuthUserId(null)
  }

  const handleGuideComplete = () => {
    setShowWelcome(true)
    setAuthState('app')
  }

  const handleSignOut = () => {
    setAuthState('landing')
    setUsername('')
    setEmail('')
    setShowWelcome(false)
    setAuthUserId(null)
  }

  // ── Pre-auth screens ─────────────────────────────────────────────────────────

  if (authState === 'landing') {
    return (
      <AuthLanding
        onLogin={() => setAuthState('login')}
        onRegister={() => setAuthState('register')}
      />
    )
  }

  if (authState === 'login') {
    return (
      <LoginPage
        onBack={() => setAuthState('landing')}
        onSuccess={handleLoginSuccess}
        onGoRegister={() => setAuthState('register')}
      />
    )
  }

  if (authState === 'register') {
    return (
      <RegisterPage
        onBack={() => setAuthState('landing')}
        onSuccess={handleRegisterSuccess}
        onGoLogin={() => setAuthState('login')}
      />
    )
  }

  if (authState === 'terms') {
    return (
      <TermsModal
        username={username}
        email={email}
        onAccept={handleTermsAccepted}
        onDecline={handleTermsDeclined}
      />
    )
  }

  if (authState === 'guide') {
    return <HowItWorks onComplete={handleGuideComplete} />
  }

  // ── Authenticated app — react-router takes over ──────────────────────────────
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      <Route
        path="/dashboard"
        element={
          <>
            <TopNav username={username} onSignOut={handleSignOut} />
            <DashboardHome username={username} />
            {showWelcome && (
              <WelcomeBanner onDismiss={() => setShowWelcome(false)} />
            )}
          </>
        }
      />

      <Route
        path="/guide"
        element={
          <>
            <TopNav username={username} onSignOut={handleSignOut} />
            {/* Standalone guide — no onComplete prop shows "Back to Dashboard" CTA */}
            <HowItWorks />
          </>
        }
      />

      <Route
        path="/projects/:projectId"
        element={
          <>
            <TopNav username={username} onSignOut={handleSignOut} />
            <ProjectWorkspace username={username} />
          </>
        }
      />

      {/* Full-screen scan terminal — no TopNav chrome */}
      <Route
        path="/projects/:projectId/runs/:runId"
        element={<Dashboard />}
      />

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default App
