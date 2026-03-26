-- ============================================================
-- LiteLLM Proxy 数据库初始化脚本
-- 版本：v1.1.0
-- 数据库：PostgreSQL 15+
-- 创建日期：2026-03-26
-- ============================================================

-- 如果数据库不存在，请先创建：
-- CREATE DATABASE litellm_gateway;

-- ============================================================
-- 1. 扩展（Extensions）
-- ============================================================

-- 启用 UUID 扩展（如果未启用）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 2. 数据表（Tables）
-- ============================================================

-- -------------------------------------------------------------
-- 2.1 用户表（users）
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR(36) PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NULL,
    role            VARCHAR(50) DEFAULT 'user',
    budget_limit    DECIMAL(10,2) DEFAULT 1000,
    rpm_limit       INTEGER DEFAULT 60,
    tpm_limit       INTEGER DEFAULT 60000,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE
);

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- 注释
COMMENT ON TABLE users IS '用户表，存储系统用户信息';
COMMENT ON COLUMN users.id IS '用户 ID（UUID）';
COMMENT ON COLUMN users.username IS '用户名（唯一）';
COMMENT ON COLUMN users.email IS '邮箱（唯一）';
COMMENT ON COLUMN users.password_hash IS '密码哈希值（BCrypt）';
COMMENT ON COLUMN users.role IS '用户角色（admin/user）';
COMMENT ON COLUMN users.budget_limit IS '预算限制（美元）';
COMMENT ON COLUMN users.rpm_limit IS '每分钟请求数限制';
COMMENT ON COLUMN users.tpm_limit IS '每分钟令牌数限制';
COMMENT ON COLUMN users.is_active IS '是否启用';

