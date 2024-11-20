from typing import Optional, BinaryIO, Union
from pathlib import Path
import aiofiles
import hashlib
from datetime import datetime
from .logger import Logger


class Storage:
    """文件存储管理器"""

    def __init__(self, base_dir: str = "data"):
        self.logger = Logger(__name__)
        self.base_dir = Path(base_dir)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保必要的目录存在"""
        dirs = [
            self.base_dir,
            self.base_dir / "temp",
            self.base_dir / "media",
            self.base_dir / "documents",
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, file_path: Union[str, Path]) -> str:
        """获取文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def save_file(
        self,
        file: Union[str, Path, BinaryIO],
        directory: str = "media",
        filename: Optional[str] = None,
    ) -> Path:
        """保存文件"""
        try:
            target_dir = self.base_dir / directory
            target_dir.mkdir(exist_ok=True)

            # 如果是文件路径
            if isinstance(file, (str, Path)):
                file_path = Path(file)
                if not file_path.exists():
                    raise FileNotFoundError(f"文件不存在: {file}")

                # 生成目标文件名
                if not filename:
                    file_hash = self._get_file_hash(file_path)
                    filename = f"{file_hash}{file_path.suffix}"

                target_path = target_dir / filename

                # 复制文件
                async with aiofiles.open(file_path, 'rb') as src, aiofiles.open(
                    target_path, 'wb'
                ) as dst:
                    await dst.write(await src.read())

            # 如果是文件对象
            else:
                if not filename:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"file_{timestamp}"

                target_path = target_dir / filename

                # 保存文件
                async with aiofiles.open(target_path, 'wb') as f:
                    if hasattr(file, 'read'):
                        content = file.read()
                        if isinstance(content, str):
                            content = content.encode()
                        await f.write(content)
                    else:
                        await f.write(file)

            self.logger.info(f"文件已保存: {target_path}")
            return target_path

        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}")
            raise

    async def get_file(self, filename: str, directory: str = "media") -> Optional[Path]:
        """获取文件"""
        try:
            file_path = self.base_dir / directory / filename
            if not file_path.exists():
                return None
            return file_path
        except Exception as e:
            self.logger.error(f"获取文件失败: {str(e)}")
            return None

    async def delete_file(self, filename: str, directory: str = "media") -> bool:
        """删除文件"""
        try:
            file_path = self.base_dir / directory / filename
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"文件已删除: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"删除文件失败: {str(e)}")
            return False

    async def cleanup_temp(self, max_age_hours: int = 24):
        """清理临时文件"""
        try:
            temp_dir = self.base_dir / "temp"
            current_time = datetime.now().timestamp()

            for file_path in temp_dir.glob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_hours * 3600:
                        file_path.unlink()
                        self.logger.debug(f"清理临时文件: {file_path}")

        except Exception as e:
            self.logger.error(f"清理临时文件失败: {str(e)}")
