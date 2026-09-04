import { useEffect, useState } from 'react'
import logo from '../assets/logo.png'
import { getHealth } from '../lib/api'
import './Header.css'

export function Header() {
  const [version, setVersion] = useState('')

  useEffect(() => {
    void getHealth()
      .then((health) => {
        if (typeof health.version === 'string' && health.version.trim()) {
          setVersion(health.version.trim())
        }
      })
      .catch(() => {})
  }, [])

  return (
    <header className="app-header">
      <div className="header-left">
        <img src={logo} alt="Abaco Universal Harness" className="header-logo" />
        <h1 className="header-title">Abaco Universal Harness</h1>
        {version ? (
          <span className="header-version" title="Installed app version">
            {version}
          </span>
        ) : null}
      </div>
    </header>
  )
}

export default Header
