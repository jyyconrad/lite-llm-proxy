import React, { useEffect, useState } from 'react'
import Header from './components/Header'
import Dashboard from './components/Dashboard'
import ModelLogs from './pages/ModelLogs'
import Users from './pages/Users'
import APIKeys from './pages/APIKeys'
import Login from './pages/Login'
import Register from './pages/Register'
import Profile from './pages/Profile'
import api from './services/api'

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [user, setUser] = useState(null)

  useEffect(() => {
    async function init() {
      if (localStorage.getItem('api_key')) {
        try {
          api.setApiKey(localStorage.getItem('api_key'))
          const me = await api.getCurrentUser()
          setUser(me)
        } catch (e) {
          api.setApiKey(null)
          setUser(null)
          setCurrentPage('login')
        }
      } else {
        setCurrentPage('login')
      }
    }
    init()
  }, [])

  function handleNavigate(p) { setCurrentPage(p) }

  function handleLoginSuccess(apiKey, me) {
    api.setApiKey(apiKey)
    setUser(me)
    setCurrentPage('dashboard')
  }

  if (!user && currentPage === 'login') {
    return <Login onLogin={handleLoginSuccess} onShowRegister={() => setCurrentPage('register')} />
  }

  if (!user && currentPage === 'register') {
    return <Register onRegistered={handleLoginSuccess} onShowLogin={() => setCurrentPage('login')} />
  }

  return (
    <div className="app">
      <Header onNavigate={handleNavigate} user={user} />
      <main className="container mx-auto">
        {currentPage === 'dashboard' && <Dashboard user={user} onNavigate={handleNavigate} />}
        {currentPage === 'users' && <Users />}
        {currentPage === 'api-keys' && <APIKeys />}
        {currentPage === 'model-logs' && <ModelLogs user={user} onNavigate={handleNavigate} />}
        {currentPage === 'profile' && <Profile />}
      </main>
    </div>
  )
}



