# 🏗️ GOVGO V1 - ARQUITETURA COMPLETA

**Data:** 29/07/2025  
**Versão:** 1.0  
**Status:** Planejamento  

---

## 📋 **RESUMO EXECUTIVO**

A GovGo v1 representa uma reformulação completa da arquitetura, consolidando:
- **Base única Supabase** (eliminando fragmentação SQLite + 2x Supabase)
- **4 tipos de dados PNCP** (Contratações + Contratos + Atas + PCAs)
- **Pipeline simplificado** (eliminando migrações desnecessárias)
- **Sistema de busca unificado** (modernizado e otimizado)

---

## 🎯 **PROBLEMAS RESOLVIDOS DA V0**

### ❌ **Problemas Identificados:**
1. **Fragmentação de dados** em 3 bases diferentes
2. **Limitação de tipos** (apenas Contratações/Contratos)
3. **Pipeline complexo** com 7 etapas e migrações
4. **Desperdício de recursos** (limpeza constante por falta de espaço)
5. **Inconsistências** entre bases SQLite ↔ Supabase

### ✅ **Soluções Implementadas:**
1. **Base única Supabase** com particionamento inteligente
2. **4 tipos completos** conforme especificação PNCP
3. **Pipeline direto** de 4 etapas otimizadas
4. **Gestão eficiente** com arquivamento automático
5. **Consistência total** com fonte única de verdade

---

## 🏛️ **ARQUITETURA GERAL**

```
┌─────────────────────────────────────────────────────────────┐
│                     GOVGO V1 PIPELINE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PNCP APIs  →  PROCESSAMENTO  →  SUPABASE ÚNICA  →  BUSCA  │
│                                                             │
│  ┌─────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │Contrataç│    │ Unificação  │    │  Partições  │         │
│  │Contratos│ →  │ Embeddings  │ →  │   por Data  │ → 🔍   │
│  │  Atas   │    │Categorização│    │  Índices    │         │
│  │  PCAs   │    │             │    │ Otimizados  │         │
│  └─────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ **ESTRUTURA DE BANCO UNIFICADA**

### **📊 Tabela Principal: `documentos_pncp`**
```sql
CREATE TABLE documentos_pncp (
    -- Identificação Universal
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero_controle_pncp TEXT UNIQUE NOT NULL,
    tipo_documento TEXT NOT NULL, -- 'contratacao', 'contrato', 'ata', 'pca'
    
    -- Metadados Temporais
    data_criacao TIMESTAMPTZ DEFAULT NOW(),
    data_atualizacao TIMESTAMPTZ DEFAULT NOW(),
    data_publicacao_pncp DATE,
    data_inclusao_sistema DATE,
    ano_referencia INTEGER,
    
    -- Dados Principais (JSON Flexível)
    dados_principais JSONB NOT NULL,
    
    -- Busca Semântica
    texto_busca TEXT, -- Texto consolidado para embeddings
    embedding VECTOR(1536), -- OpenAI embeddings
    
    -- Categorização
    categoria_codigo TEXT,
    categoria_score REAL,
    
    -- Índices de Performance
    orgao_cnpj TEXT,
    unidade_codigo TEXT,
    modalidade_id INTEGER,
    valor_estimado DECIMAL(15,2),
    valor_homologado DECIMAL(15,2),
    situacao_codigo TEXT,
    
    -- Controle de Status
    status_processamento TEXT DEFAULT 'pendente',
    tentativas_processamento INTEGER DEFAULT 0,
    erro_processamento TEXT,
    
    -- Particionamento
    particao_data DATE GENERATED ALWAYS AS (
        COALESCE(data_publicacao_pncp, data_inclusao_sistema, CURRENT_DATE)
    ) STORED
);

-- Particionamento por Data (Performance)
CREATE INDEX idx_documentos_particao ON documentos_pncp (particao_data);
CREATE INDEX idx_documentos_tipo ON documentos_pncp (tipo_documento);
CREATE INDEX idx_documentos_embedding ON documentos_pncp USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_documentos_busca ON documentos_pncp USING gin (to_tsvector('portuguese', texto_busca));
CREATE INDEX idx_documentos_categoria ON documentos_pncp (categoria_codigo);
```

### **📊 Tabelas Auxiliares:**
```sql
-- Categorias (Reutilizada da v0)
CREATE TABLE categorias (
    codigo TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    nivel_0_codigo TEXT,
    nivel_0_nome TEXT,
    nivel_1_codigo TEXT,
    nivel_1_nome TEXT,
    nivel_2_codigo TEXT,
    nivel_2_nome TEXT,
    nivel_3_codigo TEXT,
    nivel_3_nome TEXT
);

-- Órgãos e Unidades
CREATE TABLE orgaos_unidades (
    cnpj TEXT PRIMARY KEY,
    razao_social TEXT,
    poder_id TEXT,
    esfera_id TEXT,
    uf_sigla TEXT,
    municipio_nome TEXT,
    ultima_atualizacao TIMESTAMPTZ DEFAULT NOW()
);

