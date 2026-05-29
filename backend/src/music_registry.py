from pathlib import Path
from typing import Any
import re

SUPPORTED_MUSIC_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")
MUSIC_DIR = Path(__file__).parent.parent / "music"
USER_MUSIC_DIR = MUSIC_DIR / "users"
MAX_MUSIC_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _display_name(stem: str) -> str:
    return stem.replace("-", " ").replace("_", " ").strip().title()


def sanitize_user_id_for_path(user_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", user_id).strip("-")
    return safe or "user"


def get_user_music_dir(user_id: str) -> Path:
    return USER_MUSIC_DIR / sanitize_user_id_for_path(user_id)


def _collect_music_from_dir(music_dir: Path, scope: str) -> list[dict[str, Any]]:
    if not music_dir.exists():
        return []
    tracks: list[dict[str, Any]] = []
    for ext in SUPPORTED_MUSIC_EXTENSIONS:
        for path in sorted(music_dir.glob(f"*{ext}")):
            tracks.append(
                {
                    "name": path.stem,
                    "display_name": _display_name(path.stem),
                    "filename": path.name,
                    "format": ext.lstrip("."),
                    "file_path": str(path),
                    "scope": scope,
                }
            )
    return tracks


def get_available_music(user_id: str | None = None) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = _collect_music_from_dir(MUSIC_DIR, scope="system")
    if user_id:
        tracks.extend(_collect_music_from_dir(get_user_music_dir(user_id), scope="user"))
    return sorted(tracks, key=lambda t: t["display_name"])


def find_music_path(
    music_name: str,
    user_id: str | None = None,
    allow_all_user_music: bool = False,
) -> Path | None:
    requested = music_name.strip()
    if not requested:
        return None

    search_dirs = [MUSIC_DIR]
    if user_id:
        search_dirs.insert(0, get_user_music_dir(user_id))

    for search_dir in search_dirs:
        for ext in SUPPORTED_MUSIC_EXTENSIONS:
            candidate = search_dir / f"{requested}{ext}"
            if candidate.exists():
                return candidate
        exact = search_dir / requested
        if exact.exists() and exact.suffix.lower() in SUPPORTED_MUSIC_EXTENSIONS:
            return exact

    if allow_all_user_music:
        for path in USER_MUSIC_DIR.glob(f"**/{requested}.*"):
            if path.suffix.lower() in SUPPORTED_MUSIC_EXTENSIONS:
                return path

    return None


def sanitize_music_stem(file_name: str) -> str:
    raw = Path(file_name).stem
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", raw).strip("-")
    if not safe:
        raise ValueError("Invalid music file name")
    return safe


def build_user_music_stem(user_id: str, original_stem: str) -> str:
    safe_stem = sanitize_music_stem(original_stem)
    safe_user = sanitize_user_id_for_path(user_id)
    return f"mus-{safe_user}-{safe_stem}".lower()


def is_music_accessible(music_name: str, user_id: str) -> bool:
    return find_music_path(music_name, user_id=user_id) is not None
