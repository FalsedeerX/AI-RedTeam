import { useState } from 'react'
import EmailEntry from './pages/EmailEntry'
import TermsModal from './pages/TermsModal'
import ScopeConfig from './pages/ScopeConfig'
import Dashboard from './pages/Dashboard'
import './App.css'

// Main App Component
// Routing flow: email -> terms-agreement -> scope-config -> dashboard
function App() {
  const [currentPage, setCurrentPage] = useState('email')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [scanType, setScanType] = useState('')
  const [targets, setTargets] = useState([])

  const handleVerify = (name, userEmail) => {
    setUsername(name)
    setEmail(userEmail)
    // Transition to terms agreement (Legal Airlock)
    setCurrentPage('terms-agreement')
  }

  const handleTermsAccepted = () => {
    // User accepted terms, proceed to scope configuration
    setCurrentPage('scope-config')
  }

  const handleTermsDeclined = () => {
    // User declined terms, return to email entry
    setCurrentPage('email')
    // Clear user data
    setUsername('')
    setEmail('')
  }

  const handleStartScan = (type, targetList) => {
    setScanType(type)
    setTargets(targetList)
    setCurrentPage('dashboard')
  }

  return (
    <div>
      {currentPage === 'email' ? (
        <EmailEntry onVerify={handleVerify} />
      ) : currentPage === 'terms-agreement' ? (
        <TermsModal 
          username={username} 
          email={email} 
          onAccept={handleTermsAccepted}
          onDecline={handleTermsDeclined}
        />
      ) : currentPage === 'scope-config' ? (
        <ScopeConfig 
          username={username} 
          email={email} 
          onStartScan={handleStartScan}
        />
      ) : (
        <Dashboard 
          username={username} 
          email={email} 
          targets={targets} 
          scanType={scanType} 
        />
      )}
    </div>
  )
}

export default App
