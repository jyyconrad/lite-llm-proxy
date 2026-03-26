import React, { useEffect, useState } from 'react'
import api from '../services/api'
import SingleNodeForm, { createDefaultNode, PROVIDER_CONFIG } from '../components/models/SingleNodeForm'
import MultiNodeForm from '../components/models/MultiNodeForm'

export default function Models({ user, onNavigate }) {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedModel, setSelectedModel] = useState(null)
  const [filterType, setFilterType] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')

  // 新增模型管理相关状态
  const [showModal, setShowModal] = useState(false)
  const [editingModel, setEditingModel] = useState(null)
  const [form, setForm] = useState({
    model_name: '',
    description: '',
    support_types: ['text'],
    default_rpm: 10,
    default_tpm: 100000,
    default_max_tokens: 32768,
    litellm_params: {},
    is_active: true
  })
  const [formErrors, setFormErrors] = useState({})

  // 终端节点表单相关状态
  const [endpointFormMode, setEndpointFormMode] = useState('single') // 'single' | 'multi'
  const [singleNodeData, setSingleNodeData] = useState(createDefaultNode())
  const [multiNodeData, setMultiNodeData] = useState({ endpoints: [] })
  const [nodeFormErrors, setNodeFormErrors] = useState({})

  // 配置同步相关状态
  const [syncStatus, setSyncStatus] = useState(null)
  const [syncLoading, setSyncLoading] = useState(false)
  const [showSyncModal, setShowSyncModal] = useState(false)

  useEffect(() => {
    loadModels()
    loadSyncStatus()
  }, [])

  async function loadModels() {
    setLoading(true)
    try {
      const res = await api.getModelConfigs()
      setModels(res || [])
    } catch (e) {
      console.error('Failed to load models:', e)
      setModels([])
    }
    setLoading(false)
  }

  async function loadSyncStatus() {
    try {
      const status = await api.getConfigSyncStatus()
      setSyncStatus(status)
    } catch (e) {
      console.error('Failed to load sync status:', e)
    }
  }

  // 打开新增表单
  function openCreate() {
    setEditingModel(null)
    setForm({
      model_name: '',
      description: '',
      support_types: ['text'],
      default_rpm: 10,
      default_tpm: 100000,
      default_max_tokens: 32768,
      litellm_params: {},
      is_active: true
    })
    setEndpointFormMode('single')
    setSingleNodeData(createDefaultNode())
    setMultiNodeData({ endpoints: [] })
    setFormErrors({})
    setNodeFormErrors({})
    setShowModal(true)
  }

  // 打开编辑表单
  function openEdit(model, e) {
    if (e) e.stopPropagation()
    setEditingModel(model)
    setForm({
      model_name: model.model_name,
      description: model.description || '',
      support_types: model.support_types || ['text'],
      default_rpm: model.default_rpm || 10,
      default_tpm: model.default_tpm || 100000,
      default_max_tokens: model.default_max_tokens || 32768,
      litellm_params: model.litellm_params || {},
      is_active: model.is_active !== false
    })

    // 解析现有的 litellm_params 到节点表单
    const litellmParams = model.litellm_params || {}
    if (litellmParams.endpoints && Array.isArray(litellmParams.endpoints)) {
      // 多节点模式
      setEndpointFormMode('multi')
      setMultiNodeData({ endpoints: litellmParams.endpoints })
      setSingleNodeData(createDefaultNode())
    } else if (Object.keys(litellmParams).length > 0) {
      // 单节点模式
      setEndpointFormMode('single')
      setSingleNodeData({
        provider: litellmParams.provider || 'openai',
        model: litellmParams.model || '',
        api_key: litellmParams.api_key || '',
        base_url: litellmParams.base_url || PROVIDER_CONFIG.openai.defaultBaseUrl,
        max_tokens: litellmParams.max_tokens || 4096,
        rpm: litellmParams.rpm || 60,
        tpm: litellmParams.tpm || 100000,
        weight: litellmParams.weight || 1
      })
      setMultiNodeData({ endpoints: [] })
    } else {
      // 默认单节点模式
      setEndpointFormMode('single')
      setSingleNodeData(createDefaultNode())
      setMultiNodeData({ endpoints: [] })
    }

    setFormErrors({})
    setNodeFormErrors({})
    setShowModal(true)
  }

  // 表单验证
  function validateForm() {
    const errors = {}
    if (!form.model_name || !form.model_name.trim()) errors.model_name = '模型名称不能为空'
    if (form.model_name && form.model_name.length > 100) errors.model_name = '模型名称不能超过 100 字符'
    if (!form.support_types || form.support_types.length === 0) {
      errors.support_types = '至少选择一种支持类型'
    }
    if (!form.default_rpm || form.default_rpm <= 0) errors.default_rpm = 'RPM 必须大于 0'
    if (!form.default_tpm || form.default_tpm <= 0) errors.default_tpm = 'TPM 必须大于 0'
    if (!form.default_max_tokens || form.default_max_tokens <= 0) errors.default_max_tokens = 'Max Tokens 必须大于 0'
    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  // 节点表单验证
  function validateNodeForm() {
    const errors = {}

    if (endpointFormMode === 'single') {
      if (!singleNodeData.model?.trim()) errors.model = '模型名称不能为空'
      if (!singleNodeData.api_key?.trim()) errors.api_key = 'API Key 不能为空'
      if (!singleNodeData.base_url?.trim()) errors.base_url = 'Base URL 不能为空'
      if (singleNodeData.max_tokens && singleNodeData.max_tokens <= 0) errors.max_tokens = 'Max Tokens 必须大于 0'
      if (singleNodeData.rpm && singleNodeData.rpm <= 0) errors.rpm = 'RPM 必须大于 0'
      if (singleNodeData.tpm && singleNodeData.tpm <= 0) errors.tpm = 'TPM 必须大于 0'
      if (singleNodeData.weight && singleNodeData.weight < 0) errors.weight = 'Weight 必须大于等于 0'
    } else {
      // 多节点模式
      if (!multiNodeData.endpoints || multiNodeData.endpoints.length === 0) {
        errors.endpoints = '至少添加一个节点'
      } else {
        const endpointErrors = []
        multiNodeData.endpoints.forEach((ep, index) => {
          const epErrors = {}
          if (!ep.model?.trim()) epErrors.model = '模型名称不能为空'
          if (!ep.api_key?.trim()) epErrors.api_key = 'API Key 不能为空'
          if (!ep.base_url?.trim()) epErrors.base_url = 'Base URL 不能为空'
          if (Object.keys(epErrors).length > 0) {
            endpointErrors[index] = epErrors
          }
        })
        if (endpointErrors.length > 0) {
          errors.endpoints = endpointErrors
        }
      }
    }

    setNodeFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  // 提交表单
  async function submitForm(e) {
    e.preventDefault()
    if (!validateForm()) return
    if (!validateNodeForm()) return

    try {
      // 构建 litellm_params
      let litellmParams
      if (endpointFormMode === 'multi') {
        litellmParams = {
          endpoints: multiNodeData.endpoints.map(ep => ({
            ...ep,
            provider: ep.provider || 'openai'
          }))
        }
      } else {
        // 单节点模式 - 确保所有必需字段都存在
        litellmParams = {
          model: singleNodeData.model || '',
          api_key: singleNodeData.api_key || '',
          base_url: singleNodeData.base_url || '',
          provider: singleNodeData.provider || 'openai',
          max_tokens: singleNodeData.max_tokens || 4096,
          rpm: singleNodeData.rpm || 60,
          tpm: singleNodeData.tpm || 100000,
          weight: singleNodeData.weight !== undefined ? singleNodeData.weight : 1
        }
      }

      const submitData = {
        ...form,
        litellm_params: litellmParams
      }

      if (editingModel) {
        await api.updateModelConfig(editingModel.model_name, submitData)
        alert('模型配置已更新')
      } else {
        await api.createModelConfig(submitData)
        alert('模型配置已创建')
      }
      setShowModal(false)
      loadModels()
    } catch (err) {
      setFormErrors({ submit: err.message || '操作失败' })
    }
  }

  // 删除模型
  async function deleteModel(model, e) {
    if (e) e.stopPropagation()
    if (!confirm(`确定要删除模型 "${model.model_name}" 吗？`)) return
    try {
      await api.deleteModelConfig(model.model_name)
      alert('模型已删除')
      loadModels()
    } catch (err) {
      alert(err.message || '删除失败')
    }
  }

  // 切换激活状态
  async function toggleActive(model, e) {
    if (e) e.stopPropagation()
    try {
      if (model.is_active) {
        await api.deactivateModel(model.model_name)
        alert('模型已停用')
      } else {
        await api.activateModel(model.model_name)
        alert('模型已激活')
      }
      loadModels()
    } catch (err) {
      alert(err.message || '操作失败')
    }
  }

  // 处理类型选择
  function toggleSupportType(type) {
    const current = form.support_types || []
    setForm({
      ...form,
      support_types: current.includes(type)
        ? current.filter(t => t !== type)
        : [...current, type]
    })
  }

  // 处理 JSON 输入变化
  function handleJsonChange(value) {
    setForm({ ...form, litellm_params: value })
    // 清除 JSON 格式错误
    if (formErrors.litellm_params) {
      setFormErrors({ ...formErrors, litellm_params: null })
      try {
        JSON.parse(value)
      } catch (e) {
        // 不立即显示错误，等提交时再验证
      }
    }
  }

  // 从 JSON 同步到节点表单
  function syncJsonToNodeForm() {
    try {
      const litellmParams = typeof form.litellm_params === 'string'
        ? JSON.parse(form.litellm_params)
        : form.litellm_params

      if (litellmParams?.endpoints && Array.isArray(litellmParams.endpoints)) {
        setEndpointFormMode('multi')
        setMultiNodeData({ endpoints: litellmParams.endpoints })
      } else if (litellmParams && Object.keys(litellmParams).length > 0) {
        setEndpointFormMode('single')
        setSingleNodeData({
          provider: litellmParams.provider || 'openai',
          model: litellmParams.model || '',
          api_key: litellmParams.api_key || '',
          base_url: litellmParams.base_url || PROVIDER_CONFIG.openai.defaultBaseUrl,
          max_tokens: litellmParams.max_tokens || 4096,
          rpm: litellmParams.rpm || 60,
          tpm: litellmParams.tpm || 100000,
          weight: litellmParams.weight || 1
        })
      }
    } catch (e) {
      console.error('Failed to parse JSON:', e)
    }
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

  // 手动触发同步
  async function handleSync(e) {
    if (e) e.stopPropagation()

    const modelCount = syncStatus?.model_count || 0
    if (!confirm(`确定要从 YAML 配置文件同步模型配置到数据库吗？

当前数据库模型数：${modelCount}
同步规则:
• 数据库中已存在的模型将保持不变
• 只会添加 YAML 中新增的模型
• 不会删除或修改任何现有配置`)) {
      return
    }

    setSyncLoading(true)
    try {
      const result = await api.triggerConfigSync()
      alert(`同步完成：${result.result}`)
      // 并行加载数据
      await Promise.all([loadSyncStatus(), loadModels()])
    } catch (err) {
      console.error('同步失败:', err)
      alert(err.message || '同步失败，请重试')
    } finally {
      setSyncLoading(false)
    }
  }

  function openSyncModal() {
    setShowSyncModal(true)
  }

  const getStatusColor = () => {
    if (!syncStatus) return 'gray'
    if (syncStatus.is_synced) return 'green'
    if (syncStatus.yaml_changed) return 'yellow'
    return 'gray'
  }

  const getStatusText = () => {
    if (!syncStatus) return '未知'
    if (syncStatus.is_synced) return '已同步'
    if (syncStatus.yaml_changed) return 'YAML 有更新'
    if (syncStatus.db_changed) return '数据库已更新'
    return '未知'
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">模型管理</h1>
          <p className="text-gray-400">查看和管理所有可用模型</p>
        </div>
        <div className="flex gap-3 flex-wrap">
          {/* 同步状态指示器 */}
          {syncStatus && (
            <div className="flex items-center gap-2 px-3 py-2 bg-dark-800 rounded-lg border border-dark-700">
              <div className={`w-2 h-2 rounded-full ${
                getStatusColor() === 'green' ? 'bg-green-500' :
                getStatusColor() === 'yellow' ? 'bg-yellow-500' :
                'bg-gray-500'
              }`}></div>
              <span className="text-gray-300 text-sm">{getStatusText()}</span>
              {syncStatus.last_sync_time && (
                <span className="text-gray-500 text-xs">
                  · 最后同步：{new Date(syncStatus.last_sync_time).toLocaleString('zh-CN')}
                </span>
              )}
            </div>
          )}
          <button
            onClick={openSyncModal}
            disabled={syncLoading}
            className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {syncLoading ? '同步中...' : '同步配置'}
          </button>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-dark-950 rounded-lg transition-colors font-medium"
          >
            新增模型
          </button>
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
              className="bg-dark-800 rounded-xl p-5 border border-dark-700 hover:border-primary-500 transition-colors cursor-pointer relative"
            >
              {/* 操作按钮层 */}
              <div className="absolute top-3 right-3 z-10" onClick={e => e.stopPropagation()}>
                <div className="flex gap-1">
                  <button
                    onClick={(e) => openEdit(model, e)}
                    className="p-1.5 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded transition-colors"
                    title="编辑"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => toggleActive(model, e)}
                    className={`p-1.5 rounded transition-colors ${
                      model.is_active
                        ? 'bg-red-500/20 hover:bg-red-500/30 text-red-400'
                        : 'bg-green-500/20 hover:bg-green-500/30 text-green-400'
                    }`}
                    title={model.is_active ? '停用' : '激活'}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={model.is_active ? "M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" : "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"} />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => deleteModel(model, e)}
                    className="p-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded transition-colors"
                    title="删除"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>

              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-bold text-white truncate pr-16">{model.model_name}</h3>
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
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setSelectedModel(null)}>
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg w-full max-w-2xl max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
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

      {/* 创建/编辑模型表单弹窗 */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-xl font-bold text-white">
                  {editingModel ? '编辑模型配置' : '新增模型配置'}
                </h3>
                <p className="text-gray-400 text-sm">
                  {editingModel ? `修改模型：${editingModel.model_name}` : '创建新的模型配置'}
                </p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-white text-xl"
              >
                &times;
              </button>
            </div>

            <form onSubmit={submitForm} className="space-y-4">
              {/* 模型名称 */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  模型名称 *
                </label>
                <input
                  type="text"
                  value={form.model_name}
                  onChange={(e) => setForm({ ...form, model_name: e.target.value })}
                  disabled={!!editingModel}
                  placeholder="例如：GPT-4"
                  className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                    formErrors.model_name ? 'border-red-500' : 'border-dark-600'
                  }`}
                />
                {formErrors.model_name && (
                  <p className="text-red-400 text-xs mt-1">{formErrors.model_name}</p>
                )}
              </div>

              {/* 描述 */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  描述
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="模型描述信息"
                  rows={2}
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              {/* 支持类型 */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  支持类型 *
                </label>
                <div className="flex gap-3">
                  {[
                    { value: 'text', label: '文本' },
                    { value: 'image', label: '图片' },
                    { value: 'embedding', label: '向量' }
                  ].map(type => (
                    <label key={type.value} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.support_types?.includes(type.value)}
                        onChange={() => toggleSupportType(type.value)}
                        className="w-4 h-4 rounded bg-dark-700 border-dark-600 text-primary-500 focus:ring-primary-500"
                      />
                      <span className="text-gray-300 text-sm">{type.label}</span>
                    </label>
                  ))}
                </div>
                {formErrors.support_types && (
                  <p className="text-red-400 text-xs mt-1">{formErrors.support_types}</p>
                )}
              </div>

              {/* RPM / TPM / Max Tokens */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    RPM 限制 *
                  </label>
                  <input
                    type="number"
                    value={form.default_rpm}
                    onChange={(e) => setForm({ ...form, default_rpm: parseInt(e.target.value) || 0 })}
                    className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                      formErrors.default_rpm ? 'border-red-500' : 'border-dark-600'
                    }`}
                  />
                  {formErrors.default_rpm && (
                    <p className="text-red-400 text-xs mt-1">{formErrors.default_rpm}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    TPM 限制 *
                  </label>
                  <input
                    type="number"
                    value={form.default_tpm}
                    onChange={(e) => setForm({ ...form, default_tpm: parseInt(e.target.value) || 0 })}
                    className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                      formErrors.default_tpm ? 'border-red-500' : 'border-dark-600'
                    }`}
                  />
                  {formErrors.default_tpm && (
                    <p className="text-red-400 text-xs mt-1">{formErrors.default_tpm}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Max Tokens *
                  </label>
                  <input
                    type="number"
                    value={form.default_max_tokens}
                    onChange={(e) => setForm({ ...form, default_max_tokens: parseInt(e.target.value) || 0 })}
                    className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                      formErrors.default_max_tokens ? 'border-red-500' : 'border-dark-600'
                    }`}
                  />
                  {formErrors.default_max_tokens && (
                    <p className="text-red-400 text-xs mt-1">{formErrors.default_max_tokens}</p>
                  )}
                </div>
              </div>

              {/* LiteLLM 参数配置 - 使用表单组件 */}
              <div className="border border-dark-600 rounded-lg overflow-hidden">
                {/* 模式切换标签 */}
                <div className="flex border-b border-dark-600">
                  <button
                    type="button"
                    onClick={() => setEndpointFormMode('single')}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                      endpointFormMode === 'single'
                        ? 'bg-primary-500/20 text-primary-400 border-b-2 border-primary-500'
                        : 'bg-dark-800 text-gray-400 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      单节点配置
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setEndpointFormMode('multi')}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                      endpointFormMode === 'multi'
                        ? 'bg-primary-500/20 text-primary-400 border-b-2 border-primary-500'
                        : 'bg-dark-800 text-gray-400 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      多节点配置
                    </div>
                  </button>
                </div>

                {/* 表单内容 */}
                <div className="p-4">
                  {endpointFormMode === 'single' ? (
                    <SingleNodeForm
                      value={singleNodeData}
                      onChange={setSingleNodeData}
                      errors={nodeFormErrors}
                    />
                  ) : (
                    <MultiNodeForm
                      value={multiNodeData}
                      onChange={setMultiNodeData}
                      errors={nodeFormErrors}
                    />
                  )}
                </div>
              </div>

              {/* 高级模式 - JSON 编辑器 */}
              <div>
                <details className="group">
                  <summary className="flex justify-between items-center cursor-pointer list-none text-sm text-gray-400 hover:text-white">
                    <span>高级模式：JSON 代码视图</span>
                    <svg
                      className="w-4 h-4 text-gray-400 transition-transform group-open:rotate-180"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </summary>
                  <div className="mt-3">
                    <textarea
                      value={typeof form.litellm_params === 'object' && form.litellm_params !== null ? JSON.stringify(form.litellm_params, null, 2) : form.litellm_params || ''}
                      onChange={(e) => handleJsonChange(e.target.value)}
                      placeholder='例如：{"model": "gpt-4", "api_key": "sk-..."}'
                      rows={8}
                      className="w-full bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white font-mono text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <p className="text-gray-500 text-xs mt-1">
                      💡 提示：建议使用上方表单进行配置，JSON 编辑仅在需要高级配置时使用
                    </p>
                  </div>
                </details>
              </div>

              {/* 激活状态 */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  className="w-4 h-4 rounded bg-dark-700 border-dark-600 text-primary-500 focus:ring-primary-500"
                />
                <label htmlFor="is_active" className="text-gray-300 text-sm cursor-pointer">
                  启用此模型
                </label>
              </div>

              {/* 全局错误 */}
              {formErrors.submit && (
                <div className="bg-red-500/20 border border-red-500 rounded-lg p-3 text-red-400 text-sm">
                  {formErrors.submit}
                </div>
              )}

              {/* 提交按钮 */}
              <div className="flex justify-end gap-3 pt-4 border-t border-dark-700">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-dark-950 rounded-lg transition-colors font-medium"
                >
                  {editingModel ? '保存修改' : '创建模型'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 同步配置弹窗 */}
      {showSyncModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setShowSyncModal(false)}>
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-lg w-full max-w-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-xl font-bold text-white">配置同步</h3>
                <p className="text-gray-400 text-sm">YAML 配置文件 ↔ 数据库</p>
              </div>
              <button
                onClick={() => setShowSyncModal(false)}
                className="text-gray-400 hover:text-white text-xl"
              >
                &times;
              </button>
            </div>

            {/* 同步状态信息 */}
            {syncStatus && (
              <div className="space-y-4 mb-6">
                <div className="bg-dark-700 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-gray-300">同步状态</span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      syncStatus.is_synced
                        ? 'bg-green-500/20 text-green-400'
                        : syncStatus.yaml_changed
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {getStatusText()}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-dark-800 rounded-lg p-3">
                      <p className="text-gray-500 text-xs mb-1">YAML 配置</p>
                      <p className="text-white font-mono text-sm truncate" title={syncStatus.yaml_hash_short}>
                        {syncStatus.yaml_hash_short || 'N/A'}
                      </p>
                    </div>
                    <div className="bg-dark-800 rounded-lg p-3">
                      <p className="text-gray-500 text-xs mb-1">数据库配置</p>
                      <p className="text-white font-mono text-sm truncate" title={syncStatus.db_hash_short}>
                        {syncStatus.db_hash_short || 'N/A'}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 flex justify-between text-sm">
                    <span className="text-gray-400">
                      最后同步时间：{syncStatus.last_sync_time
                        ? new Date(syncStatus.last_sync_time).toLocaleString('zh-CN')
                        : '从未同步'
                      }
                    </span>
                    <span className="text-gray-400">
                      同步来源：{syncStatus.last_sync_source || '无'}
                    </span>
                  </div>
                </div>

                {/* 同步说明 */}
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                  <h4 className="text-blue-400 font-medium mb-2">同步规则</h4>
                  <ul className="text-gray-300 text-sm space-y-1">
                    <li>• 数据库优先：数据库中已存在的模型将保持不变</li>
                    <li>• 增量同步：只会添加 YAML 中新增的模型</li>
                    <li>• 安全保护：不会覆盖数据库中的配置</li>
                  </ul>
                </div>

                {/* 模型统计 */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-dark-700 rounded-lg p-3 text-center">
                    <p className="text-gray-500 text-xs mb-1">数据库模型数</p>
                    <p className="text-2xl font-bold text-white">{syncStatus.model_count}</p>
                  </div>
                  <div className="bg-dark-700 rounded-lg p-3 text-center">
                    <p className="text-gray-500 text-xs mb-1">YAML 有更新</p>
                    <p className={`text-2xl font-bold ${
                      syncStatus.yaml_changed ? 'text-yellow-400' : 'text-green-400'
                    }`}>
                      {syncStatus.yaml_changed ? '是' : '否'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowSyncModal(false)}
                className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
              >
                关闭
              </button>
              <button
                type="button"
                onClick={handleSync}
                disabled={syncLoading || (syncStatus && syncStatus.is_synced)}
                className={`px-4 py-2 rounded-lg transition-colors font-medium ${
                  syncLoading || (syncStatus && syncStatus.is_synced)
                    ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    : 'bg-primary-500 hover:bg-primary-600 text-dark-950'
                }`}
              >
                {syncLoading ? '同步中...' : '立即同步'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
