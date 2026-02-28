/**
 * API服务类，封装所有与后端API的通信
 */
class APIService {
    constructor() {
        // 从localStorage获取API基础URL，如果没有则使用相对路径
        // 默认指向8000端口的API服务
        this.baseURL = '';
        this.apiKey = localStorage.getItem('api_key') || '';
    }

    /**
     * 设置API密钥
     * @param {string} apiKey - API密钥
     */
    setApiKey(apiKey) {
        this.apiKey = apiKey;
        localStorage.setItem('api_key', apiKey);
    }

    /**
     * 获取API密钥
     * @returns {string} API密钥
     */
    getApiKey() {
        return this.apiKey;
    }

    /**
     * 发送API请求
     * @param {string} url - 请求URL
     * @param {string} method - HTTP方法
     * @param {Object} data - 请求数据
     * @returns {Promise} Promise对象
     */
    async request(url, method = 'GET', data = null) {
        const headers = {
            'Content-Type': 'application/json'
        };

        // 如果有API密钥，则添加到请求头
        headers['Authorization'] = `Bearer ${this.apiKey}`;

        const config = {
            method: method,
            headers: headers
        };

        // 如果有数据且不是GET请求，则添加到请求体
        if (data && method !== 'GET') {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(this.baseURL + url, config);

            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                let errMsg = errorData.error || errorData.detail || `HTTP Error: ${response.status}`;
                if (typeof errMsg === 'object') {
                    try {
                        errMsg = JSON.stringify(errMsg);
                    } catch (e) {
                        errMsg = String(errMsg);
                    }
                }
                throw new Error(errMsg);
            }

            // 如果响应状态是204 No Content，则返回null
            if (response.status === 204) {
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    }

    /**
     * 用户认证
     * @param {string} apiKey - API密钥
     * @returns {Promise} Promise对象
     */
    async authenticate(apiKey) {
        // 临时设置API密钥用于认证请求
        const originalApiKey = this.apiKey;
        this.apiKey = apiKey;

        try {
            // 使用用户信息端点进行认证测试
            const response = await this.request('/auth/me');
            // 认证成功后保存API密钥
            this.setApiKey(apiKey);
            return response;
        } catch (error) {
            // 恢复原始API密钥
            this.apiKey = originalApiKey;
            throw error;
        }
    }

    /**
     * 用户注册
     * @param {Object} userData - 用户注册数据
     * @returns {Promise} Promise对象
     */
    async register(userData) {
        return await this.request('/auth/register', 'POST', userData);
    }

    /**
     * 用户登录
     * @param {Object} loginData - 登录数据
     * @returns {Promise} Promise对象
     */
    async login(loginData) {
        return await this.request('/auth/login', 'POST', loginData);
    }

    /**
     * 获取当前用户信息
     * 通过用户信息接口获取完整用户信息
     * @returns {Promise} Promise对象
     */
    async getCurrentUser() {
        try {
            const response = await this.request('/auth/me');
            return {
                id: response.id,
                username: response.username,
                email: response.email,
                role: response.role,
                budget_limit: response.budget_limit,
                rpm_limit: response.rpm_limit,
                tpm_limit: response.tpm_limit,
                is_active: response.is_active,
                created_at: response.created_at
            };
        } catch (error) {
            console.error('获取用户信息失败:', error);
            throw error;
        }
    }

    /**
     * 获取统计概览
     * @returns {Promise} Promise对象
     */
    async getStatsOverview() {
        return await this.request('/admin/stats/overview');
    }

    /**
     * 获取模型使用统计
     * @returns {Promise} Promise对象
     */
    async getModelUsageStats() {
        return await this.request('/admin/stats/model-usage');
    }

    /**
     * 获取最近活动
     * @param {number} limit - 限制数量
     * @returns {Promise} Promise对象
     */
    async getRecentActivity(limit = 20) {
        return await this.request(`/admin/stats/recent-activity?limit=${limit}`);
    }

    /**
     * 获取用户列表
     * @returns {Promise} Promise对象
     */
    async getUsers() {
        return await this.request('/users');
    }

    /**
     * 创建用户
     * @param {Object} userData - 用户数据
     * @returns {Promise} Promise对象
     */
    async createUser(userData) {
        return await this.request('/admin/users', 'POST', userData);
    }

    /**
     * 创建API密钥
     * @param {Object} keyData - 密钥数据
     * @returns {Promise} Promise对象
     */
    async createAPIKey(keyData) {
        return await this.request('/admin/api-keys', 'POST', keyData);
    }

    /**
     * 获取用户详细统计
     * @param {string} userId - 用户ID
     * @returns {Promise} Promise对象
     */
    async getUserStats(userId) {
        return await this.request(`/admin/stats/user/${userId}`);
    }

    /**
     * 获取指定用户的最新 API 密钥（管理员权限）
     * @param {string} userId - 用户ID
     */
    async getUserAPIKey(userId) {
        return await this.request(`/admin/users/${userId}/key`);
    }

    /**
     * 获取当前用户使用统计
     * @returns {Promise} Promise对象
     */
    async getSelfUsageStats() {
        return await this.request('/admin/stats/usage');
    }

    /**
     * 获取使用趋势统计
     * @param {string} period - 时间段 ('7d', '30d', '90d')
     * @param {string} granularity - 粒度 ('hour', 'day', 'week')
     * @returns {Promise} Promise对象
     */
    async getUsageTrend(period = '7d', granularity = 'day') {
        return await this.request(`/admin/stats/usage-trend?period=${period}&granularity=${granularity}`);
    }

    /**
     * 获取可用模型列表
     * @returns {Promise} Promise对象
     */
    async getAvailableModels() {
        return await this.request('/models');
    }

    /**
     * 健康检查
     * @returns {Promise} Promise对象
     */
    async healthCheck() {
        return await this.request('/health');
    }
}

// 创建API服务实例
const apiService = new APIService();

// 导出API服务实例
window.apiService = apiService;