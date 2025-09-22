# GovGo V1 - Pipeline de Processamento PNCP

Este diretório contém o pipeline completo do GovGo V1 para processamento automatizado de contratos do Portal Nacional de Contratações Públicas (PNCP).

## 🎯 Visão Geral

O sistema GovGo V1 processa contratos públicos em 3 etapas principais integradas:

1. **📥 Download PNCP** - Coleta paralela de contratos via API oficial
2. **🧠 Geração de Embeddings** - Vetorização semântica usando OpenAI
3. **🎯 Categorização IA** - Classificação automática com pgvector similarity search

## ✅ Novo pipeline simplificado (recomendado)

Nova implementação leve, com menos dependências e compatível com cron do Render. Arquivos em `scripts/pipeline_pncp/`:

1) 01_pipeline_pncp_download.py
- Download de contratações e itens (API PNCP) para tabelas BDS1
- Mapeamento inline sem DEPARA, idempotente (ON CONFLICT)
- Log unificado em `logs/log_<PIPELINE_TIMESTAMP>.log`

Uso:
```bash
python scripts/pipeline_pncp/01_pipeline_pncp_download.py            # usa last_processed_date
python scripts/pipeline_pncp/01_pipeline_pncp_download.py --test 20250901
python scripts/pipeline_pncp/01_pipeline_pncp_download.py --start 20250901 --end 20250903 --workers 16
```

2) 02_pipeline_pncp_embeddings.py
- Gera embeddings para contratações sem vetor em `contratacao_emb`
- Batch sequencial estável para OpenAI, idempotente

Uso:
```bash
python scripts/pipeline_pncp/02_pipeline_pncp_embeddings.py          # usa últimas datas (system_config)
python scripts/pipeline_pncp/02_pipeline_pncp_embeddings.py --test 20250901
```

3) 03_pipeline_pncp_categorization.py
- Categorização via pgvector: top_categories/top_similarities/confidence
- Idempotente (UPDATE com top_categories IS NULL), batches sequenciais

Uso:
```bash
python scripts/pipeline_pncp/03_pipeline_pncp_categorization.py      # LCD+1 até LED
python scripts/pipeline_pncp/03_pipeline_pncp_categorization.py --test 20250901 --batch-size 300 --top-k 5
```

Execução diária (Render cron):
```bash
# 01 → 02 → 03 (na mesma janela do dia)
python scripts/pipeline_pncp/01_pipeline_pncp_download.py ; \
python scripts/pipeline_pncp/02_pipeline_pncp_embeddings.py ; \
python scripts/pipeline_pncp/03_pipeline_pncp_categorization.py
```

Requisitos mínimos:
- Python 3.12+
- pacotes: `psycopg2-binary`, `requests`, `python-dotenv`, `openai` (somente para 02)
- `.env` com SUPABASE_* e (para 02) `OPENAI_API_KEY`

## 🚀 Execução Automática DIÁRIA

### Pipeline Integrado (OBRIGATÓRIO DIÁRIO)
```bash
# Execute o pipeline completo automaticamente - TODOS OS DIAS
00_run_pncp_scripts.bat
```

⚠️ **EXECUÇÃO DIÁRIA OBRIGATÓRIA**: Este `.bat` deve ser executado **TODOS OS DIAS** pela manhã (8h-9h) para:
- Coletar contratos publicados no dia anterior
- Manter o sistema sempre atualizado
- Evitar acúmulo que degrada performance

**Como executar**: Duplo clique no arquivo `00_run_pncp_scripts.bat`

## 📝 Scripts do Pipeline

### Configuração Inicial (Execute UMA ÚNICA VEZ)

#### 99_reset_database_tables.py
**🗑️ Reset Completo do Banco**
- ⚠️ **PERIGO**: Remove TODAS as tabelas e dados
- Use apenas para reconfiguração total do sistema
- Perde TODO o histórico de processamento

```bash
python 99_reset_database_tables.py
```

#### 01_create_database_schema.py
**🏗️ Criação do Schema PostgreSQL**
- Cria todas as tabelas principais: `contratacao`, `contratacao_emb`, `categoria`
- Configura índices otimizados para performance
- Habilita extensão `pgvector` para similarity search
- Define estrutura fiel aos dados do PNCP

```bash
python 01_create_database_schema.py
```

