import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ClerkProvider, useAuth } from '@clerk/clerk-react'
import './index.css'
import App from './App.jsx'
import { registerClerkTokenGetter } from './lib/api'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  throw new Error(
    'Missing VITE_CLERK_PUBLISHABLE_KEY. Copy .env.example to .env and paste the pk_test_... key from the Clerk dashboard.'
  )
}

// Hands Clerk's getToken to the plain-JS fetch helpers in lib/api.js so
// hooks are not required at every call site.
function ClerkTokenBridge({ children }) {
  const { getToken } = useAuth()
  useEffect(() => {
    registerClerkTokenGetter(getToken)
    return () => registerClerkTokenGetter(null)
  }, [getToken])
  return children
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
      <ClerkTokenBridge>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ClerkTokenBridge>
    </ClerkProvider>
  </StrictMode>,
)
