# Plano de Implementação de Precificação, Venda e Cobrança

Este documento descreve o desenho completo para introdução de planos pagos no GovGo (Dash + Postgres) cobrindo dados, backend, UI e enforcement de limites.

## 1. Objetivos
- Exibir planos e permitir upgrade/downgrade/cancelamento.
- Cobrança recorrente mensal via gateway.
- Aplicar limites (consultas, favoritos, boletim, resumos) em tempo real.
- Mostrar plano atual e consumo ao usuário.
- Base: tabela `system_plans`.

### 1.1 Plataforma de Pagamento (Decisão)
Requisitos: recorrência mensal, boleto + pix + cartão (BRL), webhooks estáveis, antifraude básico, suporte fiscal Brasil.

Opções avaliadas (resumo):
- Stripe: excelente API; limita boleto PIX Brasil via parceiros; câmbio USD; possível aumento de custo.
- Mercado Pago: forte em boleto/PIX, API menos padronizada para assinaturas multi‑plano com trial.
- Pagar.me / Stone: recorrência robusta, cartão + boleto, antifraude integrado, settlement em BRL, boa documentação webhooks.
- Iugu / Vindi: foco em billing, porém custo maior e dependência de plataforma fechada.

Escolha recomendada: Pagar.me (camada gateway primária) com abstração para futura inclusão Stripe.

Abstração proposta:
`gateway/` módulo com interface:
```
create_customer(user)
create_subscription(user, plan_code)
cancel_subscription(subscription_id, at_period_end)
schedule_plan_change(subscription_id, new_plan_code)
parse_webhook(request_body, headers) -> { event_type, payload }
```
Implementações: `gateway/pagarme_adapter.py`, `gateway/stripe_adapter.py` (stub inicial).

Estratégia de fallback: se webhook falhar, job `invoice_sync` consulta API (últimas N faturas) e reconcilia.

Campos extras necessários (se usar Pagar.me):
`user_faturamento.gateway_subscription_metadata JSONB` (armazenar id transação, boleto_url, próximos vencimentos se diferente do ciclo padrão).

Segurança: validar assinatura HMAC do webhook; rejeitar eventos duplicados (tabela `payment_events` com unique hash do id do evento).

Impacto nos passos seguintes: Step 3 passa a gerar adapter + endpoints /billing/webhook e /billing/checkout.

## 2. Modelo de Dados
Tabelas/alterações principais:
- `system_plans` (existente).
- Alterar `users`: `plan_id` (FK), `plan_started_at`, `plan_renews_at`, `plan_status`, `trial_ends_at`.
- `user_faturamento`: assinatura/gateway (`gateway`, `gateway_customer_id`, `gateway_subscription_id`, `status`, `current_plan_id`, `next_plan_id`, `renewal_at`, `gateway_subscription_metadata JSONB`).
- `invoices`: histórico de faturas (plan_id, amount, period, paid, gateway_invoice_id).
- `payment_events`: webhooks crus (raw JSON, event_type, processed) + hash único para dedupe.
- `user_usage_events`: adicionar `plan_id_at_event SMALLINT` (snapshot). Índices: `(user_id, event_type, created_at::date)` e `(plan_id_at_event)`.

## 3. Enforcement de Limites
Criar `gvg_limits.py`:
- `get_plan_limits(user)`
- `count_usage_today(user, event_type)` → SELECT COUNT(*) em `user_usage_events` filtrando por `created_at::date = current_date`.
- `ensure_capacity(user, tipo)` (internamente chama count_usage_today ou cache in-memory).
- `increment_usage` NÃO precisa explicitamente (evento já inserido pelo aggregator); apenas usado para favoritos se quiser log.
- `LimitExceeded` (exceção).
Tipos mapeados a `event_type`:
  * consultas → `search`
  * resumos → `summary`
  * boletim_run → `boletim_run` (definir ao instrumentar)
  * favoritos_capacity → COUNT(*) em `user_bookmarks` (não há evento)
