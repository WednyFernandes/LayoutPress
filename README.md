## Impositor App

Ferramenta GUI para imposição de páginas (pré-visualização e exportação para PDF) construída com Python, PySide6, Pillow, PyMuPDF (fitz) e ReportLab.

Este repositório contém a aplicação de desktop utilizada para gerar imposições simples a partir de um PDF (usa a primeira página como origem). O foco é oferecer uma pré-visualização WYSIWYG e exportar um PDF com sangria colorida para controle de produção.

## Conteúdo

- `main.py` — Interface gráfica (PySide6).
- `impositor.py` — Lógica de geração de pré-visualização e composição do PDF final (Pillow + ReportLab).
- `dark_theme.qss` — Folha de estilo opcional (tema escuro).
- `app_icon.ico` — Ícone usado ao empacotar o aplicativo.
- `impositor_app.spec` — Spec do PyInstaller para gerar o executável onefile com o QSS e o ícone incluídos.
- `scripts/generate_icon.py` — Script auxiliar para gerar `app_icon.ico` a partir de imagens geradas dinamicamente.

## Requisitos

- Python 3.10+ (testado com 3.13)
- Dependências listadas no `requirements.txt` (instale em um virtualenv):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

Principais bibliotecas:
- PySide6
- Pillow
- PyMuPDF (fitz)
- reportlab
- pyinstaller (para empacotamento)

## Uso durante desenvolvimento

1. Ative seu ambiente virtual e instale as dependências.
2. Rode a GUI diretamente com:

```powershell
python main.py
```

3. Abra um PDF a partir da aba `Arquivo` e ajuste os parâmetros de imposição na aba `Imposição`. A pré-visualização será atualizada automaticamente.

## Gerar o executável (Windows - onefile)

O repositório já inclui um `impositor_app.spec` preparado para incluir `dark_theme.qss` e `app_icon.ico`. Para gerar o executável:

```powershell
# dentro do diretório do projeto
pyinstaller --clean impostor_app.spec
```

Se preferir a linha de comando sem usar o spec:

```powershell
pyinstaller --onefile --windowed --add-data "dark_theme.qss;." --add-data "app_icon.ico;." --icon app_icon.ico main.py
```

Observações:
- O modo onefile embala os arquivos de dados dentro do executável e os extrai para uma pasta temporária em tempo de execução (`sys._MEIPASS`). O código do aplicativo já tenta carregar `dark_theme.qss` tanto do diretório local quanto do bundle extraído.
- Se o tema não for carregado ao executar o EXE, verifique se `dark_theme.qss` foi incluído no bundle (procure por mensagens `Appending 'datas' from .spec` no log do PyInstaller) ou reexecute o PyInstaller com `--add-data` conforme o exemplo acima.

## Desenvolvimento e testes rápidos

- Para rodar um teste rápido de geração de preview sem abrir a GUI, edite o ficheiro `impositor.py` para chamar funções de teste no final do arquivo ou use um pequeno script que importe `Impositor` e execute `generate_preview()` com uma imagem de exemplo.

## Contribuição

Contribuições são bem-vindas. Para enviar mudanças:

1. Fork o repositório.
2. Crie uma branch para sua feature/bugfix.
3. Envie um Pull Request com descrição clara do que foi alterado.

## Licença

Coloque a licença do projeto aqui (por exemplo, MIT) se aplicável.

---

Se precisar que eu gere o executável final (`dist\impositor_app.exe`) agora eu posso rodar o PyInstaller neste ambiente e reportar o resultado (tamanho do EXE, logs e se o `dark_theme.qss` e o `app_icon.ico` foram incluídos corretamente). Diga quando posso prosseguir.