#### 02_import_initial_data.py
**📊 Migração de Dados Base**
- Migra dados do SQLite V0 → PostgreSQL V1
- Importa categorias de produtos/serviços (base para classificação)
- Configura parâmetros iniciais do sistema
- Processa ~50k+ contratações históricas

```bash
python 02_import_initial_data.py
```

### Pipeline Diário Automatizado (legado)

#### 03_download_pncp_contracts.py (legado)
**📥 Download Paralelo PNCP**
- Conecta à API oficial do PNCP (Portal Nacional de Contratações Públicas)
- Download paralelo com 20 workers simultâneos
- Coleta apenas contratos novos (incremental)
- Sistema robusto com retry automático e circuit breaker
- Processa contratações + itens detalhados
- **Tempo**: 2-6 horas dependendo do volume diário

```bash
python 03_download_pncp_contracts.py
```

#### 04_generate_embeddings.py (legado)
**🧠 Geração de Embeddings OpenAI**
- Usa modelo `text-embedding-3-large` (3072 dimensões)
- Concatena objeto da compra + descrições de itens
- Processamento em lotes otimizado (25 contratos/batch)
- Pool de conexões reutilizáveis para estabilidade
- Rate limiting inteligente para API OpenAI
- **Tempo**: 1-3 horas dependendo do volume

```bash
python 04_generate_embeddings.py
```

#### 05_categorize_contracts.py (legado)
**🎯 Categorização com IA + pgvector**
- Similarity search entre embeddings de contratos e categorias
- Processamento paralelo adaptativo (4-20 workers)
- Rich Progress Bar em tempo real com estatísticas
- Sistema anti-duplicação: só processa contratos não categorizados
- Confiança calculada baseada em gaps de similaridade
- **Tempo**: 30min-3h dependendo do volume diário

```bash
python 05_categorize_contracts.py
```

## 🗄️ Estrutura do Banco PostgreSQL

### Tabelas Principais
- **`contratacao`** - Dados raw dos contratos PNCP (campos oficiais)
- **`contratacao_emb`** - Embeddings vetoriais + resultados de categorização
- **`categoria`** - Base de categorias com embeddings para matching
- **`item_contratacao`** - Itens detalhados das contratações
- **`system_config`** - Controle de processamento e configurações

### Campos de Controle Críticos
- **`last_download_date`** - Controla download incremental PNCP
- **`last_embedding_date`** - Controla geração de embeddings
- **`last_categorization_date`** - Controla categorização
- **`numero_controle_pncp`** - Chave única oficial PNCP

## ⚙️ Configuração Técnica

### 1. Credenciais (.env)
```env
# Supabase PostgreSQL
SUPABASE_HOST=seu-projeto.supabase.co
SUPABASE_DBNAME=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=sua-senha-segura
SUPABASE_PORT=5432

# OpenAI para embeddings
OPENAI_API_KEY=sua-chave-openai

# Dados históricos (opcional)
V0_SQLITE_PATH=../v0/database/govgo.db
```

### 2. Dependências Críticas
```bash
pip install psycopg2-binary pandas requests rich python-dotenv
pip install openai numpy pgvector-python
```

### 3. Extensões PostgreSQL
- **pgvector** - Para similarity search de embeddings
- **uuid-ossp** - Para identificadores únicos

## 📈 Performance e Monitoramento

### Rich Progress em Tempo Real
- **Download**: Progresso de contratações e itens
- **Embeddings**: Taxa OpenAI tokens/segundo
- **Categorização**: ✅ Categorizados | ⏭️ Pulados | ❌ Erros

### Otimizações de Performance
- **Download**: 20 workers paralelos, retry automático
- **Embeddings**: Batch size adaptativo, pool de conexões
- **Categorização**: Workers adaptativos 4-20 baseado no volume

### Volume Diário Típico
| Métrica | Volume Diário | Tempo Estimado |
|---------|---------------|----------------|
| Contratos novos | 1k-5k | Download: 30min-2h |
| Embeddings | 1k-5k | Processamento: 20min-1h |
| Categorização | 1k-5k | Classificação: 10min-30min |

## 🔧 Resolução de Problemas

### Falha no Download PNCP
1. Verifique conectividade com API PNCP
2. API pode estar temporariamente indisponível
3. Logs detalhados em `../logs/03B_pncp_parallel_*.log`

### Erro de Embeddings OpenAI
1. Verifique créditos da conta OpenAI
2. Confirme OPENAI_API_KEY válida no `.env`
3. Rate limits da OpenAI podem estar atingidos

