import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { registerClerkTokenGetter } from './api'

// Hands Clerk's getToken to the plain-JS fetch helpers in lib/api.js so
// hooks are not required at every call site.
export function ClerkTokenBridge({ children }) {
  const { getToken } = useAuth()
  useEffect(() => {
    registerClerkTokenGetter(getToken)
    return () => registerClerkTokenGetter(null)
  }, [getToken])
  return children
}
