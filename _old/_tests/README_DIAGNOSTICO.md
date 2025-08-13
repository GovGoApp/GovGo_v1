# Testes de Diagnóstico do Banco de Dados - 04B Embeddings

Este diretório contém testes específicos para diagnosticar problemas de timeout na geração de embeddings do script `04B_embedding_generation_optimized.py`.

## 📋 Testes Disponíveis

### 1. `test_database_queries.py`
**Teste geral do banco de dados**
- ✅ Verifica conexão básica
- 📊 Analisa tamanho das tabelas 
- ⚙️ Verifica configurações do `system_config`
- 🏗️ Lista índices existentes
- 🎯 Testa queries em intervalos pequenos
- 🔥 Testa o intervalo problemático completo

### 2. `test_04B_query.py` 
**Teste específico da query problemática**
- 🎯 Replica EXATAMENTE a função `get_dates_needing_embeddings()`
- 🔍 Analisa cada parte da query separadamente
- ⏰ Monitora timeouts com 2 minutos de limite
- 💡 Sugere otimizações específicas

### 3. `test_performance_analysis.py`
**Análise de performance e índices**
- 📊 Verifica estatísticas das tabelas
- 🏗️ Analisa índices existentes e sua utilização
- 📋 Mostra planos de execução (EXPLAIN)
- 💡 Sugere índices faltando
- 🔄 Testa queries alternativas (NOT EXISTS, LEFT JOIN)

## 🚀 Como Executar

### Pré-requisitos
Certifique-se de que as variáveis de ambiente estão configuradas:
```bash
export SUPABASE_HOST="aws-0-sa-east-1.pooler.supabase.com"
export SUPABASE_PORT="6543"
export SUPABASE_DATABASE="postgres"
export SUPABASE_USER="postgres.xrcqjnvltvhkwrqvvddf"
export SUPABASE_PASSWORD="sua_senha_aqui"
```

### Executar Testes

**1. Teste geral (recomendado começar por este):**
```bash
cd "c:\\Users\\Haroldo Duraes\\Desktop\\PYTHON\\Python Scripts\\#GOvGO\\python\\v1\\tests"
python test_database_queries.py
```

**2. Teste específico da query problemática:**
```bash
python test_04B_query.py
```

**3. Análise de performance:**
```bash
python test_performance_analysis.py
```

## 📊 O Que Esperar

### Se o problema for **TIMEOUT**:
```
❌ TIMEOUT! Query cancelada após 2 minutos
💡 Sugestões:
   - Criar índices específicos
   - Processar em chunks menores
   - Usar query alternativa
```

### Se o problema for **VOLUME DE DADOS**:
```
📊 Registros no intervalo: 2.5M registros
⚠️ Intervalo muito grande! Query seria muito lenta
💡 Solução: Processar em chunks de 1 mês
```

### Se o problema for **ÍNDICES FALTANDO**:
```
🏗️ Índices relevantes em 'contratacao':
   ❌ Nenhum índice relevante encontrado!
💡 Criar: idx_contratacao_data_pub_func
```

## 🔧 Otimizações Sugeridas

### Índices Recomendados:
```sql
-- 1. Índice funcional para data_publicacao_pncp
CREATE INDEX CONCURRENTLY idx_contratacao_data_pub_func 
ON contratacao (TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD'));

-- 2. Índice para numero_controle_pncp na contratacao
CREATE INDEX CONCURRENTLY idx_contratacao_numero_controle 
ON contratacao (numero_controle_pncp);

-- 3. Índice para numero_controle_pncp na contratacao_emb
CREATE INDEX CONCURRENTLY idx_contratacao_emb_numero_controle 
ON contratacao_emb (numero_controle_pncp);

-- 4. Índice composto (apenas se necessário)
CREATE INDEX CONCURRENTLY idx_contratacao_composite 
ON contratacao (TO_DATE(data_publicacao_pncp, 'YYYY-MM-DD'), numero_controle_pncp);
```

### Query Alternativa (mais eficiente):
```sql
-- Usar LEFT JOIN ao invés de NOT IN/EXISTS
SELECT DISTINCT TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') as data_processamento
FROM contratacao c
LEFT JOIN contratacao_emb e ON c.numero_controle_pncp = e.numero_controle_pncp
WHERE c.data_publicacao_pncp IS NOT NULL 
  AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') > %s::date
  AND TO_DATE(c.data_publicacao_pncp, 'YYYY-MM-DD') <= %s::date
  AND e.numero_controle_pncp IS NULL
ORDER BY data_processamento
```

## 🚨 IMPORTANTE

- ⚠️ **Use CONCURRENTLY** ao criar índices para não bloquear a tabela
- 🔍 **Execute ANALYZE** após criar novos índices
- 📊 **Monitore o espaço em disco** ao criar índices grandes
- ⏰ **Índices funcionais** podem demorar muito para criar em tabelas grandes

## 📈 Interpretação dos Resultados

### ✅ **Sucesso**:
```
✅ Query executada com sucesso!
📅 Datas encontradas: 45
⏱️ Tempo de execução: 3.24s
```

### ⚠️ **Problema de Performance**:
```
⏱️ Tempo de execução: 89.45s
⚠️ Query muito lenta! Considere otimizações.
```

### ❌ **Timeout**:
```
⏰ TIMEOUT! Query cancelada após 2 minutos
🔥 Intervalo muito grande: 2.5M registros
```

## 🆘 Troubleshooting

**Erro de conexão?**
- Verifique as variáveis de ambiente
- Confirme se o Supabase está acessível
- Verifique se a senha está correta

**Timeout mesmo em queries pequenas?**
- Pode ser problema de rede
- Tabela pode estar travada por outro processo
- Considere reiniciar a conexão com Supabase

**Muitos registros?**
- Use chunks menores no processamento
- Considere arquivar dados antigos
- Implemente processamento incremental mais agressivo
