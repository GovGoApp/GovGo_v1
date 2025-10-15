# Guia de Billing e Pagamentos (Stripe)

Este guia resume o que foi feito e o que precisa ser feito para o sistema de planos, billing e pagamentos funcionar fim‑a‑fim no GovGo Search (Dash/Flask), cobrindo Banco de Dados, UI e variáveis de ambiente.

## Visão geral

- Banco de dados
  - `public.system_plans`: planos ativos com `stripe_price_id` nos planos pagos (PLUS/PRO/CORP).
  - `public.user_settings`: FK `user_id -> auth.users(id)`, guarda plano atual e IDs Stripe (`gateway_customer_id`, `gateway_subscription_id`).
  - `public.user_payment`: histórico de pagamentos; FK para usuário (UUID) e plano; campos de auditoria.
- Backend (Stripe + planos)
  - Planos/limites: `get_system_plans`, `get_user_settings`.
  - Mudança de plano: `upgrade_plan` (UPSERT em `user_settings`), helpers de downgrade/agendamento.
  - Stripe – fluxos disponíveis:
    - Embedded Checkout (principal, dentro do modal): `create_checkout_embedded_session` (retorna `client_secret`).
    - Elements (modal custom, para teste): `create_subscription_elements` + `apply_subscription_result`.
    - Checkout popup (legado): `create_checkout_session`.
  - Webhooks: `verify_webhook` + `handle_webhook_event`:
    - `checkout.session.completed` → aplica plano (UPSERT) e grava `user_payment`.
    - `customer.subscription.deleted` → rebaixa para FREE.
- UI (Dash)
  - Modal de Planos: cards com limites/preços e botões Upgrade/Downgrade.
  - Pagamento Embedded: abre modal “Pagamento” e monta `Stripe.initEmbeddedCheckout` com o `client_secret`.
  - Rotas Flask: `/billing/webhook`, `/api/plan_status` e endpoints de apoio (Elements).
- Variáveis de ambiente (arquivo `.env` em `search/gvg_browser/.env` – não alterar aqui)
  - `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`.
  - QA opcional: `PASS`, `PASS_USER_UID`, `PASS_USER_NAME`, `PASS_USER_EMAIL` (bypass).

## Fluxos suportados

- Embedded Checkout (recomendado): UX padrão do Stripe dentro do modal. Webhook confirma e aplica o plano.
- Elements (teste/backup): cria `Subscription` incomplete, retorna `client_secret` (PaymentIntent/SetupIntent) e depois `apply_subscription_result` faz UPSERT e histórico.
- Popup Checkout (legado): mantido para referência, não usado na UI atual.

## Passo‑a‑passo E2E (Embedded Checkout)

1) Banco de dados
   - Garantir tabelas/colunas conforme `db/BDS1_v3.txt`.
   - Preencher `stripe_price_id` em `public.system_plans` para PLUS/PRO/CORP.
   - Confirmar que o usuário de teste está em `auth.users` (UUID válido).

2) Stripe Dashboard
   - Criar endpoint de webhook apontando para `https://SEU_HOST/billing/webhook` (ou `http://localhost:8050/billing/webhook`).
   - Habilitar eventos: `checkout.session.completed` e `customer.subscription.deleted`.
   - Copiar o “Signing secret” para `STRIPE_WEBHOOK_SECRET` no `.env`.

3) Ambiente (`search/gvg_browser/.env`)
   - Definir `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`.
   - (Opcional QA) `PASS=1` e `PASS_USER_*` para logar automaticamente.

4) Fluxo na UI
   - Abrir “Planos” e clicar em Upgrade (PLUS/PRO/CORP).
   - O backend chama `create_checkout_embedded_session(...)` e retorna `client_secret`.
   - A UI abre o modal e monta o Embedded Checkout (`Stripe.initEmbeddedCheckout`).
   - Concluir o pagamento no modal (padrão Stripe).

5) Webhook e atualização de plano
   - Stripe envia `checkout.session.completed` → `handle_webhook_event` executa `upgrade_plan(...)` e registra `user_payment`.
   - A UI pode consultar `/api/plan_status?uid=...` para refletir o novo plano/badge/limites.

## Checklist de verificação

- [ ] `system_plans` com `stripe_price_id` preenchidos nos planos pagos.
- [ ] `.env` com chaves Stripe válidas (test/live conforme ambiente).
- [ ] Webhook configurado no Stripe para `/billing/webhook` e secret correto em `STRIPE_WEBHOOK_SECRET`.
- [ ] Usuário de teste existe em `auth.users` (UUID = `PASS_USER_UID` para QA local, se usado).
- [ ] Modal “Pagamento” renderiza o Embedded Checkout ao clicar Upgrade.
- [ ] Após pagar, webhook atualiza `user_settings` e insere registro em `user_payment`.
- [ ] Badge/limites atualizam na UI (via polling leve ou reabertura do modal “Planos”).

## Testes e utilitários

- Backend Elements (para validar persistência sem UI):
  - Script: `search/gvg_browser/scripts/test/test_elements_backend.py`.
  - Exercita: `create_subscription_elements` → `apply_subscription_result` → `get_user_settings`.
  - Requisitos: `.env` com chaves Stripe e `PASS_USER_UID` válido em `auth.users`; `system_plans` com `stripe_price_id`.

## Solução de problemas

- Embedded não renderiza no modal
  - Verifique `STRIPE_PUBLISHABLE_KEY` disponível no cliente.
  - Confirme que `create_checkout_embedded_session` retornou `client_secret` (logs).
  - Scripts Stripe v3 e v3/embedded devem carregar no HTML.

- Webhook não atualiza plano
  - Checar logs em `/billing/webhook`.
  - Validar `STRIPE_WEBHOOK_SECRET` e eventos habilitados.
  - Conferir se `client_reference_id`/`metadata.user_id` estão presentes no evento.

- Erro de FK ao aplicar
  - `PASS_USER_UID` (ou UID em produção) deve existir em `auth.users`.
  - `system_plans.code`/`stripe_price_id` devem corresponder ao plano escolhido e estar ativos.

## Onde está cada coisa

- Billing/Stripe: `search/gvg_browser/gvg_billing.py`
  - Planos/limites: `get_system_plans`, `get_user_settings`.
  - Mudança de plano: `upgrade_plan`, auxiliares.
  - Cobrança: `create_checkout_embedded_session` (principal), `create_subscription_elements`/`apply_subscription_result` (teste), `create_checkout_session` (legado).
  - Webhooks: `verify_webhook`, `handle_webhook_event`, `cancel_subscription`.
- UI e rotas: `search/gvg_browser/GvG_Search_Browser.py`
  - Rota: `/billing/webhook`, `/api/plan_status`.
  - Modal de Planos e modal “Pagamento” (Embedded Checkout).
  - Endpoints Elements para testes: `/billing/create_subscription`, `/billing/apply_subscription`.
- JS (Elements legado): `search/gvg_browser/assets/stripe-elements.js`.

## Próximos passos (recomendado)

- Adicionar polling leve (2–5s) enquanto o modal “Pagamento” está aberto para consultar `/api/plan_status` até detectar o novo plano, então fechar o modal e atualizar badge/limites.
- Se optar definitivamente pelo Embedded, remover código legado do Elements para simplificar manutenção.

---

Observação: o arquivo `.env` já contém tudo que você precisa; não é necessário alterar nada nele para seguir este guia.
