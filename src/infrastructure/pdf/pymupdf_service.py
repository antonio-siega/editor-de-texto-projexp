"""Implementação do repositório PDF usando exclusivamente PyMuPDF (fitz)."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Any

from domain.models.annotation import Annotation, AnnotationKind
from domain.models.pdf_geometry import PageGeometry, Point, Rect


class PdfServiceError(Exception):
    """Erro-base das operações de PDF."""


class PdfOpenError(PdfServiceError):
    pass


class PdfPasswordRequiredError(PdfOpenError):
    pass


class PdfRenderError(PdfServiceError):
    pass


class PdfAnnotationError(PdfServiceError):
    pass


class PdfSaveError(PdfServiceError):
    pass


@dataclass(slots=True)
class PdfSession:
    """Sessão interna; objetos fitz nunca são entregues à interface."""

    document: Any
    path: Path


class PyMuPdfService:
    def __init__(self) -> None:
        try:
            import fitz  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise PdfServiceError(
                "PyMuPDF não está instalado. Instale a dependência 'PyMuPDF'."
            ) from exc
        self._fitz = fitz

    def open(self, path: Path) -> PdfSession:
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise PdfOpenError(f"O arquivo PDF não foi encontrado: {path}")
        try:
            document = self._fitz.open(str(path))
            if not document.is_pdf:
                document.close()
                raise PdfOpenError("O arquivo selecionado não é um PDF válido.")
            if document.needs_pass:
                document.close()
                raise PdfPasswordRequiredError(
                    "Este PDF está protegido por senha. PDFs protegidos não são aceitos nesta versão."
                )
            if document.page_count < 1:
                document.close()
                raise PdfOpenError("O PDF não contém páginas para exibir.")
            return PdfSession(document=document, path=path)
        except PdfServiceError:
            raise
        except Exception as exc:
            raise PdfOpenError(f"Não foi possível abrir o PDF: {exc}") from exc

    def page_count(self, session: PdfSession) -> int:
        self._ensure_open(session)
        return int(session.document.page_count)

    def get_annotations(self, session: PdfSession) -> list[Annotation]:
        """Recupera todas as anotações existentes no documento PDF."""
        self._ensure_open(session)

        annotations = []

        try:
            for page_index in range(session.document.page_count):
                pdf_page = session.document.load_page(page_index)

                for annot in pdf_page.annots() or []:
                    annot_type = annot.type[1]
                    color = annot.colors.get("stroke") or (1.0, 0.9, 0.2)

                    if annot_type == "Highlight":
                        vertices = annot.vertices or []

                        rects = tuple(
                            (
                                min(float(vertices[i + j][0]) for j in range(4)),
                                min(float(vertices[i + j][1]) for j in range(4)),
                                max(float(vertices[i + j][0]) for j in range(4)),
                                max(float(vertices[i + j][1]) for j in range(4)),
                            )
                            for i in range(0, len(vertices), 4)
                        )

                        annotation = Annotation(
                            page_index=page_index,
                            kind=AnnotationKind.HIGHLIGHT,
                            rects=rects,
                            color=tuple(color),
                        )

                    elif annot_type == "Text":
                        point = annot.rect.tl

                        annotation = Annotation(
                            page_index=page_index,
                            kind=AnnotationKind.TEXT_NOTE,
                            content=annot.info.get("content", ""),
                            color=tuple(color),
                            point=(float(point.x), float(point.y)),
                        )

                    else:
                        continue

                    annotations.append(annotation)

            return annotations

        except Exception as exc:
            raise PdfAnnotationError(
                f"Não foi possível recuperar as anotações: {exc}"
            ) from exc

    def get_page_geometry(self, session: PdfSession, page: int) -> PageGeometry:
        pdf_page = self._get_page(session, page)
        matrix = pdf_page.derotation_matrix
        return PageGeometry(
            width=float(pdf_page.rect.width),
            height=float(pdf_page.rect.height),
            rotation=int(pdf_page.rotation),
            derotation_matrix=(
                float(matrix.a), float(matrix.b), float(matrix.c),
                float(matrix.d), float(matrix.e), float(matrix.f),
            ),
        )

    def render_page(self, session: PdfSession, page: int, scale: float) -> bytes:
        if scale <= 0:
            raise PdfRenderError("O zoom deve ser maior que zero.")
        try:
            pdf_page = self._get_page(session, page)
            pixmap = pdf_page.get_pixmap(
                matrix=self._fitz.Matrix(float(scale), float(scale)), alpha=False
            )
            return pixmap.tobytes("png")
        except PdfServiceError:
            raise
        except Exception as exc:
            raise PdfRenderError(f"Não foi possível renderizar a página: {exc}") from exc

    def add_highlight(
        self, session: PdfSession, page: int, rects: Sequence[Rect],
        color: tuple[float, float, float]
    ) -> Annotation:
        try:
            pdf_page = self._get_page(session, page)
            fitz_rects = [self._fitz.Rect(*rect) for rect in rects]
            fitz_rects = [rect for rect in fitz_rects if not rect.is_empty and rect.is_valid]
            if not fitz_rects:
                raise PdfAnnotationError("Selecione uma área válida para grifar.")
            annotation = pdf_page.add_highlight_annot(fitz_rects)
            if annotation is None:
                raise PdfAnnotationError("Não foi possível criar o grifo nesta área.")
            normalized_color = self._normalize_color(color)
            annotation.set_colors(stroke=normalized_color)
            annotation.update()
            return Annotation(
                page_index=page,
                kind=AnnotationKind.HIGHLIGHT,
                rects=tuple(tuple(float(v) for v in rect) for rect in rects),
                color=normalized_color,
            )
        except PdfServiceError:
            raise
        except Exception as exc:
            raise PdfAnnotationError(f"Não foi possível adicionar o grifo: {exc}") from exc

    def add_text_note(
        self, session: PdfSession, page: int, point: Point, text: str,
        color: tuple[float, float, float] = (1.0, 0.85, 0.2)
    ) -> Annotation:
        clean_text = text.strip()
        if not clean_text:
            raise PdfAnnotationError("A nota não pode ficar vazia.")
        try:
            pdf_page = self._get_page(session, page)
            fitz_point = self._fitz.Point(float(point[0]), float(point[1]))
            annotation = pdf_page.add_text_annot(fitz_point, clean_text)
            normalized_color = self._normalize_color(color)
            annotation.set_colors(stroke=normalized_color)
            annotation.update()
            return Annotation(
                page_index=page,
                kind=AnnotationKind.TEXT_NOTE,
                content=clean_text,
                color=normalized_color,
                point=(float(point[0]), float(point[1])),
            )
        except PdfServiceError:
            raise
        except Exception as exc:
            raise PdfAnnotationError(f"Não foi possível adicionar a nota: {exc}") from exc

    def save(self, session: PdfSession) -> Path:
        """Salva em arquivo temporário e substitui o PDF original com segurança.

        O documento é fechado antes do replace para funcionar também no Windows.
        Em caso de falha na substituição, tenta reabrir o arquivo original.
        """
        self._ensure_open(session)
        source_path = session.path
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f".{source_path.stem}_", suffix=".pdf", dir=str(source_path.parent)
        )
        os.close(temp_fd)
        temp_path = Path(temp_name)
        temp_path.unlink(missing_ok=True)  # PyMuPDF não sobrescreve destinos existentes.
        document = session.document
        try:
            document.save(str(temp_path), garbage=4, deflate=True)
            document.close()
            session.document = None
            os.replace(temp_path, source_path)
            session.document = self._fitz.open(str(source_path))
            return source_path
        except Exception as exc:
            try:
                if session.document is None:
                    session.document = self._fitz.open(str(source_path))
            except Exception:
                session.document = None
            raise PdfSaveError(f"Não foi possível salvar o PDF: {exc}") from exc
        finally:
            temp_path.unlink(missing_ok=True)

    def close(self, session: PdfSession) -> None:
        if session.document is not None:
            try:
                session.document.close()
            finally:
                session.document = None

    def _ensure_open(self, session: PdfSession) -> None:
        if session is None or session.document is None or session.document.is_closed:
            raise PdfServiceError("Não há um PDF aberto.")

    def _get_page(self, session: PdfSession, page: int):
        self._ensure_open(session)
        if page < 0 or page >= session.document.page_count:
            raise PdfServiceError("O número da página está fora do intervalo do PDF.")
        return session.document.load_page(page)

    @staticmethod
    def _normalize_color(color: tuple[float, float, float]) -> tuple[float, float, float]:
        if len(color) != 3:
            raise ValueError("A cor deve possuir três componentes RGB.")
        values = tuple(float(component) for component in color)
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("Os componentes RGB devem estar entre 0 e 1.")
        return values  # type: ignore[return-value]
