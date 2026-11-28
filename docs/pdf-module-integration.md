# Integração do módulo de PDF

O módulo foi preparado para ser encaixado na estrutura atual do repositório, sem modificar `MainWindow` ou arquivos dos demais integrantes.

## Arquivos

- `domain/models/pdf_document.py`: estado do PDF aberto.
- `domain/models/annotation.py`: modelo de anotação.
- `domain/models/pdf_geometry.py`: conversão de coordenadas de tela para coordenadas nativas da página.
- `domain/interfaces/pdf_repository.py`: contrato da infraestrutura.
- `infrastructure/pdf/pymupdf_service.py`: implementação com PyMuPDF.
- `application/pdf_controller.py`: coordenação dos casos de uso e sinais Qt.
- `presentation/widgets/pdf_viewer_widget.py`: interface visual do leitor.

## Dependências

No ambiente virtual do projeto:

```bash
pip install -r requirements-pdf.txt
```

A equipe deve incorporar `PySide6` e `PyMuPDF` ao arquivo de dependências central quando ele for criado.

## Conexão com a MainWindow

O `MainWindow` atual já possui `set_pdf_viewer_widget()` e `show_pdf_panel()`. O integrador pode conectar os componentes assim (ajuste o import ao ponto de composição da aplicação):

```python
from PySide6.QtWidgets import QMessageBox

from application.pdf_controller import PdfController
from infrastructure.pdf.pymupdf_service import PyMuPdfService
from presentation.widgets.pdf_viewer_widget import PDFViewerWidget

pdf_controller = PdfController(PyMuPdfService(), main_window)
pdf_viewer = PDFViewerWidget(main_window)
main_window.set_pdf_viewer_widget(pdf_viewer)


def show_error(title: str, error: Exception) -> None:
    QMessageBox.warning(main_window, title, str(error))


def open_pdf(path) -> None:
    current_document = pdf_controller.document
    if current_document and current_document.is_modified:
        answer = QMessageBox.question(
            main_window,
            "Anotações não salvas",
            "O PDF atual tem alterações. Deseja salvá-las antes de abrir outro?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Cancel:
            return
        if answer == QMessageBox.Save:
            try:
                pdf_controller.save_pdf()
            except Exception as error:
                show_error("Não foi possível salvar", error)
                return
        else:
            pdf_controller.close_pdf(discard_changes=True)
    try:
        pdf_controller.open_pdf(path)
        main_window.show_pdf_panel()
    except Exception as error:
        show_error("Não foi possível abrir o PDF", error)


def render_page(page_index: int) -> None:
    try:
        pdf_controller.render_page(page_index)
    except Exception as error:
        pdf_viewer.show_error(str(error))


def render_page_at_zoom(page_index: int, scale: float) -> None:
    try:
        pdf_controller.render_page(page_index, scale)
    except Exception as error:
        pdf_viewer.show_error(str(error))


def save_pdf() -> None:
    try:
        pdf_controller.save_pdf()
    except Exception as error:
        show_error("Não foi possível salvar", error)


def add_highlight(page, rects, color) -> None:
    try:
        pdf_controller.highlight(page, rects, color)
    except Exception as error:
        pdf_viewer.show_error(str(error))


def add_note(page, point, text) -> None:
    try:
        pdf_controller.add_note(page, point, text)
    except Exception as error:
        pdf_viewer.show_error(str(error))


def close_pdf() -> None:
    document = pdf_controller.document
    if document and document.is_modified:
        answer = QMessageBox.question(
            main_window,
            "Anotações não salvas",
            "Deseja salvar as anotações antes de fechar o PDF?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Cancel:
            return
        if answer == QMessageBox.Save:
            try:
                pdf_controller.save_pdf()
            except Exception as error:
                show_error("Não foi possível salvar", error)
                return
        else:
            pdf_controller.close_pdf(discard_changes=True)
            main_window.hide_pdf_panel()
            return
    try:
        pdf_controller.close_pdf()
        main_window.hide_pdf_panel()
    except Exception as error:
        show_error("Não foi possível fechar o PDF", error)


pdf_controller.pdf_opened.connect(pdf_viewer.set_document)
pdf_controller.page_rendered.connect(
    lambda page, image: (
        pdf_viewer.set_page_geometry(
            pdf_controller.get_page_geometry(page), pdf_controller.document.zoom
        ),
        pdf_viewer.display_page(page, image),
    )
)
pdf_controller.pdf_modified.connect(lambda: pdf_viewer.set_modified(True))
pdf_controller.pdf_saved.connect(pdf_viewer.set_saved)
pdf_controller.pdf_closed.connect(pdf_viewer.clear_document)

pdf_viewer.page_change_requested.connect(render_page)
pdf_viewer.zoom_change_requested.connect(
    lambda scale: render_page_at_zoom(pdf_controller.document.current_page, scale)
)
pdf_viewer.highlight_requested.connect(add_highlight)
pdf_viewer.note_requested.connect(add_note)
pdf_viewer.save_requested.connect(save_pdf)
pdf_viewer.close_requested.connect(close_pdf)

# Integração com o explorador do integrante responsável pela interface:
# file_explorer.pdf_open_requested.connect(open_pdf)
```

Conecte o sinal `FileExplorerWidget.pdf_open_requested(path)` à função `open_pdf(path)`. Não abra o arquivo diretamente no explorador.

## Decisões do MVP

- Um PDF aberto por vez.
- Páginas indexadas internamente a partir de zero.
- Zoom entre 50% e 300%.
- Seleção de grifo por arraste retangular. O retângulo é convertido para coordenadas PDF considerando escala e rotação da página.
- Nota textual por clique no local desejado e preenchimento de diálogo.
- Grifos e notas ficam gravados no próprio PDF.
- PDFs protegidos por senha são recusados nesta primeira versão.
- A abertura/fechamento de outro PDF é bloqueada quando existem anotações pendentes, evitando perda silenciosa.

## Testes

A partir da raiz deste pacote, com `src` no `PYTHONPATH`:

```bash
PYTHONPATH=src pytest -q
```

Os testes unitários exercitam renderização PNG, criação de grifo e nota, salvamento, reabertura e conversão de coordenadas.
