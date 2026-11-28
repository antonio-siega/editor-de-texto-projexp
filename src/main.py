
import sys
import PySide6.QtWidgets as qt

import presentation.windows.main_window as mw
from presentation.windows.pdf_integration import PdfIntegration


app = qt.QApplication(sys.argv)

janela = mw.MainWindow()

# Integra o módulo de visualização de PDFs.
janela.pdf_integration = PdfIntegration(janela)

janela.show()

sys.exit(app.exec())
