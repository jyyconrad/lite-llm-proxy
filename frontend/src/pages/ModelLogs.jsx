import React, { useEffect, useState } from 'react'
import api from '../services/api'

export default function ModelLogs({ user, onNavigate }) {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [total, setTotal] = useState(0)
  
  // 筛选条件
  const [searchTerm, setSearchTerm] = useState('')
  const [modelFilter, setModelFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [models, setModels] = useState([])

  useEffect(() => {
    loadModels()
  }, [])

  useEffect(() => { 
    load() 
  }, [page, modelFilter, statusFilter])

  async function loadModels() {
    try {
      const res = await api.getModels()
      setModels(res.models || [])
    } catch (e) {
      setModels([])
    }
  }

  async function load() {
    setLoading(true)
    try {
      const res = await api.getRecentActivity(perPage * 3)
      let filteredLogs = res || []
      
      // 客户端过滤
      if (modelFilter) {
        filteredLogs = filteredLogs.filter(l => l.model_name === modelFilter)
      }
      if (statusFilter !== 'all') {
        filteredLogs = filteredLogs.filter(l => 
          statusFilter === 'success' ? l.success !== false : l.success === false
        )
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase()
        filteredLogs = filteredLogs.filter(l => 
          (l.model_name && l.model_name.toLowerCase().includes(term)) ||
          (l.user_email && l.user_email.toLowerCase().includes(term)) ||
          (l.id && l.id.toLowerCase().includes(term))
        )
      }
      
      // 分页
      const start = (page - 1) * perPage
      setLogs(filteredLogs.slice(start, start + perPage))
      setTotal(filteredLogs.length)
    } catch (e) {
      setLogs([])
      setTotal(0)
    }
    setLoading(false)
  }

  if (!user || user.role !== 'admin') {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700">
          <h3 className="text-xl font-bold text-white mb-2">访问被拒绝</h3>
          <p className="text-gray-400 mb-4">只有管理员可以查看模型日志。</p>
          <button 
            onClick={() => onNavigate && onNavigate('dashboard')}
            className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-dark-950 rounded-lg transition-colors"
          >
            返回概览
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">模型日志</h1>
          <p className="text-gray-400">查看所有模型调用记录</p>
        </div>
        <button 
          onClick={() => onNavigate && onNavigate('dashboard')}
          className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
        >
          返回概览
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-dark-800 rounded-xl p-4 border border-dark-700 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="搜索日志..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && load()}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <select
            value={modelFilter}
            onChange={(e) => setModelFilter(e.target.value)}
            className="bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">全部模型</option>
            {models.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">全部状态</option>
            <option value="success">成功</option>
            <option value="error">失败</option>
          </select>
          <button
            onClick={load}
            className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-dark-950 rounded-lg transition-colors font-medium"
          >
            搜索
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
          <p className="text-gray-400 text-sm">总记录数</p>
          <p className="text-2xl font-bold text-white">{total}</p>
        </div>
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
          <p className="text-gray-400 text-sm">成功调用</p>
          <p className="text-2xl font-bold text-green-400">
            {logs.filter(l => l.success !== false).length}
          </p>
        </div>
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
          <p className="text-gray-400 text-sm">失败调用</p>
          <p className="text-2xl font-bold text-red-400">
            {logs.filter(l => l.success === false).length}
          </p>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-dark-800 rounded-xl border border-dark-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-dark-700">
              <tr>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">时间</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">用户</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">模型</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Tokens</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">成本</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">耗时</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500"></div>
                    </div>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400">
                    暂无日志数据
                  </td>
                </tr>
              ) : logs.map(l => (
                <tr key={l.id} className="border-b border-dark-700 hover:bg-dark-750 transition-colors">
                  <td className="py-3 px-4 text-gray-300 whitespace-nowrap">
                    {l.timestamp ? new Date(l.timestamp).toLocaleString() : '-'}
                  </td>
                  <td className="py-3 px-4 text-white">{l.user_email || '-'}</td>
                  <td className="py-3 px-4 text-primary-400 font-medium">{l.model_name || '-'}</td>
                  <td className="py-3 px-4 text-gray-300">{l.total_tokens?.toLocaleString() || '-'}</td>
                  <td className="py-3 px-4 text-gray-300">${l.cost?.toFixed(6) || '0.000000'}</td>
                  <td className="py-3 px-4 text-gray-300">{l.response_time ? `${l.response_time}ms` : '-'}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      l.success !== false
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {l.success !== false ? '成功' : '失败'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center mt-6">
        <div className="text-gray-400">
          第 {page} 页，共 {Math.ceil(total / perPage)} 页
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page <= 1}
            className={`px-4 py-2 rounded-lg transition-colors ${
              page <= 1
                ? 'bg-dark-800 text-gray-600 cursor-not-allowed'
                : 'bg-dark-700 hover:bg-dark-600 text-gray-300'
            }`}
          >
            上一页
          </button>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page >= Math.ceil(total / perPage)}
            className={`px-4 py-2 rounded-lg transition-colors ${
              page >= Math.ceil(total / perPage)
                ? 'bg-dark-800 text-gray-600 cursor-not-allowed'
                : 'bg-dark-700 hover:bg-dark-600 text-gray-300'
            }`}
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  )
}
