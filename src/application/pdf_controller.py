"""Coordena os casos de uso de PDF e publica eventos para a interface Qt."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QObject, Signal

from domain.interfaces.pdf_repository import PdfRepository
from domain.models.annotation import Annotation
from domain.models.pdf_document import PdfDocument
from domain.models.pdf_geometry import PageGeometry, Point, Rect, view_point_to_pdf, view_rect_to_pdf


class PdfControllerError(Exception):
    pass


class UnsavedPdfChangesError(PdfControllerError):
    pass


class PdfController(QObject):
    pdf_opened = Signal(object)                 # PdfDocument
    page_rendered = Signal(int, bytes)          # índice zero-based, PNG
    pdf_modified = Signal()
    pdf_saved = Signal(str)                     # caminho salvo
    pdf_closed = Signal()
    operation_failed = Signal(str)

    def __init__(self, repository: PdfRepository, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._repository = repository
        self._session = None
        self._document: PdfDocument | None = None

    @property
    def document(self) -> PdfDocument | None:
        return self._document

    def open_pdf(self, path: Path | str) -> PdfDocument:
        if self._document and self._document.is_modified:
            raise UnsavedPdfChangesError(
                "O PDF atual possui anotações não salvas. Salve-o antes de abrir outro arquivo."
            )
        if self._session is not None:
            self.close_pdf()
        session = self._repository.open(Path(path))
        document = PdfDocument(
            path=Path(path).expanduser().resolve(),
            page_count=self._repository.page_count(session),
        )
        self._session = session
        self._document = document
        self.pdf_opened.emit(document)
        self.render_page(0, document.zoom)
        return document

    def render_page(self, page: int, scale: float | None = None) -> bytes:
        self._require_document()
        assert self._session is not None and self._document is not None
        if page < 0 or page >= self._document.page_count:
            raise ValueError("O número da página está fora do intervalo do PDF.")
        render_scale = float(scale if scale is not None else self._document.zoom)
        image = self._repository.render_page(self._session, page, render_scale)
        self._document.current_page = page
        self._document.zoom = render_scale
        self.page_rendered.emit(page, image)
        return image

    def get_page_geometry(self, page: int | None = None) -> PageGeometry:
        self._require_document()
        assert self._session is not None and self._document is not None
        page_index = self._document.current_page if page is None else page
        return self._repository.get_page_geometry(self._session, page_index)

    def get_annotations(self) -> list[Annotation]:
        """Retorna todas as anotações do PDF aberto."""
        self._require_document()
        assert self._session is not None

        return self._repository.get_annotations(self._session)

    def highlight(
        self, page: int, rects: Sequence[Rect],
        color: tuple[float, float, float] = (1.0, 0.9, 0.2)
    ) -> Annotation:
        self._require_document()
        assert self._session is not None
        annotation = self._repository.add_highlight(self._session, page, rects, color)
        self._mark_modified()
        self.render_page(page)
        return annotation

    def highlight_from_view(
        self, page: int, rects_px: Sequence[Rect], scale: float,
        color: tuple[float, float, float] = (1.0, 0.9, 0.2)
    ) -> Annotation:
        geometry = self.get_page_geometry(page)
        rects_pdf = [view_rect_to_pdf(rect, scale, geometry) for rect in rects_px]
        return self.highlight(page, rects_pdf, color)

    def add_note(
        self, page: int, point: Point, text: str,
        color: tuple[float, float, float] = (1.0, 0.85, 0.2)
    ) -> Annotation:
        self._require_document()
        assert self._session is not None
        annotation = self._repository.add_text_note(self._session, page, point, text, color)
        self._mark_modified()
        self.render_page(page)
        return annotation

    def add_note_from_view(
        self, page: int, point_px: Point, scale: float, text: str,
        color: tuple[float, float, float] = (1.0, 0.85, 0.2)
    ) -> Annotation:
        geometry = self.get_page_geometry(page)
        point_pdf = view_point_to_pdf(point_px, scale, geometry)
        return self.add_note(page, point_pdf, text, color)

    def save_pdf(self) -> Path:
        self._require_document()
        assert self._session is not None and self._document is not None
        path = self._repository.save(self._session)
        self._document.is_modified = False
        self.pdf_saved.emit(str(path))
        return path

    def close_pdf(self, discard_changes: bool = False) -> None:
        if self._document and self._document.is_modified and not discard_changes:
            raise UnsavedPdfChangesError(
                "O PDF possui anotações não salvas. Salve ou descarte as alterações antes de fechar."
            )
        if self._session is not None:
            self._repository.close(self._session)
        self._session = None
        self._document = None
        self.pdf_closed.emit()

    def _require_document(self) -> None:
        if self._session is None or self._document is None:
            raise PdfControllerError("Abra um PDF antes de executar esta operação.")

    def _mark_modified(self) -> None:
        assert self._document is not None
        self._document.is_modified = True
        self.pdf_modified.emit()
