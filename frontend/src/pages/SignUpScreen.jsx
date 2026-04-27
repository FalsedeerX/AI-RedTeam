import { SignUp } from '@clerk/clerk-react'
import { AuthPageWrapper } from '../components/auth/AuthShared'

/**
 * Clerk's hosted <SignUp>. After sign-up succeeds, Clerk redirects new users
 * through our onboarding funnel (terms → guide) before handing them the app.
 */
export default function SignUpScreen() {
  return (
    <AuthPageWrapper>
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        fallbackRedirectUrl="/onboarding/terms"
        forceRedirectUrl="/onboarding/terms"
      />
    </AuthPageWrapper>
  )
}
