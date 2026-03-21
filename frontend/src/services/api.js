const getBaseURL = () => {
  // Default to backend on localhost:8000 unless overridden
  return window.__API_BASE__ || ''
}

class API {
  constructor() {
    this.baseURL = getBaseURL()
    this.apiKey = localStorage.getItem('api_key') || ''
  }

  setApiKey(key) {
    this.apiKey = key
    if (key) localStorage.setItem('api_key', key)
    else localStorage.removeItem('api_key')
  }

  async request(path, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' }
    if (this.apiKey) headers['Authorization'] = `Bearer ${this.apiKey}`

    const opts = { method, headers }
    if (body && method !== 'GET') opts.body = JSON.stringify(body)

    const url = (this.baseURL || '') + path
    const res = await fetch(url, opts)
    if (!res.ok) {
      const json = await res.json().catch(() => ({}))
      let errMsg = json.detail || json.error || json.message || `HTTP ${res.status}`
      if (typeof errMsg === 'object') {
        try {
          errMsg = JSON.stringify(errMsg)
        } catch (e) {
          errMsg = String(errMsg)
        }
      }
      throw new Error(errMsg)
    }
    if (res.status === 204) return null
    return await res.json()
  }

  // auth
  async login(data) { return this.request('/auth/login', 'POST', data) }
  async register(data) { return this.request('/auth/register', 'POST', data) }
  async getCurrentUser() { return this.request('/auth/me') }

  // admin / stats
  async getStatsOverview() { return this.request('/admin/stats/overview') }
  async getModelUsageStats() { return this.request('/admin/stats/model-usage') }
  async getRecentActivity(limit = 20) { return this.request(`/admin/stats/recent-activity?limit=${limit}`) }
  async getConcurrentStats() { return this.request('/admin/stats/concurrent') }
  async getUsageTrend(period = '7d', granularity = 'day', model = null, userId = null) {
    const params = new URLSearchParams({ period, granularity })
    if (model) params.set('model', model)
    if (userId) params.set('user_id', userId)
    return this.request(`/admin/stats/usage-trend?${params.toString()}`)
  }

  async getUserTrend(period = '7d', granularity = 'day', model = null) {
    const params = new URLSearchParams({ period, granularity })
    if (model) params.set('model', model)
    return this.request(`/admin/stats/user-trend?${params.toString()}`)
  }

  async getModelTrend(period = '7d', granularity = 'day', userId = null) {
    const params = new URLSearchParams({ period, granularity })
    if (userId) params.set('user_id', userId)
    return this.request(`/admin/stats/model-trend?${params.toString()}`)
  }

  // 获取用户预算使用情况
  async getUserBudgetUsage() {
    return this.request('/admin/stats/usage')
  }

  // users & keys
  async getUsers(page = 1, per_page = 20) { return this.request(`/users?page=${page}&per_page=${per_page}`) }
  async createUser(data) { return this.request('/admin/users', 'POST', data) }
  async updateUser(userId, data) { return this.request(`/users/${userId}`, 'PATCH', data) }
  async resetUserPassword(userId, data) { return this.request(`/users/${userId}/reset-password`, 'POST', data) }
  async enableUser(userId) { return this.request(`/users/${userId}/enable`, 'POST') }
  async disableUser(userId) { return this.request(`/users/${userId}/disable`, 'POST') }
  async getAPIKeys() { return this.request('/admin/api-keys') }
  async createAPIKey(data) { return this.request('/admin/api-keys', 'POST', data) }
  async getOwnAPIKeys() { return this.request('/auth/api-keys') }
  async getUserAPIKey(userId) { return this.request(`/admin/users/${userId}/key`) }
  // user-self key management
  async createOwnAPIKey(data = {}) { return this.request('/auth/api-keys', 'POST', data) }
  async disableOwnAPIKey(keyId) { return this.request(`/auth/api-keys/${keyId}/disable`, 'PATCH') }
  async enableOwnAPIKey(keyId) { return this.request(`/auth/api-keys/${keyId}/enable`, 'PATCH') }
  async getModels() { return this.request('/models') }
  async getAllModels() { return this.request('/models/all') }

  // 模型配置管理
  async getModelConfigs() { return this.request('/admin/models') }
  async getModelConfig(modelName) { return this.request(`/admin/models/${modelName}`) }
  async createModelConfig(data) { return this.request('/admin/models', 'POST', data) }
  async updateModelConfig(modelName, data) { return this.request(`/admin/models/${modelName}`, 'PUT', data) }
  async deleteModelConfig(modelName) { return this.request(`/admin/models/${modelName}`, 'DELETE') }
  async activateModel(modelName) { return this.request(`/admin/models/${modelName}/activate`, 'PATCH') }
  async deactivateModel(modelName) { return this.request(`/admin/models/${modelName}/deactivate`, 'PATCH') }

  // 配置同步
  async getConfigSyncStatus() { return this.request('/admin/config/sync-status') }
  async triggerConfigSync() { return this.request('/admin/config/sync', 'POST') }
}

const api = new API()
export default api




