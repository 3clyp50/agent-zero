import os
import shutil
from dataclasses import dataclass
from typing import Iterable, List, Dict, Tuple

from python.helpers import files

PROMPTS_DIR = files.get_abs_path("prompts")
KNOWLEDGE_DIR = files.get_abs_path("knowledge")

USER_DEFAULT_DIR_NAMES = {
    "prompts": "default",
    "knowledge": "default",
}


@dataclass
class SyncStats:
    copied_files: int = 0
    copied_dirs: int = 0
    skipped_items: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "copied_files": self.copied_files,
            "copied_dirs": self.copied_dirs,
            "skipped_items": self.skipped_items,
        }


def _resolve_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _iter_content_paths(base_dir: str, skip_default: bool = True) -> Iterable[Tuple[str, str]]:
    """Yield (src, relative) tuples for files under base_dir."""
    if not os.path.isdir(base_dir):
        return
    default_name = USER_DEFAULT_DIR_NAMES.get(os.path.basename(base_dir), "default")
    for root, dirs, files in os.walk(base_dir):
        rel_root = os.path.relpath(root, base_dir)
        if rel_root == ".":
            rel_root = ""
        if skip_default and rel_root and rel_root.split(os.sep)[0] == default_name:
            dirs[:] = []
            continue
        for filename in files:
            rel_path = os.path.join(rel_root, filename) if rel_root else filename
            yield os.path.join(root, filename), rel_path


def _clean_destination(path: str, skip_default: bool = True) -> None:
    if not os.path.isdir(path):
        return
    default_name = USER_DEFAULT_DIR_NAMES.get(os.path.basename(path), "default")
    for entry in os.listdir(path):
        if skip_default and entry == default_name:
            continue
        target = os.path.join(path, entry)
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
        else:
            try:
                os.remove(target)
            except FileNotFoundError:
                pass


def _ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _copy_items(source_dir: str, destination_dir: str, *, skip_default: bool, stats: SyncStats, log: List[str]) -> None:
    if not os.path.isdir(source_dir):
        log.append(f"Skipped {source_dir} (not found)")
        stats.skipped_items += 1
        return

    created_dirs: set[str] = set()
    for src_file, rel_path in _iter_content_paths(source_dir, skip_default=skip_default):
        dest_file = os.path.join(destination_dir, rel_path)
        dest_parent = os.path.dirname(dest_file)
        if not os.path.isdir(dest_parent):
            _ensure_directory(dest_parent)
            created_dirs.add(dest_parent)
        shutil.copy2(src_file, dest_file)
        stats.copied_files += 1
    stats.copied_dirs += len(created_dirs)


def sync_persistent_content(
    direction: str,
    target_path: str,
    items: Iterable[str],
    *,
    clean_destination: bool = False,
) -> Dict[str, object]:
    """Synchronize prompts/knowledge folders with a host folder."""
    normalized_items = [item for item in items if item in {"prompts", "knowledge"}]
    if not normalized_items:
        return {
            "success": False,
            "error": "No valid items selected. Choose prompts and/or knowledge.",
        }

    resolved_target = _resolve_path(target_path)
    log: List[str] = []
    item_results: Dict[str, Dict[str, object]] = {}

    if direction not in {"backup", "restore"}:
        return {
            "success": False,
            "error": "Direction must be 'backup' or 'restore'.",
        }

    if direction == "backup":
        _ensure_directory(resolved_target)

    for item in normalized_items:
        stats = SyncStats()
        if item == "prompts":
            source_dir = PROMPTS_DIR
            destination_name = "prompts"
        else:
            source_dir = KNOWLEDGE_DIR
            destination_name = "knowledge"

        if direction == "backup":
            destination_dir = os.path.join(resolved_target, destination_name)
            if clean_destination and os.path.isdir(destination_dir):
                _clean_destination(destination_dir, skip_default=True)
            _ensure_directory(destination_dir)
            _copy_items(source_dir, destination_dir, skip_default=True, stats=stats, log=log)
            log.append(
                f"Backed up {destination_name} to {destination_dir} ({stats.copied_files} files)."
            )
        else:
            source_backup_dir = os.path.join(resolved_target, destination_name)
            destination_dir = source_dir
            if clean_destination:
                _clean_destination(destination_dir, skip_default=True)
            _copy_items(source_backup_dir, destination_dir, skip_default=True, stats=stats, log=log)
            log.append(
                f"Restored {destination_name} from {source_backup_dir} ({stats.copied_files} files)."
            )

        item_results[item] = {
            "stats": stats.to_dict(),
            "destination": destination_dir,
        }

    return {
        "success": True,
        "direction": direction,
        "target_path": resolved_target,
        "items": item_results,
        "log": log,
    }
