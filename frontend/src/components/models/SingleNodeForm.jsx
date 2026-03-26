import React, { useState } from 'react'

// 供应商配置
const PROVIDER_CONFIG = {
  openai: {
    label: 'OpenAI',
    defaultBaseUrl: 'https://api.openai.com/v1',
    placeholder: 'sk-...'
  },
  anthropic: {
    label: 'Anthropic',
    defaultBaseUrl: 'https://api.anthropic.com',
    placeholder: 'sk-ant-...'
  },
  azure: {
    label: 'Azure',
    defaultBaseUrl: 'https://{resource}.openai.azure.com',
    placeholder: 'Azure API Key'
  },
  gemini: {
    label: 'Gemini',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com',
    placeholder: 'Google API Key'
  },
  ollama: {
    label: 'Ollama',
    defaultBaseUrl: 'http://localhost:11434',
    placeholder: 'Ollama 模型名称'
  },
  local: {
    label: '本地部署',
    defaultBaseUrl: 'http://localhost:8000',
    placeholder: '本地 API Key'
  },
  custom: {
    label: '自定义',
    defaultBaseUrl: '',
    placeholder: 'API Key'
  }
}

// 创建默认节点值
const createDefaultNode = () => ({
  provider: 'openai',
  model: '',
  api_key: '',
  base_url: PROVIDER_CONFIG.openai.defaultBaseUrl,
  max_tokens: 4096,
  rpm: 60,
  tpm: 100000,
  weight: 1
})

