# GovGo V1 - Scripts de Migração

Este diretório contém todos os scripts necessários para a migração completa do sistema GovGo da versão V0 (SQLite) para V1 (Supabase).

## 📋 Visão Geral

A migração é dividida em **FASE 2** (estrutura) e **FASE 3** (migração híbrida):

### FASE 2 - Estrutura do Banco
- ✅ Criar 7 tabelas específicas no Supabase
- ✅ Mapear campos das ATAs e PCAs via API

### FASE 3 - Migração Híbrida  
- ✅ Migrar dados do SQLite V0
- ✅ Coletar dados faltantes via API PNCP
- ✅ Reconciliar e unificar dados
- ✅ Validar integridade final

## 🚀 Execução Rápida

Para executar toda a migração de uma vez:

```bash
python run_migration.py
```

## 📝 Scripts Individuais

### 01_setup_database.py
**Configurar Base Supabase**
- Cria as 7 tabelas no Supabase
- Define índices e relacionamentos
- Substitui a abordagem de tabela unificada

```bash
python 01_setup_database.py
```

### 02_descobrir_campos_ata_pca.py  
**Descobrir Campos API**
- Mapeia campos reais das ATAs e PCAs
- Gera estruturas SQL baseadas na API
- Documenta campos descobertos

```bash
python 02_descobrir_campos_ata_pca.py
```

### 03_migrate_from_local.py
**Migrar Dados Locais**
- Migra SQLite V0 → Supabase V1
- Mantém integridade referencial
- Marca origem dos dados

```bash
python 03_migrate_from_local.py
```

### 04_collect_from_api.py
**Coletar Dados via API**
- Busca contratos faltantes
- Coleta ATAs dos últimos 12 meses
- Coleta PCAs dos últimos 3 anos

```bash
python 04_collect_from_api.py
```

### 05_reconcile_data.py
**Reconciliar Dados**
- Resolve duplicatas entre local e API
- Unifica registros com melhores dados
- Detecta e reporta conflitos

```bash
python 05_reconcile_data.py
```

### 06_migration_report.py
**Relatório Final**
- Compara V0 vs V1
- Valida integridade de dados
- Testa performance
- Gera recomendações

```bash
python 06_migration_report.py
```

## 📊 Estrutura das Tabelas V1

### Tabelas Principais (migradas de V0)
1. **contratacoes** - Dados de contratações/compras
2. **contratos** - Contratos assinados
3. **itens_contratacao** - Itens das contratações
4. **classificacoes_itens** - Classificações dos itens
5. **categorias** - Categorias de produtos/serviços

### Tabelas Novas (dados API)
6. **atas** - Atas de Registro de Preço
7. **pcas** - Planos de Contratações Anuais

## 🔧 Configuração Necessária

### 1. Credenciais Supabase
Configure as variáveis no arquivo `core/config.py`:
```python
SUPABASE_HOST = "seu-projeto.supabase.co"
SUPABASE_DATABASE = "postgres"  
SUPABASE_USER = "postgres"
SUPABASE_PASSWORD = "sua-senha"
SUPABASE_PORT = 5432
```

### 2. Banco SQLite V0
O arquivo `govgo.db` deve estar em:
```
../v0/database/govgo.db
```

### 3. Dependências Python
```bash
pip install psycopg2-binary pandas requests rich
```

## 📈 Monitoramento

### Logs Gerados
- `migracao_completa_log.json` - Log master completo
- `relatorio_migracao_completo.json` - Relatório final detalhado
- `relatorio_migracao_resumo.txt` - Resumo em texto
- `comparacao_dados_migracao.csv` - Comparação V0 vs V1

### Status de Execução
- ✅ **SUCESSO** - Script executado sem problemas
- ⚠️ **ATENÇÃO** - Concluído com ressalvas
- ❌ **FALHA** - Erro crítico na execução
- ⏱️ **TIMEOUT** - Excedeu tempo limite (30min)

## 🎯 Resultados Esperados

### Dados Migrados
- **~50.000+** contratações
- **~30.000+** contratos  
- **~200.000+** itens
- **~500.000+** classificações
- **~1.000+** categorias

### Dados Novos (API)
- **ATAs** dos últimos 12 meses
- **PCAs** dos últimos 3 anos
- **Contratos** faltantes

### Performance V1
- Consultas por ano: **< 1s**
- Joins complexos: **< 2s**
- Buscas de texto: **< 3s**

## ⚠️ Resolução de Problemas

### Erro de Conexão Supabase
1. Verifique credenciais em `config.py`
2. Confirme que o projeto Supabase está ativo
3. Teste conectividade de rede

### Erro SQLite não encontrado
1. Verifique caminho do `govgo.db`
2. Execute migração do V0 primeiro
3. Confirme permissões de leitura

### Timeout na API PNCP
1. Verifique conexão com internet
2. A API pode estar temporariamente indisponível
3. Execute novamente após algumas horas

### Duplicatas detectadas
1. Normal após múltiplas execuções
2. O script 05 resolve automaticamente
3. Verifique relatório de reconciliação

## 🔄 Reexecução

Os scripts são **idempotentes** - podem ser executados múltiplas vezes:

- **Scripts 01-02**: Recriam estruturas (safe)
- **Scripts 03-04**: Detectam dados existentes (skip)
- **Scripts 05-06**: Processam apenas novos conflitos

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs gerados
2. Consulte este README
3. Execute scripts individuais para debug
4. Analise mensagens de erro específicas

---

**Versão**: V1.0  
**Última atualização**: Dezembro 2024  
**Compatibilidade**: Python 3.8+, PostgreSQL 13+
