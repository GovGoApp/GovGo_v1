-- =========================================================================
-- SCRIPT PARA ANÁLISE COMPLETA DE ESTRUTURA DE DATABASE SQLite
-- =========================================================================

-- SQL ÚNICO PARA PEGAR OS CREATE STATEMENTS DE TODAS AS TABELAS
SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name;

-- 2. OBTER INFORMAÇÕES DETALHADAS DE CADA TABELA
SELECT '=== ESTRUTURA DAS TABELAS ===' as info;

-- Para cada tabela, você precisará executar:
-- PRAGMA table_info(nome_da_tabela);

-- 3. OBTER TODOS OS CREATE STATEMENTS
SELECT '=== CREATE STATEMENTS ===' as info;
SELECT 
    name as table_name,
    sql as create_statement
FROM sqlite_master 
WHERE type='table' 
ORDER BY name;

-- 4. LISTAR ÍNDICES
SELECT '=== ÍNDICES ===' as info;
SELECT 
    name as index_name,
    tbl_name as table_name,
    sql as create_statement
FROM sqlite_master 
WHERE type='index' 
ORDER BY tbl_name, name;

-- 5. LISTAR TRIGGERS
SELECT '=== TRIGGERS ===' as info;
SELECT 
    name as trigger_name,
    tbl_name as table_name,
    sql as create_statement
FROM sqlite_master 
WHERE type='trigger' 
ORDER BY tbl_name, name;

-- 6. LISTAR VIEWS
SELECT '=== VIEWS ===' as info;
SELECT 
    name as view_name,
    sql as create_statement
FROM sqlite_master 
WHERE type='view' 
ORDER BY name;

-- 7. ESTATÍSTICAS DAS TABELAS
SELECT '=== ESTATÍSTICAS ===' as info;
-- Para cada tabela, você precisará executar:
-- SELECT COUNT(*) as row_count FROM nome_da_tabela;

-- 8. INFORMAÇÕES DO BANCO
SELECT '=== INFORMAÇÕES DO BANCO ===' as info;
PRAGMA database_list;
PRAGMA user_version;
PRAGMA application_id;
PRAGMA page_count;
PRAGMA page_size;
PRAGMA freelist_count;

-- 9. CHAVES ESTRANGEIRAS (se habilitadas)
SELECT '=== CHAVES ESTRANGEIRAS ===' as info;
-- Para cada tabela, você precisará executar:
-- PRAGMA foreign_key_list(nome_da_tabela);

-- 10. VERIFICAR INTEGRIDADE
SELECT '=== VERIFICAÇÃO DE INTEGRIDADE ===' as info;
PRAGMA integrity_check;
