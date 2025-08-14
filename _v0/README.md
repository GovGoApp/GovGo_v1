# 🏛️ GovGo V0 - Sistema Completo de Análise de Contratações Públicas

**README COMPLETO DO SISTEMA V0**  
*Guia definitivo para navegar no "emaranhado de códigos" do GovGo V0*

---

## 📋 **VISÃO GERAL DO SISTEMA**

O GovGo V0 é um sistema complexo de coleta, processamento e análise de dados de contratações públicas do PNCP (Portal Nacional de Contratações Públicas). O sistema evoluiu organicamente, resultando em uma arquitetura distribuída com múltiplos módulos especializados.

### 🎯 **Objetivos Principais**
- **Coleta automática** de dados do PNCP via API oficial
- **Processamento inteligente** com categorização e embeddings
- **Busca avançada** semântica e textual
- **Análise de documentos** (PDFs, editais, contratos)
- **Relatórios estruturados** e exportação de dados
- **Interface Rica** para busca e navegação

---

## 🏗️ **ESTRUTURA GERAL DO PROJETO**

```
#GOvGO/python/v0/
├── 📁 Script/              # Pipeline principal de processamento
├── 📁 GvG/                # Módulos especializados
│   ├── Search/            # Sistema de busca avançado
│   ├── Supabase/          # Integração com banco de dados
│   ├── Reports/           # Geração de relatórios
│   ├── PreProcessing/     # Pré-processamento de dados
│   └── Cat/               # Categorização automática
├── 📁 DB/                 # Esquemas e documentação do banco
├── 📁 REPORTS/            # Relatórios gerados
├── 📁 API/                # Clientes para APIs externas
├── 📁 PNCP_DATA/          # Dados e testes específicos PNCP
└── 📁 Docs/               # Documentação adicional
```

---

## 🔄 **PIPELINE PRINCIPAL (Script/)**

### **Pipeline de 7 Etapas**

#### **1. Download de Dados (`01_pncp_download.py`)**
```python
# Funcionalidades:
- Download incremental de contratações via API PNCP
- Controle por data (última data processada)
- Consulta paralela por modalidades
- Campos completos (85+ campos por contratação)
- Logs estruturados e controle de erros
```

**Configuração:**
- **Arquivo:** `files.env` - Caminhos dos dados
- **Controle:** `last_processed_date.log` - Última data processada
- **Output:** CSV com contratações brutas

#### **2. Download de Itens (`02_pncp_itens.py`)**
```python
# Funcionalidades:
- Busca detalhes de itens para cada contratação
- Enriquecimento com dados de produtos/serviços
- Classificação CATMAT automática
- Tratamento de dados faltantes
```

#### **3. Banco de Contratações (`03_db_contratacoes.py`)**
```python
# Funcionalidades:
- Carregamento no banco SQLite local
- Normalização e limpeza de dados
- Indexação para performance
- Validação de integridade
```

#### **4. Banco de Itens (`04_db_itens.py`)**
```python
# Funcionalidades:
- Processamento de itens individuais
- Relacionamento com contratações
- Categorização por produtos/serviços
```

#### **5. Exportação Excel (`05_excel_export.py`)**
```python
# Funcionalidades:
- Geração de planilhas estruturadas
- Múltiplas abas por categoria
- Formatação avançada
- Filtros automáticos
```

#### **6. Embeddings Supabase (`06_supabase_embeddings.py`)**
```python
# Funcionalidades:
- Geração de embeddings OpenAI
- Upload para Supabase (produção)
- Busca vetorial (pgvector)
- Cache de embeddings
```

#### **7. Limpeza (`07_clean_expired.py`)**
```python
# Funcionalidades:
- Remoção de contratos expirados
- Limpeza de dados antigos
- Otimização de espaço
- Manutenção automática
```

### **Scripts de Utilidade**
- **`console_utils.py`** - Utilitários de console Rich
- **`00_processar_tudo.bat`** - Execução automatizada completa

---

## 🔍 **SISTEMA DE BUSCA (GvG/Search/)**

### **Módulos Principais**

#### **Terminal v9 (`Prompt/GvG_SP_Search_Terminal_v9.py`)**
```python
# Interface principal com Rich UI
Features:
- Menu de 5 opções principais
- Sistema de relevância 3 níveis
- Processamento inteligente
- Exportação avançada
- Análise de documentos
```

