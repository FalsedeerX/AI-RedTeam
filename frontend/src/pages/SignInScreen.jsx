import { SignIn } from '@clerk/clerk-react'
import { AuthPageWrapper } from '../components/auth/AuthShared'

/**
 * Clerk's hosted <SignIn> mounted inside our AuthPageWrapper chrome so the
 * dark terminal aesthetic survives the migration from the custom LoginPage.
 */
export default function SignInScreen() {
  return (
    <AuthPageWrapper>
      <SignIn
        routing="path"
        path="/sign-in"
        signUpUrl="/sign-up"
        fallbackRedirectUrl="/dashboard"
        forceRedirectUrl="/dashboard"
      />
    </AuthPageWrapper>
  )
}
