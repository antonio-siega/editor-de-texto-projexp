"""Modelo de domínio para o PDF aberto na sessão atual."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PdfDocument:
    path: Path
    page_count: int
    current_page: int = 0
    zoom: float = 1.25
    is_modified: bool = False

    @property
    def title(self) -> str:
        return self.path.name
