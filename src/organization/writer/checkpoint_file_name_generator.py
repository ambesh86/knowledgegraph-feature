import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class CheckpointFilenameGenerator:

    def __init__(self, checkpoint_root: Path, data_type_prefix: str):
        self.checkpoint_root = checkpoint_root
        self.data_type_prefix = data_type_prefix

    def has_checkpoint(self, key: str) -> bool:
        expected_path = self.build_file_path(key=key)
        path_exists = expected_path.exists()
        base_name = os.path.basename(expected_path)
        logger.info(f"{key} file {base_name} exits? {path_exists}")
        return path_exists

    def build_file_path(self, key: str) -> Path:
        hash = self._name_to_hash(key)
        return self.checkpoint_root / self.data_type_prefix / f"{hash}.json"

    def _name_to_hash(self, name: str) -> str:
        md5_hash = hashlib.md5()
        md5_hash.update(name.encode("utf-8"))
        md5_digest = md5_hash.hexdigest()
        return md5_digest
