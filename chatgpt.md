<!--Regras e contexto a serem incluídas no projeto do ChatGPT para PLANEJAMENTO do aplicativo-->

NÃO ESCREVA CÓDIGO A NÃO SER QUE EXPLICITAMENTE SOLICITADO.

# Descrição Geral

Este projeto objetiva criar um editor de texto voltado para a produção de textos acadêmicos, como TCCs, artigos científicos e resumos expandidos. A ideia é permitir que o usuário, na mesma tela, possa abrir um arquivo PDF que esteja estudando e um editor de texto, facilitando a transição entre arquivos de leitura e o arquivo em que o trabalho do usuário está sendo escrito. Será uma aplicação exclusivamente DESKTOP, com uma única tela, sendo esta um editor de texto.

# Requisitos Funcionais

Editor de texto. Possuirá ferramentas básicas de edição de texto, como alteração de fonte, tamanho de fonte, efeitos de fonte (itálico, negrito, sublinhado, tachado, entre outros) e opções de alinhamento de texto. Possuirá ferramenta de detecção automática de erros ortográficos (sugestões de mudança para o usuáiro através de highlighting de palavras que o programa pensa serem incorretas).

Explorador de arquivos lateral (como em programas como VSCode e Obsidian). Uma pasta específica será escolhida pelo usuário para servir como repositório de arquivos. Ao colocar arquivos PDF nessa pasta, eles ficarão visíveis através da lista do menu dentro do aplicativo. Clicando no nome de um arquivo na lista abre o pdf em uma janela fechável dentro do aplicativo, dividindo o espaço da tela do aplicativo com o editor de texto (algo como um modo "split screen"). Permitirá inserção de notas e grifo de palavras ou frases (ferramenta de highlighting) no documento PDF.

As janelas internas (como editor de texto e visualização de arquivos PDF) terão largura ajustável. Clicando e arrastando a aresta que as telas compartilham deverá aumentar ou diminuir o espaço de cada janela, a depender da direção para a qual a aresta for arrastada. Mesma funcionalidade vista em sites como o Overleaf.

A interface deverá ser minimalista, contando com modos claro e escuro. O usuário não deverá ser sobrecarregado por funcionalidades supérfluas; o objetivo é criar uma aplicação simples, rápida e eficiente.

# Restrições de escopo e tempo

Este trabalho deverá ser realizado com um escopo realista em mente. Apenas as funcionalidades essenciais serão incluídas, e um MVP deverá estar pronto até o dia 04 de dezembro de 2026.