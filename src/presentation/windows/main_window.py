"""Janela principal: estrutura base para os demais módulos da interface.

Contém apenas layout, menus e barra de status. Não possui lógica de
documento, PDF ou configurações; os demais membros plugam seus widgets
e conectam as ações expostas.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QLabel, QMainWindow, QSplitter, QWidget

applicationTitle = "Editor de Texto Acadêmico"


def create_placeholder(text: str) -> QLabel:
    """Cria um painel provisório até o widget real ser plugado."""
    placeholder = QLabel(text)
    placeholder.setAlignment(Qt.AlignCenter)
    placeholder.setFrameShape(QLabel.StyledPanel)
    return placeholder


class MainWindow(QMainWindow):
    """Janela com explorador, editor e painel PDF em splitters redimensionáveis."""

    explorerIndex = 0
    workAreaIndex = 1
    editorIndex = 0
    pdfViewerIndex = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.closeValidators = []

        self.build_layout()
        self.build_menus()
        self.statusBar()  # barra de status padrão do Qt
        self.setWindowTitle(applicationTitle)
        self.setMinimumSize(900, 600)
        self.resize(1280, 800)

    # ---------- construção ----------

    def build_layout(self):
        # Editor e PDF lado a lado; o painel PDF começa oculto
        self.workAreaSplitter = QSplitter(Qt.Horizontal)
        self.workAreaSplitter.setChildrenCollapsible(False)
        self.workAreaSplitter.addWidget(create_placeholder("Editor de texto"))
        self.workAreaSplitter.addWidget(create_placeholder("Visualizador de PDF"))
        self.workAreaSplitter.widget(self.pdfViewerIndex).hide()

        # Explorador à esquerda, área de trabalho à direita
        self.mainSplitter = QSplitter(Qt.Horizontal)
        self.mainSplitter.setChildrenCollapsible(False)
        self.mainSplitter.addWidget(create_placeholder("Explorador de arquivos"))
        self.mainSplitter.addWidget(self.workAreaSplitter)
        self.mainSplitter.setStretchFactor(self.explorerIndex, 0)
        self.mainSplitter.setStretchFactor(self.workAreaIndex, 1)
        self.mainSplitter.setSizes([260, 1020])

        self.setCentralWidget(self.mainSplitter)

    def build_menus(self):
        # Ações públicas: os demais módulos conectam em triggered
        self.newAction = self.create_action("&Novo", QKeySequence.New)
        self.openAction = self.create_action("&Abrir...", QKeySequence.Open)
        self.saveAction = self.create_action("&Salvar", QKeySequence.Save)
        self.saveAsAction = self.create_action("Salvar &como...", QKeySequence.SaveAs)
        self.savePdfAction = self.create_action("Salvar &PDF", "Ctrl+Alt+S")
        self.savePdfAction.setEnabled(False)
        self.quitAction = self.create_action("S&air", QKeySequence.Quit)
        self.quitAction.triggered.connect(self.close)
        self.toggleThemeAction = self.create_action("Alternar &tema", "Ctrl+Shift+T")

        fileMenu = self.menuBar().addMenu("&Arquivo")
        fileMenu.addActions([self.newAction, self.openAction, self.saveAction, self.saveAsAction])
        fileMenu.addSeparator()
        fileMenu.addAction(self.savePdfAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.quitAction)

        viewMenu = self.menuBar().addMenu("E&xibir")
        viewMenu.addAction(self.toggleThemeAction)

    def create_action(self, text: str, shortcut=None) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        return action

    # ---------- pontos de integração ----------

    def replace_panel(self, splitter: QSplitter, index: int, newWidget: QWidget):
        """Troca o widget do painel mantendo posição e visibilidade."""
        oldWidget = splitter.replaceWidget(index, newWidget)
        newWidget.setVisible(oldWidget.isVisible())
        oldWidget.deleteLater()

    def set_explorer_widget(self, explorerWidget: QWidget):
        self.replace_panel(self.mainSplitter, self.explorerIndex, explorerWidget)

    def set_editor_widget(self, editorWidget: QWidget):
        self.replace_panel(self.workAreaSplitter, self.editorIndex, editorWidget)

    def set_pdf_viewer_widget(self, pdfViewerWidget: QWidget):
        self.replace_panel(self.workAreaSplitter, self.pdfViewerIndex, pdfViewerWidget)

    def show_pdf_panel(self):
        pdfPanel = self.workAreaSplitter.widget(self.pdfViewerIndex)
        if pdfPanel.isVisible():
            return
        pdfPanel.show()
        halfWidth = self.workAreaSplitter.width() // 2
        self.workAreaSplitter.setSizes([halfWidth, halfWidth])

    def hide_pdf_panel(self):
        self.workAreaSplitter.widget(self.pdfViewerIndex).hide()

    def update_window_title(self, documentName: str | None = None, isModified: bool = False):
        if not documentName:
            self.setWindowTitle(applicationTitle)
            return
        modifiedMark = "*" if isModified else ""
        self.setWindowTitle(f"{documentName}{modifiedMark} - {applicationTitle}")

    def add_close_validator(self, validator):
        """Registra uma função sem argumentos; retornar False cancela o fechamento."""
        self.closeValidators.append(validator)

    def closeEvent(self, event):
        if all(validator() for validator in self.closeValidators):
            event.accept()
        else:
            event.ignore()