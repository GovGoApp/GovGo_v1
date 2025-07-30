# GovGo V1 - Sistema Unificado de Licitações 🏛️

Sistema de análise e busca de documentos PNCP (Portal Nacional de Contratações Públicas) com **total compatibilidade** com o sistema V0 existente.

## 🎯 Características Principais

- **✅ 100% Compatível** com sistema V0 existente
- **🔄 Migração Segura** mantendo dados intactos
- **🔍 Busca Híbrida** semântica + textual + vetorial
- **📊 4 Tipos de Documentos** contratações, contratos, atas, PCAs
- **⚡ Pipeline Simplificado** 7 → 4 etapas
- **🗄️ Banco Unificado** Supabase com pgvector
- **🤖 IA Integrada** OpenAI para processamento

## 🏗️ Arquitetura

```
v1/
├── core/                   # Núcleo do sistema
│   ├── config.py          # Configurações centralizadas
│   ├── database.py        # Gerenciador Supabase + compatibilidade V0
│   ├── models.py          # Modelos de dados (V0 + V1)
│   └── logging_config.py  # Sistema de logs
├── collectors/             # Coletores de dados PNCP
├── processors/             # Processadores de documentos
├── search/                 # Sistema de busca unificado
├── setup_database.py      # Script de setup do banco
├── migrate_data.py         # Migração V0 → V1
├── test_setup.py          # Validação do sistema
└── examples.py            # Exemplos de uso
```

## 🚀 Quick Start

### 1. Configuração Inicial

```bash
# Clone e configure ambiente
cd "c:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\v1"

# Configure variáveis de ambiente (.env)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key
DATABASE_URL=postgresql://user:pass@host:port/db
```

### 2. Validação do Sistema

```bash
# Testa configuração e compatibilidade
python test_setup.py
```

### 3. Setup do Banco (se necessário)

```bash
# Cria tabela unificada documentos_pncp
python setup_database.py
```

### 4. Migração dos Dados (opcional)

```bash
# Migra dados V0 para estrutura V1
python migrate_data.py
```

### 5. Exemplos de Uso

```bash
# Demonstra funcionalidades
python examples.py
```

## 📊 Compatibilidade Total com V0

### Busca Compatível

```python
from core.database import supabase_manager

# Busca igual ao gvg_search_utils_v3.py
resultados = supabase_manager.buscar_compativel_v0(
    query="equipamento médico",
    search_type='hybrid',  # semantic, textual, hybrid
    limit=10
)

for resultado in resultados:
    print(f"{resultado.numerocontrolepncp}: {resultado.objeto}")
    print(f"Similaridade: {resultado.similarity}")
```

### Acesso aos Dados Existentes

```python
# Busca contratações (formato V0)
contratacoes = supabase_manager.buscar_contratacoes(
    texto_busca="software",
    limite=10
)

# Insere embedding (compatível com contratacoes_embeddings)
supabase_manager.inserir_embedding(
    numero_controle="12345678901234567890",
    embedding=[0.1, 0.2, 0.3, ...]  # 3072 dimensões
)
```

### Conversão de Dados

```python
# Converte contratação V0 para documento V1
dados_v0 = supabase_manager.buscar_contratacoes(limite=1)[0]
documento_v1 = supabase_manager.converter_contratacao_para_documento(dados_v0)

print(f"V0: {dados_v0['numerocontrolepncp']}")
print(f"V1: {documento_v1.numero_controle_pncp}")
```

## 🔍 Sistema de Busca Unificado

### Busca Semântica (Embeddings)

```python
# Busca por similaridade vetorial
documentos = supabase_manager.buscar_documentos_unificado(
    embedding=embedding_vector,  # 3072 dimensões
    tipos_documento=["contratacao", "contrato"],
    threshold=0.8,
    limite=10
)
```

### Busca Textual (PostgreSQL FTS)

```python
# Busca por texto completo
documentos = supabase_manager.buscar_documentos_unificado(
    texto_busca="consultoria tecnologia",
    tipos_documento=["contratacao", "ata"],
    limite=10
)
```

### Busca Híbrida (Combinada)

```python
# Combina busca semântica + textual
resultados = supabase_manager.buscar_compativel_v0(
    query="equipamento hospitalar",
    search_type='hybrid',
    limit=20
)
```

## 📈 Estrutura de Dados

### Modelo Unificado (V1)

```python
class DocumentoPNCP:
    numero_controle_pncp: str      # Chave primária
    tipo_documento: str            # contratacao, contrato, ata, pca
    dados_originais: Dict          # JSON com dados completos da API
    objeto: str                    # Descrição do objeto
    orgao_cnpj: str               # CNPJ do órgão
    orgao_razao_social: str       # Nome do órgão
    unidade_codigo: str           # Código da unidade
    unidade_nome: str             # Nome da unidade
    valor_estimado: float         # Valor estimado
    situacao: str                 # Status do documento
    modalidade: str               # Modalidade de licitação
    data_publicacao: datetime     # Data de publicação
    status_processamento: str     # processado, erro, pendente
    embedding: List[float]        # Vetor 3072D para busca semântica
```

### Compatibilidade V0

