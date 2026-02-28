import React from 'react'

export default function Header({ onNavigate, user }) {
  return (
    <header className="bg-dark-950/80 backdrop-blur-md border-b border-dark-800 sticky top-0 z-10">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-primary-500 flex items-center justify-center">
            <span className="text-white font-bold text-lg">L</span>
          </div>
          <h1 className="text-xl font-bold text-secondary-400">LLM Proxy</h1>
        </div>
        
        <nav className=" md:flex items-center space-x-1">
          <button
            onClick={() => onNavigate('dashboard')}
            className="px-4 py-2 rounded-lg text-gray-300 hover:bg-dark-800 hover:text-white transition-colors"
          >
            数据概览
          </button>
          <button
            onClick={() => onNavigate('api-keys')}
            className="px-4 py-2 rounded-lg text-gray-300 hover:bg-dark-800 hover:text-white transition-colors"
          >
            APIKeys
          </button>
          {user && user.role === 'admin' && (
            <button
              onClick={() => onNavigate('users')}
              className="px-4 py-2 rounded-lg text-gray-300 hover:bg-dark-800 hover:text-white transition-colors"
            >
              用户信息
            </button>
          )}
        </nav>
        
        {user ? (
          <div className="relative group">
            <button className="flex items-center space-x-2 focus:outline-none">
              <div className="w-8 h-8 rounded-full bg-secondary-500 flex items-center justify-center">
                <span className="text-dark-950 font-medium">
                  {user.username?.charAt(0).toUpperCase() || 'U'}
                </span>
              </div>
              <span className="text-gray-300 hidden md:inline">{user.username}</span>
            </button>
            
            <div className="absolute right-0 mt-2 w-48 bg-dark-800 rounded-md shadow-lg py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-20">
              <button
                onClick={() => onNavigate && onNavigate('profile')}
                className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-dark-700 hover:text-white"
              >
                个人信息
              </button>
              <button
                onClick={() => {
                  localStorage.removeItem('api_key');
                  window.location.reload();
                }}
                className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-dark-700 hover:text-white"
              >
                退出登录
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => onNavigate('login')}
            className="px-4 py-2 bg-primary-500 text-dark-950 rounded-lg hover:bg-primary-600 transition-colors font-medium"
          >
            登录
          </button>
        )}
      </div>
    </header>
  )
}