#### **Linha de Comando (`Prompt/GvG_Search_Prompt_v0.py`)**
```python
# Interface CLI para automação
Features:
- Busca por argumentos
- Output JSON/Excel
- Integração com scripts
- Processamento em lote
```

#### **Utilitários v3 (`Prompt/gvg_search_utils_v3.py`)**
```python
# Motor de busca avançado
Features:
- Busca semântica (embeddings)
- Busca textual (PostgreSQL FTS)
- Busca híbrida combinada
- Filtros avançados
- Cache inteligente
```

#### **Pré-processamento v3 (`Prompt/gvg_pre_processing_v3.py`)**
```python
# Processamento inteligente de consultas
Features:
- OpenAI Assistant integration
- Separação de termos e filtros
- Expansão automática de consultas
- Debug detalhado
```

#### **Análise de Documentos (`Prompt/gvg_document_utils_v3.py`)**
```python
# Processamento de PDFs e documentos
Features:
- Docling integration (v3)
- MarkItDown fallback (v2)
- Extração de texto
- Resumos automáticos
- Análise estrutural
```

### **Configurações do Sistema de Busca**

#### **Banco de Dados (`Prompt/supabase_v0.env`)**
```env
user=postgres.bzgtlersjbetwilubnng 
password=GovGo2025!!
host=aws-0-sa-east-1.pooler.supabase.com
port=6543
dbname=postgres
```

#### **OpenAI (`Prompt/openai.env`)**
```env
api_key=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
```

#### **Diretórios (`Prompt/dir.env`)**
```env
BASE_PATH=C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\GvG\Terminal\
RESULTS_PATH=${BASE_PATH}Relatórios\
FILES_PATH=${BASE_PATH}Arquivos\
```

---

## 🗄️ **ESTRUTURA DE BANCO DE DADOS**

### **Banco Local SQLite (`DB/DOC/PNCP_DB_v2.txt`)**

#### **Tabela Principal: `contratacao`**
```sql
CREATE TABLE contratacao (
    ID_CONTRATACAO INTEGER PRIMARY KEY AUTOINCREMENT,
    numeroControlePNCP TEXT,           -- Chave única PNCP
    orgaoEntidade_cnpj TEXT,          -- CNPJ do órgão
    orgaoEntidade_razaosocial TEXT,   -- Nome do órgão
    unidadeOrcamentaria_codigo TEXT,  -- Código da unidade
    unidadeOrcamentaria_nome TEXT,    -- Nome da unidade
    valorestimado REAL,               -- Valor estimado
    valorTotalHomologado REAL,        -- Valor homologado
    situacao TEXT,                    -- Status da contratação
    modalidade TEXT,                  -- Modalidade de licitação
    objetoCompra TEXT,                -- Descrição do objeto
    dataPublicacaoPncp TEXT,         -- Data de publicação
    CODCAT TEXT,                      -- Código de categoria
    SCORE REAL                        -- Score de categorização
);
```

#### **Tabela de Categorias: `categoria`**
```sql
CREATE TABLE categoria (
    CODCAT TEXT PRIMARY KEY,          -- Código da categoria
    NOMCAT TEXT,                      -- Nome da categoria
    CODNV0 TEXT,                      -- Nível 0 (setor)
    NOMNV0 TEXT,                      -- Nome nível 0
    CODNV1 TEXT,                      -- Nível 1 (grupo)
    NOMNV1 TEXT,                      -- Nome nível 1
    CODNV2 TEXT,                      -- Nível 2 (classe)
    NOMNV2 TEXT,                      -- Nome nível 2
    CODNV3 TEXT,                      -- Nível 3 (item)
    NOMNV3 TEXT                       -- Nome nível 3
);
```

### **Banco Supabase (Produção)**

#### **Tabela: `contratacoes`**
- Espelho da tabela local SQLite
- Dados de produção sincronizados
- Índices otimizados para busca

