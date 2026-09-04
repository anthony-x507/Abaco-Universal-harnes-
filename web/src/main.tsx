import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

const splash = document.getElementById('splash')
if (splash) {
  requestAnimationFrame(() => {
    splash.classList.add('is-done')
    splash.addEventListener('transitionend', () => splash.remove(), { once: true })
    window.setTimeout(() => splash.remove(), 600)
  })
}
