import { useState } from 'react'
import EmailEntry from './pages/EmailEntry'
import TermsModal from './pages/TermsModal'
import ProjectScopeManager from './pages/ProjectScopeManager'
import Dashboard from './pages/Dashboard'
import './App.css'

// Main App Component
// Routing flow: email -> terms-agreement -> project-scope -> dashboard
function App() {
  const [currentPage, setCurrentPage] = useState('email')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [scanType, setScanType] = useState('')
  const [targets, setTargets] = useState([])
  // projectId is forwarded to Dashboard so it can be passed to the run-start
  // endpoint once the backend scan routes are wired (Phase 2).
  const [projectId, setProjectId] = useState(null)

  const handleVerify = (name, userEmail) => {
    setUsername(name)
    setEmail(userEmail)
    setCurrentPage('terms-agreement')
  }

  const handleTermsAccepted = () => {
    setCurrentPage('project-scope')
  }

  const handleTermsDeclined = () => {
    setCurrentPage('email')
    setUsername('')
    setEmail('')
  }

  // ProjectScopeManager passes (scanType, targetValues, projectId)
  const handleStartScan = (type, targetList, projId) => {
    setScanType(type)
    setTargets(targetList)
    setProjectId(projId ?? null)
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
      ) : currentPage === 'project-scope' ? (
        <ProjectScopeManager
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
          projectId={projectId}
        />
      )}
    </div>
  )
}

export default App