```python
class ContratacaoSupabase:
    numerocontrolepncp: str
    objeto: str
    orgaoentidade_cnpj: str
    orgaoentidade_razaosocial: str
    unidadeorcamentaria_codigo: str
    unidadeorcamentaria_nome: str
    valorestimado: float
    situacao: str
    # ... todos os campos do PNCP_DB_v2
```

## 🛠️ Pipeline de Processamento

### 1. Coleta (Collectors)
- **PNCP API Client**: Coleta dados de contratações, contratos, atas e PCAs
- **Rate Limiting**: Controle de requisições
- **Retry Logic**: Recuperação de falhas

### 2. Processamento (Processors)  
- **Docling Integration**: Extração de texto de PDFs
- **Data Cleaning**: Limpeza e normalização
- **Validation**: Validação de integridade

### 3. Embeddings (OpenAI)
- **text-embedding-3-large**: Vetores 3072D
- **Batch Processing**: Processamento em lotes
- **Cache System**: Cache de embeddings

### 4. Armazenamento (Database)
- **Supabase**: Banco principal
- **pgvector**: Busca vetorial
- **Full-Text Search**: Busca textual PostgreSQL

## 📊 Monitoramento e Estatísticas

```python
# Estatísticas do sistema
stats = supabase_manager.obter_estatisticas()
print(f"Contratações V0: {stats['total_contratacoes']:,}")
print(f"Documentos V1: {stats['total_documentos_pncp']:,}")
print(f"Com embeddings: {stats['contratacoes_com_embedding']:,}")

# Saúde do sistema
saude = supabase_manager.verificar_saude_sistema()
print(f"Conexão: {'OK' if saude['conexao_ok'] else 'ERRO'}")
print(f"Extensões: {saude['extensoes_instaladas']}")
print(f"Tabelas: {saude['tabelas_existentes']}")
```

## 🔧 Configuração Avançada

### Variáveis de Ambiente

```env
# Banco de dados
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=text-embedding-3-large

# Sistema
LOG_LEVEL=INFO
BATCH_SIZE=1000
MAX_RETRIES=3
RATE_LIMIT_DELAY=1.0
```

### Configuração do Banco

```sql
-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Índices de performance
CREATE INDEX IF NOT EXISTS idx_contratacoes_embedding 
ON contratacoes_embeddings USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_documentos_pncp_embedding 
ON documentos_pncp USING ivfflat (embedding vector_cosine_ops);
```

## 🧪 Testes e Validação

### Teste de Setup

```bash
python test_setup.py
```

**Verifica:**
- ✅ Configuração de variáveis
- ✅ Conexão com Supabase  
- ✅ Extensões PostgreSQL
- ✅ Tabelas existentes
- ✅ Compatibilidade V0
- ✅ Sistema de busca

### Teste de Migração

```bash
python migrate_data.py
```

**Executa:**
- 🔍 Análise dos dados V0
- 🔄 Migração em lotes
- ✅ Verificação de integridade
- 📊 Relatório de resultados

## 🚨 Solução de Problemas

### Erro de Conexão

```bash
# Verificar variáveis de ambiente
echo $SUPABASE_URL
echo $SUPABASE_KEY

# Testar conexão
python -c "from core.database import supabase_manager; print(supabase_manager.verificar_saude_sistema())"
```

### Tabelas Não Encontradas

```bash
# Executar setup do banco
python setup_database.py

# Verificar tabelas criadas
python -c "from core.database import supabase_manager; print(supabase_manager.obter_estatisticas())"
```

### Embeddings Faltando

```bash
# Verificar configuração OpenAI
echo $OPENAI_API_KEY

# Gerar embeddings em lote
python -c "from processors.embedding_processor import EmbeddingProcessor; EmbeddingProcessor().processar_pendentes()"
```

## 📚 Referências

### Documentação Relacionada
- [ARQUITETURA_V1.md](./ARQUITETURA_V1.md) - Arquitetura detalhada do sistema
- [PNCP_DB_v2.txt](../v0/PNCP_DB_v2.txt) - Schema original do banco V0
- [gvg_search_utils_v3.py](../v0/GvG/Search/Prompt/gvg_search_utils_v3.py) - Sistema de busca V0

### APIs e Integrações
- [Portal PNCP](https://pncp.gov.br/api) - API oficial de contratações
- [Supabase](https://supabase.com/docs) - Banco de dados e backend
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings) - Geração de vetores
- [pgvector](https://github.com/pgvector/pgvector) - Extensão de vetores PostgreSQL

## 🤝 Contribuição

### Estrutura de Desenvolvimento

```bash
# Desenvolvimento local
cd v1/
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Guidelines

1. **Compatibilidade**: Sempre manter compatibilidade com V0
2. **Testes**: Executar `test_setup.py` antes de commits
3. **Logs**: Usar sistema de logging configurado
4. **Documentação**: Atualizar README.md para novas funcionalidades

---

## 📝 Changelog

### V1.0.0 (2024-01-XX)
- ✨ Sistema unificado para 4 tipos de documentos PNCP
- ✨ Compatibilidade total com sistema V0
- ✨ Pipeline simplificado (7 → 4 etapas)
- ✨ Busca híbrida semântica + textual
- ✨ Migração segura de dados
- ✨ Sistema de monitoramento integrado

---

**GovGo V1** - Transformando a análise de contratações públicas com IA 🚀
