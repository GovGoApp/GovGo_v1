# Sistema de Processamento de Relatórios PDF com Docling

Este sistema processa relatórios mensais em PDF, extrai os dados usando **Docling**, gera um resumo via OpenAI Assistant e insere o texto na área vazia da segunda página.

## Funcionalidades

✅ **Extração com Docling**: Usa Docling para extrair dados do PDF  
✅ **Identificação automática**: Localiza área vazia na segunda página  
✅ **Geração de resumo**: OpenAI Assistant cria resumo personalizado  
✅ **Inserção de texto**: Adiciona resumo no PDF em Arial 10  
✅ **Salvamento**: Gera novo arquivo com sufixo "_com_resumo"  

## Arquivos do Sistema

- **`monthly_report_processor.py`**: Classe principal com integração Docling
- **`test_processor.py`**: Script de teste
- **`requirements.txt`**: Dependências (inclui docling)
- **`.env.example`**: Exemplo de configuração
- **`README.md`**: Esta documentação

## Configuração

1. **Instalar dependências**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Configurar API Key**:
   ```powershell
   # Copie o arquivo de exemplo
   copy .env.example .env
   
   # Edite o arquivo .env e adicione sua chave da OpenAI
   OPENAI_API_KEY=sk-your-key-here
   ```

3. **Executar**:
   ```powershell
   python test_processor.py
   ```

## Como Usar

### Método 1: Script de teste interativo
```powershell
python test_processor.py
```

### Método 2: Importar na sua aplicação
```python
from monthly_report_processor import PDFReportProcessor

# Criar processador
processor = PDFReportProcessor()

# Processar relatório
pdf_path = "caminho/para/seu/relatorio.pdf"
user_prompt = "Destaque os principais indicadores financeiros"

result = processor.process_monthly_report(pdf_path, user_prompt)
print(f"Arquivo gerado: {result}")
```

## Exemplo de Uso

```
Digite o caminho completo do PDF: C:\Users\...\Relatório_Mensal_Junho_2025.pdf
Contexto: Destacar crescimento em vendas, novos projetos e perspectivas para julho
```

O sistema gerará um novo PDF com o sufixo `_com_resumo.pdf` contendo o resumo inserido.

## Estrutura do Resumo

O Assistant é configurado para gerar resumos com:
- Overview dos resultados principais
- Destaques positivos e conquistas  
- Desafios ou pontos de atenção
- Perspectivas e próximos passos
- Máximo de 300 palavras
- Formatação Arial 10 no PDF

## Requisitos

- Python 3.8+
- Chave da API OpenAI
- Arquivos PDF com estrutura de 2 páginas
- Espaço designado na parte inferior da segunda página
