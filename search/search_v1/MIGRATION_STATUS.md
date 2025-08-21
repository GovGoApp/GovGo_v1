## Migração Search V1 – Status Atual (Consolidação Plano B)

Data: 2025-08-15

Decisão: Eliminado modo de compatibilidade/aliases v0. Resultado exposto somente em snake_case conforme schema central (`gvg_schema.py`).

### Concluído
- Refatoração `gvg_search_core` (semantic / keyword / hybrid) usando campos V1 snake_case.
- Exporters (`gvg_exporters.py`) ajustados para consumir apenas snake_case.
- `GvG_Search_Function.py` atualizado (ordenar e exibir usando snake_case).
- Remoção de fallbacks CamelCase/versões mistas nos pontos alterados.

### Pendente (Próximos Passos)
1. Atualizar `GvG_Search_Terminal.py` (UI permanece funcional; remover quaisquer resíduos de fallback se existirem – não prioritário imediato a pedido do usuário).
2. Tests básicos automatizados (latência, ordenação, filtros de data, consistência de colunas) consumindo `sanity_check()` como guarda inicial.
3. Integração opcional das recomendações de índices (`index_advice`) em documentação operativa / script SQL.
4. Avaliar necessidade de normalização numérica para `valor_total_estimado` (tipo numeric_text) antes de ranking avançado.
5. Pequeno harness de benchmark persistindo resultados (atual: função `simple_benchmark`).

### Convenção Oficial
| Conceito | Campo Final |
|----------|-------------|
| ID Processo | numero_controle_pncp |
| Texto principal | objeto_compra |
| Valor estimado | valor_total_estimado |
| Encerramento | data_encerramento_proposta |
| Inclusão | data_inclusao |
| Unidade | unidade_orgao_nome_unidade |
| Município | unidade_orgao_municipio_nome |
| UF | unidade_orgao_uf_sigla |
| Órgão | orgao_entidade_razao_social |

### Justificativas
- Reduz complexidade: evita manter dupla camada de alias.
- Minimiza risco de esquecer remoção de compat no futuro.
- Facilita indexação e tuning (nomes consistentes nos scripts SQL).

### Riscos / Mitigação
| Risco | Mitigação |
|-------|-----------|
| Algum consumidor externo ainda espera CamelCase | Comunicar mudança + adaptar chamada; adicionar teste de contrato |
| Campos de data como TEXT | Cast explícito `to_date()` já aplicado nas queries; planejar coluna derivada em etapa de otimização |

### Ação Imediata Recomendada
Introduzir suíte de testes mínimos + executar `sanity_check()` em pipeline CI para garantir aderência ao schema central; posteriormente decidir sobre atualização fina do Terminal.

---
Arquivo gerado automaticamente como parte da consolidação da Fase 2/3 (Plano B).