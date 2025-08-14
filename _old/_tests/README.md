# GovGo V1 - Testes

Esta pasta contém os scripts de teste para o sistema GovGo V1.

## Scripts de Teste

### test_migration.py
**Teste de Migração (Dry Run)**

Script que analisa todas as conexões e dados antes da migração real.

**Funcionalidades:**
- ✅ Teste de conectividade com todas as bases (DBL SQLite, Supabase V0, Supabase V1)
- 📊 Análise de dados disponíveis em cada fonte
- 🎯 Validação de cobertura dos embeddings
- 🏗️ Verificação de estruturas das tabelas
- ⏱️ Estimativa de tempo de migração
- 📋 Relatório completo de status

**Como usar:**
```bash
cd tests
python test_migration.py
```

**⚠️ IMPORTANTE:** Este script NÃO modifica nenhum dado - apenas analisa e reporta.

**Verificações realizadas:**
1. **Conectividade:** Testa conexão com SQLite (DBL), Supabase V0 e V1
2. **Dados:** Conta registros em todas as tabelas
3. **Embeddings:** Verifica cobertura entre embeddings V0 e dados SQLite
4. **Estruturas:** Valida se todas as tabelas V1 foram criadas corretamente
5. **Tempo:** Estima duração da migração completa

**Resultado esperado:**
- ✅ Todas as conexões funcionando
- 📊 Cobertura de embeddings > 80%
- 🏗️ Todas as 9 tabelas V1 criadas
- ⚠️ Nenhum erro crítico

Se todos os testes passarem, o sistema estará pronto para a migração real.

## Estrutura do Projeto

```
python/v1/
├── scripts/          # Scripts de migração e setup
│   ├── 00_drop_all_tables.py
│   ├── 01_setup_database.py
│   └── 02_migrate_data.py
├── tests/            # Scripts de teste
│   └── test_migration.py
└── .env             # Configurações das bases
```

## Próximos Passos

1. Execute `test_migration.py` para validar o sistema
2. Se todos os testes passarem, execute a migração real:
   ```bash
   cd ../scripts
   python 02_migrate_data.py
   ```