export default function SingleNodeForm({
  value = {},
  onChange,
  errors = {},
  disabled = false
}) {
  // 合并默认值
  const nodeValue = { ...createDefaultNode(), ...value }

  // API Key 可见性状态
  const [showApiKey, setShowApiKey] = useState(false)

  // 处理供应商切换
  const handleProviderChange = (e) => {
    const provider = e.target.value
    const config = PROVIDER_CONFIG[provider]
    onChange({
      ...nodeValue,
      provider,
      base_url: config.defaultBaseUrl
    })
  }

  // 处理字段变化
  const handleFieldChange = (field, fieldValue) => {
    onChange({
      ...nodeValue,
      [field]: fieldValue
    })
  }

  // 处理数字输入
  const handleNumberChange = (field, e) => {
    const numValue = parseInt(e.target.value) || 0
    handleFieldChange(field, numValue)
  }

  // 切换 API Key 可见性
  const toggleApiKeyVisibility = () => {
    setShowApiKey(!showApiKey)
  }

  return (
    <div className="space-y-4">
      {/* 供应商选择 */}
      <div>
        <label htmlFor="provider" className="block text-sm font-medium text-gray-300 mb-1">
          供应商 *
        </label>
        <select
          id="provider"
          value={nodeValue.provider}
          onChange={handleProviderChange}
          disabled={disabled}
          className="w-full bg-dark-700 border border-dark-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {Object.entries(PROVIDER_CONFIG).map(([key, config]) => (
            <option key={key} value={key}>
              {config.label}
            </option>
          ))}
        </select>
      </div>

      {/* 模型名称 */}
      <div>
        <label htmlFor="model" className="block text-sm font-medium text-gray-300 mb-1">
          模型名称 *
        </label>
        <input
          id="model"
          type="text"
          value={nodeValue.model}
          onChange={(e) => handleFieldChange('model', e.target.value)}
          disabled={disabled}
          placeholder="例如：gpt-4-turbo"
          className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed ${
            errors.model ? 'border-red-500' : 'border-dark-600'
          }`}
        />
        {errors.model && (
          <p className="text-red-400 text-xs mt-1">{errors.model}</p>
        )}
      </div>

      {/* API Key */}
      <div>
        <label htmlFor="api-key" className="block text-sm font-medium text-gray-300 mb-1">
          API Key *
        </label>
        <div className="relative">
          <input
            id="api-key"
            data-testid="api-key-input"
            type={showApiKey ? 'text' : 'password'}
            value={nodeValue.api_key}
            onChange={(e) => handleFieldChange('api_key', e.target.value)}
            disabled={disabled}
            placeholder={PROVIDER_CONFIG[nodeValue.provider]?.placeholder || 'API Key'}
            className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed ${
              errors.api_key ? 'border-red-500' : 'border-dark-600'
            }`}
          />
          <button
            type="button"
            onClick={toggleApiKeyVisibility}
            disabled={disabled}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label={showApiKey ? '隐藏 API Key' : '显示 API Key'}
          >
            {showApiKey ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
          </button>
        </div>
        {errors.api_key && (
          <p className="text-red-400 text-xs mt-1">{errors.api_key}</p>
        )}
      </div>

      {/* Base URL */}
      <div>
        <label htmlFor="base-url" className="block text-sm font-medium text-gray-300 mb-1">
          Base URL *
        </label>
        <input
          id="base-url"
          type="url"
          value={nodeValue.base_url}
          onChange={(e) => handleFieldChange('base_url', e.target.value)}
          disabled={disabled}
          placeholder="https://api.example.com"
          className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed ${
            errors.base_url ? 'border-red-500' : 'border-dark-600'
          }`}
        />
        {errors.base_url && (
          <p className="text-red-400 text-xs mt-1">{errors.base_url}</p>
        )}
        <p className="text-gray-500 text-xs mt-1">
          当前供应商 ({PROVIDER_CONFIG[nodeValue.provider]?.label}) 的默认地址
        </p>
      </div>

      {/* 高级设置 - 折叠面板 */}
      <div className="border border-dark-600 rounded-lg p-4">
        <details className="group">
          <summary className="flex justify-between items-center cursor-pointer list-none">
            <span className="text-sm font-medium text-gray-300">高级设置</span>
            <svg
              className="w-4 h-4 text-gray-400 transition-transform group-open:rotate-180"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </summary>
          <div className="mt-4 grid grid-cols-2 gap-4">
            {/* Max Tokens */}
            <div>
              <label htmlFor="max-tokens" className="block text-sm font-medium text-gray-300 mb-1">
                Max Tokens
              </label>
              <input
                id="max-tokens"
                type="number"
                value={nodeValue.max_tokens}
                onChange={(e) => handleNumberChange('max_tokens', e)}
                disabled={disabled}
                className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed ${
                  errors.max_tokens ? 'border-red-500' : 'border-dark-600'
                }`}
              />
              {errors.max_tokens && (
                <p className="text-red-400 text-xs mt-1">{errors.max_tokens}</p>
              )}
            </div>

            {/* RPM */}
            <div>
              <label htmlFor="rpm" className="block text-sm font-medium text-gray-300 mb-1">
                RPM (请求/分钟)
              </label>
              <input
                id="rpm"
                type="number"
                value={nodeValue.rpm}
                onChange={(e) => handleNumberChange('rpm', e)}
                disabled={disabled}
                className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed ${
                  errors.rpm ? 'border-red-500' : 'border-dark-600'
                }`}
              />
              {errors.rpm && (
                <p className="text-red-400 text-xs mt-1">{errors.rpm}</p>
              )}
            </div>

            {/* TPM */}
            <div>
              <label htmlFor="tpm" className="block text-sm font-medium text-gray-300 mb-1">
                TPM (Token/分钟)
              </label>
              <input
                id="tpm"
                type="number"
                value={nodeValue.tpm}
                onChange={(e) => handleNumberChange('tpm', e)}
                disabled={disabled}
                className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed ${
                  errors.tpm ? 'border-red-500' : 'border-dark-600'
                }`}
              />
              {errors.tpm && (
                <p className="text-red-400 text-xs mt-1">{errors.tpm}</p>
              )}
            </div>

            {/* Weight */}
            <div>
              <label htmlFor="weight" className="block text-sm font-medium text-gray-300 mb-1">
                Weight (权重)
              </label>
              <input
                id="weight"
                type="number"
                value={nodeValue.weight}
                onChange={(e) => handleNumberChange('weight', e)}
                disabled={disabled}
                className={`w-full bg-dark-700 border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed ${
                  errors.weight ? 'border-red-500' : 'border-dark-600'
                }`}
              />
              {errors.weight && (
                <p className="text-red-400 text-xs mt-1">{errors.weight}</p>
              )}
            </div>
          </div>
        </details>
      </div>
    </div>
  )
}

// 导出供应商配置和默认值创建函数供外部使用
export { PROVIDER_CONFIG, createDefaultNode }
