
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMessageBox

from application.pdf_controller import PdfController
from infrastructure.pdf.pymupdf_service import PyMuPdfService
from presentation.widgets.pdf_viewer_widget import PDFViewerWidget


class PdfIntegration:
    """Conecta o visualizador, o controlador e a janela principal."""

    def __init__(self, window):
        self.window = window

        # Instancia as camadas responsáveis pelo PDF.
        self.repository = PyMuPdfService()
        self.controller = PdfController(self.repository)
        self.viewer = PDFViewerWidget()

        # Substitui o painel provisório pelo visualizador real.
        self.window.set_pdf_viewer_widget(self.viewer)

        self._connect_signals()
        self._create_menu()

    def _connect_signals(self):
        # Interface -> controlador
        self.viewer.page_change_requested.connect(
            self._change_page
        )
        self.viewer.zoom_change_requested.connect(
            self._change_zoom
        )
        self.viewer.highlight_requested.connect(
            self._highlight
        )
        self.viewer.note_requested.connect(
            self._add_note
        )
        self.viewer.save_requested.connect(
            self._save_pdf
        )
        self.viewer.close_requested.connect(
            self._close_pdf
        )

        # Controlador -> interface
        self.controller.pdf_opened.connect(
            self.viewer.set_document
        )
        self.controller.page_rendered.connect(
            self._display_page
        )
        self.controller.pdf_modified.connect(
            lambda: self.viewer.set_modified(True)
        )
        self.controller.pdf_saved.connect(
            self.viewer.set_saved
        )
        self.controller.pdf_closed.connect(
            self._on_pdf_closed
        )

    def _create_menu(self):
        menu = self.window.menuBar().addMenu("&PDF")

        self.open_action = QAction("Abrir PDF...", self.window)
        self.open_action.setShortcut("Ctrl+Shift+O")
        self.open_action.triggered.connect(self._open_pdf)

        self.close_action = QAction("Fechar PDF", self.window)
        self.close_action.triggered.connect(self._close_pdf)
        self.close_action.setEnabled(False)

        menu.addAction(self.open_action)
        menu.addAction(self.close_action)

    def _open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Abrir arquivo PDF",
            "",
            "Arquivos PDF (*.pdf)"
        )

        if not path:
            return

        if not self._confirm_changes():
            return

        try:
            self.controller.open_pdf(Path(path))

            annotations = self.controller.get_annotations()
            self.viewer.set_annotations(annotations)

            self.window.show_pdf_panel()
            self.close_action.setEnabled(True)

        except Exception as error:
            self._show_error(str(error))

    def _display_page(self, page, image_bytes):
        try:
            geometry = self.controller.get_page_geometry(page)
            document = self.controller.document

            self.viewer.set_page_geometry(
                geometry,
                document.zoom
            )
            self.viewer.display_page(page, image_bytes)

        except Exception as error:
            self._show_error(str(error))

    def _change_page(self, page):
        try:
            self.controller.render_page(page)
        except Exception as error:
            self._show_error(str(error))

    def _change_zoom(self, scale):
        try:
            document = self.controller.document

            if document:
                self.controller.render_page(
                    document.current_page,
                    scale
                )
        except Exception as error:
            self._show_error(str(error))

    def _highlight(self, page, rects, color):
        try:
            self.controller.highlight(page, rects, color)
        except Exception as error:
            self._show_error(str(error))

    def _add_note(self, page, point, text):
        try:
            self.controller.add_note(page, point, text)
        except Exception as error:
            self._show_error(str(error))

    def _save_pdf(self):
        try:
            self.controller.save_pdf()
            return True
        except Exception as error:
            self._show_error(str(error))
            return False

    def _confirm_changes(self):
        document = self.controller.document

        if not document or not document.is_modified:
            return True

        choice = QMessageBox.question(
            self.window,
            "Alterações não salvas",
            "O PDF possui anotações não salvas. Deseja salvá-las?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )

        if choice == QMessageBox.Save:
            return self._save_pdf()

        if choice == QMessageBox.Discard:
            self.controller.close_pdf(discard_changes=True)
            return True

        return False

    def _close_pdf(self):
        if not self._confirm_changes():
            return

        if self.controller.document:
            self.controller.close_pdf()

    def _on_pdf_closed(self):
        self.viewer.clear_document()
        self.window.hide_pdf_panel()
        self.close_action.setEnabled(False)

    def _show_error(self, message):
        QMessageBox.critical(
            self.window,
            "Erro no visualizador de PDF",
            message
        )
