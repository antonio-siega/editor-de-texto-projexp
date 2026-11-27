import PySide6.QtWidgets as qt
import sys
import presentation.windows.main_window as mw

app = qt.QApplication(sys.argv)

janela = mw.MainWindow()
janela.show()
sys.exit(app.exec())