Hooks: run_search, summarize_document, execução boletim, adicionar favorito.
Cache opcional: dicionário em memória `{(user_id,event_type,date): count}` incrementado a cada novo evento; invalida ao virar o dia.

## 4. Fluxos de Assinatura
### Upgrade
1. Usuário clica Upgrade.
2. Modal → POST /billing/create_checkout.
3. Redireciona gateway.
4. Webhook confirma → atualiza `users.plan_id`, `plan_renews_at`.
### Downgrade
- Agenda em `next_plan_id` aplica na renovação.
### Cancelar
- Marca `status=canceled`; mantém acesso até `plan_renews_at`.
### Trial
- `plan_status=trial`, `trial_ends_at`. Após expirar → FREE.
### Renovação
- Webhook invoice.paid → cria invoice, avança `renewal_at`, aplica downgrade agendado.
### Reativar
- Se canceled antes de expirar → limpar flags.

## 5. UI / Páginas
- Cabeçalho: badge "Plano: PLUS" (cor por plano, tooltip renovação).
- `/planos`: cards dos 4 planos (nome, preço, limites, botão). Botão varia: atual (disabled), superior (Upgrade), inferior (Downgrade agendado), downgrade (Agendar Downgrade).
- `/conta`: seções: Plano Atual, Consumo Hoje, Próxima Mudança, Faturas, Ações.
- Modais: Upgrade, Cancelar, Confirmar Downgrade.
- Toast de limite atingido / aviso >=80%.
Cores:
- FREE #6C757D
- PLUS #7B3FE4
- PRO #3b00a1ff
- CORP #089800ff

### 5.1 Rotas Detalhadas
| Rota | Propósito | Observações |
|------|-----------|-------------|
| /planos | Comparação e escolha de upgrade | SEO indexável |
| /conta | Dashboard de billing/uso | Requer auth |
| /checkout/retorno | Mostrar status pós gateway | Querystring status=success|pending|failed |
| /fatura/<id> (opcional) | Detalhe de fatura | Link PDF/segunda via |

### 5.2 Modais e Drawers
- ModalUpgrade: seleção de plano destino + CTA checkout.
- ModalCancelar: confirma cancelamento imediato (acesso até renew_at).
- ModalDowngrade: agenda mudança (explica efeito na renovação).
- ModalFatura: resumo rápido (valor, período, status, link completo).
- DrawerPagamento (opcional): exibe QR Pix / linha digitável sem sair de /checkout/retorno.

### 5.3 Componentes Reutilizáveis
- BillingBadge(plan, renew_at, percent_used)
- PlanCard(plan, is_current, next_plan_id)
- UsageBars({consultas,resumos,boletim,favoritos}, limits)
- InvoiceList(invoices[])
- CheckoutStatus(status, details)

### 5.4 Stores (Dash)
- store-billing-plan: { plan_id, code, renew_at, status, next_plan_id }
- store-usage-today: { consultas, resumos, boletim_run, favoritos, limits: { ... } }
- store-invoices: [ { id, amount, period_start, period_end, paid, url } ]
- store-checkout-status: { status, reference } (preenchido via querystring)

### 5.5 Fluxos UX Principais
Upgrade:
1. /planos → botão Upgrade abre ModalUpgrade.
2. POST /billing/checkout cria sessão (retorna redirect_url).
3. Redireciona gateway.
4. Retorno em /checkout/retorno (pending ou success).
5. Webhook confirma → store-billing-plan atualizada → banner sucesso.

Cancelamento:
1. /conta → botão Cancelar → ModalCancelar.
2. POST /billing/cancel → status=canceled (mantém acesso até renew_at).

Downgrade:
1. /planos ou /conta → botão “Agendar Downgrade”.
2. POST /billing/schedule_downgrade(new_plan_id).
3. Mostra aviso “Aplicará em DD/MM/AAAA”.

Trial:
1. Novo user → plan_status=trial, trial_ends_at.
2. Job diário: expira trial → plan_id=FREE se não convertido.

