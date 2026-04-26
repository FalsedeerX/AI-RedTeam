import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { SignedIn, SignedOut, useUser, useClerk } from '@clerk/clerk-react'

import AuthLanding       from './pages/AuthLanding'
import SignInScreen      from './pages/SignInScreen'
import SignUpScreen      from './pages/SignUpScreen'
import OnboardingTerms   from './pages/OnboardingTerms'
import OnboardingGuide   from './pages/OnboardingGuide'
import HowItWorks        from './pages/HowItWorks'
import DashboardHome     from './pages/DashboardHome'
import ProjectWorkspace  from './pages/ProjectWorkspace'
import Dashboard         from './pages/Dashboard'
import TopNav            from './components/TopNav'

/**
 * Resolve a friendly display name from Clerk's user object without surfacing
 * raw email ids in the header when a first name / username exists.
 */
function useDisplayName() {
  const { user } = useUser()
  if (!user) return { username: '', email: '' }
  const email = user.primaryEmailAddress?.emailAddress ?? ''
  const username = user.firstName || user.username || (email ? email.split('@')[0] : 'analyst')
  return { username, email }
}

/**
 * Gate for routes that require (a) a signed-in Clerk session and (b) the
 * onboarding funnel (terms + guide) to have been completed.  Users mid-funnel
 * are redirected to the appropriate step instead of the app.
 */
function RequireOnboarded({ children }) {
  const { isLoaded, isSignedIn, user } = useUser()
  const location = useLocation()

  if (!isLoaded) return null
  if (!isSignedIn) {
    return <Navigate to="/sign-in" replace state={{ from: location }} />
  }
  const done = Boolean(user?.unsafeMetadata?.onboardingComplete)
  if (!done) {
    return <Navigate to="/onboarding/terms" replace />
  }
  return children
}

/**
 * TopNav with Clerk sign-out wired in — mounted above every authenticated
 * screen so the dropdown's "Sign Out" triggers a real Clerk session end.
 */
function AuthedTopNav() {
  const { username } = useDisplayName()
  const { signOut } = useClerk()
  return <TopNav username={username} onSignOut={() => signOut({ redirectUrl: '/' })} />
}

function App() {
  return (
    <Routes>
      {/* ── Public landing ───────────────────────────────────────────── */}
      <Route
        path="/"
        element={
          <>
            <SignedOut>
              <AuthLanding />
            </SignedOut>
            <SignedIn>
              <Navigate to="/dashboard" replace />
            </SignedIn>
          </>
        }
      />

      {/* ── Clerk auth screens (path routing wants a splat) ──────────── */}
      <Route path="/sign-in/*" element={<SignInScreen />} />
      <Route path="/sign-up/*" element={<SignUpScreen />} />

      {/* ── Onboarding funnel (signed in, not-yet-onboarded) ─────────── */}
      <Route
        path="/onboarding/terms"
        element={
          <>
            <SignedIn><OnboardingTerms /></SignedIn>
            <SignedOut><Navigate to="/sign-in" replace /></SignedOut>
          </>
        }
      />
      <Route
        path="/onboarding/guide"
        element={
          <>
            <SignedIn><OnboardingGuide /></SignedIn>
            <SignedOut><Navigate to="/sign-in" replace /></SignedOut>
          </>
        }
      />

      {/* ── Authenticated app ────────────────────────────────────────── */}
      <Route
        path="/dashboard"
        element={
          <RequireOnboarded>
            <AuthedTopNav />
            <DashboardHome />
          </RequireOnboarded>
        }
      />
      <Route
        path="/guide"
        element={
          <RequireOnboarded>
            <AuthedTopNav />
            <HowItWorks />
          </RequireOnboarded>
        }
      />
      <Route
        path="/projects/:projectId"
        element={
          <RequireOnboarded>
            <AuthedTopNav />
            <ProjectWorkspace />
          </RequireOnboarded>
        }
      />
      <Route
        path="/projects/:projectId/runs/:runId"
        element={
          <RequireOnboarded>
            <Dashboard />
          </RequireOnboarded>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
