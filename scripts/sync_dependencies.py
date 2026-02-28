#!/usr/bin/env python3
"""
依赖同步脚本
用于在安装新依赖时自动同步更新 pyproject.toml 和 requirements.txt
"""

import os
import tomllib
import subprocess
from pathlib import Path


def read_pyproject_dependencies():
    """读取 pyproject.toml 中的依赖"""
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["dependencies"]


def write_requirements_file(dependencies):
    """将依赖写入 requirements.txt"""
    with open("requirements.txt", "w") as f:
        for dep in dependencies:
            f.write(f"{dep}\n")


def sync_dependencies():
    """同步依赖到 requirements.txt"""
    print("正在同步依赖...")

    # 读取当前 pyproject.toml 中的依赖
    dependencies = read_pyproject_dependencies()

    # 写入 requirements.txt
    write_requirements_file(dependencies)

    print(f"已成功同步 {len(dependencies)} 个依赖到 requirements.txt")
    print("依赖同步完成！")


def add_dependency(package_spec):
    """添加新依赖并同步"""
    print(f"正在添加依赖: {package_spec}")

    # 使用 uv 添加依赖
    result = subprocess.run(
        ["uv", "add", package_spec],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"成功添加依赖: {package_spec}")
        sync_dependencies()
    else:
        print(f"添加依赖失败: {result.stderr}")


def remove_dependency(package_name):
    """移除依赖并同步"""
    print(f"正在移除依赖: {package_name}")

    # 使用 uv 移除依赖
    result = subprocess.run(
        ["uv", "remove", package_name],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"成功移除依赖: {package_name}")
        sync_dependencies()
    else:
        print(f"移除依赖失败: {result.stderr}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="依赖同步工具")
    parser.add_argument("action", choices=["sync", "add", "remove"],
                        help="操作类型: sync(同步), add(添加), remove(移除)")
    parser.add_argument("package", nargs="?", help="包名称（用于 add/remove 操作）")

    args = parser.parse_args()

    if args.action == "sync":
        sync_dependencies()
    elif args.action == "add" and args.package:
        add_dependency(args.package)
    elif args.action == "remove" and args.package:
        remove_dependency(args.package)
    else:
        parser.print_help()