Checkout Pix/Boleto:
1. Gateway retorna payload com boleto_url ou pix_qr.
2. Exibir DrawerPagamento (QR ou link); status=pending.
3. Webhook confirma → status success.

Limites/Toasts:
1. Ao chamar ensure_capacity e receber LimitExceeded → toast + link /planos.
2. Se uso >=80% e <100% → toast warning (uma vez por dia por tipo).

### 5.6 Estados de Cor / Acessibilidade
- Badge usa background conforme plano + texto branco (contraste ≥4.5). Para CORP (#089800ff) usar texto branco puro.
- Barras de uso: verde (#4CAF50) <80%; laranja (#FF9800) 80–99%; vermelho (#D32F2F) >=100%.

### 5.7 Deep Links
- Links compartilháveis: /planos?target=PRO abre modal upgrade pré-selecionado.
- /checkout/retorno?status=pending&ref=abc permite reabrir DrawerPagamento se store vazia.

### 5.8 Fallback sem JS Extra
- Toda lógica em callbacks Dash (sem libs externas). QR ou boleto exibidos como imagem/base64 ou link.

### 5.9 Erros UX
- Falha criar checkout: modal mostra erro e sugere tentar novamente ou suporte.
- Webhook atrasado: /checkout/retorno mostra aviso “Pagamento em processamento” e botão “Recarregar”.

## 6. Estilos (gvg_styles.py)
Novas chaves: `plan_badge_free|plus|pro|corp`, `plan_card`, `plan_card_current`, `usage_bar_container`, `usage_bar_fill_warning`, `usage_bar_fill_exceeded`, `upgrade_button_primary`, `downgrade_button`, `cancel_button`, `reenable_button`.

## 7. Backend Billing (`gvg_billing.py`)
Funções:
- `create_checkout_session(user_id, target_plan_id)`
- `handle_webhook(payload)`
- `schedule_downgrade(user_id, target_plan_id)`
- `cancel_subscription(user_id)`
- `reactivate_subscription(user_id)`
- `renew_subscription(user_id)`
- `apply_trial(user_id)`

## 8. Limites (`gvg_limits.py`)
Integração com fluxos:
- Antes de run_search: `ensure_capacity('consultas')` (evento será registrado por aggregator -> `search`).
- Antes de summarize: `ensure_capacity('resumos')` (evento `summary`).
- Antes de execução boletim: `ensure_capacity('boletim_run')` (criar evento correspondente).
- Antes de add favorito: validar capacidade (não gera evento).
Não há upsert manual de uso; a própria inserção em `user_usage_events` pelo ciclo de negócio cobre contagem.

## 9. Integração com Aggregator
No `usage_event_finish` os eventos já ficam persistidos para contagem:
- `event_type='search'` → consultas do dia.
- `event_type='summary'` → resumos do dia.
- `event_type='boletim_run'` (ao instrumentar execução de boletim).
Nenhuma tabela auxiliar; apenas SELECT COUNT.

## 10. Segurança / Validação
- Checagem server-side sempre.
- Webhooks: assinatura verificada.
- Downgrade não remove favoritos excedentes; apenas bloqueia novos.

## 11. UX / Mensagens
- Toast limite: "Limite de CONSULTAS (30/dia) atingido. Faça upgrade.".
- Percentual >=80%: barra laranja, >=100% vermelha.
- Painel consumo mostra used/limit e %.

## 12. Roadmap (Sprints)
1. Migração base: colunas plano + `plan_id_at_event` + índices usage + badge plano.
2. `gvg_limits.py` usando `user_usage_events` (consultas counts) + instrumentar boletim_run.
3. Adapters gateway (pagarme_adapter stub + interface), endpoints `/billing/checkout` & `/billing/webhook`, página planos (mock checkout).
4. Painel conta (consumo, faturas stub), downgrade/cancelar/reativar.
5. Gateway produção + webhooks reais + invoice sync job.
6. Trial, alertas (80%/100%), refinamentos e cache de uso.

### Status Step1
Executado: migração criada (`20251007_step1_billing.sql`), estilos de badge adicionados, badge exibido no header (placeholder plano FREE).

Atualização Step1b: user_settings recriado com PK = user_id (uuid) + colunas de plano; (substituída depois).

Atualização Step1c: Removida coluna gerada (erro de imutabilidade). Agora usamos coluna simples `created_at_date` + trigger BEFORE INSERT preenchendo `created_at_date = created_at::date`. Índice diário usa `(user_id,event_type,created_at_date)`.

Atualização Step1d: Simplificação para compatibilidade Supabase removendo DO blocks onde possível, recriando user_settings e garantindo criação idempotente de índices via blocos DO apenas para captura de duplicate_table.

### Step2 (Limites - Implementado)
- Constraint de `user_usage_events` mantida usando somente `query` (sem tipo separado para sucesso; só gravamos quando a consulta conclui).
- Backend `gvg_limits.py` com `ensure_capacity` / `LimitExceeded`.
- Busca: `ensure_capacity('consultas')` antes de processar; evento `query` gravado após término.
- Resumo: `summary_request` + `summary_success` ao finalizar (sem alteração).
- Favoritos: checagem de capacidade antes de inserir (`favoritos`).
- Helper `record_success_event` permanece para reutilização em `summary_success`.
- Mensageria/toasts pendentes (pin para etapa futura).

## 13. SQL Exemplos
Consultas do dia:
```
SELECT COUNT(*)
FROM user_usage_events
WHERE user_id=$1 AND event_type='search' AND created_at::date=current_date;
```
Resumos do dia:
```
SELECT COUNT(*)
FROM user_usage_events
WHERE user_id=$1 AND event_type='summary' AND created_at::date=current_date;
```
Execuções boletim do dia:
```
SELECT COUNT(*)
FROM user_usage_events
WHERE user_id=$1 AND event_type='boletim_run' AND created_at::date=current_date;
```
Capacidade favoritos:
```
SELECT COUNT(*) FROM user_bookmarks WHERE user_id=$1 AND active=true;
```
Limites atuais do plano:
```
SELECT p.limit_consultas_per_day,
       p.limit_resumos_per_day,
       p.limit_boletim_per_day,
       p.limit_favoritos_capacity
FROM system_plans p
JOIN users u ON u.plan_id = p.id
WHERE u.id=$1;
```

## 14. Exceções
- `LimitExceeded` → payload `{error:'LIMIT', tipo:'consultas'}`.
- `past_due` → banner aviso pagamento.

## 15. Pseudo-código Crítico
```
run_search(user,...):
  ensure_capacity(user,'consultas')
  usage_event_start('consulta','search')
  ...
  usage_event_finish(...)
  increment_usage(user,'consultas')
```

## 16. Métricas Internas
Correlacionar custos (tokens/db) x plano para análise interna (não expor).
Exemplo (tokens por plano no período):
```
SELECT plan_id_at_event,
       SUM( (meta->>'tokens_total')::int ) AS tokens_total
FROM user_usage_events
WHERE created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 2 DESC;
```

## 17. Anti-Abuso
- Rate-limit IP para FREE.
- Bloqueio de bursts de favoritos.
- Auditoria para alterações de plano manuais.

## 18. Passos Iniciais Resumidos
A. Migrar DB (colunas plano + plan_id_at_event + índices + badge).
B. Implementar `gvg_limits.py` usando contagem em user_usage_events.
C. Instrumentar boletim_run e validar favoritos.
D. Página planos + endpoints checkout/webhook (sandbox gateway).
E. Painel conta (consumo) + cancelar/downgrade.
F. Gateway produção + invoice sync.
G. Trial + alertas 80%/100% + cache uso.

## 19. Extensões Futuras
- Planos anuais, add-ons, e-mails de proximidade de limite, dashboard MRR.

## 20. Resumo Final
Arquitetura modular: billing e limits separados; UI mostra estado e incentiva upgrade; limites aplicados antes do consumo; integração com aggregator para insights de custo.
