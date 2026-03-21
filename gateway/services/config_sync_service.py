# -*- coding: utf-8 -*-
"""
配置同步服务，用于在应用启动时同步 litellm_config.yaml 与数据库配置

同步策略：
1. 仅启动时同步一次
2. 数据库绝对优先 - 如果数据库配置有变更，保持数据库版本
3. YAML 有更新时，同步到数据库（只添加新模型）
"""

import hashlib
import json
import uuid
import yaml
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from data.tables import ConfigCheckpoint, ModelConfig
from gateway.config import get_settings


logger = logging.getLogger(__name__)

# 模型名称最大长度（与数据库定义保持一致）
MAX_MODEL_NAME_LENGTH = 100


class ConfigSyncService:
    """配置同步服务"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "./litellm_config.yaml"

    def compute_yaml_hash(self) -> str:
        """计算 YAML 配置文件内容的 SHA256 哈希"""
        try:
            if not os.path.exists(self.config_path):
                return ""

            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()

            return hashlib.sha256(content.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.warning(f"计算 YAML 哈希失败：{e}")
            return ""

    def compute_db_hash(self, db_configs: Dict[str, ModelConfig]) -> str:
        """计算数据库配置内容的 SHA256 哈希

        统一使用手动构建字典方式，避免依赖可能变化的 to_dict 方法。
        """
        try:
            sorted_configs = {}
            for model_name, config in sorted(db_configs.items()):
                # 统一使用 ORM 对象的属性访问，确保哈希计算一致性
                sorted_configs[model_name] = {
                    'model_name': config.model_name,
                    'litellm_params': config.litellm_params,
                    'support_types': config.support_types,
                    'default_rpm': config.default_rpm,
                    'default_tpm': config.default_tpm,
                    'default_max_tokens': config.default_max_tokens,
                    'description': config.description,
                    'is_active': config.is_active,
                }

            json_str = json.dumps(sorted_configs, sort_keys=True, ensure_ascii=False, default=str)
            return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.error(f"计算数据库哈希失败：{e}")
            return ""

    def get_yaml_mtime(self) -> Optional[datetime]:
        """获取 YAML 文件的最后修改时间"""
        try:
            if os.path.exists(self.config_path):
                mtime = os.path.getmtime(self.config_path)
                return datetime.fromtimestamp(mtime)
        except Exception:
            pass
        return None

    async def get_checkpoint(self, db: AsyncSession) -> Optional[ConfigCheckpoint]:
        """获取配置同步检查点"""
        try:
            stmt = select(ConfigCheckpoint).where(
                ConfigCheckpoint.config_type == "litellm_config"
            )
            result = await db.execute(stmt)
            return result.scalars().first()
        except Exception:
            return None

    async def save_checkpoint(
        self,
        db: AsyncSession,
        yaml_hash: str,
        db_hash: str,
        sync_source: str,
    ) -> ConfigCheckpoint:
        """保存配置同步检查点"""
        try:
            stmt = select(ConfigCheckpoint).where(
                ConfigCheckpoint.config_type == "litellm_config"
            )
            result = await db.execute(stmt)
            checkpoint = result.scalars().first()

            if checkpoint is None:
                checkpoint = ConfigCheckpoint(
                    config_type="litellm_config",
                    yaml_hash=yaml_hash,
                    db_hash=db_hash,
                    last_sync_source=sync_source,
                    last_sync_time=datetime.now(timezone.utc),
                    yaml_updated_at=self.get_yaml_mtime(),
                    db_updated_at=datetime.now(timezone.utc),
                )
                db.add(checkpoint)
            else:
                checkpoint.yaml_hash = yaml_hash
                checkpoint.db_hash = db_hash
                checkpoint.last_sync_source = sync_source
                checkpoint.last_sync_time = datetime.now(timezone.utc)
                checkpoint.yaml_updated_at = self.get_yaml_mtime()
                checkpoint.db_updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(checkpoint)
            return checkpoint
        except Exception as e:
            logger.error(f"保存检查点失败：{e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"回滚失败：{rollback_error}")
            raise

    async def get_db_model_configs(self, db: AsyncSession) -> dict:
        """获取数据库中所有模型配置"""
        try:
            stmt = select(ModelConfig).where(ModelConfig.is_active == True)
            result = await db.execute(stmt)
            configs = result.scalars().all()
            return {config.model_name: config for config in configs}
        except Exception:
            return {}

    async def sync_yaml_to_db(self, db: AsyncSession) -> Tuple[bool, str]:
        """
        将 YAML 配置同步到数据库（只添加新模型，不更新已有模型）

        Returns:
            Tuple[是否执行了同步，同步结果描述]
        """
        try:
            # 从 YAML 文件加载配置
            if not os.path.exists(self.config_path):
                return False, "YAML 配置文件不存在"

            with open(self.config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)

            model_list = yaml_config.get("model_list", [])
            if not model_list:
                return False, "YAML 配置中没有模型定义"

            # 获取数据库中的现有配置
            db_configs = await self.get_db_model_configs(db)
            db_model_names = set(db_configs.keys())

            # 需要同步的模型
            yaml_model_names = set()
            created_count = 0
            failed_models: List[Tuple[str, str]] = []

            for model_dict in model_list:
                model_name = model_dict.get("model_name", "").strip()
                if not model_name:
                    logger.warning("跳过无名的模型配置")
                    continue
                if len(model_name) > MAX_MODEL_NAME_LENGTH:
                    logger.warning(f"模型名称过长（>{MAX_MODEL_NAME_LENGTH} 字符），跳过：{model_name[:50]}...")
                    continue

                yaml_model_names.add(model_name)

                # 数据库优先策略：只添加新模型，不更新已有模型
                if model_name in db_model_names:
                    # 数据库中已存在，跳过不更新
                    continue

                # 数据库中不存在，创建新配置
                try:
                    # 转换配置格式
                    litellm_params = model_dict.get("litellm_params", {})
                    support_types = model_dict.get("support_types", ["text"])
                    if isinstance(support_types, str):
                        support_types = [support_types]

                    default_rpm = model_dict.get("default_rpm", model_dict.get("rpm", 10))
                    default_tpm = model_dict.get("default_tpm", model_dict.get("tpm", 100000))
                    default_max_tokens = model_dict.get("default_max_tokens", model_dict.get("max_tokens", 32768))
                    description = model_dict.get("description", f"模型 {model_name}")

                    new_config = ModelConfig(
                        id=str(uuid.uuid4()),  # 使用 UUID 替代 MD5，避免碰撞风险
                        model_name=model_name,
                        litellm_params=litellm_params,
                        support_types=support_types,
                        default_rpm=default_rpm,
                        default_tpm=default_tpm,
                        default_max_tokens=default_max_tokens,
                        description=description,
                        is_active=True,
                    )
                    db.add(new_config)
                    created_count += 1
                except Exception as e:
                    logger.warning(f"创建模型配置失败 {model_name}: {e}")
                    failed_models.append((model_name, str(e)))
                    continue

            # 记录失败模型详情
            if failed_models:
                logger.warning(f"同步完成，但有 {len(failed_models)} 个模型同步失败：{failed_models}")

            if created_count > 0:
                await db.commit()
                if failed_models:
                    # 部分成功：有模型创建成功，但也有失败的
                    return True, f"从 YAML 同步了 {created_count} 个新模型到数据库（{len(failed_models)} 个失败）"
                return True, f"从 YAML 同步了 {created_count} 个新模型到数据库"
            else:
                if failed_models and len(failed_models) == len(model_list):
                    # 全部失败
                    return False, f"同步失败：所有模型都创建失败"
                return False, "没有需要同步的新模型"

        except Exception as e:
            logger.error(f"同步 YAML 到数据库失败：{e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"回滚失败：{rollback_error}")
            return False, f"同步失败：{str(e)}"

    async def sync_on_startup(self, db: AsyncSession) -> str:
        """
        应用启动时执行配置同步

        同步逻辑：
        1. 计算 YAML 哈希和数据库哈希
        2. 获取检查点记录
        3. 如果 YAML 哈希与检查点不同 → YAML 有更新，只添加新模型到数据库
        4. 如果数据库哈希与检查点不同 → 数据库有更新，保持不变
        5. 更新检查点记录

        Returns:
            同步结果描述
        """
        try:
            # 计算当前 YAML 哈希
            yaml_hash = self.compute_yaml_hash()
            if not yaml_hash:
                logger.warning("YAML 配置文件不存在或读取失败")
                return "YAML 配置文件不存在"

            # 获取数据库配置和哈希
            db_configs = await self.get_db_model_configs(db)
            db_hash = self.compute_db_hash(db_configs)

            # 获取检查点
            checkpoint = await self.get_checkpoint(db)

            if checkpoint is None:
                # 首次启动，执行同步
                logger.info("首次启动，执行配置同步...")
                synced, message = await self.sync_yaml_to_db(db)

                # 重新计算数据库哈希（如果执行了同步）
                if synced:
                    db_configs = await self.get_db_model_configs(db)
                    db_hash = self.compute_db_hash(db_configs)
                    await self.save_checkpoint(db, yaml_hash, db_hash, "yaml")
                    logger.info(f"启动同步完成：{message}")
                    return f"首次启动同步：{message}"
                else:
                    # 同步失败，不保存检查点，下次启动重试
                    logger.warning(f"首次启动同步失败：{message}")
                    return f"首次启动同步失败：{message}"

            # 检查 YAML 是否有更新
            yaml_changed = yaml_hash != checkpoint.yaml_hash
            # 检查数据库是否有更新
            db_changed = db_hash != checkpoint.db_hash

            if yaml_changed:
                logger.info("检测到 YAML 配置有更新，执行同步...")
                synced, message = await self.sync_yaml_to_db(db)

                # 重新计算数据库哈希
                if synced:
                    db_configs = await self.get_db_model_configs(db)
                    db_hash = self.compute_db_hash(db_configs)
                    await self.save_checkpoint(db, yaml_hash, db_hash, "yaml")
                    logger.info(f"YAML 同步完成：{message}")
                    return f"YAML 更新同步：{message}"
                else:
                    # YAML 有更新但没有新模型（可能只是修改了现有模型）
                    await self.save_checkpoint(db, yaml_hash, db_hash, "none")
                    logger.info(f"YAML 有变更但无新模型：{message}")
                    return f"YAML 有变更但无新模型：{message}"

            elif db_changed:
                # 数据库有更新，保持不动，只更新检查点
                logger.info("检测到数据库配置有更新，保持数据库版本")
                await self.save_checkpoint(db, yaml_hash, db_hash, "database")
                return "数据库配置已更新，保持当前版本"

            else:
                # 都没有变化
                logger.info("配置无变化，跳过同步")
                return "配置无变化"

        except Exception as e:
            logger.error(f"启动同步失败：{e}", exc_info=True)
            return f"同步失败：{str(e)}"

    async def get_sync_status(self, db: AsyncSession) -> dict:
        """获取当前同步状态"""
        checkpoint = await self.get_checkpoint(db)
        yaml_hash = self.compute_yaml_hash()
        db_configs = await self.get_db_model_configs(db)
        db_hash = self.compute_db_hash(db_configs)

        yaml_changed = checkpoint and yaml_hash != checkpoint.yaml_hash
        db_changed = checkpoint and db_hash != checkpoint.db_hash

        return {
            "yaml_hash_short": yaml_hash[:16] if yaml_hash else None,
            "db_hash_short": db_hash[:16] if db_hash else None,
            "last_sync_time": checkpoint.last_sync_time.isoformat() if checkpoint and checkpoint.last_sync_time else None,
            "last_sync_source": checkpoint.last_sync_source if checkpoint else None,
            "yaml_changed": yaml_changed or (checkpoint is None),
            "db_changed": db_changed,
            "is_synced": not yaml_changed and not db_changed and checkpoint is not None,
            "model_count": len(db_configs),
        }


# 全局单例
_config_sync_service: Optional[ConfigSyncService] = None


def get_config_sync_service() -> ConfigSyncService:
    """获取配置同步服务单例"""
    global _config_sync_service
    if _config_sync_service is None:
        _config_sync_service = ConfigSyncService()
    return _config_sync_service
