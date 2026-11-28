"""Modelo simples de anotação criada pelo usuário."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .pdf_geometry import Point, Rect


class AnnotationKind(str, Enum):
    HIGHLIGHT = "HIGHLIGHT"
    TEXT_NOTE = "TEXT_NOTE"


@dataclass(frozen=True, slots=True)
class Annotation:
    page_index: int
    kind: AnnotationKind
    rects: tuple[Rect, ...] = ()
    content: str | None = None
    color: tuple[float, float, float] = (1.0, 0.9, 0.2)
    point: Point | None = None
