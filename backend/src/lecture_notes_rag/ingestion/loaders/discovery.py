from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".md"}
SEMESTER_PATTERN = re.compile(r"^semester_(?P<number>[1-8])$", re.IGNORECASE)


@dataclass(frozen=True)
class DiscoveredFile:
    path: Path
    relative_path: str
    extension: str
    semester: int | None
    course: str | None
    content_hash: str
    size_bytes: int


def discover_corpus(corpus_root: Path) -> list[DiscoveredFile]:
    root = corpus_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Corpus root does not exist or is not a directory: {root}")

    discovered: list[DiscoveredFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            continue
        relative = resolved.relative_to(root)
        semester, course = metadata_from_relative_path(relative)
        discovered.append(
            DiscoveredFile(
                path=resolved,
                relative_path=relative.as_posix(),
                extension=resolved.suffix.lower(),
                semester=semester,
                course=course,
                content_hash=sha256_file(resolved),
                size_bytes=resolved.stat().st_size,
            )
        )
    return discovered


def metadata_from_relative_path(relative_path: Path) -> tuple[int | None, str | None]:
    """Derive metadata from `semester_N/course/file` without trusting filenames."""
    parts = relative_path.parts
    if len(parts) < 2:
        return None, None
    match = SEMESTER_PATTERN.match(parts[0])
    semester = int(match.group("number")) if match else None
    course = parts[1] if semester is not None and len(parts) >= 3 else None
    return semester, course


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
