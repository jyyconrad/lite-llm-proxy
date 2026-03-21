#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置同步功能测试脚本
"""
import asyncio
import hashlib
import yaml
import os

# 测试 YAML 哈希计算
def test_yaml_hash():
    config_path = "./litellm_config.yaml"
    if not os.path.exists(config_path):
        print(f"YAML 文件不存在：{config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    yaml_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    print(f"YAML 文件哈希：{yaml_hash[:32]}...")
    print(f"文件大小：{len(content)} 字节")

# 测试 YAML 配置加载
def test_yaml_loading():
    config_path = "./litellm_config.yaml"
    if not os.path.exists(config_path):
        print(f"YAML 文件不存在：{config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    model_list = config.get("model_list", [])
    print(f"YAML 中模型数量：{len(model_list)}")

    for model in model_list[:3]:
        print(f"  - {model.get('model_name')}")

    if len(model_list) > 3:
        print(f"  ... 还有 {len(model_list) - 3} 个模型")

if __name__ == "__main__":
    print("=" * 50)
    print("配置同步功能测试")
    print("=" * 50)

    print("\n1. 测试 YAML 哈希计算")
    test_yaml_hash()

    print("\n2. 测试 YAML 配置加载")
    test_yaml_loading()

    print("\n" + "=" * 50)
    print("测试完成")
