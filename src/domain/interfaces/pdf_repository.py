"""Contrato de infraestrutura para leitura e anotação de PDFs."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence, Any

from domain.models.annotation import Annotation
from domain.models.pdf_geometry import PageGeometry, Point, Rect


class PdfRepository(Protocol):
    def open(self, path: Path) -> Any:
        """Abre o arquivo e devolve um identificador de sessão opaco."""
        ...

    def page_count(self, session: Any) -> int:
        ...

    def get_annotations(self, session: Any) -> list[Annotation]:
        ...

    def get_page_geometry(self, session: Any, page: int) -> PageGeometry:
        ...

    def get_page_text(self, session: Any, page: int) -> list[dict[str, Any]]:
        """Retorna trechos de texto e suas caixas em coordenadas da página exibida."""
        ...

    def render_page(self, session: Any, page: int, scale: float) -> bytes:
        """Renderiza a página como bytes PNG, sem depender de Qt."""
        ...

    def add_highlight(
        self, session: Any, page: int, rects: Sequence[Rect], color: tuple[float, float, float]
    ) -> Annotation:
        ...

    def add_text_note(
        self, session: Any, page: int, point: Point, text: str,
        color: tuple[float, float, float]
    ) -> Annotation:
        ...

    def save(self, session: Any) -> Path:
        ...

    def close(self, session: Any) -> None:
        ...
