"""共享工具函数 — 路径管理、JSON I/O、日志配置。"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# 路径管理
# ---------------------------------------------------------------------------

TIDE_DIR = ".tide"
REPOS_DIR = ".repos"
TRASH_DIR = ".trash"


def ensure_tide_dirs(project_root: Path) -> Path:
    """确保 .tide/ 目录存在并返回其路径。"""
    tide_dir = project_root / TIDE_DIR
    tide_dir.mkdir(parents=True, exist_ok=True)
    return tide_dir


def ensure_repos_dir(project_root: Path) -> Path:
    """确保 .repos/ 目录存在并返回其路径。"""
    repos_dir = project_root / REPOS_DIR
    repos_dir.mkdir(parents=True, exist_ok=True)
    return repos_dir


# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------


def write_json_result(path: Path, data: BaseModel) -> None:
    """将 Pydantic 模型序列化为 JSON 并写入文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data.model_dump_json(indent=2))


def read_json_model[T: BaseModel](path: Path, model_class: type[T]) -> T:
    """从 JSON 文件读取并验证为 Pydantic 模型。"""
    if not path.exists():
        raise FileNotFoundError(f"{path}: file not found")
    return model_class.model_validate_json(path.read_text())


# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------


def setup_logger(name: str, *, level: int = logging.INFO) -> logging.Logger:
    """创建带有统一格式的 logger。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