#### **Tabela: `contratacoes_embeddings`**
```sql
CREATE TABLE contratacoes_embeddings (
    numerocontrolepncp TEXT PRIMARY KEY,
    embedding VECTOR(3072),           -- OpenAI embeddings
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

---

## 🔧 **MÓDULOS ESPECIALIZADOS**

### **1. Supabase Integration (`GvG/Supabase/`)**

#### **Setup de Tabelas (`GvG_SP_Tables_v0.py`)**
```python
# Funcionalidades:
- Criação automática de tabelas Supabase
- Configuração de índices pgvector
- Funções de busca por similaridade
- Triggers de atualização
```

#### **Configuração:**
```env
USER=postgres.bzgtlersjbetwilubnng
PASSWORD=GovGo2025!!
HOST=aws-0-sa-east-1.pooler.supabase.com
PORT=6543
DBNAME=postgres
```

### **2. Relatórios (`GvG/Reports/` + `REPORTS/`)**

#### **Versões Disponíveis:**
- **`reports.py`** - Versão básica
- **`reports_v2.py`** - Melhorias de formatação
- **`reports_v3.py`** - Análise estatística
- **`reports_v4.py`** - Gráficos e visualizações
- **`reports_v5.py`** - Exportação multi-formato
- **`reports_v6.py`** - Dashboard interativo
- **`reports_v7.py`** - Análise temporal
- **`reports_v8.py`** - IA integrada

### **3. Categorização (`GvG/Cat/`)**
```python
# Sistema de categorização automática
Features:
- Machine Learning para classificação
- Árvore hierárquica de categorias
- Score de confiança
- Aprendizado contínuo
```

### **4. Pré-processamento (`GvG/PreProcessing/`)**
```python
# Limpeza e normalização de dados
Features:
- Tratamento de caracteres especiais
- Normalização de valores
- Detecção de duplicatas
- Validação de campos obrigatórios
```

---

## ⚙️ **CONFIGURAÇÕES E AMBIENTES**

### **Arquivos de Configuração por Módulo**

#### **Script Principal:**
```
Script/
├── files.env                    # Caminhos dos arquivos
├── supabase_v0.env             # Credenciais Supabase
├── openai.env                  # API Key OpenAI
└── last_processed_date.log     # Controle de estado
```

#### **Sistema de Busca:**
```
GvG/Search/Prompt/
├── supabase_v0.env             # Banco de produção
├── openai.env                  # OpenAI para busca
├── dir.env                     # Diretórios de trabalho
├── relevance_pncp_v2.txt      # Prompts restritivos
└── relevance_pncp_v3.txt      # Prompts flexíveis
```

#### **Supabase:**
```
GvG/Supabase/
└── .env                        # Credenciais para setup
```

### **Variáveis de Ambiente Importantes**

#### **Banco de Dados:**
```env
# Supabase (Produção)
USER=postgres.bzgtlersjbetwilubnng
PASSWORD=GovGo2025!!
HOST=aws-0-sa-east-1.pooler.supabase.com
PORT=6543
DBNAME=postgres

# Banco para contratos expirados
EXPIRED_USER=postgres.bzgtlersjbetwilubnng
EXPIRED_PASSWORD=GovGo2025!!
EXPIRED_HOST=aws-0-sa-east-1.pooler.supabase.com
EXPIRED_PORT=6543
EXPIRED_DBNAME=postgres
```

#### **OpenAI:**
```env
# API Key (modelo: gpt-4-turbo, embeddings: text-embedding-3-small)
api_key=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
```

#### **Diretórios de Trabalho:**
```env
# Paths base do sistema
CONTRATACOES_NEW=C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DCP\2024\
ITENS_NEW=C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DCI\2024\
CONTRATACOES_OLD=C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DCP\OLD\
ITENS_OLD=C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DCI\OLD\

# Banco SQLite local
DATABASE=C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DB\govgo.db
CATEGORIAS=C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DB\categorias_governamentais.db

# Terminal de busca
BASE_PATH=C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\GvG\Terminal\
RESULTS_PATH=${BASE_PATH}Relatórios\
FILES_PATH=${BASE_PATH}Arquivos\
```

---

## 🚀 **COMO USAR O SISTEMA V0**

### **1. Executar Pipeline Completo**
```bash
# Windows
cd Script/
.\00_processar_tudo.bat

