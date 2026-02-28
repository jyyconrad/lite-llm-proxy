import React, { useEffect, useState } from 'react'
import api from '../services/api'

export default function Profile() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchUserProfile() {
      setLoading(true)
      try {
        const userData = await api.getCurrentUser()
        setUser(userData)
      } catch (error) {
        console.error('获取用户信息失败:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchUserProfile()
  }, [])

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-primary-500"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
          <p className="text-gray-400">无法加载用户信息</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg">
        <h2 className="text-xl font-bold text-white mb-6">个人信息</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm mb-1">用户名</label>
              <div className="text-white font-medium">{user.username}</div>
            </div>
            
            <div>
              <label className="block text-gray-400 text-sm mb-1">邮箱</label>
              <div className="text-white font-medium">{user.email || '未设置'}</div>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm mb-1">角色</label>
              <div className="text-white font-medium">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  user.role === 'admin'
                    ? 'bg-purple-500/20 text-purple-400'
                    : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {user.role === 'admin' ? '管理员' : '普通用户'}
                </span>
              </div>
            </div>
            
            <div>
              <label className="block text-gray-400 text-sm mb-1">注册时间</label>
              <div className="text-white font-medium">
                {user.created_at ? new Date(user.created_at).toLocaleString() : '未知'}
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm mb-1">RPM限制 (每分钟请求数)</label>
              <div className="text-white font-medium">{user.rpm_limit === -1 ? '无限制' : (user.rpm_limit || '无限制')}</div>
            </div>
            
            <div>
              <label className="block text-gray-400 text-sm mb-1">TPM限制 (每周token数)</label>
              <div className="text-white font-medium">{user.tpm_limit === -1 ? '无限制' : (user.tpm_limit || '无限制')}</div>
            </div>
            
            <div className="text-xs text-gray-500 mt-2">
              <p>注：当限制值为-1时，表示不进行任何限制</p>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm mb-1">账户状态</label>
              <div className="text-white font-medium">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  user.is_active
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  {user.is_active ? '启用' : '停用'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}



