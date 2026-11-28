from pathlib import Path

import fitz

from infrastructure.pdf.pymupdf_service import PyMuPdfService


def make_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 100), "Texto para teste de anotacao", fontsize=14)
    document.save(path)
    document.close()


def test_open_render_annotate_save_and_reopen(tmp_path: Path):
    pdf_path = tmp_path / "artigo.pdf"
    make_pdf(pdf_path)
    service = PyMuPdfService()
    session = service.open(pdf_path)

    assert service.page_count(session) == 1
    image = service.render_page(session, 0, 1.0)
    assert image.startswith(b"\x89PNG\r\n\x1a\n")

    page = session.document.load_page(0)
    text_rect = page.search_for("Texto para teste")
    assert text_rect
    service.add_highlight(session, 0, [tuple(text_rect[0])], (1.0, 0.9, 0.2))
    service.add_text_note(session, 0, (200, 200), "Revisar esta ideia")
    service.save(session)
    service.close(session)

    reopened = fitz.open(pdf_path)
    reopened_page = reopened[0]
    annotations = list(reopened_page.annots() or [])
    annotation_types = {annotation.type[1] for annotation in annotations}
    assert len(annotations) == 2
    assert annotation_types >= {"Highlight", "Text"}
    reopened.close()


def test_service_rejects_missing_file(tmp_path: Path):
    service = PyMuPdfService()
    try:
        service.open(tmp_path / "nao-existe.pdf")
    except Exception as exc:
        assert "não foi encontrado" in str(exc)
    else:
        raise AssertionError("Era esperado erro ao abrir arquivo inexistente")

def test_get_annotations_returns_saved_annotations(tmp_path: Path):
    pdf_path = tmp_path / "anotacoes.pdf"
    make_pdf(pdf_path)

    service = PyMuPdfService()
    session = service.open(pdf_path)

    page = session.document.load_page(0)
    text_rect = page.search_for("Texto para teste")

    service.add_highlight(
        session, 0, [tuple(text_rect[0])], (1.0, 0.9, 0.2)
    )
    service.add_text_note(
        session, 0, (200, 200), "Minha nota de teste"
    )

    service.save(session)

    annotations = service.get_annotations(session)

    assert len(annotations) == 2

    highlights = [
        item for item in annotations
        if item.kind.value == "HIGHLIGHT"
    ]

    notes = [
        item for item in annotations
        if item.kind.value == "TEXT_NOTE"
    ]

    assert len(highlights) == 1
    assert len(notes) == 1

    assert highlights[0].page_index == 0
    assert highlights[0].rects

    assert notes[0].page_index == 0
    assert notes[0].content == "Minha nota de teste"
    assert notes[0].point is not None

    service.close(session)