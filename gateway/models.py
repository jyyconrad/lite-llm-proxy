import httpx
from pydantic import BaseModel, ConfigDict

from typing import List, Iterable, Optional, Union, Literal, Dict, Any
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: str
    password_hash: Optional[str] = None
    role: str = "user"
    budget_limit: Optional[float] = 1000.0
    rpm_limit: Optional[int] = 60
    tpm_limit: Optional[int] = 60000

class UserRegister(BaseModel):
    username: str
    email: str
    password_hash: Optional[str] = None
    role: str = "user"

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    budget_limit: float
    rpm_limit: int
    tpm_limit: int
    created_at: datetime
    is_active: bool

class APIKeyCreate(BaseModel):
    user_id: str
    description: str

class APIKeyResponse(BaseModel):
    id: str
    api_key: str
    user_id: str
    description: str
    created_at: datetime
    is_active: bool

class CompletionRequest(BaseModel):
    model: str
    messages: List = []
    timeout: Optional[Union[float, int]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop:Union[str,list] = None
    max_tokens: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[dict] = None
    user: Optional[str] = None
    # openai v1.0+ new params
    response_format: Optional[dict] = None
    seed: Optional[int] = None
    tools: Optional[List] = None
    tool_choice: Optional[str] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    functions: Optional[List] = None
    function_call: Optional[str] = None
    # set api_base, api_version, api_key
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    api_key: Optional[str] = None
    model_list: Optional[list] = None

class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str,list]
    timeout: int = 600
    dimensions: int = 1024

class EmbeddingResponse(BaseModel):
    id: str
    model: str
    data: List[Dict[str,Any]]
    usage: Optional[Dict[str ,int]]
    cost: Optional[float]

# admin dashboard
class StatsOverview(BaseModel):
    total_calls: int
    total_tokens: int
    active_users: int
    total_users: int
    total_cost: float
    cost_trend: str
    success_rate: float
    avg_response_time: int

class ModelUsageStats(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str
    call_count: int
    total_tokens: int
    total_cost: float
    avg_response_time: int
    success_rate: float
    status: str

class RecentActivity(BaseModel):
    id: str
    user_email: str
    model_name: str
    total_tokens: int
    cost: float
    timestamp: datetime
    success: bool
    response_time: int