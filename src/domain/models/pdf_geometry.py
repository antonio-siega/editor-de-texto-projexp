"""Geometria independente de Qt/PyMuPDF para mapear seleções à página PDF."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

Point: TypeAlias = tuple[float, float]
Rect: TypeAlias = tuple[float, float, float, float]
AffineMatrix: TypeAlias = tuple[float, float, float, float, float, float]


@dataclass(frozen=True, slots=True)
class PageGeometry:
    """Geometria da página como ela aparece na tela e matriz de desrotação.

    width/height são dimensões em pontos PDF já considerando a rotação visual.
    derotation_matrix transforma coordenadas visuais em coordenadas nativas.
    """

    width: float
    height: float
    rotation: int
    derotation_matrix: AffineMatrix


def transform_point(point: Point, matrix: AffineMatrix) -> Point:
    """Aplica uma matriz afim no formato usado pelo PyMuPDF."""
    x, y = point
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)


def view_point_to_pdf(point_px: Point, scale: float, geometry: PageGeometry) -> Point:
    """Converte um ponto em pixels do raster para coordenadas nativas do PDF."""
    if scale <= 0:
        raise ValueError("A escala de renderização deve ser maior que zero.")
    point_in_display_space = (point_px[0] / scale, point_px[1] / scale)
    return transform_point(point_in_display_space, geometry.derotation_matrix)


def view_rect_to_pdf(rect_px: Rect, scale: float, geometry: PageGeometry) -> Rect:
    """Converte um retângulo da tela para o menor retângulo PDF que o contém.

    Os quatro vértices são transformados para que a operação também funcione
    quando a página possui rotação de 90, 180 ou 270 graus.
    """
    x0, y0, x1, y1 = rect_px
    left, right = sorted((x0, x1))
    top, bottom = sorted((y0, y1))
    corners = (
        view_point_to_pdf((left, top), scale, geometry),
        view_point_to_pdf((right, top), scale, geometry),
        view_point_to_pdf((left, bottom), scale, geometry),
        view_point_to_pdf((right, bottom), scale, geometry),
    )
    xs = [point[0] for point in corners]
    ys = [point[1] for point in corners]
    return (min(xs), min(ys), max(xs), max(ys))
