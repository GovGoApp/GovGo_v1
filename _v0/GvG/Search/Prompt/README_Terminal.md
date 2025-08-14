# 🚀 GvG Search Terminal v9 - Sistema Avançado de Busca PNCP

Sistema de Busca Inteligente para Contratos Públicos com Interface Terminal Rica
===============================================================================

O **GvG Search Terminal v9** é um sistema avançado de busca semântica para contratos públicos do PNCP (Portal Nacional de Contratações Públicas), desenvolvido com tecnologias de IA e interface terminal moderna usando Rich.

## 🎯 Novidades da Versão 9

### ✨ Interface Reestruturada - Menu de 5 Opções
1. **Tipo de Busca** → Semântica, Palavras-chave, Híbrida
2. **Abordagem** → Direta, Correspondência, Filtro  
3. **🆕 Relevância** → Sem filtro, Flexível, Restritivo
4. **Ordenação** → Similaridade, Data, Valor
5. **Configurações** → Sistema, filtros, processamento

### 🎯 Sistema de Relevância 3 Níveis (NOVO!)
- **Nível 1 - Sem Filtro**: Todos os resultados são retornados
- **Nível 2 - Flexível**: Filtro suave com conexões amplas
  - 🤖 Assistant: `asst_tfD5oQxSgoGhtqdKQHK9UwRi`
  - 📄 Arquivo: `relevance_pncp_v3.txt`
- **Nível 3 - Restritivo**: Filtro rigoroso para alta relevância
  - 🤖 Assistant: `asst_XmsefQEKbuVWu51uNST7kpYT`
  - 📄 Arquivo: `relevance_pncp_v2.txt`

### 🧹 Código v3 Limpo
- ❌ Removidas todas as dependências legacy
- ✅ Sistema v3 exclusivo sem warnings
- ⚡ Melhor performance e estabilidade

---

## 🚀 Principais Funcionalidades

### 🔍 Três Tipos de Busca
- **Semântica**: Busca baseada no significado usando embeddings OpenAI
- **Palavras-chave**: Busca exata de termos específicos
- **Híbrida**: Combinação inteligente de semântica + palavras-chave

### 📊 Três Abordagens de Busca
1. **Direta**: Busca tradicional sem filtro de categorias
2. **Correspondência**: Multiplica similarities entre query e categorias
3. **Filtro**: Restringe universo por categorias + busca textual

### 🤖 Processamento Inteligente v3
- Separação automática de termos e condições SQL
- Processamento via OpenAI Assistant
- Suporte a negation embeddings (`termo --exclusão`)
- Debug avançado com informações detalhadas

### 📄 Análise de Documentos
- **Docling v3**: Extração avançada de tabelas e estruturas
- **MarkItDown v2**: Alternativa rápida e compatível
- Suporte a arquivos ZIP com extração automática
- Sumarização inteligente via IA

---

## ⚙️ Requisitos do Sistema

### 🛠️ Dependências Principais
```bash
pip install rich pandas numpy supabase psycopg2-binary
pip install openai python-dotenv sqlalchemy reportlab
pip install docling markitdown  # Para processamento de documentos
```

### 🗃️ Banco de Dados
- **PostgreSQL** com extensão **pgvector**
- Tabelas: `contratacoes`, `contratacoes_embeddings`, `categorias`
- Arquivo de configuração: `supabase_v0.env`

### 🔑 APIs Necessárias
- **OpenAI API Key** (para processamento inteligente)
- Configuração no arquivo `.env` ou variáveis de ambiente

---

## 🚀 Como Usar

### 💻 Modo Terminal Interativo
```bash
python GvG_SP_Search_Terminal_v9.py
```

### 📝 Modo Linha de Comando
```bash
python GvG_Search_Prompt_v0.py --prompt "sua consulta aqui"
```

### 🎯 Exemplos Práticos

#### Busca Semântica com Filtro de Relevância
```bash
# Terminal interativo
python GvG_SP_Search_Terminal_v9.py
# 1. Escolher "Tipo de Busca" → Semântica
# 2. Escolher "Relevância" → Restritivo
# 3. Digitar consulta: "notebooks para escolas estaduais"
```

#### Busca Híbrida com Negation Embeddings
```bash
# Consulta: "serviços de TI --terceirização --outsourcing"
# O sistema automaticamente exclui resultados relacionados a terceirização
```

#### Busca por Correspondência de Categorias
```bash
# Abordagem "Correspondência" encontra contratos que têm 
# categorias similares à sua consulta e multiplica as similarities
```

---

## 📊 Parâmetros de Configuração

| Parâmetro | Opções | Descrição |
|-----------|---------|-----------|
| **search_type** | 1, 2, 3 | Semântica, Palavras-chave, Híbrida |
| **search_approach** | 1, 2, 3 | Direta, Correspondência, Filtro |
| **relevance_level** | 1, 2, 3 | Sem filtro, Flexível, Restritivo |
| **sort_mode** | 1, 2, 3 | Similaridade, Data, Valor |
| **max_results** | int | Número máximo de resultados (padrão: 30) |
| **top_categories** | int | TOP categorias para filtro (padrão: 10) |
| **filter_expired** | bool | Filtrar contratações encerradas |
| **negation_embeddings** | bool | Usar prompts negativos |

