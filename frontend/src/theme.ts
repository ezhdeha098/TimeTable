import { createTheme, type ThemeOptions } from '@mui/material/styles'

const common: ThemeOptions = {
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Apple Color Emoji", "Segoe UI Emoji"',
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiTextField: {
      defaultProps: {
        fullWidth: true,
        size: 'medium',
        margin: 'normal',
        variant: 'outlined',
      },
    },
    MuiFormControl: {
      defaultProps: {
        fullWidth: true,
        margin: 'normal',
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: ({ theme }) => ({
          fontWeight: 600,
        }),
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 10,
          transition: 'box-shadow 200ms ease',
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.divider,
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.text.secondary,
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.primary.main,
            boxShadow: `0 0 0 3px ${theme.palette.primary.main}22`,
          },
        }),
        input: {
          paddingTop: 12,
          paddingBottom: 12,
          paddingLeft: 14,
          paddingRight: 14,
        },
      },
    },
    MuiSelect: {
      defaultProps: {
        MenuProps: {
          PaperProps: {
            elevation: 8,
          },
        },
      },
      styleOverrides: {
        select: {
          paddingTop: 12,
          paddingBottom: 12,
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: ({ theme }) => ({
          borderRadius: 12,
        }),
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 8,
          minHeight: 44,
        }),
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
        },
      },
    },
    MuiCheckbox: {
      defaultProps: {
        size: 'medium',
      },
    },
    MuiFormHelperText: {
      styleOverrides: {
        root: {
          marginLeft: 0,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: {
          borderRadius: 12,
        },
      },
    },
  },
}

export const lightTheme = createTheme({
  ...common,
  components: {
    MuiTextField: {
      defaultProps: { size: 'medium', margin: 'normal' },
    },
    MuiFormControl: {
      defaultProps: { margin: 'normal', size: 'medium' },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 12,
          backgroundColor: theme.palette.background.paper,
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.divider,
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.text.secondary,
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.primary.main,
          },
          '&.Mui-focused': {
            boxShadow: `0 0 0 3px ${theme.palette.primary.main}20`,
          },
        }),
        input: {
          paddingTop: 14,
          paddingBottom: 14,
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: ({ theme }) => ({
          fontWeight: 600,
          color: theme.palette.text.secondary,
          '&.Mui-focused': { color: theme.palette.primary.main },
        }),
      },
    },
    MuiSelect: {
      defaultProps: {
        MenuProps: {
          transformOrigin: { horizontal: 'left', vertical: 'top' },
          anchorOrigin: { horizontal: 'left', vertical: 'bottom' },
          PaperProps: { elevation: 3 },
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: ({ theme }) => ({
          borderRadius: 12,
          paddingTop: 6,
          paddingBottom: 6,
          border: `1px solid ${theme.palette.divider}`,
        }),
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: ({ theme }) => ({
          minHeight: 44,
          borderRadius: 8,
          margin: '2px 6px',
          '&.Mui-selected': {
            backgroundColor: `${theme.palette.primary.main}14`,
          },
        }),
      },
    },
    MuiAutocomplete: {
      defaultProps: {
        size: 'medium',
      },
      styleOverrides: {
        paper: ({ theme }) => ({
          borderRadius: 12,
          border: `1px solid ${theme.palette.divider}`,
        }),
      },
    },
    MuiButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 10,
          textTransform: 'none',
          fontWeight: 600,
          paddingLeft: theme.spacing(2.5),
          paddingRight: theme.spacing(2.5),
        }),
      },
    },
  },
  palette: {
    mode: 'light',
    background: { default: 'hsl(222 47% 99%)', paper: 'hsl(0 0% 100%)' },
    text: { primary: 'hsl(222 47% 11%)', secondary: 'hsl(222 15% 40%)' },
    primary: { main: '#6366f1' }, // indigo-500
    secondary: { main: '#0ea5e9' }, // sky-500
    error: { main: '#ef4444' },
    warning: { main: '#f59e0b' },
    success: { main: '#10b981' },
    divider: 'hsl(220 13% 90%)',
  },
})

export const darkTheme = createTheme({
  ...common,
  components: {
    MuiTextField: {
      defaultProps: { size: 'medium', margin: 'normal' },
    },
    MuiFormControl: {
      defaultProps: { margin: 'normal', size: 'medium' },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 12,
          backgroundColor: theme.palette.background.paper,
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.divider,
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.text.secondary,
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: theme.palette.primary.main,
          },
          '&.Mui-focused': {
            boxShadow: `0 0 0 3px ${theme.palette.primary.main}33`,
          },
        }),
        input: {
          paddingTop: 14,
          paddingBottom: 14,
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: ({ theme }) => ({
          fontWeight: 600,
          color: theme.palette.text.secondary,
          '&.Mui-focused': { color: theme.palette.primary.main },
        }),
      },
    },
    MuiSelect: {
      defaultProps: {
        MenuProps: {
          transformOrigin: { horizontal: 'left', vertical: 'top' },
          anchorOrigin: { horizontal: 'left', vertical: 'bottom' },
          PaperProps: { elevation: 3 },
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: ({ theme }) => ({
          borderRadius: 12,
          paddingTop: 6,
          paddingBottom: 6,
          border: `1px solid ${theme.palette.divider}`,
        }),
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: ({ theme }) => ({
          minHeight: 44,
          borderRadius: 8,
          margin: '2px 6px',
          '&.Mui-selected': {
            backgroundColor: `${theme.palette.primary.main}33`,
          },
        }),
      },
    },
    MuiAutocomplete: {
      defaultProps: {
        size: 'medium',
      },
      styleOverrides: {
        paper: ({ theme }) => ({
          borderRadius: 12,
          border: `1px solid ${theme.palette.divider}`,
        }),
      },
    },
    MuiButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 10,
          textTransform: 'none',
          fontWeight: 600,
          paddingLeft: theme.spacing(2.5),
          paddingRight: theme.spacing(2.5),
        }),
      },
    },
  },
  palette: {
    mode: 'dark',
    background: { default: 'hsl(222 47% 7%)', paper: 'hsl(222 47% 9%)' },
    text: { primary: 'hsl(210 40% 98%)', secondary: 'hsl(219 16% 70%)' },
    primary: { main: '#818cf8' },
    secondary: { main: '#38bdf8' },
    error: { main: '#f87171' },
    warning: { main: '#fbbf24' },
    success: { main: '#34d399' },
    divider: 'hsl(220 17% 20%)',
  },
})

// removed duplicate enhanceInputs; consolidated component overrides above
