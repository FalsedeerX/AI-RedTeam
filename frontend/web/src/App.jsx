import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import EmailEntry from './pages/EmailEntry'
import TermsModal from './pages/TermsModal'
import HowItWorks from './pages/HowItWorks'
import DashboardHome from './pages/DashboardHome'
import ProjectWorkspace from './pages/ProjectWorkspace'
import Dashboard from './pages/Dashboard'
import TopNav from './components/TopNav'
import { setAuthUserId } from './lib/api'

// Auth flow:  login → terms → guide → app (react-router routes)
// Pre-auth states are managed with useState (they are transient and don't
// benefit from URL routing — a page refresh during login resets to login anyway).
function App() {
  const [authState, setAuthState] = useState('login')
  const [username, setUsername]   = useState('')
  const [email, setEmail]         = useState('')

  const handleVerify = (name, userEmail, userId) => {
    setAuthUserId(userId)
    setUsername(name)
    setEmail(userEmail)
    setAuthState('terms')
  }

  const handleTermsAccepted = () => setAuthState('guide')

  const handleTermsDeclined = () => {
    setAuthState('login')
    setUsername('')
    setEmail('')
  }

  const handleGuideComplete = () => setAuthState('app')

  const handleSignOut = () => {
    setAuthState('login')
    setUsername('')
    setEmail('')
    setAuthUserId(null)
  }

  // ── Pre-auth screens ──────────────────────────────────────────────────────
  if (authState === 'login') {
    return <EmailEntry onVerify={handleVerify} />
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

  // ── Authenticated app — react-router takes over ───────────────────────────
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      <Route
        path="/dashboard"
        element={
          <>
            <TopNav username={username} onSignOut={handleSignOut} />
            <DashboardHome username={username} />
          </>
        }
      />

      <Route
        path="/guide"
        element={
          <>
            <TopNav username={username} onSignOut={handleSignOut} />
            {/* Standalone guide — no onComplete prop, shows "Back to Dashboard" CTA */}
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