# Manual (passo a passo)
python 01_pncp_download.py
python 02_pncp_itens.py
python 03_db_contratacoes.py
python 04_db_itens.py
python 05_excel_export.py
python 06_supabase_embeddings.py
python 07_clean_expired.py
```

### **2. Sistema de Busca Interativo**
```bash
cd GvG/Search/Prompt/
python GvG_SP_Search_Terminal_v9.py
```

**Menu Principal:**
```
1. Tipo de Busca → Semântica, Palavras-chave, Híbrida
2. Abordagem → Direta, Correspondência, Filtro  
3. Relevância → Sem filtro, Flexível, Restritivo
4. Ordenação → Similaridade, Data, Valor
5. Configurações → Sistema, filtros, processamento
```

### **3. Busca por Linha de Comando**
```bash
# Busca simples
python GvG_Search_Prompt_v0.py --prompt "equipamento médico" --max_results 10

# Busca com filtros
python GvG_Search_Prompt_v0.py --prompt "software" --category "8" --value_min 50000

# Output JSON
python GvG_Search_Prompt_v0.py --prompt "consultoria" --output json --file resultado.json
```

### **4. Geração de Relatórios**
```bash
cd REPORTS/
python reports_v8.py  # Versão mais recente com IA
```

### **5. Setup Inicial do Banco**
```bash
cd GvG/Supabase/
python GvG_SP_Tables_v0.py  # Cria tabelas no Supabase
```

---

## 🎛️ **FUNCIONALIDADES AVANÇADAS**

### **Sistema de Relevância (3 Níveis)**

#### **Nível 1 - Sem Filtro**
- Todos os resultados retornados
- Ordenação por similaridade
- Velocidade máxima

#### **Nível 2 - Flexível**
- Filtro suave via IA
- Assistant: `asst_tfD5oQxSgoGhtqdKQHK9UwRi`
- Arquivo: `relevance_pncp_v3.txt`

#### **Nível 3 - Restritivo**
- Filtro rigoroso via IA
- Assistant: `asst_XmsefQEKbuVWu51uNST7kpYT`
- Arquivo: `relevance_pncp_v2.txt`

### **Processamento Inteligente**
```python
# Funcionalidades:
- Separação automática de termos vs filtros
- Expansão de consultas com IA
- Processamento de linguagem natural
- Cache de consultas processadas
```

### **Análise de Documentos**
```python
# Suporte a formatos:
- PDFs (editais, contratos, anexos)
- DOC/DOCX (documentos oficiais)
- ZIP (pacotes de documentos)
- Imagens com OCR
- Planilhas Excel/CSV
```

### **Exportação Avançada**
```python
# Formatos suportados:
- Excel (.xlsx) com múltiplas abas
- PDF com formatação
- JSON estruturado
- CSV para análise
- HTML para visualização
```

---

## 🔍 **COMPONENTES ESPECÍFICOS**

### **APIs Integradas**

#### **PNCP API Client (`API/`)**
```python
# Endpoints utilizados:
- /contratacoes/ - Dados de licitações
- /itens/ - Detalhes de produtos/serviços
- /documentos/ - PDFs e anexos
- /orgaos/ - Informações de órgãos
```

#### **OpenAI Integration**
```python
# Modelos utilizados:
- gpt-4-turbo - Processamento de texto
- text-embedding-3-small - Embeddings (1536D)
- Assistants - Filtros de relevância
```

### **Utilitários Especializados**

#### **ExpiredContracts**
```python
# Gestão de contratos vencidos:
- Detecção automática de expiração
- Transferência para banco separado
- Limpeza de dados antigos
- Relatórios de contratos vencidos
```

#### **CatMatFinder**
```python
# Classificação CATMAT:
- Busca automática de códigos
- Mapeamento produto → categoria
- Score de confiança
- Base atualizada do governo
```

#### **LEADS**
```python
# Análise de oportunidades:
- Detecção de padrões
- Previsão de licitações
- Score de oportunidade
- Alertas automáticos
```

---

## 📊 **DADOS E PERFORMANCE**

### **Volumes Típicos**
- **Contratações/dia:** ~500-2000
- **Itens/contratação:** ~5-20
- **Banco SQLite:** ~1-5GB
- **Embeddings:** ~3GB (Supabase)
- **Tempo de processamento:** 2-6h (completo)

### **Performance do Sistema de Busca**
- **Busca semântica:** ~200-500ms
- **Busca textual:** ~50-200ms
- **Busca híbrida:** ~300-800ms
- **Cache hit rate:** ~70-85%

### **Recursos Necessários**
- **RAM:** 8GB+ recomendado
- **Storage:** 20GB+ para dados completos
- **CPU:** 4+ cores para processamento paralelo
- **Internet:** Estável para APIs

---

## 🚨 **PROBLEMAS COMUNS E SOLUÇÕES**

### **1. Erro de Conexão com Supabase**
```bash
# Verificar credenciais
cat GvG/Search/Prompt/supabase_v0.env