-- -------------------------------------------------------------
-- 2.2 API 密钥表（api_keys）
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_keys (
    id              VARCHAR(36) PRIMARY KEY,
    api_key         VARCHAR(255) UNIQUE NOT NULL,
    user_id         VARCHAR(36) NOT NULL,
    description     TEXT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_api_keys_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- API 密钥表索引
CREATE INDEX IF NOT EXISTS idx_api_keys_api_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- 注释
COMMENT ON TABLE api_keys IS 'API 密钥表，存储用户 API 密钥';
COMMENT ON COLUMN api_keys.id IS '密钥 ID（UUID）';
COMMENT ON COLUMN api_keys.api_key IS 'API 密钥值（唯一）';
COMMENT ON COLUMN api_keys.user_id IS '关联用户 ID';
COMMENT ON COLUMN api_keys.description IS '密钥描述';
COMMENT ON COLUMN api_keys.is_active IS '是否启用';

-- -------------------------------------------------------------
-- 2.3 使用统计表（usage_stats）
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usage_stats (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    model_name      VARCHAR(100) NOT NULL,
    request_count   INTEGER DEFAULT 0,
    total_tokens    INTEGER DEFAULT 0,
    total_cost      DECIMAL(10,6) DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_model UNIQUE (user_id, model_name)
);

-- 使用统计表索引
CREATE INDEX IF NOT EXISTS idx_usage_stats_user_id ON usage_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_model_name ON usage_stats(model_name);
CREATE INDEX IF NOT EXISTS idx_usage_stats_last_used ON usage_stats(last_used);

-- 注释
COMMENT ON TABLE usage_stats IS '使用统计表，按用户和模型聚合使用数据';
COMMENT ON COLUMN usage_stats.id IS '统计 ID（UUID）';
COMMENT ON COLUMN usage_stats.user_id IS '用户 ID';
COMMENT ON COLUMN usage_stats.model_name IS '模型名称';
COMMENT ON COLUMN usage_stats.request_count IS '请求次数';
COMMENT ON COLUMN usage_stats.total_tokens IS '总令牌数';
COMMENT ON COLUMN usage_stats.total_cost IS '总费用（美元）';
COMMENT ON COLUMN usage_stats.last_used IS '最后使用时间';

-- -------------------------------------------------------------
-- 2.4 完成日志表（completion_logs）
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS completion_logs (
    id                  VARCHAR(36) PRIMARY KEY,
    user_id             VARCHAR(36) NOT NULL,
    model_name          VARCHAR(100) NOT NULL,
    request_data        JSONB NOT NULL,
    response_data       JSONB NULL,
    request_tokens      INTEGER DEFAULT 0,
    response_tokens     INTEGER DEFAULT 0,
    total_tokens        INTEGER DEFAULT 0,
    cost                DECIMAL(10,6) DEFAULT 0,
    status              VARCHAR(50) DEFAULT 'success',
    error_message       TEXT NULL,
    duration            INTEGER DEFAULT 0,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 完成日志表索引
CREATE INDEX IF NOT EXISTS idx_completion_logs_user_id ON completion_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_completion_logs_model_name ON completion_logs(model_name);
CREATE INDEX IF NOT EXISTS idx_completion_logs_status ON completion_logs(status);
CREATE INDEX IF NOT EXISTS idx_completion_logs_created_at ON completion_logs(created_at);

-- 注释
COMMENT ON TABLE completion_logs IS '完成日志表，存储 API 请求日志';
COMMENT ON COLUMN completion_logs.id IS '日志 ID（UUID）';
COMMENT ON COLUMN completion_logs.user_id IS '用户 ID';
COMMENT ON COLUMN completion_logs.model_name IS '模型名称';
COMMENT ON COLUMN completion_logs.request_data IS '请求数据（JSON）';
COMMENT ON COLUMN completion_logs.response_data IS '响应数据（JSON）';
COMMENT ON COLUMN completion_logs.request_tokens IS '请求令牌数';
COMMENT ON COLUMN completion_logs.response_tokens IS '响应令牌数';
COMMENT ON COLUMN completion_logs.total_tokens IS '总令牌数';
COMMENT ON COLUMN completion_logs.cost IS '费用（美元）';
COMMENT ON COLUMN completion_logs.status IS '状态（success/error）';
COMMENT ON COLUMN completion_logs.error_message IS '错误消息';
COMMENT ON COLUMN completion_logs.duration IS '请求耗时（毫秒）';

-- -------------------------------------------------------------
-- 2.5 完成详情表（completion_details）
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS completion_details (
    id                  VARCHAR(36) PRIMARY KEY,
    completion_log_id   VARCHAR(36) NOT NULL,
    messages            JSONB NULL,
    tools               JSONB NULL,
    full_response       JSONB NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_completion_details_log FOREIGN KEY (completion_log_id)
        REFERENCES completion_logs(id) ON DELETE CASCADE
);

-- 完成详情表索引
CREATE INDEX IF NOT EXISTS idx_completion_details_log_id ON completion_details(completion_log_id);

-- 注释
COMMENT ON TABLE completion_details IS '完成详情表，存储完整的对话消息和工具信息';
COMMENT ON COLUMN completion_details.id IS '详情 ID（UUID）';
COMMENT ON COLUMN completion_details.completion_log_id IS '关联的日志 ID';
COMMENT ON COLUMN completion_details.messages IS '完整对话消息（JSON）';
COMMENT ON COLUMN completion_details.tools IS '工具信息（JSON）';
COMMENT ON COLUMN completion_details.full_response IS '完整模型响应（JSON）';

-- -------------------------------------------------------------
-- 2.6 模型配置表（model_configs）
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_configs (
    id                  VARCHAR(36) PRIMARY KEY,
    model_name          VARCHAR(100) UNIQUE NOT NULL,
    litellm_params      JSONB NOT NULL,
    support_types       JSONB DEFAULT '["text"]',
    default_rpm         INTEGER DEFAULT 10,
    default_tpm         INTEGER DEFAULT 100000,
    default_max_tokens  INTEGER DEFAULT 32768,
    description         VARCHAR(500) DEFAULT '大语言模型',
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 模型配置表索引
CREATE INDEX IF NOT EXISTS idx_model_configs_model_name ON model_configs(model_name);
CREATE INDEX IF NOT EXISTS idx_model_configs_is_active ON model_configs(is_active);

-- 注释
COMMENT ON TABLE model_configs IS '模型配置表，存储 LLM 模型配置';
COMMENT ON COLUMN model_configs.id IS '配置 ID（UUID）';
COMMENT ON COLUMN model_configs.model_name IS '模型名称（唯一）';
COMMENT ON COLUMN model_configs.litellm_params IS 'LiteLLM 参数（JSON）';
COMMENT ON COLUMN model_configs.support_types IS '支持的类型（text/image/embedding）';
COMMENT ON COLUMN model_configs.default_rpm IS '默认 RPM 限制';
COMMENT ON COLUMN model_configs.default_tpm IS '默认 TPM 限制';
COMMENT ON COLUMN model_configs.default_max_tokens IS '默认最大令牌数';
COMMENT ON COLUMN model_configs.description IS '模型描述';
COMMENT ON COLUMN model_configs.is_active IS '是否启用';

-- -------------------------------------------------------------
-- 2.7 配置同步检查点表（config_checkpoints）
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config_checkpoints (
    id              VARCHAR(36) PRIMARY KEY,
    config_type     VARCHAR(50) NOT NULL UNIQUE DEFAULT 'litellm_config',
    yaml_hash       VARCHAR(64) NOT NULL,
    db_hash         VARCHAR(64) NULL,
    last_sync_source VARCHAR(20) NULL,
    last_sync_time  TIMESTAMP WITH TIME ZONE NULL,
    yaml_updated_at TIMESTAMP WITH TIME ZONE NULL,
    db_updated_at   TIMESTAMP WITH TIME ZONE NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 注释
COMMENT ON TABLE config_checkpoints IS '配置同步检查点表，记录 YAML 与数据库配置的同步状态';
COMMENT ON COLUMN config_checkpoints.id IS '检查点 ID（UUID）';
COMMENT ON COLUMN config_checkpoints.config_type IS '配置类型';
COMMENT ON COLUMN config_checkpoints.yaml_hash IS 'YAML 文件内容 SHA256 哈希';
COMMENT ON COLUMN config_checkpoints.db_hash IS '数据库配置 SHA256 哈希';
COMMENT ON COLUMN config_checkpoints.last_sync_source IS '最后同步来源（yaml/database/none）';
COMMENT ON COLUMN config_checkpoints.last_sync_time IS '最后同步时间';
COMMENT ON COLUMN config_checkpoints.yaml_updated_at IS 'YAML 文件修改时间戳';
COMMENT ON COLUMN config_checkpoints.db_updated_at IS '数据库最后更新时间戳';

-- ============================================================
-- 3. 初始数据（Initial Data）
-- ============================================================

-- -------------------------------------------------------------
-- 3.1 默认管理员用户
-- -------------------------------------------------------------
INSERT INTO users (id, username, email, password_hash, role, budget_limit, rpm_limit, tpm_limit, is_active)
VALUES (
    'admin001',
    'admin',
    'admin@litellm-gateway.com',
    NULL,
    'admin',
    10000.00,
    1000,
    1000000,
    TRUE
)
ON CONFLICT (id) DO NOTHING;

-- -------------------------------------------------------------
-- 3.2 默认 API 密钥（实际密钥值通过 config_manager.py 生成）
-- 注意：这里插入占位符，实际密钥应在 .env 中配置
-- -------------------------------------------------------------
INSERT INTO api_keys (id, api_key, user_id, description, is_active)
SELECT
    'admin-key-001',
    COALESCE(
        (SELECT value FROM pg_settings WHERE name = 'application_name'),
        'admin1234'
    ),
    'admin001',
    'Master admin key',
    TRUE
WHERE NOT EXISTS (SELECT 1 FROM api_keys WHERE id = 'admin-key-001');

-- 注释：实际生产环境中，请通过以下方式设置正确的 API 密钥
-- 1. 设置环境变量 MASTER_KEY=your-secure-key
-- 2. 或者手动更新：UPDATE api_keys SET api_key = 'your-secure-key' WHERE id = 'admin-key-001';

-- ============================================================
-- 4. 视图（Views）
-- ============================================================

-- -------------------------------------------------------------
-- 4.1 用户 API 密钥视图
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_api_keys AS
SELECT
    u.id AS user_id,
    u.username,
    u.email,
    u.role,
    ak.id AS api_key_id,
    ak.api_key,
    ak.description,
    ak.is_active AS key_is_active,
    ak.created_at AS key_created_at
FROM users u
LEFT JOIN api_keys ak ON u.id = ak.user_id
WHERE u.is_active = TRUE;

-- -------------------------------------------------------------
-- 4.2 用户使用统计视图
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_usage_summary AS
SELECT
    u.id AS user_id,
    u.username,
    u.email,
    us.model_name,
    us.request_count,
    us.total_tokens,
    us.total_cost,
    us.last_used
FROM users u
LEFT JOIN usage_stats us ON u.id = us.user_id
WHERE u.is_active = TRUE
ORDER BY u.id, us.model_name;

-- -------------------------------------------------------------
-- 4.3 模型配置概览视图
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_model_config_overview AS
SELECT
    id,
    model_name,
    description,
    is_active,
    default_rpm,
    default_tpm,
    default_max_tokens,
    support_types,
    created_at,
    updated_at
FROM model_configs
ORDER BY model_name;

-- ============================================================
-- 5. 函数（Functions）
-- ============================================================

-- -------------------------------------------------------------
-- 5.1 自动更新 updated_at 时间戳
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -------------------------------------------------------------
-- 5.2 为需要 updated_at 的表创建触发器
-- -------------------------------------------------------------

-- users 表
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- model_configs 表
DROP TRIGGER IF EXISTS update_model_configs_updated_at ON model_configs;
CREATE TRIGGER update_model_configs_updated_at
    BEFORE UPDATE ON model_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- config_checkpoints 表
DROP TRIGGER IF EXISTS update_config_checkpoints_updated_at ON config_checkpoints;
CREATE TRIGGER update_config_checkpoints_updated_at
    BEFORE UPDATE ON config_checkpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 6. 权限（Permissions）- 可选
-- ============================================================

-- 如果创建了专用数据库用户，可以取消以下注释：
--
-- CREATE USER litellm_app WITH PASSWORD 'your-password';
-- GRANT CONNECT ON DATABASE litellm_gateway TO litellm_app;
-- GRANT USAGE ON SCHEMA public TO litellm_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO litellm_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO litellm_app;

-- ============================================================
-- 7. 验证查询（Verification Queries）
-- ============================================================

-- 验证表是否创建成功
SELECT
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 验证索引数量
SELECT
    tablename,
    COUNT(indexname) AS index_count
FROM pg_indexes
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

-- ============================================================
-- 脚本完成
-- ============================================================

-- 显示完成消息
DO $$
BEGIN
    RAISE NOTICE 'LiteLLM Proxy 数据库初始化完成！';
    RAISE NOTICE '表数量：7 (users, api_keys, usage_stats, completion_logs, completion_details, model_configs, config_checkpoints)';
    RAISE NOTICE '视图数量：3';
    RAISE NOTICE '触发器数量：3';
END $$;
