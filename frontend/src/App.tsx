import { Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import HomePage from './pages/HomePage'
import RepositoriesPage from './pages/RepositoriesPage'
import PoliciesPage from './pages/PoliciesPage'
import ConflictsPage from './pages/ConflictsPage'
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
      </Routes>
    </Layout>
  )
}

export default App
