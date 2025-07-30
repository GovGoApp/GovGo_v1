# 📁 Pasta _old - Backups e Arquivos Antigos

Esta pasta contém backups e versões antigas de arquivos criados durante o processo de reestruturação do GovGo V1.

## 📋 Conteúdo:

### `setup_database_original.py`
- **Origem**: Arquivo original do V1 antes da reestruturação
- **Descrição**: Versão original que usava tabela unificada `documentos_pncp`
- **Status**: SUBSTITUÍDO pela nova versão com 7 tabelas específicas
- **Data**: Backup criado em 30/07/2025

### `setup_database_backup.py`
- **Origem**: Backup adicional criado durante a reestruturação
- **Descrição**: Backup de segurança da versão original
- **Status**: BACKUP SECUNDÁRIO
- **Data**: Backup criado em 30/07/2025

## 🔄 Processo de Reestruturação:

### ANTES (Original):
- ❌ 1 tabela unificada `documentos_pncp` 
- ❌ Campos específicos armazenados em JSONB
- ❌ Estrutura não otimizada para queries específicas

### DEPOIS (Nova versão):
- ✅ 7 tabelas específicas:
  1. `contratacoes` (Compras/Editais/Avisos)
  2. `contratos` (Contratos firmados)
  3. `itens_contratacao` (Itens das contratações)
  4. `classificacoes_itens` (Classificação ML)
  5. `categorias` (Categorias de produtos)
  6. `atas` (Atas de Registro de Preço) - NOVO
  7. `pcas` (Planos de Contratações) - NOVO

- ✅ Estrutura baseada no SQLite V0 + Manual PNCP
- ✅ Relacionamentos otimizados (Foreign Keys)
- ✅ Índices para performance
- ✅ Triggers automáticos
- ✅ Busca full-text

## ⚠️ Importante:
**NÃO DELETE** estes arquivos! Eles são importantes para:
- Histórico do desenvolvimento
- Possível reversão se necessário
- Comparação entre versões
- Documentação do processo

## 📝 Logs da Reestruturação:
- **30/07/2025**: Início da FASE 2 - Reestruturação da base Supabase
- **30/07/2025**: Backup da versão original
- **30/07/2025**: Criação da nova estrutura com 7 tabelas específicas
- **30/07/2025**: Implementação de ATAs e PCAs baseadas no Manual PNCP
- **30/07/2025**: Arquivos movidos para pasta _old
