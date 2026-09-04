import logo from '../assets/logo.png'
import './Header.css'

export function Header() {
  return (
    <header className="app-header">
      <div className="header-left">
        <img src={logo} alt="Abaco Universal Harness" className="header-logo" />
        <h1 className="header-title">Abaco Universal Harness</h1>
      </div>
    </header>
  )
}

export default Header
