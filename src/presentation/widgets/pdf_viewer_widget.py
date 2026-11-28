"""Widget PySide6 para visualização, navegação e anotação de PDFs."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractSpinBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QToolButton, QVBoxLayout,
    QWidget, QInputDialog, QSizePolicy, QListWidget, QListWidgetItem,
    QTextBrowser, QSplitter,
)

from domain.models.pdf_document import PdfDocument
from domain.models.pdf_geometry import PageGeometry, Rect, view_rect_to_pdf, view_point_to_pdf
from domain.models.annotation import Annotation, AnnotationKind

class PdfPageCanvas(QLabel):
    """Canvas com seleção retangular por arraste e captura de clique para notas."""

    selection_completed = Signal(object)  # Rect em pixels do raster
    point_clicked = Signal(object)         # Point em pixels do raster

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._drag_start = None
        self._rubber_band = None
        self.note_mode = False

    def set_image(self, pixmap: QPixmap) -> None:
        self.setPixmap(pixmap)
        self.resize(pixmap.size())
        self.updateGeometry()

    def clear_selection(self) -> None:
        if self._rubber_band:
            self._rubber_band.hide()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.pixmap() is not None:
            self._drag_start = event.position().toPoint()
            if self.note_mode:
                return
            if self._rubber_band is None:
                from PySide6.QtWidgets import QRubberBand
                self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
            self._rubber_band.setGeometry(QRect(self._drag_start, self._drag_start))
            self._rubber_band.show()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is not None and not self.note_mode and self._rubber_band:
            current = event.position().toPoint()
            self._rubber_band.setGeometry(QRect(self._drag_start, current).normalized())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._drag_start is not None:
            end = event.position().toPoint()
            start = self._drag_start
            self._drag_start = None
            if self.note_mode:
                if self._rubber_band:
                    self._rubber_band.hide()
                self.point_clicked.emit((float(end.x()), float(end.y())))
            else:
                rect = QRect(start, end).normalized()
                if rect.width() >= 4 and rect.height() >= 4:
                    self.selection_completed.emit((
                        float(rect.left()), float(rect.top()),
                        float(rect.right()), float(rect.bottom()),
                    ))
                elif self._rubber_band:
                    self._rubber_band.hide()
        super().mouseReleaseEvent(event)


class PDFViewerWidget(QWidget):
    """Widget de apresentação; não importa nem manipula objetos do PyMuPDF."""

    page_change_requested = Signal(int)
    zoom_change_requested = Signal(float)
    highlight_requested = Signal(int, object, object)  # page, rects PDF, RGB
    note_requested = Signal(int, object, str)           # page, point PDF, texto
    save_requested = Signal()
    close_requested = Signal()

    HIGHLIGHT_COLOR = (1.0, 0.88, 0.20)
    NOTE_COLOR = (1.0, 0.82, 0.20)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._document: PdfDocument | None = None
        self._current_page = 0
        self._scale = 1.25
        self._geometry: PageGeometry | None = None
        self._selection_rects: list[Rect] = []
        self._annotations: list[Annotation] = []
        self._build_ui()
        self._set_document_controls_enabled(False)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        self.title_label = QLabel("Leitor de PDF")
        self.title_label.setObjectName("pdfTitle")
        self.title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        self.status_label = QLabel("Nenhum PDF aberto")
        self.status_label.setStyleSheet("color: #64748b; font-size: 11px;")
        self.save_button = QPushButton("Salvar anotações")
        self.save_button.clicked.connect(self.save_requested.emit)
        self.close_button = QToolButton()
        self.close_button.setText("×")
        self.close_button.setToolTip("Fechar PDF")
        self.close_button.clicked.connect(self.close_requested.emit)
        header.addWidget(self.title_label)
        header.addWidget(self.status_label, 1)
        header.addWidget(self.save_button)
        header.addWidget(self.close_button)
        header_widget = QWidget()
        header_widget.setLayout(header)
        header_widget.setStyleSheet("background: palette(base); border-bottom: 1px solid palette(mid);")
        root.addWidget(header_widget)

        tools = QHBoxLayout()
        self.previous_button = QToolButton()
        self.previous_button.setText("‹")
        self.previous_button.setToolTip("Página anterior")
        self.previous_button.clicked.connect(self._go_previous)
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.page_spin.setFixedWidth(66)
        self.page_spin.valueChanged.connect(self._page_spin_changed)
        self.page_total_label = QLabel("/ 0")
        self.next_button = QToolButton()
        self.next_button.setText("›")
        self.next_button.setToolTip("Próxima página")
        self.next_button.clicked.connect(self._go_next)

        self.zoom_out_button = QToolButton()
        self.zoom_out_button.setText("−")
        self.zoom_out_button.setToolTip("Diminuir zoom")
        self.zoom_out_button.clicked.connect(lambda: self._change_zoom(-0.1))
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(50, 300)
        self.zoom_spin.setSingleStep(10)
        self.zoom_spin.setSuffix("%")
        self.zoom_spin.setValue(125)
        self.zoom_spin.setFixedWidth(82)
        self.zoom_spin.valueChanged.connect(lambda value: self.zoom_change_requested.emit(value / 100))
        self.zoom_in_button = QToolButton()
        self.zoom_in_button.setText("+")
        self.zoom_in_button.setToolTip("Aumentar zoom")
        self.zoom_in_button.clicked.connect(lambda: self._change_zoom(0.1))

        self.highlight_button = QPushButton("Grifar seleção")
        self.highlight_button.setToolTip("Arraste sobre uma área do PDF e clique para grifar")
        self.highlight_button.clicked.connect(self._emit_highlight)
        self.note_button = QPushButton("Adicionar nota")
        self.note_button.setCheckable(True)
        self.note_button.setToolTip("Ative e clique no PDF para inserir um comentário")
        self.note_button.toggled.connect(self._set_note_mode)

        self.annotations_toggle_button = QToolButton()
        self.annotations_toggle_button.setText("Anotações")
        self.annotations_toggle_button.setCheckable(True)
        self.annotations_toggle_button.setToolTip(
            "Mostrar ou ocultar o painel de anotações"
        )
        self.annotations_toggle_button.toggled.connect(
            self._toggle_annotations_panel
        )

        tools.addWidget(self.previous_button)
        tools.addWidget(self.page_spin)
        tools.addWidget(self.page_total_label)
        tools.addWidget(self.next_button)
        tools.addSpacing(14)
        tools.addWidget(self.zoom_out_button)
        tools.addWidget(self.zoom_spin)
        tools.addWidget(self.zoom_in_button)
        tools.addStretch(1)
        tools.addWidget(self.highlight_button)
        tools.addWidget(self.note_button)
        tools.addWidget(self.annotations_toggle_button)
        toolbar = QWidget()
        toolbar.setLayout(tools)
        toolbar.setStyleSheet("padding: 5px 8px; border-bottom: 1px solid palette(mid);")
        root.addWidget(toolbar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: #e9edf4; }")
        self.canvas = PdfPageCanvas()
        self.canvas.setText("Abra um PDF pelo explorador de arquivos.")
        self.canvas.setStyleSheet("QLabel { background: white; color: #64748b; }")
        self.canvas.selection_completed.connect(self._on_selection_completed)
        self.canvas.point_clicked.connect(self._on_canvas_clicked)
        self.scroll_area.setWidget(self.canvas)

        # Área central redimensionável: página do PDF e anotações.
        self.content_splitter = QSplitter(Qt.Horizontal)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.addWidget(self.scroll_area)
        self.content_splitter.setStretchFactor(0, 1)

        self.annotations_panel = QWidget()
        self.annotations_panel.setMinimumWidth(240)
        annotations_layout = QVBoxLayout(self.annotations_panel)
        annotations_layout.setContentsMargins(10, 8, 10, 8)
        annotations_layout.setSpacing(8)

        self.annotations_title = QLabel("Anotações (0)")
        self.annotations_title.setStyleSheet(
            "font-weight: 600; font-size: 13px;"
        )
        self.annotation_list = QListWidget()
        self.annotation_list.setWordWrap(True)
        self.annotation_list.setSpacing(3)
        self.annotation_list.setStyleSheet(
            "QListWidget { border: none; }"
            "QListWidget::item { padding: 7px; }"
            "QListWidget::item:selected { background: palette(highlight); "
            "color: palette(highlighted-text); }"
        )
        self.annotation_list.itemClicked.connect(
            self._on_annotation_clicked
        )

        self.annotation_detail_title = QLabel("Conteúdo da anotação")
        self.annotation_detail_title.setStyleSheet(
            "font-weight: 600; font-size: 12px; margin-top: 6px;"
        )
        self.annotation_detail = QTextBrowser()
        self.annotation_detail.setOpenExternalLinks(False)
        self.annotation_detail.setPlaceholderText(
            "Selecione uma anotação para visualizar seu conteúdo."
        )
        self.annotation_detail.setPlainText(
            "Selecione uma anotação na lista acima."
        )

        annotations_layout.addWidget(self.annotations_title)
        annotations_layout.addWidget(self.annotation_list, 2)
        annotations_layout.addWidget(self.annotation_detail_title)
        annotations_layout.addWidget(self.annotation_detail, 3)
        self.annotations_panel.setStyleSheet(
            "background: palette(base); "
            "border-left: 1px solid palette(mid);"
        )
        self.content_splitter.addWidget(self.annotations_panel)
        self.content_splitter.setStretchFactor(1, 0)
        self.content_splitter.setSizes([780, 300])
        self.annotations_panel.hide()

        root.addWidget(self.content_splitter, 1)

        self.footer_label = QLabel("Selecione um PDF para começar a leitura.")
        self.footer_label.setStyleSheet("padding: 5px 9px; color: #64748b; font-size: 11px;")
        root.addWidget(self.footer_label)

        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        save_shortcut.activated.connect(self.save_requested.emit)

    def _toggle_annotations_panel(self, visible: bool) -> None:
        """Mostra ou recolhe o painel lateral de anotações."""
        if visible:
            self.annotations_panel.show()
            total_width = max(600, self.content_splitter.width())
            self.content_splitter.setSizes([
                max(300, total_width - 300),
                300,
            ])
        else:
            self.annotations_panel.hide()

    def set_annotations(self, annotations: list[Annotation]) -> None:
        """Atualiza a lista lateral sem perder o conteúdo completo das notas."""
        self._annotations = list(annotations)
        self.annotation_list.clear()
        self.annotation_detail.setPlainText(
            "Selecione uma anotação na lista acima."
        )

        for index, annotation in enumerate(self._annotations):
            page_number = annotation.page_index + 1

            if annotation.kind == AnnotationKind.TEXT_NOTE:
                label = f"📝 Nota — Página {page_number}"
            elif annotation.kind == AnnotationKind.HIGHLIGHT:
                label = f"🖍️ Destaque — Página {page_number}"
            else:
                continue

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, index)
            if annotation.content:
                item.setToolTip(annotation.content)
            self.annotation_list.addItem(item)

        self.annotations_title.setText(
            f"Anotações ({self.annotation_list.count()})"
        )

    def _on_annotation_clicked(self, item: QListWidgetItem) -> None:
        """Exibe o conteúdo completo e navega até a página da anotação."""
        index = item.data(Qt.UserRole)
        if index is None or not (0 <= int(index) < len(self._annotations)):
            return

        annotation = self._annotations[int(index)]
        if annotation.kind == AnnotationKind.TEXT_NOTE:
            self.annotation_detail.setPlainText(
                annotation.content or "Esta nota não possui texto."
            )
            self.annotation_detail_title.setText("Texto da nota")
        elif annotation.kind == AnnotationKind.HIGHLIGHT:
            self.annotation_detail.setPlainText(
                "Destaque de texto\n"
                f"Página {annotation.page_index + 1}"
            )
            self.annotation_detail_title.setText("Detalhes do destaque")

        self.page_change_requested.emit(annotation.page_index)

    def set_document(self, document: PdfDocument) -> None:
        self._document = document
        self._current_page = document.current_page
        self._scale = document.zoom
        self.title_label.setText(document.title)
        self.status_label.setText(f"{document.page_count} páginas")
        self.page_spin.blockSignals(True)
        self.page_spin.setRange(1, document.page_count)
        self.page_spin.setValue(document.current_page + 1)
        self.page_spin.blockSignals(False)
        self.page_total_label.setText(f"/ {document.page_count}")
        self.zoom_spin.blockSignals(True)
        self.zoom_spin.setValue(round(document.zoom * 100))
        self.zoom_spin.blockSignals(False)
        self._set_document_controls_enabled(True)
        self.footer_label.setText("Arraste sobre o conteúdo para selecionar uma área e grifar.")

    def set_page_geometry(self, geometry: PageGeometry, scale: float) -> None:
        self._geometry = geometry
        self._scale = scale

    def display_page(self, page: int, image_bytes: bytes) -> None:
        pixmap = QPixmap()
        if not pixmap.loadFromData(image_bytes, "PNG"):
            self.show_error("Não foi possível exibir a imagem da página PDF.")
            return
        self._current_page = page
        self._selection_rects.clear()
        self.highlight_button.setEnabled(False)
        self.canvas.clear_selection()
        self.canvas.set_image(pixmap)
        if self._document:
            self.page_spin.blockSignals(True)
            self.page_spin.setValue(page + 1)
            self.page_spin.blockSignals(False)
        self.footer_label.setText(f"Página {page + 1} • Zoom {round(self._scale * 100)}%")

    def set_modified(self, modified: bool) -> None:
        if modified:
            self.status_label.setText("Anotações não salvas")
            self.status_label.setStyleSheet("color: #b45309; font-size: 11px;")
        elif self._document:
            self.status_label.setText(f"{self._document.page_count} páginas • Salvo")
            self.status_label.setStyleSheet("color: #15803d; font-size: 11px;")

    def set_saved(self, path: str | Path) -> None:
        self.status_label.setText("Anotações salvas")
        self.status_label.setStyleSheet("color: #15803d; font-size: 11px;")
        self.footer_label.setText(f"PDF salvo em: {path}")

    def set_loading(self, loading: bool) -> None:
        if loading:
            self.footer_label.setText("Carregando página…")
            self.setEnabled(False)
        else:
            self.setEnabled(True)

    def show_error(self, message: str) -> None:
        self.footer_label.setText(message)
        self.footer_label.setStyleSheet("padding: 5px 9px; color: #b91c1c; font-size: 11px;")

    def clear_document(self) -> None:
        self._document = None
        self._geometry = None
        self._selection_rects.clear()
        self._annotations.clear()
        self.annotation_list.clear()
        self.annotations_title.setText("Anotações (0)")
        self.annotation_detail.setPlainText(
            "Selecione uma anotação na lista acima."
        )
        self.canvas.clear_selection()
        self.canvas.clear()
        self.canvas.setText("Abra um PDF pelo explorador de arquivos.")
        self.title_label.setText("Leitor de PDF")
        self.status_label.setText("Nenhum PDF aberto")
        self.page_total_label.setText("/ 0")
        self.footer_label.setText("Selecione um PDF para começar a leitura.")
        self.note_button.setChecked(False)
        self._set_document_controls_enabled(False)

    def _set_document_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.save_button, self.previous_button, self.page_spin, self.next_button,
            self.zoom_out_button, self.zoom_spin, self.zoom_in_button,
            self.highlight_button, self.note_button,
            self.annotations_toggle_button, self.close_button,
        ):
            widget.setEnabled(enabled)

    def _go_previous(self) -> None:
        if self._document and self._current_page > 0:
            self.page_change_requested.emit(self._current_page - 1)

    def _go_next(self) -> None:
        if self._document and self._current_page < self._document.page_count - 1:
            self.page_change_requested.emit(self._current_page + 1)

    def _page_spin_changed(self, value: int) -> None:
        self.page_change_requested.emit(value - 1)

    def _change_zoom(self, delta: float) -> None:
        value = max(0.5, min(3.0, self._scale + delta))
        self.zoom_spin.setValue(round(value * 100))

    def _on_selection_completed(self, rect_px: Rect) -> None:
        if not self._geometry:
            self.show_error("A geometria da página ainda não foi carregada.")
            return
        try:
            rect_pdf = view_rect_to_pdf(rect_px, self._scale, self._geometry)
        except ValueError as exc:
            self.show_error(str(exc))
            return
        self._selection_rects = [rect_pdf]
        self.highlight_button.setEnabled(True)
        self.footer_label.setText("Área selecionada. Clique em 'Grifar seleção' para salvar o destaque.")

    def _emit_highlight(self) -> None:
        if self._selection_rects:
            self.highlight_requested.emit(self._current_page, list(self._selection_rects), self.HIGHLIGHT_COLOR)
            self._selection_rects.clear()
            self.canvas.clear_selection()
            self.highlight_button.setEnabled(False)

    def _set_note_mode(self, enabled: bool) -> None:
        self.canvas.note_mode = enabled
        if enabled:
            self.canvas.clear_selection()
            self._selection_rects.clear()
            self.highlight_button.setEnabled(False)
            self.canvas.setCursor(Qt.CrossCursor)
            self.footer_label.setText("Clique no local do PDF em que deseja inserir a nota.")
        else:
            self.canvas.unsetCursor()
            self.footer_label.setText("Modo de seleção de área ativado.")

    def _on_canvas_clicked(self, point_px) -> None:
        if not self.canvas.note_mode or not self._geometry:
            return
        text, accepted = QInputDialog.getMultiLineText(
            self, "Nova anotação", "Comentário:", ""
        )
        if accepted and text.strip():
            point_pdf = view_point_to_pdf(point_px, self._scale, self._geometry)
            self.note_requested.emit(self._current_page, point_pdf, text.strip())
        self.note_button.setChecked(False)
