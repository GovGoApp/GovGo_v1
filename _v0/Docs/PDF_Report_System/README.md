# 📊 Sistema de Processamento de Relatórios PDF com Resumo Automático

Sistema automatizado que analisa relatórios PDF mensais, extrai dados usando **Docling**, gera resumos executivos via **OpenAI Assistant** e insere o texto automaticamente na área vazia da segunda página do PDF.

## 🎯 Funcionalidades

✅ **Extração Inteligente**: Usa Docling para extrair texto, tabelas e reconhecer gráficos em PDF  
✅ **Detecção Automática**: Identifica automaticamente área vazia na segunda página  
✅ **IA Especializada**: OpenAI Assistant configurado para resumos executivos financeiros  
✅ **Inserção Precisa**: Adiciona resumo em Arial 10 com quebras de linha automáticas  
✅ **Processamento Completo**: Mantém formatação original e salva nova versão do PDF  

## 📁 Estrutura do Projeto

```
PDF_Report_System/
├── 📄 ASSISTANT_CONFIG.txt        # Configuração completa do OpenAI Assistant
├── 📄 pdf_report_processor.py     # Classe principal do sistema
├── 📄 test_system.py              # Script de teste
├── 📄 openai.env                  # Configuração da API OpenAI
├── 📄 requirements.txt            # Dependências Python
└── 📄 README.md                   # Esta documentação
```

## 🚀 Como Usar

### **Passo 1: Configurar Ambiente**

```powershell
# Instalar dependências
pip install -r requirements.txt
```

### **Passo 2: Criar OpenAI Assistant**

1. **Acesse**: https://platform.openai.com/assistants
2. **Copie o texto completo** do arquivo `ASSISTANT_CONFIG.txt`
3. **Cole nas instruções** do novo Assistant
4. **Configure**:
   - Model: `gpt-4o`
   - Tools: `file_search` ✅
   - Temperature: `0.3`
5. **Anote o Assistant ID** (formato: `asst-xxxxxxxxxxxxx`)

### **Passo 3: Executar Sistema**

```powershell
# Teste com o arquivo de exemplo
python test_system.py

# Ou usar diretamente
python pdf_report_processor.py
```

O sistema irá:
1. **Solicitar o Assistant ID** (primeira execução)
2. **Extrair dados** do PDF com Docling
3. **Identificar área vazia** na segunda página
4. **Gerar resumo** via OpenAI Assistant
5. **Inserir texto** no PDF e salvar

## 📋 Arquivo de Teste

O sistema está configurado para o arquivo de exemplo:
```
C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\2025 - 06\Relatório_Mensal_-_Supera_-_Junho_2025.pdf
```

## 🔧 Funcionamento Técnico

### **1. Extração de Dados (Docling)**
- Processa PDF completo incluindo gráficos e tabelas
- Converte para formato Markdown estruturado
- Preserva hierarquia e relacionamentos dos dados

### **2. Detecção de Área Vazia**
- Analisa segunda página com PyMuPDF
- Identifica blocos de texto existentes
- Calcula área disponível na parte inferior
- Define coordenadas precisas para inserção

### **3. Geração de Resumo (OpenAI Assistant)**
- Upload dos dados extraídos
- Prompt especializado em análise financeira
- Resumo executivo limitado a 150 palavras
- Foco em indicadores, variações e insights

### **4. Inserção no PDF**
- Fonte Arial 10 (Helvetica no PyMuPDF)
- Quebras de linha automáticas
- Respeita limites da área disponível
- Preserva formatação original do PDF

## 📊 Exemplo de Resumo Gerado

```
HIGHLIGHTS JUNHO 2025

• RECEITA: R$ 2.1M (+15% vs maio), crescimento impulsionado por novos contratos
• MARGEM BRUTA: 68% (+3pp), melhoria na mix de produtos e eficiência operacional  
• CUSTOS FIXOS: R$ 450K (-2%), otimização em despesas administrativas
• EBITDA: R$ 680K (+22%), superando meta mensal em 8%

DESTAQUES: Maior receita trimestral, redução de inadimplência para 2.1% 
e aprovação de linha de crédito adicional.

ATENÇÃO: Aumento de 12% nos custos de matéria-prima previsto para julho.
```

## 🛠️ Tecnologias Utilizadas

- **Docling**: Extração inteligente de dados PDF
- **PyMuPDF**: Manipulação e análise de PDF
- **OpenAI API**: Geração de resumos via Assistant
- **Python 3.8+**: Linguagem base do sistema

## 📝 Configuração do Assistant

O arquivo `ASSISTANT_CONFIG.txt` contém instruções completas para criar um Assistant OpenAI especializado em:

- Análise financeira e contábil
- Geração de resumos executivos
- Identificação de indicadores-chave
- Linguagem corporativa adequada
- Formatação para executives

## 🔍 Solução de Problemas

### **Erro: "Assistant ID não encontrado"**
- Verifique se o Assistant foi criado corretamente
- Confirme se o ID está no formato `asst-xxxxxxxxxxxxx`

### **Erro: "PDF deve ter pelo menos 2 páginas"**
- O sistema requer PDFs com 2+ páginas
- A segunda página deve ter área disponível na parte inferior

### **Erro: "Docling import failed"**
- Execute: `pip install docling`
- Verifique compatibilidade com NumPy: `pip install "numpy<2.0.0"`

### **Timeout na análise**
- Verifique conexão com internet
- Confirme se a API key OpenAI está válida
- Tente novamente em alguns minutos

## 🎯 Baseado em Sistema Existente

Este projeto reutiliza e adapta funcionalidades do sistema `financial_analyzer.py`:

- ✅ Integração OpenAI Assistant
- ✅ Upload e processamento de arquivos
- ✅ Gestão de threads e execução
- ✅ Tratamento de erros e timeouts
- ✅ Sistema de cleanup automático

## 📈 Próximos Passos

1. **Teste o sistema** com o PDF de exemplo
2. **Ajuste o prompt** conforme necessário
3. **Personalize as instruções** do Assistant
4. **Adapte para outros tipos** de relatório
5. **Implemente processamento em lote** para múltiplos PDFs

---

**🚀 Sistema pronto para uso! Execute `python test_system.py` para começar.**
