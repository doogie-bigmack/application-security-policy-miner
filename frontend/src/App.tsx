import { Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import HomePage from './pages/HomePage'
import RepositoriesPage from './pages/RepositoriesPage'
import PoliciesPage from './pages/PoliciesPage'
import ConflictsPage from './pages/ConflictsPage'
import ChangesPage from './pages/ChangesPage'
import SecretsPage from './pages/SecretsPage'
import AuditLogsPage from './pages/AuditLogsPage'
import { SecurityAuditPage } from './pages/SecurityAuditPage'
import SettingsPage from './pages/SettingsPage'
import ProvisioningPage from './pages/ProvisioningPage'
import CodeAdvisoriesPage from './pages/CodeAdvisoriesPage'
import AutoApprovalPage from './pages/AutoApprovalPage'
import RiskDashboardPage from './pages/RiskDashboardPage'
import OrganizationsPage from './pages/OrganizationsPage'
import ApplicationsPage from './pages/ApplicationsPage'
import NormalizationPage from './pages/NormalizationPage'
import PolicyFixesPage from './pages/PolicyFixesPage'
import InconsistentEnforcementPage from './pages/InconsistentEnforcementPage'
import DuplicatesPage from './pages/DuplicatesPage'
import BulkScanPage from './pages/BulkScanPage'
import Layout from './components/Layout'

function App() {
  const [darkMode, setDarkMode] = useState(false)

  useEffect(() => {
    // Check system preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    setDarkMode(prefersDark)
  }, [])

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  return (
    <Layout darkMode={darkMode} setDarkMode={setDarkMode}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/repositories" element={<RepositoriesPage />} />
        <Route path="/policies" element={<PoliciesPage />} />
        <Route path="/conflicts" element={<ConflictsPage />} />
        <Route path="/changes" element={<ChangesPage />} />
        <Route path="/secrets" element={<SecretsPage />} />
        <Route path="/audit-logs" element={<AuditLogsPage />} />
        <Route path="/security" element={<SecurityAuditPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/provisioning" element={<ProvisioningPage />} />
        <Route path="/code-advisories" element={<CodeAdvisoriesPage />} />
        <Route path="/auto-approval" element={<AutoApprovalPage />} />
        <Route path="/risk" element={<RiskDashboardPage />} />
        <Route path="/organizations" element={<OrganizationsPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/normalization" element={<NormalizationPage />} />
        <Route path="/policy-fixes" element={<PolicyFixesPage />} />
        <Route path="/inconsistent-enforcement" element={<InconsistentEnforcementPage />} />
        <Route path="/duplicates" element={<DuplicatesPage />} />
        <Route path="/bulk-scan" element={<BulkScanPage />} />
      </Routes>
    </Layout>
  )
}

export default App