-- Logs de Processamento
CREATE TABLE logs_processamento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_execucao TIMESTAMPTZ DEFAULT NOW(),
    tipo_processamento TEXT,
    documentos_processados INTEGER,
    documentos_erro INTEGER,
    tempo_execucao_segundos INTEGER,
    detalhes JSONB
);
```

---

## 🔌 **MAPEAMENTO APIs PNCP**

### **📋 Tipos de Documento por API:**

| Tipo | Endpoint PNCP | Status v0 | Status v1 |
|------|---------------|-----------|-----------|
| **Contratações** | `/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}` | ✅ Implementado | ✅ Migrado |
| **Contratos** | `/pncp/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}` | ✅ Implementado | ✅ Migrado |
| **Atas de Preço** | `/pncp/v1/orgaos/{cnpj}/atas-registro-preco/{ano}/{sequencial}` | ❌ Ausente | 🆕 **Novo** |
| **PCAs** | `/pncp/v1/orgaos/{cnpj}/planos-contratacao/{ano}` | ❌ Ausente | 🆕 **Novo** |

### **🔄 Estrutura JSON por Tipo:**

#### **1. Contratações (Existente + Melhorado)**
```json
{
  "tipo_documento": "contratacao",
  "numero_controle": "...",
  "modalidade": {...},
  "modo_disputa": {...},
  "objeto_compra": "...",
  "valor_estimado": 0.0,
  "valor_homologado": 0.0,
  "orgao": {...},
  "unidade": {...},
  "datas": {...},
  "situacao": {...},
  "itens": [...] // Novo: itens integrados
}
```

#### **2. Contratos (Existente + Melhorado)**
```json
{
  "tipo_documento": "contrato",
  "numero_controle": "...",
  "tipo_contrato": {...},
  "contratacao_origem": "...", // Link com contratação
  "valor_inicial": 0.0,
  "valor_global": 0.0,
  "vigencia": {...},
  "fornecedor": {...},
  "objeto": "...",
  "termos_aditivos": [...] // Novo: termos integrados
}
```

#### **3. Atas de Registro de Preço (NOVO)**
```json
{
  "tipo_documento": "ata",
  "numero_controle": "...",
  "numero_ata": "...",
  "contratacao_origem": "...",
  "valor_total": 0.0,
  "vigencia": {...},
  "fornecedores": [...],
  "itens_registrados": [...],
  "orgaos_participantes": [...]
}
```

#### **4. Planos de Contratação Anual (NOVO)**
```json
{
  "tipo_documento": "pca",
  "numero_controle": "...",
  "ano_exercicio": 2025,
  "orgao": {...},
  "valor_total_previsto": 0.0,
  "itens_planejados": [...],
  "status_aprovacao": "...",
  "data_aprovacao": "..."
}
```

---

## ⚙️ **PIPELINE SIMPLIFICADO V1**

### **🔄 Fluxo Otimizado (4 Etapas):**

```python
# ETAPA 1: Coleta Unificada
def coletar_dados_pncp():
    """
    Coleta TODOS os tipos de documento do PNCP
    - Contratações (API existente)
    - Contratos (API existente)  
    - Atas de Preço (API nova)
    - PCAs (API nova)
    """
    
# ETAPA 2: Processamento Direto
def processar_documentos():
    """
    Processa e unifica todos os tipos
    - Extração de texto para busca
    - Geração de embeddings
    - Categorização automática
    - Inserção direta no Supabase
    """
    
# ETAPA 3: Indexação Inteligente
def indexar_documentos():
    """
    Otimiza índices e partições
    - Atualização de índices vetoriais
    - Manutenção de partições
    - Estatísticas de performance
    """
    
# ETAPA 4: Arquivamento Automático
def arquivar_antigos():
    """
    Arquiva documentos antigos (não deleta)
    - Move para partições de arquivo
    - Mantém disponibilidade
    - Otimiza performance
    """
```

### **📂 Estrutura de Arquivos V1:**
```
v1/
├── 📁 core/
│   ├── config.py          # Configuração centralizada
│   ├── database.py        # Conexões e queries
│   ├── models.py          # Modelos de dados
│   └── utils.py           # Utilitários comuns
├── 📁 collectors/
│   ├── pncp_client.py     # Cliente API PNCP
│   ├── contratacoes.py    # Coletor contratações
│   ├── contratos.py       # Coletor contratos
│   ├── atas.py            # Coletor atas (NOVO)
│   └── pcas.py            # Coletor PCAs (NOVO)
├── 📁 processors/
│   ├── text_processor.py  # Processamento de texto
│   ├── embeddings.py      # Geração de embeddings
│   ├── categorizer.py     # Categorização automática
│   └── validator.py       # Validação de dados
├── 📁 search/
│   ├── search_engine.py   # Motor de busca unificado
│   ├── semantic_search.py # Busca semântica
│   ├── filters.py         # Filtros avançados
│   └── exporters.py       # Exportação de resultados
├── 📁 interfaces/
│   ├── cli.py             # Interface linha de comando
│   ├── terminal_ui.py     # Interface terminal Rica
│   └── api.py             # API REST (futuro)
├── 📄 govgo_v1_pipeline.py  # Pipeline principal
├── 📄 govgo_v1_search.py    # Sistema de busca
└── 📄 requirements.txt      # Dependências
```

---

## 🔍 **SISTEMA DE BUSCA UNIFICADO**

### **🎯 Funcionalidades:**
- **Busca Semântica:** Embeddings OpenAI + pgvector
- **Busca Textual:** Full-text search PostgreSQL
- **Busca Híbrida:** Combinação otimizada
- **Filtros Avançados:** Por tipo, data, valor, órgão
- **Exportação:** Excel, PDF, JSON

### **🖥️ Interface Modernizada:**
```python
# Exemplo de uso
python govgo_v1_search.py

