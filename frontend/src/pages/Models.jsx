import React, { useEffect, useState } from 'react'
import api from '../services/api'

export default function Models({ user, onNavigate }) {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedModel, setSelectedModel] = useState(null)
  const [filterType, setFilterType] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadModels()
  }, [])

  async function loadModels() {
    setLoading(true)
    try {
      const res = await api.getAllModels()
      setModels(res.models || [])
    } catch (e) {
      console.error('Failed to load models:', e)
      setModels([])
    }
    setLoading(false)
  }

  const filteredModels = models.filter(m => {
    const matchesType = filterType === 'all' || 
      (m.support_types && m.support_types.includes(filterType))
    const matchesSearch = !searchTerm || 
      m.model_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (m.description && m.description.toLowerCase().includes(searchTerm.toLowerCase()))
    return matchesType && matchesSearch
  })

  const getTypeColor = (types) => {
    if (!types) return 'gray'
    if (types.includes('image')) return 'purple'
    if (types.includes('embedding')) return 'green'
    return 'blue'
  }

  const getProviderBadge = (provider) => {
    const colors = {
      openai: 'bg-green-500/20 text-green-400',
      anthropic: 'bg-purple-500/20 text-purple-400',
      azure: 'bg-blue-500/20 text-blue-400',
      local: 'bg-orange-500/20 text-orange-400',
      ollama: 'bg-yellow-500/20 text-yellow-400',
      custom: 'bg-gray-500/20 text-gray-400',
    }
    return colors[provider] || colors.custom
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">模型管理</h1>
          <p className="text-gray-400">查看和管理所有可用模型</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => onNavigate && onNavigate('dashboard')}
            className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
          >
            返回概览
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-dark-800 rounded-xl p-4 border border-dark-700 shadow-lg mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="搜索模型..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="flex gap-2">
            {['all', 'text', 'image', 'embedding'].map(type => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  filterType === type
                    ? 'bg-primary-500 text-dark-950'
                    : 'bg-dark-700 text-gray-300 hover:bg-dark-600'
                }`}
              >
                {type === 'all' ? '全部' : type === 'text' ? '文本' : type === 'image' ? '图片' : '向量'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
          <p className="text-gray-400 text-sm">总模型数</p>
          <p className="text-2xl font-bold text-white">{models.length}</p>
        </div>
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
          <p className="text-gray-400 text-sm">文本模型</p>
          <p className="text-2xl font-bold text-blue-400">
            {models.filter(m => m.support_types?.includes('text')).length}
          </p>
        </div>
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
          <p className="text-gray-400 text-sm">图片模型</p>
          <p className="text-2xl font-bold text-purple-400">
            {models.filter(m => m.support_types?.includes('image')).length}
          </p>
        </div>
        <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
          <p className="text-gray-400 text-sm">向量模型</p>
          <p className="text-2xl font-bold text-green-400">
            {models.filter(m => m.support_types?.includes('embedding')).length}
          </p>
        </div>
      </div>

      {/* Models Grid */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredModels.map(model => (
            <div
              key={model.model_name}
              onClick={() => setSelectedModel(model)}
              className="bg-dark-800 rounded-xl p-5 border border-dark-700 hover:border-primary-500 transition-colors cursor-pointer"
            >
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-bold text-white truncate">{model.model_name}</h3>
                {model.support_types && model.support_types.map(type => (
                  <span
                    key={type}
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      type === 'text' ? 'bg-blue-500/20 text-blue-400' :
                      type === 'image' ? 'bg-purple-500/20 text-purple-400' :
                      'bg-green-500/20 text-green-400'
                    }`}
                  >
                    {type}
                  </span>
                ))}
              </div>
              
              <p className="text-gray-400 text-sm mb-3 line-clamp-2">
                {model.description || '暂无描述'}
              </p>

              <div className="flex flex-wrap gap-2 mb-3">
                {model.endpoints?.slice(0, 3).map((ep, idx) => (
                  <span
                    key={idx}
                    className={`px-2 py-1 rounded text-xs ${getProviderBadge(ep.provider)}`}
                  >
                    {ep.provider}
                  </span>
                ))}
                {(model.endpoints?.length || 0) > 3 && (
                  <span className="text-gray-500 text-xs">+{model.endpoints.length - 3} more</span>
                )}
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <p className="text-gray-500">RPM</p>
                  <p className="text-white font-medium">{model.default_rpm}</p>
                </div>
                <div>
                  <p className="text-gray-500">TPM</p>
                  <p className="text-white font-medium">{(model.default_tpm / 1000).toFixed(0)}K</p>
                </div>
                <div>
                  <p className="text-gray-500">Max Tokens</p>
                  <p className="text-white font-medium">{(model.default_max_tokens / 1024).toFixed(0)}K</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && filteredModels.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400">没有找到匹配的模型</p>
        </div>
      )}

      {/* Model Detail Modal */}
      {selectedModel && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-bold text-white">{selectedModel.model_name}</h3>
                <p className="text-gray-400 text-sm">{selectedModel.description}</p>
              </div>
              <button
                onClick={() => setSelectedModel(null)}
                className="text-gray-400 hover:text-white text-xl"
              >
                &times;
              </button>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-dark-700 rounded-lg p-3">
                <p className="text-gray-400 text-xs">RPM限制</p>
                <p className="text-white font-bold">{selectedModel.default_rpm}</p>
              </div>
              <div className="bg-dark-700 rounded-lg p-3">
                <p className="text-gray-400 text-xs">TPM限制</p>
                <p className="text-white font-bold">{selectedModel.default_tpm.toLocaleString()}</p>
              </div>
              <div className="bg-dark-700 rounded-lg p-3">
                <p className="text-gray-400 text-xs">最大Token</p>
                <p className="text-white font-bold">{selectedModel.default_max_tokens.toLocaleString()}</p>
              </div>
            </div>

            <h4 className="text-lg font-bold text-white mb-3">终端节点 ({selectedModel.endpoints?.length || 0})</h4>
            <div className="space-y-3">
              {selectedModel.endpoints?.map((ep, idx) => (
                <div key={idx} className="bg-dark-700 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <span className={`px-2 py-1 rounded text-xs ${getProviderBadge(ep.provider)}`}>
                      {ep.provider}
                    </span>
                    <span className="text-gray-400 text-xs">权重: {ep.weight}</span>
                  </div>
                  <p className="text-white text-sm font-medium mb-1">{ep.model}</p>
                  <p className="text-gray-500 text-xs truncate">{ep.base_url}</p>
                  <div className="flex gap-4 mt-2 text-xs text-gray-400">
                    <span>RPM: {ep.rpm}</span>
                    <span>TPM: {ep.tpm.toLocaleString()}</span>
                    <span>Max: {ep.max_tokens?.toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => setSelectedModel(null)}
                className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