### Performance de Categorização
1. Monitore uso de CPU/RAM durante processamento
2. Ajuste `MAX_WORKERS` se necessário (padrão: 20)
3. pgvector similarity search requer RAM suficiente

## 🔄 Operação Contínua

### Rotina Diária Obrigatória
1. **08:00** - Execute `00_run_pncp_scripts.bat`
2. **Monitoramento** - Acompanhe Rich Progress de cada etapa
3. **Verificação** - Confirme estatísticas finais
4. **Log** - Verifique erros se houver

### Manutenção Periódica
- **Semanal**: Analisar logs de erro acumulados
- **Mensal**: Otimizar índices PostgreSQL
- **Trimestral**: Avaliar performance de categorização

### Backup e Continuidade
- Supabase faz backup automático
- Processamento é incremental (retomável)
- Sistema anti-duplicação protege integridade

## 📞 Suporte Técnico

### Diagnóstico de Problemas
```bash
# Teste cada etapa separadamente
python 03_download_pncp_contracts.py    # Teste API PNCP
python 04_generate_embeddings.py        # Teste OpenAI
python 05_categorize_contracts.py       # Teste categorização
```

### Logs e Debugging
- **Download**: `../logs/03B_pncp_parallel_*.log`
- **Embeddings**: Output detalhado no console
- **Categorização**: Rich Progress + estatísticas finais

Para suporte, inclua sempre:
1. Logs completos da execução com erro
2. Arquivo `.env` (sem senhas)
3. Estatísticas de sistema (CPU, RAM, espaço)
4. Descrição detalhada do comportamento

---

**Versão**: V1.0 Production  
**Última atualização**: Janeiro 2025  
**Compatibilidade**: Python 3.8+, PostgreSQL 13+, pgvector, OpenAI API

## 📝 Scripts Individuais

### Setup Inicial (Execute apenas uma vez)

#### 99_reset_database_tables.py
**Reset Completo do Banco**
- ⚠️ **CUIDADO**: Apaga todas as tabelas
- Use apenas para reconfiguração completa
- Perde todos os dados processados

```bash
python 99_reset_database_tables.py
```

#### 01_create_database_schema.py
**Criação do Schema**
- Cria todas as tabelas necessárias
- Define índices e relacionamentos
- Configura extensões PostgreSQL/pgvector

```bash
python 01_create_database_schema.py
```

#### 02_import_initial_data.py
**Importação de Dados Iniciais**
- Importa categorias de produtos/serviços
- Configura parâmetros do sistema
- Carrega dados de referência

```bash
python 02_import_initial_data.py
```

### Pipeline de Processamento (Execute regularmente)

#### 03_download_pncp_contracts.py
**Download de Contratos PNCP**
- Coleta contratos via API PNCP paralela
- Download incremental (apenas novos)
- Sistema robusto com retry automático
- **Tempo estimado**: 2-6 horas (dependendo do volume)

```bash
python 03_download_pncp_contracts.py
```

#### 04_generate_embeddings.py
**Geração de Embeddings**
- Cria vetores semânticos dos textos
- Processamento otimizado em lotes
- Suporte a múltiplos modelos de embedding
- **Tempo estimado**: 1-3 horas (dependendo do volume)

```bash
python 04_generate_embeddings.py
```

#### 05_categorize_contracts.py
**Categorização Automática**
- Classifica contratos usando IA + pgvector
- Processamento paralelo adaptativo (4-32 workers)
- Rich Progress Bar em tempo real
- Sistema anti-duplicação integrado
- **Tempo estimado**: 15-20 horas para ~825k contratos

```bash
python 05_categorize_contracts.py
```

## 📊 Estrutura do Banco de Dados

### Tabelas Principais
- **`contratacao`** - Dados principais dos contratos
- **`contratacao_emb`** - Embeddings e categorizações
- **`categoria`** - Categorias de produtos/serviços
- **`system_config`** - Configurações do sistema

### Campos Importantes
- **`numero_controle_pncp`** - ID único do contrato
- **`embeddings`** - Vetores semânticos (pgvector)
- **`top_categories`** - Top 5 categorias similares
- **`confidence`** - Confiança da categorização
- **`last_processed_date`** - Controle de última data de processamento
- **`last_embedding_date`** - Controle da última data de embedding 
- **`last_categorization_date`** - Controle de última data de categorização

