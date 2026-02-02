import React from 'react'
import Snackbar from '@mui/material/Snackbar'
import Alert from '@mui/material/Alert'

let showToastFn: ((message: string, severity: 'success' | 'error' | 'info' | 'warning') => void) | null = null

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false)
  const [message, setMessage] = React.useState('')
  const [severity, setSeverity] = React.useState<'success' | 'error' | 'info' | 'warning'>('info')

  React.useEffect(() => {
    showToastFn = (msg: string, sev: 'success' | 'error' | 'info' | 'warning') => {
      setMessage(msg)
      setSeverity(sev)
      setOpen(true)
    }
    return () => { showToastFn = null }
  }, [])

  return (
    <>
      {children}
      <Snackbar
        open={open}
        autoHideDuration={4000}
        onClose={() => setOpen(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert onClose={() => setOpen(false)} severity={severity} variant="filled">
          {message}
        </Alert>
      </Snackbar>
    </>
  )
}

export const toast = {
  success: (message: string, _opts?: any) => showToastFn?.(message, 'success'),
  error: (message: string, _opts?: any) => showToastFn?.(message, 'error'),
  info: (message: string, _opts?: any) => showToastFn?.(message, 'info'),
  warning: (message: string, _opts?: any) => showToastFn?.(message, 'warning'),
  message: (message: string, _opts?: any) => showToastFn?.(message, 'info'),
}