# Testar conexão
python -c "import psycopg2; conn = psycopg2.connect(host='aws-0-sa-east-1.pooler.supabase.com', port=6543, dbname='postgres', user='postgres.bzgtlersjbetwilubnng', password='GovGo2025!!')"
```

### **2. OpenAI API Limits**
```python
# Verificar quota
curl -H "Authorization: Bearer sk-proj-..." https://api.openai.com/v1/usage

# Reduzir batch size
MAX_BATCH_SIZE = 50  # Em vez de 100
```

### **3. Banco SQLite Corrompido**
```bash
# Backup e reparo
cp govgo.db govgo.db.backup
sqlite3 govgo.db "PRAGMA integrity_check;"
sqlite3 govgo.db ".recover" | sqlite3 govgo_recovered.db
```

### **4. Embeddings Faltando**
```bash
# Reprocessar embeddings
cd Script/
python 06_supabase_embeddings.py --force-rebuild
```

---

## 🔄 **FLUXO DE DADOS COMPLETO**

```mermaid
graph TD
    A[PNCP API] --> B[01_pncp_download.py]
    B --> C[02_pncp_itens.py]
    C --> D[03_db_contratacoes.py]
    D --> E[SQLite Local]
    E --> F[04_db_itens.py]
    F --> G[05_excel_export.py]
    E --> H[06_supabase_embeddings.py]
    H --> I[Supabase + pgvector]
    I --> J[GvG_SP_Search_Terminal_v9.py]
    J --> K[Relatórios e Análises]
    E --> L[07_clean_expired.py]
    L --> M[Banco de Contratos Expirados]
```

---

## 📚 **DOCUMENTAÇÃO ADICIONAL**

### **Arquivos de Referência**
- **`DB/DOC/PNCP_DB_v2.txt`** - Schema completo do banco
- **`GvG/Search/Prompt/README.md`** - Documentação do sistema de busca
- **`GvG/Search/Prompt/SETUP.md`** - Guia de instalação
- **`ARQUITETURA_V1.md`** - Planos para próxima versão

### **Logs e Monitoramento**
- **`Script/LOGS/`** - Logs do pipeline principal
- **`Script/processed_contratacoes_itens.log`** - Histórico de processamento
- **`Script/last_processed_date.log`** - Controle de estado

### **Modelos e Prompts**
- **`GvG/Search/Prompt/relevance_pncp_v2.txt`** - Prompts restritivos
- **`GvG/Search/Prompt/relevance_pncp_v3.txt`** - Prompts flexíveis

---

## ⚡ **MIGRAÇÃO PARA V1**

O sistema V0 continuará funcional durante a transição. A V1 oferecerá:

### **Melhorias Planejadas**
- **Base única** Supabase (elimina SQLite)
- **4 tipos de documento** (+ Atas e PCAs)
- **Pipeline simplificado** (7 → 4 etapas)
- **Interface unificada** moderna
- **Compatibilidade total** com dados V0

### **Cronograma**
- **Fase 1:** Estrutura base V1 (Concluída)
- **Fase 2:** Migração de dados (Em andamento)
- **Fase 3:** Funcionalidades expandidas
- **Fase 4:** Sunset V0 (gradual)

---

**🎯 Este README deve servir como mapa completo para navegar no sistema V0. Qualquer desenvolvedor pode usar este guia para entender, usar e manter o GovGo V0 até a transição completa para V1.**

**Mantenedor:** Haroldo Duraes  
**Última atualização:** 29/07/2025  
**Status:** Produção (V0) + Desenvolvimento (V1)**
