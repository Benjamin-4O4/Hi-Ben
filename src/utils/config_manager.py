from typing import Any, Dict, Optional
import yaml
from pathlib import Path
import os
from .logger import Logger


class ConfigManager:
    """配置管理器

    职责:
    1. 系统配置管理 (data/config/system_config.yml)
    2. 用户配置管理 (data/config/user_config_{platform}-{id}.yml)
    3. 配置文件的读写和验证
    """

    def __init__(self):
        """初始化配置管理器"""
        self.logger = Logger("config")
        self.config_dir = Path("data/config")
        self.system_config_file = self.config_dir / "system_config.yml"
        self.users_dir = self.config_dir

        # 创建必要的目录
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.users_dir.mkdir(exist_ok=True)

        # 加载系统配置
        self.system_config = self._load_system_config()

    def _load_system_config(self) -> Dict:
        """加载系统配置"""
        try:
            if not self.system_config_file.exists():
                self.logger.error("系统配置文件不存在")
                return {}

            with open(self.system_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if not config:
                    self.logger.error("系统配置为空")
                    return {}
                return config

        except Exception as e:
            self.logger.error(f"加载系统配置失败: {str(e)}")
            return {}

    def _get_user_config_file(self, user_id: str, platform: str = "tg") -> Path:
        """获取用户配置文件路径"""
        return self.users_dir / f"user_config_{platform}_{user_id}.yml"

    def _load_user_config(self, user_id: str, platform: str = "tg") -> Dict:
        """加载用户配置"""
        config_file = self._get_user_config_file(user_id, platform)
        if not config_file.exists():
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"加载用户配置失败: {str(e)}")
            return {}

    def _save_user_config(
        self, user_id: str, config: Dict, platform: str = "tg"
    ) -> None:
        """保存用户配置"""
        config_file = self._get_user_config_file(user_id, platform)
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, allow_unicode=True)
        except Exception as e:
            self.logger.error(f"保存用户配置失败: {str(e)}")
            raise

    def get(self, section: str, key: str, default: Any = None) -> Optional[Any]:
        """获取系统配置值

        Args:
            section: 配置段
            key: 配置键
            default: 默认值

        Returns:
            Any: 配置值
            None: 如果配置不存在且未提供默认值

        Raises:
            ValueError: 如果必要的配置不存在且未提供默认值
        """
        try:
            value = self.system_config.get(section, {}).get(key)
            if value is None and default is None:
                raise ValueError(f"必要的配置项不存在: {section}.{key}")
            return value if value is not None else default
        except Exception as e:
            self.logger.error(f"获取系统配置失败: {str(e)}")
            if default is None:
                raise
            return default

    def get_user_value(
        self, user_id: str, path: str, platform: str = "tg", default: Any = None
    ) -> Optional[Any]:
        """获取用户配置值

        Args:
            user_id: 用户ID
            path: 配置路径 (例如: "notion.api_key")
            platform: 平台标识(tg, wx等)
            default: 默认值

        Returns:
            Any: 配置值
            None: 如果配置不存在且未提供默认值
        """
        try:
            config = self._load_user_config(user_id, platform)
            value = config
            for key in path.split('.'):
                value = value.get(key, {})
            return value if value != {} else default
        except Exception as e:
            self.logger.error(f"获取用户配置失败: {str(e)}")
            return default

    def set_user_config(
        self, user_id: str, path: str, value: Any, platform: str = "tg"
    ) -> None:
        """设置用户配置值"""
        try:
            config = self._load_user_config(user_id, platform)

            # 解析路径
            keys = path.split('.')
            current = config

            # 创建嵌套结构
            for key in keys[:-1]:
                current = current.setdefault(key, {})

            # 设置值
            current[keys[-1]] = value

            # 保存配置
            self._save_user_config(user_id, config, platform)

        except Exception as e:
            self.logger.error(f"设置用户配置失败: {str(e)}")
            raise

    def delete_user_config(self, user_id: str, path: str, platform: str = "tg") -> None:
        """删除用户配置"""
        try:
            config = self._load_user_config(user_id, platform)

            # 解析路径
            keys = path.split('.')
            current = config

            # 遍历到最后一个键的父级
            for key in keys[:-1]:
                if key not in current:
                    return
                current = current[key]

            # 删除最后一个键
            if keys[-1] in current:
                del current[keys[-1]]

            # 保存配置
            self._save_user_config(user_id, config, platform)

        except Exception as e:
            self.logger.error(f"删除用户配置失败: {str(e)}")
            raise

    def get_service(self, service_name: str, user_id: str) -> Any:
        """获取服务实例

        Args:
            service_name: 服务名称
            user_id: 用户ID

        Returns:
            Any: 服务实例，如果配置无效则返回None
        """
        try:
            self.logger.info(f"正在获取服务: {service_name}, user_id={user_id}")

            if service_name == "dida365":
                # 检查token配置
                token_info = self.get_user_value(user_id, "dida.token")
                if not token_info:
                    self.logger.error(f"未找到滴答清单token配置: user_id={user_id}")
                    return None

                # 获取access_token
                access_token = token_info.get('access_token')
                if not access_token:
                    self.logger.error(f"滴答清单token无效: {token_info}")
                    return None

                # 创建服务实例
                from ..services.dida365.dida_service import DidaService

                service = DidaService()
                self.logger.info(f"已创建滴答清单服务实例: user_id={user_id}")
                return service

            self.logger.warning(f"未知的服务类型: {service_name}")
            return None

        except Exception as e:
            self.logger.error(f"获取服务失败: {str(e)}", exc_info=True)
            return None
