import json

import litellm
import openai
import torch
from sentence_transformers import SentenceTransformer
from config_manager import get_all_model_configs,get_all_models
from data.model_info import ModelEndPoint, ModelInfoList
from .dependencies import get_logger
logger = get_logger()

class LocalModelManage:
    
    def __init__(self):
        self.mac_emb_models=dict[str,SentenceTransformer]()
    def _load_model(self,models:list[ModelEndPoint]):
        """
        
        """
        for model in models:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self.mac_emb_models[model.model] = SentenceTransformer(model.base_url, device=device)
            self.mac_emb_models[model.model].encode(["初始化本地模型完成"], normalize_embeddings=True)

    def load_models(self):
        models = get_all_model_configs()

        need_load_models=[]
        for model_name, model_config in models.items():
            # 判断是否为本地模型
            if model_config and hasattr(model_config.litellm_params,'endpoints') and isinstance(model_config.litellm_params.endpoints,ModelInfoList):
                for i,endpoint in model_config.litellm_params.endpoints:
                    if endpoint.provider == 'local':
                        need_load_models.append(endpoint)
            elif isinstance(model_config.litellm_params,ModelEndPoint) and model_config.litellm_params.provider == 'local':
                need_load_models.append(model_config.litellm_params)

        self._load_model(need_load_models)


# 全局配置管理器实例
local_model_manager = LocalModelManage()

def initialize_local_models():
    local_model_manager.load_models()

def embedding_encode(model_name: str, inputs: list[str], normalize: bool=True) -> litellm.EmbeddingResponse:
    model=local_model_manager.mac_emb_models.get(model_name)
    if not model:
        raise ValueError(f"Local model not found: {model_name}")
    embeddings=model.encode(inputs, normalize_embeddings=normalize)
    resp=litellm.EmbeddingResponse(
                data=[
                    openai.types.embedding.Embedding(
                        object="embedding",
                        embedding=emb,
                        index=i
                    ) for i,emb in enumerate(embeddings)
                ],
                model=model_name,
                usage=litellm.Usage(
                    prompt_tokens=0,
                    total_tokens=0
                )
            )
    return resp