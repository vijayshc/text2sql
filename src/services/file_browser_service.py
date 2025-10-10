"""Service utilities for admin file browser operations."""

from __future__ import annotations

import io
import json
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from werkzeug.datastructures import FileStorage

from config.config import FILE_BROWSER_ALLOWED_EXTENSIONS, FILE_BROWSER_ROOT


class FileBrowserService:
    """Encapsulates secure file-system operations for the admin file browser."""

    _METADATA_FILENAME = ".file_metadata.json"

    def __init__(
        self,
        root_path: Optional[str] = None,
        allowed_extensions: Optional[Iterable[str]] = None,
    ) -> None:
        self.root = Path(root_path or FILE_BROWSER_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

        allowed = allowed_extensions or FILE_BROWSER_ALLOWED_EXTENSIONS
        self.allowed_extensions = {
            ext if ext.startswith(".") else f".{ext}"
            for ext in (ext.lower() for ext in allowed)
        }

        self._metadata_path = self.root / self._METADATA_FILENAME
        self._lock = threading.Lock()
        self._ensure_metadata_file()

    # ------------------------------------------------------------------
    # Metadata management helpers
    # ------------------------------------------------------------------
    def _ensure_metadata_file(self) -> None:
        if not self._metadata_path.exists():
            with self._metadata_path.open("w", encoding="utf-8") as handle:
                json.dump({}, handle)

    def _load_metadata(self) -> Dict[str, Dict[str, Optional[int]]]:
        with self._lock:
            with self._metadata_path.open("r", encoding="utf-8") as handle:
                try:
                    data = json.load(handle)
                except json.JSONDecodeError:
                    data = {}
        return data

    def _save_metadata(self, data: Dict[str, Dict[str, Optional[int]]]) -> None:
        with self._lock:
            with self._metadata_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle)

    def _update_metadata(self, rel_path: str, user_id: Optional[int]) -> None:
        rel_key = rel_path.strip("/")
        meta = self._load_metadata()
        entry = meta.get(rel_key, {})
        entry.update({"uploaded_by": user_id, "updated_at": datetime.utcnow().isoformat()})
        meta[rel_key] = entry
        self._save_metadata(meta)

    def _remove_metadata(self, rel_path: str) -> None:
        rel_key = rel_path.strip("/")
        meta = self._load_metadata()
        if rel_key in meta:
            del meta[rel_key]
            self._save_metadata(meta)

    def _remove_metadata_tree(self, rel_path: str) -> None:
        rel_prefix = rel_path.strip("/")
        meta = self._load_metadata()
        changed = False
        for key in list(meta.keys()):
            if key == rel_prefix or key.startswith(f"{rel_prefix}/"):
                del meta[key]
                changed = True
        if changed:
            self._save_metadata(meta)

    # ------------------------------------------------------------------
    # General helpers
    # ------------------------------------------------------------------
    def _resolve_path(self, relative_path: str) -> Path:
        sanitized = Path(relative_path).as_posix().lstrip("/")
        candidate = (self.root / sanitized).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("Invalid path")
        return candidate

    def _relativize(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _is_extension_allowed(self, filename: str) -> bool:
        if not self.allowed_extensions:
            return True
        extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return extension in self.allowed_extensions

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------
    def list_directory(self, relative_path: str = "") -> Dict[str, object]:
        target_dir = self._resolve_path(relative_path)
        if not target_dir.exists():
            raise FileNotFoundError("Directory does not exist")
        if not target_dir.is_dir():
            raise NotADirectoryError("Path is not a directory")

        meta = self._load_metadata()
        items: List[Dict[str, object]] = []
        for entry in target_dir.iterdir():
            if entry.name == self._METADATA_FILENAME:
                continue

            stat = entry.stat()
            rel_path = self._relativize(entry)
            metadata = meta.get(rel_path, {})
            items.append(
                {
                    "name": entry.name,
                    "isDirectory": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                    "relativePath": rel_path,
                    "uploadedBy": metadata.get("uploaded_by"),
                    "updatedAt": metadata.get("updated_at"),
                }
            )

        items.sort(key=lambda item: (not item["isDirectory"], item["name"].lower()))

        breadcrumbs = self._build_breadcrumbs(relative_path)
        return {
            "path": self._normalize_relative_path(relative_path),
            "breadcrumbs": breadcrumbs,
            "items": items,
        }

    def _build_breadcrumbs(self, relative_path: str) -> List[Dict[str, str]]:
        cleaned = self._normalize_relative_path(relative_path)
        if not cleaned:
            return [{"label": "Root", "path": ""}]

        parts = cleaned.split("/")
        breadcrumbs = [{"label": "Root", "path": ""}]
        cumulative = []
        for part in parts:
            cumulative.append(part)
            breadcrumbs.append({"label": part, "path": "/".join(cumulative)})
        return breadcrumbs

    def _normalize_relative_path(self, relative_path: str) -> str:
        sanitized = Path(relative_path).as_posix().strip("/")
        return sanitized

    def get_file_content(self, relative_path: str, max_bytes: int = 2_097_152) -> str:
        file_path = self._resolve_path(relative_path)
        if not file_path.is_file():
            raise FileNotFoundError("File does not exist")
        if not self._is_extension_allowed(file_path.name):
            raise ValueError("File type not permitted")
        if file_path.stat().st_size > max_bytes:
            raise ValueError("File too large to open in editor")
        with file_path.open("r", encoding="utf-8") as handle:
            return handle.read()

    def update_file_content(self, relative_path: str, content: str, user_id: Optional[int]) -> None:
        file_path = self._resolve_path(relative_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("File does not exist")
        if not self._is_extension_allowed(file_path.name):
            raise ValueError("File type not permitted")
        with file_path.open("w", encoding="utf-8") as handle:
            handle.write(content)
        self._update_metadata(self._relativize(file_path), user_id)

    def save_uploaded_file(
        self,
        target_directory: str,
        storage: FileStorage,
        user_id: Optional[int],
    ) -> str:
        if not storage.filename:
            raise ValueError("Missing filename")
        if not self._is_extension_allowed(storage.filename):
            raise ValueError("File type not permitted")

        directory_path = self._resolve_path(target_directory)
        if not directory_path.exists() or not directory_path.is_dir():
            raise NotADirectoryError("Destination directory does not exist")

        destination = directory_path / storage.filename
        storage.save(str(destination))
        rel_path = self._relativize(destination)
        self._update_metadata(rel_path, user_id)
        return rel_path

    def save_uploaded_folder(
        self,
        target_directory: str,
        files: Iterable[FileStorage],
        relative_paths: Iterable[str],
        user_id: Optional[int],
    ) -> List[str]:
        directory_path = self._resolve_path(target_directory)
        if not directory_path.is_dir():
            raise NotADirectoryError("Destination directory does not exist")

        stored_paths: List[str] = []
        file_list = list(files)
        path_list = list(relative_paths)
        for index, storage in enumerate(file_list):
            if index >= len(path_list):
                break
            rel_path = path_list[index]
            if not storage.filename:
                continue
            if not self._is_extension_allowed(storage.filename):
                raise ValueError(f"File type not permitted: {storage.filename}")

            sanitized_rel_path = Path(rel_path).as_posix().lstrip("/")
            destination = (directory_path / sanitized_rel_path).resolve()
            if self.root not in destination.parents and destination != self.root:
                raise ValueError("Invalid folder structure")

            destination.parent.mkdir(parents=True, exist_ok=True)
            storage.save(str(destination))

            rel_path_norm = self._relativize(destination)
            stored_paths.append(rel_path_norm)
            self._update_metadata(rel_path_norm, user_id)

        return stored_paths

    def delete_path(self, relative_path: str) -> None:
        target_path = self._resolve_path(relative_path)
        if not target_path.exists():
            raise FileNotFoundError("Path does not exist")
        if target_path == self.root:
            raise ValueError("Cannot delete root directory")

        if target_path.is_dir():
            for child in list(target_path.iterdir()):
                self.delete_path(self._relativize(child))
            target_path.rmdir()
            self._remove_metadata_tree(self._relativize(target_path))
        else:
            target_path.unlink()
            self._remove_metadata(self._relativize(target_path))

    def get_file_path(self, relative_path: str) -> Path:
        file_path = self._resolve_path(relative_path)
        if not file_path.exists():
            raise FileNotFoundError("Path does not exist")
        return file_path

    def stream_folder_as_zip(self, relative_path: str) -> Tuple[io.BytesIO, str]:
        folder_path = self._resolve_path(relative_path)
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError("Folder does not exist")
        if folder_path == self.root:
            base_name = "root"
        else:
            base_name = folder_path.name

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in folder_path.rglob("*"):
                if item.name == self._METADATA_FILENAME:
                    continue
                arcname = Path(base_name) / item.relative_to(folder_path)
                archive.write(item, arcname=str(arcname))
        buffer.seek(0)
        filename = f"{base_name}.zip"
        return buffer, filename


# Default singleton used by routes
file_browser_service = FileBrowserService()
