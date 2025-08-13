# 📊 Analisador Financeiro Automático

Sistema integrado que converte relatórios Excel do Zoho para Markdown e faz análise financeira automática usando IA (OpenAI Assistant).

## 🎯 Funcionalidades

- ✅ **Conversão Universal**: Excel → Markdown com precisão decimal
- 🤖 **Análise IA**: Assistente especializado em DRE brasileira  
- 📊 **Indicadores**: CMV, Pessoal, Administrativo automático
- 🚨 **Alertas**: Variações críticas >50% em contas >R$ 50.000
- 💾 **Auto-save**: Salva análise na pasta do arquivo original

## 📁 Estrutura dos Arquivos

```
Reports/
├── financial_analyzer.py      # Código principal
├── universal_converter.py     # Conversor universal
├── openai.env                # Configurações OpenAI
├── requirements.txt           # Dependências
├── test_analyzer.py          # Script de teste
└── README.md                 # Este arquivo
```

## ⚙️ Configuração

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar OpenAI
Arquivo `openai.env`:
```
api_key=sua_chave_aqui
```

### 3. Verificar Assistente
O assistente `asst_G8pkl29kFjPbAhYlS2kAclsU` deve estar ativo no seu projeto OpenAI.

## 🚀 Como Usar

### Uso Básico
```bash
python financial_analyzer.py relatorio.xlsx
```

### Opções Avançadas
```bash
# Com prompt personalizado
python financial_analyzer.py relatorio.xlsx --prompt "Foque apenas no CMV e INSS"

# Não limpar arquivo do OpenAI
python financial_analyzer.py relatorio.xlsx --no-cleanup

# Arquivo de configuração específico
python financial_analyzer.py relatorio.xlsx --env custom.env
```

### Teste Rápido
```bash
python test_analyzer.py
```

## 📄 Arquivos Gerados

Para um arquivo `RELATORIO.xlsx`, são gerados:

1. **`RELATORIO_dec4_20250721_143025.md`**
   - Conversão do Excel para Markdown
   - Números com 4 casas decimais
   - Timestamp de quando foi convertido

2. **`RELATORIO_ANALISE_20250721_143145.md`**
   - Análise financeira completa da IA
   - Resumo executivo + grupos contábeis
   - Alertas críticos + indicadores
   - Ações prioritárias

## 🔍 Formato da Análise

A IA retorna análise estruturada:

```markdown
🔍 RESUMO EXECUTIVO
Empresa em situação crítica com CMV 48.6% | CRÍTICO

📊 ANÁLISE POR GRUPOS

G2 INSUMOS/CMV: R$ 629K (48% receita) | CRÍTICO
• ESTOCÁVEIS: R$ 207K (+4.97%)
• PERECÍVEIS: R$ 238K (-1.86%)
• HORTIFRUTI: R$ 109K (-9.15%)

G3 PESSOAL: R$ 407K (31% receita) | CRÍTICO  
• SALÁRIOS: R$ 180K (+4.51%)
• INSS: R$ 77K (+22.31%)
• ESTAGIÁRIOS: R$ 37K (0%)
• Alertas: INSS R$ 701→67K (+9.517%)

🚨 ALERTAS CRÍTICOS
• INSS: R$ 701→67.422 (9.517% variação)
• UNIFORMES: R$ 240→8.747 (3.548% variação)

📊 INDICADORES: CMV 48.6% | Pessoal 31.5% | Admin 12.8%

🎯 AÇÕES: [3 ações específicas baseadas nos alertas]
```

## 🔧 Integração com Código Próprio

```python
from financial_analyzer import FinancialAnalyzer

# Criar analisador
analyzer = FinancialAnalyzer()

# Analisar arquivo
md_file, analysis_file = analyzer.analyze_financial_report(
    excel_file="relatorio.xlsx",
    custom_prompt="Análise focada em custos",
    cleanup=True
)

print(f"Markdown: {md_file}")
print(f"Análise: {analysis_file}")
```

## 🎛️ Parâmetros do Conversor

O conversor usa configurações otimizadas:
- **Casas decimais**: 4 (configurável)
- **Formatos suportados**: XLSX, XLS, CSV, PDF, HTML
- **Engine**: Docling + Pandas (fallback)

## 🚨 Tratamento de Erros

O sistema trata automaticamente:
- ❌ Arquivo não encontrado
- ❌ Formato não suportado  
- ❌ Erro na API OpenAI
- ❌ Falha na conversão
- 🗑️ Limpeza automática em caso de erro

## 📊 Exemplo de Log

```
🎯 INICIANDO ANÁLISE FINANCEIRA AUTOMÁTICA
================================================================================
📁 Arquivo: relatorio.xlsx
🤖 Assistente: asst_G8pkl29kFjPbAhYlS2kAclsU
================================================================================

🔄 ETAPA 1: Convertendo Excel para Markdown
============================================================
✅ Conversão concluída: relatorio_dec4_20250721_143025.md

📤 ETAPA 2: Upload do arquivo para OpenAI  
============================================================
✅ Arquivo enviado - ID: file-abc123

🤖 ETAPA 3: Análise com Assistente IA
============================================================
📝 Thread criada: thread_xyz789
🚀 Execução iniciada: run_def456
⏳ Aguardando análise...
📊 Status: completed
✅ Análise concluída!

💾 ETAPA 4: Salvando análise
============================================================
✅ Análise salva: relatorio_ANALISE_20250721_143145.md

🗑️ Arquivo removido do OpenAI: file-abc123

🎉 ANÁLISE CONCLUÍDA COM SUCESSO!
================================================================================
📄 Markdown: relatorio_dec4_20250721_143025.md
📊 Análise: relatorio_ANALISE_20250721_143145.md
```

## 🔧 Troubleshooting

### Erro: "Biblioteca OpenAI não instalada"
```bash
pip install openai
```

### Erro: "universal_converter.py não encontrado"
- Certifique-se que ambos arquivos estão na mesma pasta

### Erro: "api_key não encontrada"
- Verifique o arquivo `openai.env`
- Formato: `api_key=sk-proj-...`

### Erro: "Assistente não encontrado"
- Verifique se `asst_G8pkl29kFjPbAhYlS2kAclsU` existe no seu projeto OpenAI

## 📈 Performance

- **Conversão**: ~10-30 segundos (depende do tamanho)
- **Análise IA**: ~30-60 segundos (depende da complexidade)
- **Upload**: ~5-15 segundos (depende da conexão)

## 🔄 Próximas Versões

- [ ] Interface gráfica (GUI)
- [ ] Análise comparativa entre meses
- [ ] Exportação para PDF
- [ ] Dashboard interativo
- [ ] Integração direta com Zoho API