## ⚙️ Configuração

### 1. Arquivo .env
Configure as credenciais do Supabase:
```env
SUPABASE_HOST=seu-projeto.supabase.co
SUPABASE_DBNAME=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=sua-senha-super-segura
SUPABASE_PORT=5432
```

### 2. Dependências Python
```bash
pip install psycopg2-binary pandas requests rich python-dotenv pgvector
```

### 3. Extensões PostgreSQL
O banco deve ter as extensões:
- `pgvector` - Para similarity search
- `uuid-ossp` - Para UUIDs

## 🔍 Monitoramento e Logs

### Progress Bars em Tempo Real
- **Rich Progress** com estatísticas detalhadas
- Tempo executado / tempo restante
- Contadores: ✅ Categorizados | ⏭️ Pulados | ❌ Erros
- Taxa de processamento (contratos/segundo)

### Sistema de Controle
- **`last_categorization_date`** - Última data processada
- **`last_embedding_date`** - Última data com embeddings
- **Anti-duplicação** - Evita reprocessamento desnecessário

### Logs de Sistema
- Output detalhado no console
- Estatísticas finais de cada execução
- Relatórios de performance e erros

## 📈 Performance e Otimizações

### Processamento Paralelo
- **Workers Adaptativos**: 4-32 baseado no volume
- **Batch Processing**: Lotes de 100 contratos
- **ThreadPoolExecutor** para paralelização

### Otimizações de Banco
- **Índices otimizados** para queries frequentes
- **pgvector similarity search** para categorização
- **Conexões pooled** para melhor performance

### Estimativas de Tempo
| Volume | Download | Embeddings | Categorização |
|--------|----------|------------|---------------|
| 1k contratos | ~5 min | ~10 min | ~30 min |
| 10k contratos | ~30 min | ~1 hora | ~3 horas |
| 100k contratos | ~3 horas | ~8 horas | ~24 horas |
| 825k contratos | ~6 horas | ~20 horas | ~20 horas |

## 🔧 Resolução de Problemas

### Erro de Conexão
1. Verifique credenciais no `.env`
2. Confirme conectividade com Supabase
3. Verifique firewall/proxy

### Performance Lenta
1. Monitore uso de CPU/RAM
2. Ajuste `MAX_WORKERS` se necessário
3. Verifique latência da rede

### Erros de Categorização
1. Verifique se embeddings foram gerados
2. Confirme que categorias estão carregadas
3. Monitore logs de erro detalhados

### Timeout de API
1. API PNCP pode estar temporariamente indisponível
2. Sistema tem retry automático
3. Execute novamente após algumas horas

## 🔄 Execução Contínua

### Pipeline Diário OBRIGATÓRIO
1. **TODOS OS DIAS**: Execute `00_run_pncp_scripts.bat`
2. **Horário recomendado**: Primeira coisa pela manhã (8h-9h)
3. **Monitor**: Acompanhe progresso via Rich Progress
4. **Verificação**: Confirme estatísticas finais antes de sair

### Por que execução diária é obrigatória?
- **Contratos novos**: PNCP publica contratos diariamente
- **Volume crescente**: Atraso gera acúmulo exponencial
- **Performance**: Lotes menores são mais eficientes
- **Disponibilidade**: Sistema sempre atualizado para consultas

### Manutenção Semanal
- Verificar logs de erro acumulados
- Analisar performance de categorização
- Ajustar parâmetros se necessário
- Monitorar espaço em disco

### Backup e Segurança
- Supabase faz backup automático
- Dados são incrementais (não sobrescreve)
- Sistema anti-duplicação protege integridade

## 📞 Suporte

### Debug Individual
Execute scripts separadamente para identificar problemas:
```bash
python 03_download_pncp_contracts.py    # Teste download
python 04_generate_embeddings.py        # Teste embeddings  
python 05_categorize_contracts.py       # Teste categorização
```

### Logs Detalhados
- Console mostra progresso em tempo real
- Estatísticas finais incluem rates e tempos
- Erros são reportados com contexto específico

### Contato
Para suporte técnico, inclua:
1. Logs completos da execução
2. Configuração do ambiente (.env mascarado)
3. Descrição detalhada do problema
4. Estatísticas do sistema (RAM, CPU, rede)

---

**Versão**: V1.0  
**Última atualização**: Agosto 2025  
**Compatibilidade**: Python 3.8+, PostgreSQL 13+, pgvector
