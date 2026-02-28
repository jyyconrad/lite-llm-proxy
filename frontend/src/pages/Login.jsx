import React, { useState } from 'react'
import api from '../services/api'

export default function Login({ onLogin, onShowRegister }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      const res = await api.login({ username, password })
      if (res && res.api_key) {
        api.setApiKey(res.api_key)
        const me = await api.getCurrentUser()
        onLogin(res.api_key, me)
      } else {
        setError('登录未返回 api_key')
      }
    } catch (err) {
      const msg = err && err.message ? err.message : (typeof err === 'object' ? JSON.stringify(err) : String(err))
      setError(msg)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-950 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-dark-800 rounded-xl p-8 border border-dark-700 shadow-lg">
          <div className="text-center mb-8">
            <div className="mx-auto h-16 w-16 rounded-lg bg-primary-500 flex items-center justify-center">
              <span className="text-white font-bold text-2xl">L</span>
            </div>
            <h2 className="mt-4 text-3xl font-extrabold text-white">登录账户</h2>
            <p className="mt-2 text-gray-400">请输入您的用户名和密码</p>
          </div>
          
          <form className="mt-8 space-y-6" onSubmit={submit}>
            <div className="rounded-md space-y-4">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-400 mb-1">
                  用户名
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={username}
                  onChange={e=>setUsername(e.target.value)}
                  className="appearance-none rounded-lg relative block w-full px-3 py-3 border border-dark-600 placeholder-gray-500 text-white bg-dark-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="用户名"
                />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-400 mb-1">
                  密码
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  value={password}
                  onChange={e=>setPassword(e.target.value)}
                  className="appearance-none rounded-lg relative block w-full px-3 py-3 border border-dark-600 placeholder-gray-500 text-white bg-dark-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="密码"
                />
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-red-500/20 p-4">
                <div className="text-sm text-red-400">
                  {error}
                </div>
              </div>
            )}

            <div>
              <button
                type="submit"
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-dark-950 bg-primary-500 hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
              >
                登录
              </button>
            </div>
          </form>
          
          <div className="mt-6 text-center">
            <a
              href="#"
              onClick={(e)=>{e.preventDefault(); onShowRegister && onShowRegister()}}
              className="font-medium text-secondary-400 hover:text-secondary-300"
            >
              注册新用户
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

