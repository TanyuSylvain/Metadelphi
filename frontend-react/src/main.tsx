import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, theme } from 'antd'
import App from './App'
import ErrorBoundary from './components/layout/ErrorBoundary'
import 'highlight.js/styles/github.css'
import './styles/global.css'

const appTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#4a9eff',
    colorLink: '#4a9eff',
    colorBgBase: '#f5f5f5',
    colorBgContainer: '#ffffff',
    borderRadius: 6,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    fontSize: 14,
    colorText: 'rgba(0,0,0,0.88)',
    colorTextSecondary: 'rgba(0,0,0,0.45)',
  },
  components: {
    Layout: {
      siderBg: '#1a1a2e',
      triggerBg: '#2a2a4e',
    },
    Menu: {
      darkItemBg: '#1a1a2e',
      darkSubMenuItemBg: '#2a2a4e',
      darkItemSelectedBg: '#3a3a5e',
      darkItemHoverBg: '#2a2a4e',
      darkItemColor: 'rgba(255,255,255,0.75)',
      darkItemSelectedColor: '#ffffff',
    },
    Segmented: {
      itemSelectedBg: '#4a9eff',
      itemSelectedColor: '#ffffff',
      trackBg: '#f0f0f0',
    },
    Drawer: {
      colorBgElevated: '#1a1a2e',
      colorText: 'rgba(255,255,255,0.88)',
      colorTextHeading: '#ffffff',
      colorIcon: 'rgba(255,255,255,0.45)',
      colorIconHover: 'rgba(255,255,255,0.88)',
      colorBorderSecondary: '#2a2a4e',
    },
    Collapse: {
      contentBg: '#ffffff',
      headerBg: '#f9fafb',
    },
    Slider: {
      colorPrimaryBorder: '#4a9eff',
      colorPrimary: '#4a9eff',
    },
    Switch: {
      colorPrimary: '#4a9eff',
    },
    Button: {
      colorPrimary: '#4a9eff',
    },
    Select: {
      colorPrimary: '#4a9eff',
    },
  },
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider theme={appTheme}>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </ConfigProvider>
  </React.StrictMode>,
)
