import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { UpdatePrompt } from './components/UpdatePrompt'
import { ActivityProvider } from './lib/activity'
import { AskSessionProvider } from './lib/ask-session'
import { LayoutProvider } from './lib/layout-context'
import { AgentsPage } from './pages/AgentsPage'
import { ChatPage } from './pages/ChatPage'
import { DesignPage } from './pages/DesignPage'
import { SettingsPage } from './pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <AskSessionProvider>
        <ActivityProvider>
          <LayoutProvider>
            <UpdatePrompt />
            <Routes>
              <Route element={<AppShell />}>
                <Route path="/" element={<ChatPage />} />
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/design" element={<DesignPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </LayoutProvider>
        </ActivityProvider>
      </AskSessionProvider>
    </BrowserRouter>
  )
}