┌─ GovGo v1 - Sistema de Busca Unificado ─┐
│                                         │
│ 🔍 Termo de busca: [equipamentos médicos] │
│                                         │
│ 📋 Filtros:                             │
│ ├─ Tipo: [Todos] ▼                     │
│ ├─ Período: [2024-2025] ▼              │
│ ├─ Valor: [R$ 0 - ∞] ▼                 │
│ └─ Órgão: [Todos] ▼                    │
│                                         │
│ 🎯 Buscar [Enter] | ⚙️ Config [C]        │
└─────────────────────────────────────────┘
```

---

## 📈 **BENEFÍCIOS DA V1**

### **⚡ Performance:**
- **3x mais rápido** (elimina migrações entre bases)
- **Índices otimizados** pgvector + gin + btree
- **Particionamento** automático por data

### **💾 Eficiência:**
- **Base única** (elimina duplicação)
- **Arquivamento** ao invés de exclusão
- **Cache inteligente** de embeddings

### **🔧 Manutenção:**
- **Pipeline simplificado** (7→4 etapas)
- **Configuração centralizada**
- **Logs estruturados**
- **Monitoramento automático**

### **📊 Funcionalidades:**
- **4 tipos de documento** (vs 2 na v0)
- **Busca unificada** em todos os tipos
- **Análise completa** do ciclo de contratação
- **Relatórios integrados**

---

## 🚀 **PLANO DE IMPLEMENTAÇÃO**

### **Fase 1: Estrutura Base (Semana 1)**
1. ✅ Configuração do ambiente v1
2. ✅ Criação da estrutura de banco
3. ✅ Migração das categorias existentes
4. ✅ Configuração dos coletores base

### **Fase 2: Coletores Expandidos (Semana 2)**
1. 🔄 Implementação coletor Atas
2. 🔄 Implementação coletor PCAs
3. 🔄 Testes de integração APIs
4. 🔄 Validação estrutura dados

### **Fase 3: Pipeline Unificado (Semana 3)**
1. 🔄 Desenvolvimento pipeline principal
2. 🔄 Sistema de embeddings otimizado
3. 🔄 Categorização automática
4. 🔄 Testes de performance

### **Fase 4: Sistema de Busca (Semana 4)**
1. 🔄 Motor de busca unificado
2. 🔄 Interface terminal modernizada
3. 🔄 Exportadores atualizados
4. 🔄 Testes finais e documentação

---

## ⚙️ **CONFIGURAÇÃO E DEPLOYMENT**

### **🔧 Requisitos:**
- **Python 3.11+**
- **PostgreSQL 15+** com pgvector
- **Supabase Pro** (para volume de dados)
- **OpenAI API** (embeddings)

### **📋 Dependências Principais:**
```txt
supabase>=2.0.0
openai>=1.0.0
psycopg2-binary>=2.9.0
pgvector>=0.2.0
pandas>=2.0.0
numpy>=1.24.0
rich>=13.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
fastapi>=0.100.0  # Para API futura
```

### **🗂️ Variáveis de Ambiente:**
```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
SUPABASE_DB_URL=postgresql://xxx

# OpenAI
OPENAI_API_KEY=sk-xxx

# PNCP
PNCP_BASE_URL=https://pncp.gov.br/api
PNCP_TOKEN=xxx

# Configurações
BATCH_SIZE=100
MAX_WORKERS=4
CACHE_EMBEDDINGS=true
LOG_LEVEL=INFO
```

---

## 📚 **DOCUMENTAÇÃO ADICIONAL**

- **📘 [Manual APIs PNCP](./docs/apis_pncp.md)** - Documentação completa das APIs
- **📗 [Guia de Migração v0→v1](./docs/migracao.md)** - Processo de migração
- **📙 [Manual do Usuário](./docs/usuario.md)** - Como usar o sistema
- **📕 [Troubleshooting](./docs/troubleshooting.md)** - Solução de problemas

---

## 👥 **EQUIPE E CONTATOS**

**Desenvolvedor Principal:** Haroldo Duraes  
**Repositório:** govgo/v1  
**Status:** Em Desenvolvimento  
**Próxima Revisão:** 05/08/2025  

---

*Este documento será atualizado conforme o progresso da implementação.*