---

## 📂 Estrutura de Arquivos

```
/Prompt/
├── GvG_SP_Search_Terminal_v9.py    # Interface terminal principal
├── GvG_Search_Prompt_v0.py         # Interface linha de comando  
├── gvg_search_utils_v3.py          # Funções de busca v3
├── gvg_pre_processing_v3.py        # Processamento inteligente
├── gvg_document_utils_v3_o.py      # Análise de documentos
├── supabase_v0.env                 # Configurações do banco
├── relevance_pncp_v2.txt           # Prompts restritivos
├── relevance_pncp_v3.txt           # Prompts flexíveis
└── README.md                       # Este arquivo
```

---

## 🎨 Interface Rica

### 🖥️ Terminal Moderno
- **Rich Console**: Cores, tabelas e painéis elegantes
- **Progress Bars**: Acompanhamento em tempo real
- **Syntax Highlighting**: Destaque de termos importantes
- **Menu Contextual**: Opções adaptadas aos resultados

### 📊 Visualização de Resultados
- **Tabelas Organizadas**: Ranking, similarity, valores
- **Painéis Detalhados**: Informações completas por contrato
- **Metadados**: Estatísticas e informações de processamento
- **Links Diretos**: Acesso aos documentos oficiais do PNCP

---

## 📋 Campos Retornados

### 📄 Dados Básicos
- `numeroControlePNCP`, `anoCompra`, `descricaoCompleta`
- `valorTotalEstimado`, `valorTotalHomologado`

### 📅 Datas
- `dataInclusao`, `dataAberturaProposta`, `dataEncerramentoProposta`

### 🏢 Informações do Órgão
- `orgaoEntidade_razaosocial`, `unidadeOrgao_nomeUnidade`
- `orgaoEntidade_poderId/esferaId`, `unidadeOrgao_ufSigla/municipioNome`

### ⚖️ Modalidade e Disputa
- `modalidadeId/modalidadeNome`, `modaDisputaId/modaDisputaNome`
- `usuarioNome`, `linkSistemaOrigem`

---

## 🔧 Troubleshooting

### ❌ Erros Comuns
```bash
# Erro: gvg_search_utils_v3 não encontrado
# Solução: Verificar se o arquivo está na mesma pasta

# Erro: Conexão com banco falhou  
# Solução: Verificar credenciais em supabase_v0.env

# Erro: OpenAI API key não configurada
# Solução: Definir OPENAI_API_KEY no ambiente
```

### 🐛 Debug
```python
# Ativar debug inteligente no menu Configurações
# Ou via parâmetro --debug True no modo prompt
```

---

## 📈 Exemplos de Saída

### 📊 JSON Estruturado
```json
{
  "metadata": {
    "query": "serviços de limpeza hospitalar",
    "search_type": "Híbrida", 
    "relevance_level": 2,
    "total_results": 25,
    "export_date": "2025-07-14 15:30:00"
  },
  "results": [
    {
      "rank": 1,
      "id": "12345678000199-1-000001/2025",
      "similarity": 0.8547,
      "relevance_score": 0.9234,
      "orgao": "Hospital Regional Norte",
      "valor_estimado": 2500000.0,
      "descricao": "Contratação de empresa especializada..."
    }
  ]
}
```

### 📝 Log Detalhado  
```text
🚀 SISTEMA v3 - STATUS
Processamento: 🤖 INTELIGENTE
Debug: 🐛 ATIVO  
Relevância: 🎯 Restritivo (nível 3)

✅ Query processada: "serviços limpeza hospitalar"
⚙️ Condições SQL detectadas: 2
   1. c.unidadeorgao_ufsigla IN ('SP','RJ','MG')  
   2. c.valortotalestimado > 1000000

🎯 TOP Categorias da Query
┌──────┬──────────────┬────────────────────────────┬──────────────┐
│ Rank │ Código       │ Descrição                  │ Similaridade │
├──────┼──────────────┼────────────────────────────┼──────────────┤
│  1   │ 8011600000  │ Serviços de limpeza        │    0.9234    │
│  2   │ 8541100000  │ Serviços hospitalares      │    0.8765    │
└──────┴──────────────┴────────────────────────────┴──────────────┘
```

---

## 🤝 Contribuição

### 🐛 Reportar Bugs
- Abra uma issue no repositório
- Inclua logs e configuração do sistema

### 💡 Sugestões
- Propostas de melhorias são bem-vindas
- Fork + Pull Request para contribuições

### 📧 Contato
- Mantenedor: Haroldo Duraes
- Email: [seu-email@dominio.com]

---

## 📄 Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para detalhes.

---

## 🏆 Versões

- **v9**: Sistema v3 limpo + relevância 3 níveis + menu reestruturado
- **v8**: Processamento inteligente + negation embeddings  
- **v7**: Campos completos PNCP + análise de documentos
- **v6**: Três abordagens de busca + categorização
- **v5**: Interface Rica + exportação avançada

**Última atualização**: 14 de Julho de 2025
