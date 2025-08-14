# Testes MarkItDown

Este diretório contém uma suite completa de testes para a biblioteca **MarkItDown** da Microsoft.

## Sobre o MarkItDown

MarkItDown é uma ferramenta Python que converte vários tipos de arquivos para Markdown, incluindo:

- 📄 **PDF** - Documentos PDF
- 📊 **Excel** - Planilhas (.xlsx, .xls)
- 📝 **Word** - Documentos (.docx)
- 🎨 **PowerPoint** - Apresentações (.pptx)
- 🖼️ **Imagens** - OCR e metadados EXIF
- 🎵 **Áudio** - Transcrição de fala
- 🌐 **HTML** - Páginas web
- 📋 **CSV/JSON/XML** - Formatos de dados
- 📦 **ZIP** - Arquivos compactados
- 🎬 **YouTube** - URLs de vídeos
- 📚 **EPub** - Livros eletrônicos

## Arquivos de Teste

### 🚀 `run_tests.py`
Script principal com menu interativo para executar todos os testes.

**Uso:**
```bash
# Modo interativo
python run_tests.py

# Executar todos os testes automaticamente
python run_tests.py --all
```

### 📋 `test_basic.py`
Testes básicos com formatos simples:
- Conversão HTML → Markdown
- Conversão CSV → Markdown  
- Conversão JSON → Markdown

### 🖼️ `test_images.py`
Testes de processamento de imagens:
- OCR (reconhecimento de texto)
- Extração de metadados EXIF
- Integração com LLM para descrição (requer OpenAI API)

### 📊 `test_office.py`
Testes com arquivos Microsoft Office:
- Excel (.xlsx) → Markdown
- Word (.docx) → Markdown
- URLs web → Markdown

### ⚡ `test_advanced.py`
Funcionalidades avançadas:
- Processamento via streaming
- Arquivos ZIP (múltiplos arquivos)
- XML estruturado
- Sistema de plugins

## Como Usar

1. **Instalar MarkItDown** (se ainda não instalou):
   ```bash
   pip install 'markitdown[all]'
   ```

2. **Navegar para o diretório**:
   ```bash
   cd "C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\Docs\Markitdown"
   ```

3. **Executar os testes**:
   ```bash
   python run_tests.py
   ```

## Dependências Opcionais

Para funcionalidades específicas, você pode precisar instalar:

```bash
# Para Excel
pip install pandas openpyxl

# Para Word
pip install python-docx

# Para imagens avançadas
pip install pillow

# Para OCR
pip install 'markitdown[all]'

# Para LLM com imagens
pip install openai
```

## Estrutura dos Arquivos de Saída

Os testes geram arquivos `.md` com prefixo `output_`:

- `output_html.md` - Conversão de HTML
- `output_csv.md` - Conversão de CSV
- `output_json.md` - Conversão de JSON
- `output_image.md` - Conversão de imagem
- `output_excel.md` - Conversão de Excel
- `output_word.md` - Conversão de Word
- `output_zip.md` - Conversão de ZIP
- `output_xml.md` - Conversão de XML
- E outros...

## Funcionalidades Testadas

### ✅ Conversões Básicas
- [x] HTML para Markdown
- [x] CSV para tabelas Markdown
- [x] JSON para estrutura legível

### ✅ Processamento de Imagens  
- [x] Criação de imagens de teste
- [x] OCR básico
- [x] Integração com LLM (opcional)

### ✅ Microsoft Office
- [x] Excel com múltiplas colunas
- [x] Word com formatação
- [x] URLs web dinâmicas

### ✅ Funcionalidades Avançadas
- [x] Streaming de dados
- [x] Arquivos ZIP multi-arquivo
- [x] XML estruturado
- [x] Sistema de plugins

## Exemplos de Uso

### Conversão Simples
```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("arquivo.pdf")
print(result.text_content)
```

### Com OpenAI para Imagens
```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")
result = md.convert("imagem.jpg")
```

### Streaming
```python
import io
from markitdown import MarkItDown

md = MarkItDown()
stream = io.BytesIO(content.encode('utf-8'))
result = md.convert_stream(stream, file_extension='.html')
```

## Resolução de Problemas

### Erro de OCR
Se o OCR não funcionar, instale dependências:
```bash
pip install 'markitdown[all]'
```

### Erro OpenAI
Para usar LLM com imagens, configure:
```bash
export OPENAI_API_KEY="sua_chave_aqui"
```

### Erro Office
Para arquivos Office, instale:
```bash
pip install 'markitdown[docx,xlsx,pptx]'
```

## Links Úteis

- 📚 [Repositório MarkItDown](https://github.com/microsoft/markitdown)
- 📖 [Documentação Oficial](https://github.com/microsoft/markitdown#readme)
- 🐍 [PyPI Package](https://pypi.org/project/markitdown/)

---

**Criado em:** 2025-07-09  
**Versão:** 1.0  
**Autor:** Teste MarkItDown
