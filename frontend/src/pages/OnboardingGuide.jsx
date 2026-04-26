import { useNavigate } from 'react-router-dom'
import { useUser } from '@clerk/clerk-react'
import HowItWorks from './HowItWorks'

/**
 * Final onboarding step: the "How It Works" tour.
 * On completion, flips ``unsafeMetadata.onboardingComplete`` on the Clerk
 * user object so the guard in App.jsx stops redirecting them here.
 */
export default function OnboardingGuide() {
  const navigate = useNavigate()
  const { user } = useUser()

  const handleComplete = async () => {
    try {
      await user?.update({
        unsafeMetadata: {
          ...(user.unsafeMetadata ?? {}),
          onboardingComplete: true,
        },
      })
    } catch (err) {
      console.error('Failed to persist onboarding flag', err)
    }
    navigate('/dashboard', { replace: true })
  }

  return <HowItWorks onComplete={handleComplete} />
}
