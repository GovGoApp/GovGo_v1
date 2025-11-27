# Sommelier — fluxo de snapshots

## Estrutura de `sommelier.prompt`

| Coluna      | Tipo   | Descrição |
|-------------|--------|-----------|
| `dados`     | jsonb  | Snapshot completo da empresa (payload encaminhado para `store-company`). Deve conter ao menos `cnpj`, `razao_social`, `municipio`, `uf` e `timestamp` ISO. |
| `contratos` | jsonb  | Lista já ordenada dos contratos renderizados na aba Contratos, incluindo `lat`/`lon` resolvidos no momento da busca. |
| `editais`   | jsonb  | Lista ordenada dos editais renderizados na aba Editais, também com `lat`/`lon`. |

### Formato dos itens

#### Contratos
```json
{
  "numero_controle_pncp": "BR2025-00012345",
  "orgao_entidade_razao_social": "Prefeitura de Campinas",
  "unidade_orgao_municipio_nome": "Campinas",
  "unidade_orgao_uf_sigla": "SP",
  "unidade_orgao_codigo_ibge": "3509502",
  "objeto_contrato": "Descrição resumida",
  "valor_total_homologado": 125000.75,
  "data_encerramento_proposta": "2025-12-18",
  "link_sistema_origem": "https://pncp.gov.br/...",
  "lat": -22.909938,
  "lon": -47.062633
}
```

#### Editais
```json
{
  "numero_controle_pncp": "BR2025-00054321",
  "orgao_entidade_razao_social": "Ministério X",
  "unidade_orgao_municipio_nome": "Brasília",
  "unidade_orgao_uf_sigla": "DF",
  "unidade_orgao_codigo_ibge": "5300108",
  "objeto_compra": "Objeto do edital",
  "valor_total_homologado": 98000.0,
  "data_encerramento_proposta": "2025-11-30",
  "similarity": 0.87,
  "final_score": 0.91,
  "link_sistema_origem": "https://pncp.gov.br/...",
  "lat": -15.793889,
  "lon": -47.882778
}
```

Campos adicionais podem ser preservados contanto que permaneçam serializáveis em JSON.

## Fluxo “Buscar” vs “Repetir”

1. **Buscar** executa `run_search`, monta os snapshots (`dados`, `contratos`, `editais`) e salva em `sommelier.prompt` via `insert_cnpj_prompt`.
2. **Repetir** apenas carrega o snapshot existente (sem chamar `run_search`), preenche `store-company`, `store-contratos`, `store-editais` e re-renderiza as abas/mapas imediatamente.

Dessa forma, tanto o histórico local quanto o banco mantêm uma única entrada por `(user_id, cnpj)` com dados completos para reuso instantâneo.

## Configuração de ambiente local

- O app carrega automaticamente o arquivo `.env` desta pasta (`search/gvg_select/.env`).
- Esse arquivo precisa conter todas as variáveis `SUPABASE_*`, chaves da OpenAI e demais parâmetros usados pelo `gvg_cnpj_search`.
- Em produção (ex.: Render), replique esses valores nas variáveis de ambiente do serviço; o `.env` local serve apenas para desenvolvimento.
