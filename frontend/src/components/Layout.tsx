import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import AppBar from '@mui/material/AppBar'
import Toolbar from '@mui/material/Toolbar'
import IconButton from '@mui/material/IconButton'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Box from '@mui/material/Box'
import Container from '@mui/material/Container'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Paper from '@mui/material/Paper'
import Divider from '@mui/material/Divider'
import Fab from '@mui/material/Fab'
import Tooltip from '@mui/material/Tooltip'
import { useTheme } from '@mui/material/styles'
import useMediaQuery from '@mui/material/useMediaQuery'
import MenuIcon from '@mui/icons-material/Menu'
import CloseIcon from '@mui/icons-material/Close'
import Brightness7Icon from '@mui/icons-material/Brightness7'
import Brightness4Icon from '@mui/icons-material/Brightness4'
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import TableChartIcon from '@mui/icons-material/TableChart'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import DownloadIcon from '@mui/icons-material/Download'
import SettingsIcon from '@mui/icons-material/Settings'
import KeyboardCommandKeyIcon from '@mui/icons-material/KeyboardCommandKey'

interface LayoutProps {
  children: React.ReactNode
  dark: boolean
  onToggleDark: () => void
  onOpenPalette: () => void
}

export default function Layout({ children, dark, onToggleDark, onOpenPalette }: LayoutProps) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = React.useState(false)
  const theme = useTheme()
  const isLgUp = useMediaQuery(theme.breakpoints.up('lg'))

  const navItems = [
    { path: '/', label: 'Planner', icon: AccessTimeIcon },
    { path: '/schedule', label: 'Schedule', icon: CalendarMonthIcon },
    { path: '/timetable', label: 'Timetable', icon: TableChartIcon },
    { path: '/export', label: 'Export', icon: DownloadIcon },
    { path: '/settings', label: 'Settings', icon: SettingsIcon },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const NavList = ({ onItemClick }: { onItemClick?: () => void }) => (
    <List disablePadding>
      {navItems.map((item) => {
        const Icon = item.icon
        const active = isActive(item.path)
        return (
          <ListItemButton
            key={item.path}
            component={Link}
            to={item.path}
            selected={active}
            onClick={() => {
              setSidebarOpen(false)
              onItemClick?.()
            }}
            sx={{
              borderRadius: 1.5,
              mb: 0.5,
            }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>
              <Icon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        )
      })}
    </List>
  )

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Header */}
      <AppBar position="sticky" color="default" elevation={1} sx={{ backdropFilter: 'blur(8px)' }}>
        <Toolbar sx={{ gap: 2 }}>
          {!isLgUp && (
            <IconButton edge="start" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
              <MenuIcon />
            </IconButton>
          )}
          <Box component={Link} to="/" sx={{ display: 'flex', alignItems: 'center', gap: 1.5, textDecoration: 'none', color: 'inherit' }}>
            <Box sx={{
              height: 40,
              width: 40,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 800,
              background: 'linear-gradient(135deg, #3b82f6, #9333ea)'
            }}>
              TS
            </Box>
            <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
              <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: 0.2 }}>
                Timetable Scheduler
              </Typography>
              <Typography variant="caption" color="text.secondary">AI-Powered Scheduling</Typography>
            </Box>
          </Box>
          <Box sx={{ flexGrow: 1 }} />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button variant="outlined" onClick={onOpenPalette} sx={{ display: { xs: 'none', sm: 'inline-flex' } }} startIcon={<KeyboardCommandKeyIcon fontSize="small" />}>Ctrl+K</Button>
            <Button variant="outlined" onClick={onToggleDark} startIcon={dark ? <Brightness7Icon fontSize="small" /> : <Brightness4Icon fontSize="small" />}
            >
              <Box component="span" sx={{ display: { xs: 'none', md: 'inline' } }}>{dark ? 'Light' : 'Dark'}</Box>
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Mobile Drawer */}
      <Drawer
        anchor="left"
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sx={{ display: { lg: 'none' } }}
      >
        <Box sx={{ width: 320, display: 'flex', flexDirection: 'column', height: '100%' }} role="presentation">
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2 }}>
            <Box component={Link} to="/" onClick={() => setSidebarOpen(false)} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, textDecoration: 'none', color: 'inherit' }}>
              <Box sx={{ height: 48, width: 48, borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, background: 'linear-gradient(135deg, #3b82f6, #9333ea)' }}>TS</Box>
              <Typography variant="subtitle1" fontWeight={700}>Timetable Scheduler</Typography>
            </Box>
            <IconButton onClick={() => setSidebarOpen(false)} aria-label="Close menu"><CloseIcon /></IconButton>
          </Box>
          <Divider />
          <Box sx={{ p: 1, flex: 1, overflow: 'auto' }}>
            <NavList onItemClick={() => setSidebarOpen(false)} />
          </Box>
        </Box>
      </Drawer>

      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', lg: '260px 1fr' },
            gap: 3,
          }}
        >
          {/* Sidebar - Desktop */}
          <Box sx={{ display: { xs: 'none', lg: 'block' }, position: 'sticky', top: 96, alignSelf: 'start', zIndex: 1 }}>
            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 3 }}>
              <NavList />
            </Paper>
          </Box>

          {/* Main Content */}
          <Box component="main" sx={{ minHeight: 'calc(100vh - 10rem)', maxWidth: '100%' }}>
            {children}
          </Box>
        </Box>
      </Container>

      {/* Quick action button */}
      <Tooltip title="Command Palette (Ctrl+K)">
        <Fab
          color="primary"
          onClick={onOpenPalette}
          sx={{ position: 'fixed', right: 24, bottom: 24, zIndex: 1300,
            background: 'linear-gradient(135deg, #3b82f6, #9333ea)'
          }}
          aria-label="Open command palette"
        >
          <KeyboardCommandKeyIcon />
        </Fab>
      </Tooltip>
    </Box>
  )
}

