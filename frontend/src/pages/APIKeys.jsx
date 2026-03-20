import React, { useEffect, useState } from 'react'
import api from '../services/api'

export default function APIKeys(){
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [currentUser, setCurrentUser] = useState(null)

  // 新增：展开显示的密钥 ID 和复制状态
  const [expandedKeyId, setExpandedKeyId] = useState(null)
  const [copyingKeyId, setCopyingKeyId] = useState(null)

  useEffect(()=>{ init() }, [])
  async function init(){
    setLoading(true)
    try{
      const me = await api.getCurrentUser()
      setCurrentUser(me)
      const data = await api.getOwnAPIKeys()
      setKeys(data||[])
    }catch(e){ setKeys([]) }
    setLoading(false)
  }

  async function createKey(e){
    e.preventDefault()
    try{
      const res = await api.createOwnAPIKey({ description: 'Created from UI' })
      // show plain api_key to user for copying
      alert('Key created: ' + (res.api_key||res))
      init()
    }catch(err){ alert(err.message||String(err)) }
  }

  async function copyKey(k){
    // 如果已经展开，则收起
    if (expandedKeyId === k.id) {
      setExpandedKeyId(null)
      setCopyingKeyId(null)
      return
    }

    try {
      const keyToCopy = k.api_key;
      if(keyToCopy){
        // 先展开显示完整密钥
        setExpandedKeyId(k.id)
        setCopyingKeyId(k.id)

        // 执行复制
        await navigator.clipboard.writeText(keyToCopy)

        // 3 秒后自动收起
        setTimeout(() => {
          setExpandedKeyId(null)
          setCopyingKeyId(null)
        }, 3000)
        return
      }

      // fallback: 尝试从 API 获取
      const res = await api.getUserAPIKey(k.user_id)
      if(res && res.api_key){
        setExpandedKeyId(k.id)
        await navigator.clipboard.writeText(res.api_key)
        setTimeout(() => setExpandedKeyId(null), 3000)
      } else {
        alert('无法获取密钥值')
      }
    }catch(e){
      alert(String(e))
      setExpandedKeyId(null)
      setCopyingKeyId(null)
    }
  }

  async function toggleKey(k){
    try{
      if(k.is_active){
        await api.disableOwnAPIKey(k.id)
      } else {
        await api.enableOwnAPIKey(k.id)
      }
      init()
    }catch(e){ alert(String(e)) }
  }

  // 隐藏密钥中间部分的函数
  function maskApiKey(apiKey) {
    if (!apiKey || apiKey.length <= 8) {
      return apiKey;
    }

    const prefix = apiKey.substring(0, 4);
    const suffix = apiKey.substring(apiKey.length - 4);
    return `${prefix}****${suffix}`;
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg mb-6">
        <h2 className="text-xl font-bold text-white mb-4">创建 API 密钥</h2>
        <form onSubmit={createKey} className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
          <div className="text-gray-400">用户：{currentUser? currentUser.username : '加载中...'}</div>
          <button
            type="submit"
            className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-dark-950 rounded-lg transition-colors font-medium"
          >
            创建密钥
          </button>
        </form>
      </div>

      <div className="bg-dark-800 rounded-xl border border-dark-700 shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-dark-700">
              <tr>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">密钥（ApiKey）</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">创建时间</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">状态</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-gray-400">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-primary-500"></div>
                    </div>
                  </td>
                </tr>
              ) : keys.map(k => (
                <tr key={k.id} className="border-b border-dark-700 hover:bg-dark-750 transition-colors">
                  <td className="py-3 px-4 text-white font-mono text-sm">
                    {/* 掩码显示 */}
                    {maskApiKey(k.api_key || k.id)}

                    {/* 展开状态下的完整密钥显示 */}
                    {expandedKeyId === k.id && (
                      <div className="mt-2 p-3 bg-primary-500/20 border border-primary-500/50 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-xs text-gray-300 font-medium">完整密钥（3 秒后自动隐藏）：</p>
                          {copyingKeyId === k.id && (
                            <span className="text-green-400 text-xs flex items-center gap-1">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                              已复制!
                            </span>
                          )}
                        </div>
                        <code className="text-white text-sm break-all bg-dark-800/50 px-3 py-2 rounded block font-mono">
                          {k.api_key || '加载中...'}
                        </code>
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-300">{k.created_at}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      k.is_active
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {k.is_active ? '启用' : '停用'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={()=>copyKey(k)}
                        className={`px-3 py-1 rounded-lg transition-colors text-sm ${
                          expandedKeyId === k.id
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-dark-700 hover:bg-dark-600 text-gray-300'
                        }`}
                      >
                        {expandedKeyId === k.id ? '已复制' : '复制'}
                      </button>
                      <button
                        onClick={()=>toggleKey(k)}
                        className={`px-3 py-1 rounded-lg transition-colors text-sm ${
                          k.is_active
                            ? 'bg-red-500/20 hover:bg-red-500/30 text-red-400'
                            : 'bg-green-500/20 hover:bg-green-500/30 text-green-400'
                        }`}
                      >
                        {k.is_active ? '停用' : '启用'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && keys.length===0 && (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-gray-400">
                    暂无 API 密钥
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
