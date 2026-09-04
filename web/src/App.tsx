import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { UpdatePrompt } from './components/UpdatePrompt'
import { AskSessionProvider } from './lib/ask-session'
import { LayoutProvider } from './lib/layout-context'
import { AgentsPage } from './pages/AgentsPage'
import { ChatPage } from './pages/ChatPage'
import { SettingsPage } from './pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <AskSessionProvider>
        <LayoutProvider>
          <UpdatePrompt />
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<ChatPage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </LayoutProvider>
      </AskSessionProvider>
    </BrowserRouter>
  )
}
