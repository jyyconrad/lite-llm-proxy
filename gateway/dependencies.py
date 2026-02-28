import json
import logging
import random

import redis, litellm, requests, os
import bcrypt
from fastapi import HTTPException, Depends, Header
from openai import api_key
from redis.asyncio import Redis
from sqlalchemy import select, and_

from data.model_info import ModelConfig, ModelEndPoint, ModelInfoList
from .config import get_settings
from data import User, APIKey,get_db_session,sync_session

# 获取logger实例
def get_logger():
    logger = logging.getLogger("gateway")
    if not logger.handlers:
        settings = get_settings()
        logging.basicConfig(
            level=getattr(logging, settings.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    return logger

logger = get_logger()

_redis_client = None
def get_redis():
    global _redis_client
    if _redis_client is None:
        url = get_settings().redis_url
        host, port, pwd = parse_redis(url)
        _redis_client = redis.Redis(host=host, port=port, password=pwd, db=3, decode_responses=True)
    return _redis_client

def parse_redis(url: str):
    # redis://[:password]@host:port
    # 移除redis://前缀
    url_without_scheme = url.replace("redis://", "")
    
    # 检查是否有认证信息
    if "@" in url_without_scheme:
        # 格式: password@host:port 或 username:password@host:port
        auth_part, host_part = url_without_scheme.split("@", 1)
        
        # 处理认证信息
        if ":" in auth_part:
            # 有用户名和密码
            username, password = auth_part.split(":", 1)
            pwd = password
        else:
            # 只有密码
            pwd = auth_part
            
        # 处理主机和端口
        if ":" in host_part:
            host, port_str = host_part.split(":", 1)
            port = int(port_str)
        else:
            host = host_part
            port = 6379
    else:
        # 没有认证信息
        pwd = None
        if ":" in url_without_scheme:
            host, port_str = url_without_scheme.split(":", 1)
            port = int(port_str)
        else:
            host = url_without_scheme
            port = 6379
    
    return host, port, pwd

# ---------- password utilities ----------
def hash_password(password: str) -> str:
    """生成密码哈希值"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# ---------- auth ----------
class AuthException(Exception):
    """认证异常类"""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

async def authenticate_user(
    authorization: str = Header(..., alias="Authorization"),
    db = Depends(get_db_session),
) -> dict:
    """校验 Bearer API-Key，返回用户基本信息（全部字段已转为 Python 原生类型）"""
    if not authorization.startswith("Bearer "):
        raise AuthException(status_code=401, detail="Invalid API key format")

    key = authorization.replace("Bearer ", "")
    logger.debug(f"Authenticating API key: {key[:8]}...")  # 只记录前8位用于调试
    
    # 使用 scalars().first() 替代 first() 来避免事件循环问题
    api_key_stmt = select(APIKey).where(APIKey.api_key == key)
    api_key_result = await db.execute(api_key_stmt)
    api_key_row = api_key_result.scalars().first()
    
    if not api_key_row:
        raise AuthException(status_code=401, detail="Invalid API key")
        
    # 检查API密钥是否激活
    if not api_key_row.is_active:
        raise AuthException(status_code=401, detail="API key is deactivated")
    
    user_stmt = select(User).where(User.id == api_key_row.user_id)
    user_result = await db.execute(user_stmt)
    user_row = user_result.scalars().first()
    
    if not user_row:
        raise AuthException(status_code=401, detail="Invalid User")
    
    # 检查用户是否激活
    if not user_row.is_active:
        raise AuthException(status_code=401, detail="User account is deactivated")

    # 2. 字段映射：分清 user 主键 与 api_key 主键
    return {
        "key_id": str(api_key_row.id),                       # 命中的 APIKey 主键
        "user_id": user_row.id,                          # 用户主键
        "username": user_row.username,
        "email": user_row.email,
        "role": user_row.role,
        "budget_limit": float(user_row.budget_limit or 0),
        "rpm_limit": int(user_row.rpm_limit or 0),
        "tpm_limit": int(user_row.tpm_limit or 0),
    }

# ---------- admin auth ----------
async def require_admin(user=Depends(authenticate_user)):
    """验证用户是否为管理员"""
    if user["role"] != "admin":
        raise AuthException(status_code=403, detail="需要管理员权限")
    return user

# ---------- rate limit ----------
async def check_rate_limit(user: dict, model: ModelConfig):
    # 如果限制为-1，则不限制
    r = get_redis()
    model_endpoint = None
    try:
        if isinstance(model.litellm_params, ModelEndPoint):
            model_endpoint = model.litellm_params
        elif isinstance(model.litellm_params, ModelInfoList):
            model_endpoint = _weighted_random_choice(model, model.litellm_params.endpoints, r)
    except ValueError as e:
        logger.error(f"{e}")
        raise HTTPException(404, "Model Not Found")
    model_rpm_key, model_tpm_key = f"rpm:{model}:{model_endpoint.model}", f"tpm:{model}:{model_endpoint.model}"
    m_rpm = int(r.get(model_rpm_key) or 0)
    m_tpm = int(r.get(model_tpm_key) or 0)
    if (m_rpm>0 and m_tpm>0) and ((0 < model_endpoint.rpm <= m_rpm) or (m_tpm >= model_endpoint.tpm > 0)):
        raise HTTPException(429, f"{model.model_name} Rate limit exceeded,is limit to {model_endpoint.rpm}")
    if user["rpm_limit"] == -1 and user["tpm_limit"] == -1:
        return model_endpoint
    uid = user["user_id"]
    rpm_key, tpm_key, budget_key = f"rpm:{uid}:{model.model_name}", f"tpm:{uid}:{model.model_name}", f"budget:{uid}"
    
    # 检查RPM限制（每分钟最大请求数）
    u_rpm=int(r.get(rpm_key) or 0)
    if user["rpm_limit"] != -1 and u_rpm >= user["rpm_limit"]:
        raise HTTPException(429, "Rate limit exceeded")
    if user["rpm_limit"] != -1 and u_rpm >= model.default_rpm:
        raise HTTPException(429, "Rate limit exceeded")

    # 检查TPM限制（最大tokens数）
    u_tpm=int(r.get(tpm_key) or 0)
    if user["tpm_limit"]!=-1 and user["tpm_limit"] <= u_tpm:
        raise HTTPException(429, "Token rate limit exceeded")
    if user["tpm_limit"] !=-1 and u_tpm >= model.default_tpm:
        raise HTTPException(429, f"Token rate limit exceeded,limit to {model.default_tpm}")
    # # 检查预算限制
    # if user["budget_limit"] != -1 and float(r.get(budget_key) or 0) >= user["budget_limit"]:
    #     raise HTTPException(429, "Budget limit exceeded")
    return model_endpoint
def _weighted_random_choice(model:str,endpoints:list[ModelEndPoint],r:Redis)->ModelEndPoint:
    """
    根据权重从列表中随机选择一项

    Args:
        endpoints:
    Returns:
        根据权重随机选中的项的

    Raises:
        ValueError: 如果列表为空或所有权重为0
    """
    if not endpoints:
        raise ValueError("模型不能为空")
    
    # 提取权重
    weights = []
    choice_endpoints = []
    for endpoint in endpoints:
        model_rpm_key, model_tpm_key = f"rpm:{model}:{endpoint.model}",f"tpm:{model}:{endpoint.model}"
        m_rpm=int(r.get(model_rpm_key) or 0)
        m_tpm=int(r.get(model_tpm_key) or 0)
        logger.info(endpoint.model_dump_json())
        if endpoint.weight>0:
            if ((endpoint.rpm>m_rpm and endpoint.rpm>0) or endpoint.rpm==0) and ((m_tpm<endpoint.tpm and endpoint.tpm>0) or endpoint.tpm==0):
                weights.append(endpoint.weight*10)
                choice_endpoints.append(endpoint)

    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("所有项的权重不能都为0")
    if len(choice_endpoints)==0:
        raise ValueError(f"{model}模型都不可用")
    if len(choice_endpoints)==1:
        return choice_endpoints[0]
    # 使用 random.choices 根据权重随机选择
    selected = random.choices(choice_endpoints, weights=weights, k=1)[0]
    return selected
def incr_rate_limit(uid: str, model: str,used_model:str, tokens: int, cost: float):
    r = get_redis()
    rpm_key, tpm_key, budget_key,m_rpm,m_tpm = f"rpm:{uid}:{model}", f"tpm:{uid}:{model}", f"budget:{uid}",f"rpm:{model}:{used_model}",f"tpm:{model}:{used_model}"
    pipe = r.pipeline()
    # RPM计数器：每分钟过期
    pipe.incr(rpm_key).expire(rpm_key, 60)
    # TPM计数器：每周过期（60秒 * 60分钟 * 24小时 * 7天 = 604800秒）
    pipe.incrby(tpm_key, tokens).expire(tpm_key, 604800)
    pipe.incr(m_rpm).expire(tpm_key, 60)
    pipe.incrby(m_tpm, tokens).expire(tpm_key, 60)
    pipe.incrbyfloat(budget_key, cost)
    pipe.execute()

# ---------- proxy ----------
def configure_proxy():
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy: proxies["http"] = http_proxy
        if https_proxy: proxies["https"] = https_proxy
        session = requests.Session()
        session.proxies.update(proxies)
        for method in ("request", "get", "post", "put", "delete", "patch"):
            setattr(requests, method, getattr(session, method))
        litellm.proxy = https_proxy or http_proxy
configure_proxy()
