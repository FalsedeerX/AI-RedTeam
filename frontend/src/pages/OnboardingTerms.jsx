import { useNavigate } from 'react-router-dom'
import { useUser, useClerk } from '@clerk/clerk-react'
import TermsModal from './TermsModal'

/**
 * Terms gate rendered after Clerk sign-up completes.
 * Accepting stores no metadata yet (we wait for the guide to finish so a
 * half-onboarded user can't slip past the tour).
 * Declining signs the user out and returns them to the landing page.
 */
export default function OnboardingTerms() {
  const navigate = useNavigate()
  const { user } = useUser()
  const { signOut } = useClerk()

  const email = user?.primaryEmailAddress?.emailAddress ?? ''
  const username = user?.firstName || user?.username || (email ? email.split('@')[0] : 'analyst')

  const handleAccept = () => {
    navigate('/onboarding/guide', { replace: true })
  }

  const handleDecline = async () => {
    await signOut()
    navigate('/', { replace: true })
  }

  return (
    <TermsModal
      username={username}
      email={email}
      onAccept={handleAccept}
      onDecline={handleDecline}
    />
  )
}
