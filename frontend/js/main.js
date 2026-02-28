/**
 * 主应用类，处理前端应用的核心逻辑
 */
class App {
    constructor() {
        this.currentUser = null;
        this.modelUsageChart = null;
        this.init();
    }

    /**
     * 初始化应用
     */
    init() {
        // 检查是否已登录
        const apiKey = localStorage.getItem('api_key');
        if (apiKey) {
            this.showMainPage();
            this.loadCurrentUser()
                .then(() => {
                    this.updateUserInfo();
                    this.loadDashboardData();
                })
                .catch(error => {
                    console.error('加载用户信息失败:', error);
                    this.showLoginPage();
                });
        } else {
            this.showLoginPage();
        }

        // 绑定事件监听器
        this.bindEvents();
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 登录表单提交
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }

        // 注册表单提交
        const registerForm = document.getElementById('register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleRegister();
            });
        }

        // 显示注册页面链接
        const showRegisterLink = document.getElementById('show-register-link');
        if (showRegisterLink) {
            showRegisterLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showRegisterPage();
            });
        }

        // 显示登录页面链接
        const showLoginLink = document.getElementById('show-login-link');
        if (showLoginLink) {
            showLoginLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showLoginPage();
            });
        }

        // 退出按钮点击
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.handleLogout();
            });
        }

        // 菜单项点击
        const menuItems = document.querySelectorAll('.menu-item');
        menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.getAttribute('data-page');
                this.switchPage(page);
            });
        });

        // 添加用户按钮点击
        const addUserBtn = document.getElementById('add-user-btn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => {
                this.showAddUserModal();
            });
        }

        // 关闭模态框
        const closeButtons = document.querySelectorAll('.close');
        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.hideModals();
            });
        });

        // 点击模态框背景关闭
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModals();
                }
            });
        });

        // 添加用户表单提交
        const addUserForm = document.getElementById('add-user-form');
        if (addUserForm) {
            addUserForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleAddUser();
            });
        }

        // 重新生成API密钥按钮点击
        const regenerateApiKeyBtn = document.getElementById('regenerate-api-key');
        if (regenerateApiKeyBtn) {
            regenerateApiKeyBtn.addEventListener('click', () => {
                this.handleRegenerateApiKey();
            });
        }

        // 复制/显示配置页面 API 密钥 按钮
        const copyProfileBtn = document.getElementById('copy-profile-key');
        if (copyProfileBtn) {
            copyProfileBtn.addEventListener('click', () => {
                const val = document.getElementById('profile-api-key').value || '';
                this.copyToClipboard(val).then(() => {
                    alert('API 密钥已复制到剪贴板');
                }).catch(err => {
                    alert('复制失败: ' + this.formatError(err));
                });
            });
        }

        const toggleProfileBtn = document.getElementById('toggle-profile-key');
        if (toggleProfileBtn) {
            toggleProfileBtn.addEventListener('click', () => {
                const input = document.getElementById('profile-api-key');
                if (!input) return;
                if (input.type === 'password') {
                    input.type = 'text';
                    toggleProfileBtn.textContent = '隐藏';
                } else {
                    input.type = 'password';
                    toggleProfileBtn.textContent = '显示';
                }
            });
        }

        // 新用户 API 密钥模态框内按钮
        const copyKeyBtn = document.getElementById('copy-key-btn');
        if (copyKeyBtn) {
            copyKeyBtn.addEventListener('click', () => {
                const val = document.getElementById('created-api-key').value || '';
                this.copyToClipboard(val).then(() => {
                    alert('API 密钥已复制到剪贴板');
                }).catch(err => {
                    alert('复制失败: ' + this.formatError(err));
                });
            });
        }

        const closeKeyBtn = document.getElementById('close-key-btn');
        if (closeKeyBtn) {
            closeKeyBtn.addEventListener('click', () => {
                this.hideModals();
            });
        }
    }

    /**
     * 格式化错误对象为可读字符串
     * @param {any} error
     * @returns {string}
     */
    formatError(error) {
        if (!error) return '未知错误';
        if (typeof error === 'string') return error;
        if (error.message) return error.message;
        if (error.detail) return error.detail;
        if (error.error) return error.error;
        try {
            return JSON.stringify(error);
        } catch (e) {
            return String(error);
        }
    }

    /**
     * 处理登录
     */
    async handleLogin() {
        const usernameInput = document.getElementById('login-username');
        const passwordInput = document.getElementById('login-password');
        const username = usernameInput ? usernameInput.value.trim() : '';
        const password = passwordInput ? passwordInput.value : '';
        const errorDiv = document.getElementById('login-error');

        if (!username || !password) {
            errorDiv.textContent = '请输入用户名和密码';
            return;
        }

        try {
            errorDiv.textContent = '';
            const loginButton = document.querySelector('#login-form button');
            loginButton.textContent = '登录中...';
            loginButton.disabled = true;

            // 使用账号密码登录
            const result = await apiService.login({ username: username, password: password });

            // 设置返回的API密钥并进入主页面
            if (result && result.api_key) {
                apiService.setApiKey(result.api_key);
            }

            this.showMainPage();
            await this.loadCurrentUser();
            this.updateUserInfo();
            this.loadDashboardData();
        } catch (error) {
            const msg = this.formatError(error);
            errorDiv.textContent = `登录失败: ${msg}`;
        } finally {
            const loginButton = document.querySelector('#login-form button');
            loginButton.textContent = '登录';
            loginButton.disabled = false;
        }
    }

    /**
     * 处理注册
     */
    async handleRegister() {
        const usernameInput = document.getElementById('register-username');
        const emailInput = document.getElementById('register-email');
        const passwordInput = document.getElementById('register-password');
        const confirmPasswordInput = document.getElementById('register-confirm-password');
        const errorDiv = document.getElementById('register-error');

        const username = usernameInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        // 验证输入
        if (!username || !email || !password || !confirmPassword) {
            errorDiv.textContent = '请填写所有必填字段';
            return;
        }

        if (password !== confirmPassword) {
            errorDiv.textContent = '密码确认不匹配';
            return;
        }

        if (password.length < 6) {
            errorDiv.textContent = '密码长度至少为6位';
            return;
        }

        try {
            errorDiv.textContent = '';
            // 显示加载状态
            const registerButton = document.querySelector('#register-form button');
            const originalText = registerButton.textContent;
            registerButton.textContent = '注册中...';
            registerButton.disabled = true;

            // 发送注册请求
            const result = await apiService.register({
                username: username,
                email: email,
                password: password
            });

            // 注册成功，自动登录
            apiService.setApiKey(result.api_key);
            this.showMainPage();
            await this.loadCurrentUser();
            this.updateUserInfo();
            this.loadDashboardData();
        } catch (error) {
            const msg = this.formatError(error);
            errorDiv.textContent = `注册失败: ${msg}`;
        } finally {
            // 恢复按钮状态
            const registerButton = document.querySelector('#register-form button');
            registerButton.textContent = '注册';
            registerButton.disabled = false;
        }
    }

    /**
     * 处理退出
     */
    handleLogout() {
        // 清除本地存储的API密钥
        localStorage.removeItem('api_key');

        // 重置当前用户
        this.currentUser = null;

        // 显示登录页面
        this.showLoginPage();
    }

    /**
     * 加载当前用户信息
     */
    async loadCurrentUser() {
        try {
            this.currentUser = await apiService.getCurrentUser();
        } catch (error) {
            console.error('加载用户信息失败:', error);
            throw error;
        }
    }

    /**
     * 更新用户信息显示
     */
    updateUserInfo() {
        if (this.currentUser) {
            document.getElementById('current-user-role').textContent =
                this.currentUser.role === 'admin' ? '管理员' : '用户';
            document.getElementById('current-user-email').textContent =
                this.currentUser.email || '未知邮箱';

            // 根据用户角色显示/隐藏特定功能
            this.updateUIByRole();
        }
    }

    /**
     * 根据用户角色更新UI
     */
    updateUIByRole() {
        if (this.currentUser && this.currentUser.role === 'admin') {
            // 显示管理员功能
            document.getElementById('admin-settings').style.display = 'block';

            // 显示用户管理菜单项
            const usersMenuItem = document.querySelector('.menu-item[data-page="users"]');
            if (usersMenuItem) {
                usersMenuItem.parentElement.style.display = 'block';
            }
        } else {
            // 隐藏管理员功能
            document.getElementById('admin-settings').style.display = 'none';

            // 隐藏用户管理菜单项
            const usersMenuItem = document.querySelector('.menu-item[data-page="users"]');
            if (usersMenuItem) {
                usersMenuItem.parentElement.style.display = 'none';
            }

            // 如果当前在用户管理页面，则切换到仪表盘
            const usersPage = document.getElementById('users-page');
            if (usersPage && !usersPage.classList.contains('hidden')) {
                this.switchPage('dashboard');
            }
        }
    }

    /**
     * 显示登录页面
     */
    showLoginPage() {
        document.getElementById('login-page').classList.remove('hidden');
        document.getElementById('register-page').classList.add('hidden');
        document.getElementById('main-page').classList.add('hidden');
    }

    /**
     * 显示注册页面
     */
    showRegisterPage() {
        document.getElementById('login-page').classList.add('hidden');
        document.getElementById('register-page').classList.remove('hidden');
        document.getElementById('main-page').classList.add('hidden');
    }

    /**
     * 显示主页面
     */
    showMainPage() {
        document.getElementById('login-page').classList.add('hidden');
        document.getElementById('main-page').classList.remove('hidden');
    }

    /**
     * 切换页面
     * @param {string} pageName - 页面名称
     */
    switchPage(pageName) {
        // 隐藏所有页面内容
        const pages = document.querySelectorAll('.page-content');
        pages.forEach(page => {
            page.classList.add('hidden');
        });

        // 显示指定页面
        const targetPage = document.getElementById(`${pageName}-page`);
        if (targetPage) {
            targetPage.classList.remove('hidden');
        }

        // 更新页面标题
        const pageTitleMap = {
            'dashboard': '仪表盘',
            'users': '用户管理',
            'usage': '使用统计',
            'settings': '设置'
        };
        document.getElementById('page-title').textContent = pageTitleMap[pageName] || '页面';

        // 更新菜单激活状态
        const menuItems = document.querySelectorAll('.menu-item');
        menuItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('data-page') === pageName) {
                item.classList.add('active');
            }
        });

        // 根据页面加载相应数据
        switch (pageName) {
            case 'dashboard':
                this.loadDashboardData();
                break;
            case 'users':
                this.loadUsersData();
                break;
            case 'usage':
                this.loadUsageData();
                break;
            case 'settings':
                this.loadSettingsData();
                break;
        }
    }

    /**
     * 加载仪表盘数据
     */
    async loadDashboardData() {
        try {
            // 显示加载状态
            this.showLoadingState('dashboard-page');

            // 获取统计数据概览
            const stats = await apiService.getStatsOverview();
            this.updateStatsOverview(stats);

            // 获取模型使用统计
            const modelStats = await apiService.getModelUsageStats();
            this.updateModelUsageChart(modelStats);

            // 获取最近活动
            const activities = await apiService.getRecentActivity();
            this.updateRecentActivity(activities);
        } catch (error) {
            console.error('加载仪表盘数据失败:', error);
            this.showErrorState('dashboard-page', '加载数据失败，请稍后重试');
        }
    }

    /**
     * 更新统计数据概览
     * @param {Object} stats - 统计数据
     */
    updateStatsOverview(stats) {
        document.getElementById('total-calls').textContent = stats.total_calls.toLocaleString();
        document.getElementById('total-tokens').textContent = stats.total_tokens.toLocaleString();
        document.getElementById('active-users').textContent = stats.active_users;
    }

    /**
     * 更新模型使用图表
     * @param {Array} modelStats - 模型统计数据
     */
    updateModelUsageChart(modelStats) {
        const ctx = document.getElementById('model-usage-chart').getContext('2d');

        // 如果已有图表实例，则销毁
        if (this.modelUsageChart) {
            this.modelUsageChart.destroy();
        }

        // 准备图表数据
        const labels = modelStats.map(stat => stat.model_name);
        const data = modelStats.map(stat => stat.call_count);

        // 创建新图表
        this.modelUsageChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '调用次数',
                    data: data,
                    backgroundColor: 'rgba(52, 152, 219, 0.7)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    /**
     * 更新最近活动列表
     * @param {Array} activities - 活动数据
     */
    updateRecentActivity(activities) {
        const activityList = document.getElementById('recent-activity-list');
        activityList.innerHTML = '';

        if (activities.length === 0) {
            activityList.innerHTML = '<p>暂无活动记录</p>';
            return;
        }

        activities.forEach(activity => {
            const activityItem = document.createElement('div');
            activityItem.className = 'activity-item';

            const date = new Date(activity.timestamp);
            const formattedDate = date.toLocaleString('zh-CN');

            activityItem.innerHTML = `
                <div class="activity-header">
                    <span class="activity-model">${activity.model_name}</span>
                    <span class="activity-time">${formattedDate}</span>
                </div>
                <div class="activity-details">
                    <span class="activity-user">${activity.user_email}</span>
                    <span class="activity-tokens">${activity.total_tokens} tokens</span>
                </div>
            `;

            activityList.appendChild(activityItem);
        });
    }

    /**
     /**
      * 加载用户数据
      */
     async loadUsersData() {
         // 检查是否为管理员
         if (!this.currentUser || this.currentUser.role !== 'admin') {
             return;
         }

         try {
             // 显示加载状态
             this.showLoadingState('users-page');

             // 获取用户列表
             const users = await apiService.getUsers();
             this.updateUsersTable(users);
         } catch (error) {
             console.error('加载用户数据失败:', error);
             this.showErrorState('users-page', '加载用户数据失败，请稍后重试');
         }
     }

     /**
      * 更新用户表格
      * @param {Array} users - 用户数据数组
      */
     updateUsersTable(users) {
         const tbody = document.querySelector('#users-table tbody');
         tbody.innerHTML = '';

         if (!users || users.length === 0) {
             tbody.innerHTML = `
                 <tr>
                     <td colspan="10" style="text-align: center; padding: 40px;">
                         <p>暂无用户数据</p>
                     </td>
                 </tr>
             `;
             return;
         }

        users.forEach(user => {
            const row = document.createElement('tr');

            // 格式化用户角色
            const roleText = user.role === 'admin' ? '管理员' : '用户';

            // 格式化用户状态
            const statusText = user.is_active ? '启用' : '禁用';
            const statusClass = user.is_active ? 'status-active' : 'status-inactive';

            // 管理员行高亮
            if (user.role === 'admin') {
                row.classList.add('admin-row');
            }

            // 头像（使用用户名首字母）
            const avatar = user.username ? String(user.username).trim().charAt(0).toUpperCase() : '?';

            // 使用可用字段显示并发/请求限制与使用统计
            const rpm = (user.rpm_limit || user.rpm || user.rate_limit || 0) || 0;
            const tpm = (user.tpm_limit || user.tpm || user.request_limit || 0) || 0;
            const calls = (user.usage_calls || user.total_calls || user.calls || 0) || 0;
            const tokens = (user.usage_tokens || user.total_tokens || user.tokens || 0) || 0;

            row.innerHTML = `
                <td><div class="user-avatar">${avatar}</div></td>
                <td>${user.username}</td>
                <td>${user.email || '未设置'}</td>
                <td>${roleText}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${rpm}</td>
                <td>${tpm}</td>
                <td>${(calls || 0).toLocaleString()}</td>
                <td>${(tokens || 0).toLocaleString()}</td>
                <td>
                    <button class="btn-small btn-secondary view-user-btn" data-user-id="${user.id}">查看</button>
                    <button class="btn-small btn-danger delete-user-btn" data-user-id="${user.id}" style="margin-left: 8px;">删除</button>
                    <button class="btn-small btn-primary copy-api-key-btn" data-user-id="${user.id}" style="margin-left: 8px;">复制 API Key</button>
                </td>
            `;

            tbody.appendChild(row);
        });
         
         // 绑定查看和删除按钮事件
         this.bindUserActionEvents();
     }

     /**
      * 绑定用户操作按钮事件
      */
     bindUserActionEvents() {
         // 查看用户按钮点击事件
         const viewButtons = document.querySelectorAll('.view-user-btn');
         viewButtons.forEach(button => {
             button.addEventListener('click', (e) => {
                 const userId = e.target.getAttribute('data-user-id');
                 this.showUserDetails(userId);
             });
         });
         
         // 删除用户按钮点击事件
         const deleteButtons = document.querySelectorAll('.delete-user-btn');
         deleteButtons.forEach(button => {
             button.addEventListener('click', (e) => {
                 const userId = e.target.getAttribute('data-user-id');
                 this.handleDeleteUser(userId);
             });
         });

        // 复制 API Key 按钮点击事件
        const copyKeyButtons = document.querySelectorAll('.copy-api-key-btn');
        copyKeyButtons.forEach(button => {
            button.addEventListener('click', async (e) => {
                const userId = e.target.getAttribute('data-user-id');
                if (!userId) return;

                try {
                    let keyResponse = null;

                    if (apiService && typeof apiService.getUserAPIKey === 'function') {
                        keyResponse = await apiService.getUserAPIKey(userId);
                    } else if (apiService && typeof apiService.getUserKey === 'function') {
                        keyResponse = await apiService.getUserKey(userId);
                    } else if (apiService && typeof apiService.getAPIKey === 'function') {
                        // some services may expose a generic getAPIKey that accepts an object
                        try {
                            keyResponse = await apiService.getAPIKey({ user_id: userId });
                        } catch (e) {
                            // ignore
                        }
                    }

                    const returned = keyResponse && (keyResponse.api_key || keyResponse.key) ? (keyResponse.api_key || keyResponse.key) : null;
                    if (returned) {
                        await this.copyToClipboard(returned);
                        alert('API 密钥已复制到剪贴板');
                    } else {
                        // 如果无法从 API 获取密钥，提示用户使用后台或重新生成
                        alert('无法直接获取 API 密钥。请在后台生成或使用“重新生成API密钥”操作。');
                    }
                } catch (err) {
                    console.error('复制 API 密钥失败:', err);
                    alert('复制 API 密钥失败: ' + this.formatError(err));
                }
            });
        });
     }

     /**
      * 显示用户详情
      * @param {string} userId - 用户ID
      */
     showUserDetails(userId) {
         // 这里可以实现显示用户详情的逻辑
         // 暂时用alert显示用户ID
         alert(`查看用户详情功能待实现，用户ID: ${userId}`);
     }

     /**
      * 处理删除用户
      * @param {string} userId - 用户ID
      */
     async handleDeleteUser(userId) {
         if (!confirm('确定要删除这个用户吗？此操作不可恢复。')) {
             return;
         }
         
         try {
             // 这里应该调用API删除用户
             // 暂时只是显示提示信息
             alert(`删除用户功能待实现，用户ID: ${userId}`);
             
             // 删除成功后重新加载用户列表
             // await this.loadUsersData();
        } catch (error) {
            console.error('删除用户失败:', error);
            alert(`删除用户失败: ${this.formatError(error)}`);
         }
     }

     /**
      * 显示用户数据占位符
      */
     showUsersDataPlaceholder() {
        const tbody = document.querySelector('#users-table tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 40px;">
                    <p>用户管理功能</p>
                    <p>可以通过"添加用户"按钮创建新用户</p>
                    <p>注意：API文档中没有提供获取用户列表的端点</p>
                </td>
            </tr>
        `;
     }

     /**
      * 显示添加用户模态框
      */
     showAddUserModal() {
         document.getElementById('add-user-modal').classList.remove('hidden');
     }

     /**
      * 隐藏所有模态框
      */
     hideModals() {
         const modals = document.querySelectorAll('.modal');
         modals.forEach(modal => {
             modal.classList.add('hidden');
         });
     }

     /**
      * 处理添加用户
      */
     async handleAddUser() {
         const form = document.getElementById('add-user-form');
         const username = document.getElementById('new-username').value.trim();
         const email = document.getElementById('new-email').value.trim();
         const role = document.getElementById('new-role').value;
         const rpmLimit = parseInt(document.getElementById('new-rpm').value);
         const tpmLimit = parseInt(document.getElementById('new-tpm').value);

         if (!username || !email) {
             alert('请填写用户名和邮箱');
             return;
         }

         try {
             const userData = {
                 username: username,
                 email: email,
                 role: role,
                 rpm_limit: rpmLimit,
                 tpm_limit: tpmLimit
             };

             const response = await apiService.createUser(userData);

            // 后端会在创建时返回明文 API Key（仅管理员可见）
            const createdApiKey = response && response.api_key ? response.api_key : null;

            if (createdApiKey) {
                // 展示模态框，便于用户复制/查看
                this.showKeyModal(createdApiKey, response.username || username);
            } else {
                alert(`用户创建成功！\n用户名: ${response.username || username}\n注意：服务器未返回API密钥，请在后台或通过“重新生成API密钥”来获取。`);
            }

             // 关闭模态框并重置表单
             this.hideModals();
             form.reset();

        } catch (error) {
            console.error('创建用户失败:', error);
            alert(`创建用户失败: ${this.formatError(error)}`);
         }
     }
    /**
     * 加载使用统计数据
     */
    async loadUsageData() {
        try {
            // 显示加载状态
            this.showLoadingState('usage-page');

            // 获取当前用户使用统计
            const usageStats = await apiService.getSelfUsageStats();
            this.updateUsageTable([usageStats]);

            // 如果是管理员，加载更多统计选项
            if (this.currentUser && this.currentUser.role === 'admin') {
                // 加载可用模型列表
                await this.loadAvailableModels();
                // 加载使用趋势统计
                await this.loadUsageTrend();
            }
        } catch (error) {
            console.error('加载使用统计数据失败:', error);
            this.showErrorState('usage-page', '加载使用统计数据失败，请稍后重试');
        }
    }

    /**
     * 更新使用统计表格
     * @param {Array} usageData - 使用数据
     */
    updateUsageTable(usageData) {
        const tbody = document.querySelector('#usage-table tbody');
        tbody.innerHTML = '';

        usageData.forEach(data => {
            const row = document.createElement('tr');

            // 格式化最后使用时间
            const lastUsed = data.last_activity
                ? new Date(data.last_activity).toLocaleString('zh-CN')
                : '无记录';

            row.innerHTML = `
                <td>${data.user_email || data.user_id || '当前用户'}</td>
                <td>${data.active_models ? data.active_models.join(', ') : '总计'}</td>
                <td>${(data.total_calls || 0).toLocaleString()}</td>
                <td>${(data.total_tokens || 0).toLocaleString()}</td>
                <td>${lastUsed}</td>
            `;

            tbody.appendChild(row);
        });
    }

    /**
     * 加载可用模型列表
     */
    async loadAvailableModels() {
        try {
            const models = await apiService.getAvailableModels();
            const modelFilter = document.getElementById('model-filter');

            // 清空现有选项（保留"所有模型"选项）
            modelFilter.innerHTML = '<option value="">所有模型</option>';

            // 添加模型选项
            models.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelFilter.appendChild(option);
            });
        } catch (error) {
            console.error('加载模型列表失败:', error);
        }
    }

    /**
     * 加载使用趋势统计
     */
    async loadUsageTrend() {
        try {
            // 创建趋势图表容器
            const usagePage = document.getElementById('usage-page');

            // 检查是否已存在趋势图表区域
            let trendSection = document.getElementById('usage-trend-section');
            if (!trendSection) {
                trendSection = document.createElement('div');
                trendSection.id = 'usage-trend-section';
                trendSection.className = 'chart-container';
                trendSection.innerHTML = `
                    <h3>使用趋势</h3>
                    <div class="trend-filters">
                        <select id="trend-period">
                            <option value="7d">最近7天</option>
                            <option value="30d">最近30天</option>
                            <option value="90d">最近90天</option>
                        </select>
                        <select id="trend-granularity">
                            <option value="day">按天</option>
                            <option value="hour">按小时</option>
                            <option value="week">按周</option>
                        </select>
                        <button id="load-trend-btn">加载趋势</button>
                    </div>
                    <canvas id="usage-trend-chart"></canvas>
                `;

                // 将趋势图表插入到表格之前
                const tableContainer = usagePage.querySelector('.table-container');
                usagePage.insertBefore(trendSection, tableContainer);

                // 绑定趋势加载事件
                document.getElementById('load-trend-btn').addEventListener('click', () => {
                    this.loadTrendData();
                });
            }

            // 初始加载趋势数据
            await this.loadTrendData();
        } catch (error) {
            console.error('加载使用趋势失败:', error);
        }
    }

    /**
     * 加载趋势数据
     */
    async loadTrendData() {
        try {
            const period = document.getElementById('trend-period').value;
            const granularity = document.getElementById('trend-granularity').value;

            const trendData = await apiService.getUsageTrend(period, granularity);
            this.updateUsageTrendChart(trendData);
        } catch (error) {
            console.error('加载趋势数据失败:', error);
        }
    }

    /**
     * 更新使用趋势图表
     * @param {Object} trendData - 趋势数据
     */
    updateUsageTrendChart(trendData) {
        const ctx = document.getElementById('usage-trend-chart').getContext('2d');

        // 如果已有图表实例，则销毁
        if (this.usageTrendChart) {
            this.usageTrendChart.destroy();
        }

        const labels = trendData.data.map(item => item.date);
        const callsData = trendData.data.map(item => item.calls);
        const tokensData = trendData.data.map(item => item.tokens);

        this.usageTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '调用次数',
                        data: callsData,
                        borderColor: 'rgba(52, 152, 219, 1)',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderWidth: 2,
                        yAxisID: 'y'
                    },
                    {
                        label: '令牌数',
                        data: tokensData,
                        borderColor: 'rgba(46, 204, 113, 1)',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        borderWidth: 2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: '调用次数'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '令牌数'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    }

    /**
     * 加载设置数据
     */
    async loadSettingsData() {
        try {
            // 显示加载状态
            this.showLoadingState('settings-page');

            // 更新个人设置信息
            if (this.currentUser) {
                document.getElementById('profile-email').value = this.currentUser.email || '';
                const profileInput = document.getElementById('profile-api-key');
                if (profileInput) {
                    profileInput.type = 'password';
                    profileInput.value = apiService.getApiKey() || '';
                }
                const toggleBtn = document.getElementById('toggle-profile-key');
                if (toggleBtn) toggleBtn.textContent = '显示';
            }
        } catch (error) {
            console.error('加载设置数据失败:', error);
            this.showErrorState('settings-page', '加载设置数据失败，请稍后重试');
        }
    }

    /**
     * 显示添加用户模态框
     */
    showAddUserModal() {
        document.getElementById('add-user-modal').classList.remove('hidden');
    }

    /**
     * 隐藏所有模态框
     */
    hideModals() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.add('hidden');
        });
    }


    

    /**
     * 处理重新生成API密钥
     */
    async handleRegenerateApiKey() {
        if (!this.currentUser) {
            alert('请先登录');
            return;
        }

        if (!confirm('确定要重新生成API密钥吗？旧的API密钥将失效。')) {
            return;
        }

        try {
            // 创建新的API密钥
            const keyData = {
                user_id: this.currentUser.id,
                description: '重新生成的API密钥'
            };

            const newKey = await apiService.createAPIKey(keyData);

            const returned = newKey && newKey.api_key ? newKey.api_key : null;
            if (returned) {
                // 更新显示的API密钥（并默认隐藏）
                const profileInput = document.getElementById('profile-api-key');
                if (profileInput) {
                    profileInput.type = 'password';
                    profileInput.value = returned;
                }

                // 更新本地存储的API密钥
                apiService.setApiKey(returned);

                // 用模态框提示便于复制
                this.showKeyModal(returned, this.currentUser && this.currentUser.username ? this.currentUser.username : '用户');
            } else {
                alert('API 密钥已重新生成，但服务器未返回密钥。请在后台或通过下载/邮件获取新密钥。');
            }
        } catch (error) {
            console.error('重新生成API密钥失败:', error);
            alert(`重新生成API密钥失败: ${this.formatError(error)}`);
        }
    }

    /**
     * 显示加载状态
     * @param {string} pageId - 页面ID
     */
    showLoadingState(pageId) {
        const page = document.getElementById(pageId);
        if (page) {
            // 这里可以添加具体的加载状态显示逻辑
            // 比如显示加载动画等
        }
    }

    /**
     * 显示用于查看/复制 API 密钥的模态框
     * @param {string} apiKey
     * @param {string} username
     */
    showKeyModal(apiKey, username) {
        const modal = document.getElementById('show-key-modal');
        if (!modal) return;
        const keyInput = document.getElementById('created-api-key');
        const info = document.getElementById('key-modal-info');
        if (keyInput) keyInput.value = apiKey || '';
        if (info) info.textContent = `${username || '用户'} 的 API 密钥（请妥善保存，仅会显示一次）`;
        modal.classList.remove('hidden');
    }

    /**
     * 复制文本到剪贴板（带回退）
     * @param {string} text
     * @returns {Promise}
     */
    async copyToClipboard(text) {
        if (!text) return Promise.reject(new Error('没有密钥可复制'));
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }
        return new Promise((resolve, reject) => {
            try {
                const ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                const ok = document.execCommand('copy');
                document.body.removeChild(ta);
                if (ok) resolve(); else reject(new Error('复制命令失败'));
            } catch (e) {
                reject(e);
            }
        });
    }

    /**
     * 显示错误状态
     * @param {string} pageId - 页面ID
     * @param {string} message - 错误消息
     */
    showErrorState(pageId, message) {
        const page = document.getElementById(pageId);
        if (page) {
            // 这里可以添加具体的错误状态显示逻辑
            alert(message);
        }
    }
}

// 当DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});

