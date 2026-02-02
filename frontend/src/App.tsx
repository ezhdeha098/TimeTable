import { BrowserRouter, Routes, Route } from 'react-router-dom'
import React from 'react'
import Layout from './components/Layout'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { lightTheme, darkTheme } from './theme'
import { ToastProvider } from './utils/toast'
import CommandPalette from './components/CommandPalette'
import SchedulePage from './pages/SchedulePage'
import TimetablePage from './pages/TimetablePage'
import PlannerPage from './pages/PlannerPage'
import ExportPage from './pages/ExportPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  const [dark, setDark] = React.useState<boolean>(() => {
    const stored = localStorage.getItem('theme')
    if (stored === 'dark') return true
    if (stored === 'light') return false
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  
  React.useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])
  
  const [paletteOpen, setPaletteOpen] = React.useState(false)
  
  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <ThemeProvider theme={dark ? darkTheme : lightTheme}>
      <CssBaseline />
      <ToastProvider>
        <BrowserRouter>
          <Layout dark={dark} onToggleDark={() => setDark(!dark)} onOpenPalette={() => setPaletteOpen(true)}>
            <Routes>
              <Route path="/" element={<PlannerPage />} />
              <Route path="/schedule" element={<SchedulePage />} />
              <Route path="/timetable" element={<TimetablePage />} />
              <Route path="/export" element={<ExportPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </Layout>
          <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
        </BrowserRouter>
      </ToastProvider>
    </ThemeProvider>
  )
}

export default App
