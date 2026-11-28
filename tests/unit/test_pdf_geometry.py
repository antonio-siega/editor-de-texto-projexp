from domain.models.pdf_geometry import PageGeometry, view_point_to_pdf, view_rect_to_pdf


def test_view_point_applies_scale_and_identity_matrix():
    geometry = PageGeometry(600, 800, 0, (1, 0, 0, 1, 0, 0))
    assert view_point_to_pdf((125, 250), 2.5, geometry) == (50, 100)


def test_view_rect_normalizes_coordinates_and_applies_scale():
    geometry = PageGeometry(600, 800, 0, (1, 0, 0, 1, 0, 0))
    result = view_rect_to_pdf((100, 80, 20, 30), 2, geometry)
    assert result == (10, 15, 50, 40)


def test_view_point_applies_derotation_translation():
    geometry = PageGeometry(300, 200, 90, (0, -1, 1, 0, 0, 300))
    assert view_point_to_pdf((20, 40), 1, geometry) == (40, 280)
