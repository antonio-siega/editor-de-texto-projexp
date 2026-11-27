# Módulo PDF — Editor de Texto Acadêmico

Este pacote contém arquivos novos para a Frente PDF. Foi organizado para ser extraído na raiz do repositório do projeto, sem sobrescrever o `README.md` existente.

## O que está incluído

- Visualizador PySide6 com navegação por página e zoom de 50% a 300%.
- Seleção retangular por arraste e grifo persistente.
- Inserção de nota textual por clique na página.
- Serviço PyMuPDF para abrir, renderizar, anotar, salvar e fechar PDFs.
- Controlador com sinais Qt e proteção contra descarte acidental de anotações não salvas.
- Conversão de coordenadas levando em conta zoom e rotação da página.
- Testes unitários para renderização, anotações, salvamento, reabertura e geometria.
- Guia de integração com a `MainWindow` que já existe no repositório.

## Instalação

```bash
pip install -r requirements-pdf.txt
```

## Testes

Executar na raiz do projeto, depois de extrair o pacote:

```bash
PYTHONPATH=src pytest -q tests/unit/test_pdf_geometry.py tests/unit/test_pymupdf_service.py
```

## Integração

Leia `docs/pdf-module-integration.md`. O guia mostra como conectar os sinais do `PDFViewerWidget` ao `PdfController` e como usar `MainWindow.set_pdf_viewer_widget()` e `MainWindow.show_pdf_panel()`.

## Limitações conhecidas desta primeira entrega

- A seleção para grifo é retangular, não uma seleção textual por palavras. Essa escolha foi necessária para entregar um fluxo funcional sem depender de seleção de texto complexa no raster.
- PDFs protegidos por senha são recusados.
- Só há uma sessão PDF aberta por vez.
- O visual do widget precisa ser executado e conferido em um ambiente com PySide6; nesta preparação, PySide6 não estava instalado. A camada de serviço PyMuPDF e a conversão geométrica foram testadas.
