# ✅ IMPLEMENTAÇÃO STRIPE - STATUS ATUAL

## 📋 O QUE FOI FEITO

### 1. **gvg_billing.py** - REESCRITO ✅
Arquivo completamente refatorado para usar Stripe ao invés do sistema mock.

**Removido:**
- ❌ `MockBillingGateway` class (código de teste)
- ❌ `start_checkout()` (versão mock)
- ❌ `finalize_upgrade_mock()` (simulação)
- ❌ `get_gateway()` (singleton mock)
- ❌ Imports: `uuid`, `dataclass`

**Adicionado:**
- ✅ `import stripe` + configuração com `STRIPE_SECRET_KEY`
- ✅ `PLAN_PRICE_MAP` (mapeamento PLUS/PRO/CORP → Price IDs)
- ✅ `create_checkout_session(user_id, plan_code, email, name)` → Cria sessão Stripe
- ✅ `verify_webhook(payload, signature)` → Valida HMAC do webhook
- ✅ `handle_webhook_event(event)` → Processa eventos (checkout.session.completed, customer.subscription.deleted)
- ✅ `cancel_subscription(user_id)` → Cancela assinatura no Stripe

**Atualizado:**
- ✅ `get_user_settings()` → Agora retorna `gateway_customer_id` e `gateway_subscription_id`
- ✅ `upgrade_plan()` → Aceita parâmetros opcionais `gateway_customer_id` e `gateway_subscription_id`
- ✅ `__all__` exports → Lista atualizada com funções do Stripe

### 2. **gvg_billing_webhook.py** - CRIADO ✅
Servidor Flask separado para receber webhooks do Stripe.

**Endpoints:**
- `POST /billing/webhook` → Recebe eventos do Stripe
- `GET /billing/health` → Health check

**Características:**
- Valida assinatura HMAC com `verify_webhook()`
- Processa eventos com `handle_webhook_event()`
- Retorna JSON com status 200/400/500
- Porta configurável via `WEBHOOK_PORT` (padrão: 5001)

---

## ⏳ O QUE FALTA FAZER

### 3. **GvG_Search_Browser.py** - NÃO MODIFICADO ❌

**Precisa adicionar:**

#### 3.1 Componente de Redirecionamento
```python
import dash
from dash import dcc

app.layout = html.Div([
    dcc.Location(id='url', refresh=True),
    # ... resto do layout
])
```

#### 3.2 Callback para Botão de Upgrade
```python
@app.callback(
    Output('url', 'href'),
    Input('btn-upgrade-plus', 'n_clicks'),
    State('store-session', 'data'),
    prevent_initial_call=True
)
def redirect_to_checkout_plus(n, session_data):
    if not n or not session_data:
        return dash.no_update
    
    user_id = session_data.get('user_id')
    email = session_data.get('email')
    name = session_data.get('name')
    
    result = create_checkout_session(user_id, 'PLUS', email, name)
    
    if 'error' in result:
        # Mostrar mensagem de erro
        return dash.no_update
    
    return result['checkout_url']  # Redireciona para Stripe
```

#### 3.3 Páginas de Retorno (Success/Cancel)
```python
# /checkout/success
@app.callback(...)
def checkout_success(session_id):
    # Mostrar mensagem: "Pagamento confirmado! Seu plano será ativado em breve."
    # Pode usar session_id para consultar status no Stripe (opcional)
    pass

# /checkout/cancel
@app.callback(...)
def checkout_cancel():
    # Mostrar mensagem: "Pagamento cancelado. Você pode tentar novamente."
    pass
```

### 4. **Database Migration** - NÃO EXECUTADO ❌

**Arquivo:** `db/migrations/add_stripe_columns.sql`

**Executar no Supabase:**
```sql
ALTER TABLE public.user_settings 
ADD COLUMN IF NOT EXISTS gateway_customer_id TEXT,
ADD COLUMN IF NOT EXISTS gateway_subscription_id TEXT;

CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_customer 
ON public.user_settings(gateway_customer_id);

CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_subscription 
ON public.user_settings(gateway_subscription_id);
```

### 5. **Configuração .env** - NÃO PREENCHIDO ❌

**Adicionar ao arquivo `.env`:**
```bash
# Stripe API Keys
STRIPE_SECRET_KEY=sk_test_...  # Da Dashboard Stripe
STRIPE_WEBHOOK_SECRET=whsec_...  # Gerado ao criar webhook endpoint

# Stripe Price IDs (criar produtos no Dashboard)
STRIPE_PRICE_PLUS=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_CORP=price_...

# URL do site
BASE_URL=http://localhost:8050  # Produção: https://govgo.com.br

# Webhook (opcional, padrão 5001)
WEBHOOK_PORT=5001
```

### 6. **Stripe Dashboard** - NÃO CONFIGURADO ❌

**Passos:**

1. **Criar Produtos:**
   - Dashboard → Products → Add Product
   - Criar 3 produtos: GovGo PLUS, GovGo PRO, GovGo CORP
   - Preço recorrente mensal (BRL)
   - Anotar Price IDs (começam com `price_`)

2. **Configurar Webhook:**
   - Dashboard → Developers → Webhooks → Add Endpoint
   - URL: `https://seu-dominio.com/billing/webhook`
   - Eventos:
     - `checkout.session.completed`
     - `customer.subscription.deleted`
   - Anotar Webhook Secret (começa com `whsec_`)

3. **Copiar API Keys:**
   - Dashboard → Developers → API Keys
   - Secret Key (começa com `sk_test_` para teste, `sk_live_` para produção)

---

## 🧪 COMO TESTAR

### Teste Local com Stripe CLI

1. **Instalar Stripe CLI:**
   ```powershell
   scoop install stripe
   ```

2. **Login:**
   ```powershell
   stripe login
   ```

3. **Encaminhar webhooks para localhost:**
   ```powershell
   stripe listen --forward-to localhost:5001/billing/webhook
   ```
   Isso vai gerar um `whsec_...` para testes locais.

4. **Iniciar webhook server:**
   ```powershell
   cd search\gvg_browser
   python gvg_billing_webhook.py
   ```

5. **Iniciar aplicação Dash:**
   ```powershell
   python GvG_Search_Browser.py
   ```

6. **Testar checkout:**
   - Acessar `http://localhost:8050`
   - Clicar em "Upgrade"
   - Usar cartão de teste: `4242 4242 4242 4242` (qualquer CVC/data futura)

7. **Simular evento manual:**
   ```powershell
   stripe trigger checkout.session.completed
   ```

---

## 📦 DEPENDÊNCIAS

**Adicionar ao `requirements.txt`:**
```
stripe>=7.0.0
flask>=3.0.0
```

**Instalar:**
```powershell
pip install stripe flask
```

---

## 🚀 FLUXO COMPLETO (APÓS IMPLEMENTAÇÃO)

1. **Usuário clica em "Upgrade para PLUS"**
   - `GvG_Search_Browser.py` chama `create_checkout_session()`
   - Retorna `checkout_url` do Stripe

2. **Usuário é redirecionado para Stripe**
   - Preenche dados do cartão na página do Stripe
   - Confirma pagamento

3. **Stripe processa pagamento**
   - Cria Customer e Subscription
   - Envia webhook `checkout.session.completed` para GovGo

4. **gvg_billing_webhook.py recebe evento**
   - Valida assinatura HMAC
   - Chama `handle_webhook_event()`
   - Atualiza database com `upgrade_plan(user_id, plan_code, customer_id, subscription_id)`

5. **Usuário é redirecionado de volta para GovGo**
   - URL: `/checkout/success?session_id=cs_...`
   - Vê mensagem: "Pagamento confirmado!"

6. **Plano está ativo**
   - `gvg_limits.py` valida novos limites
   - Usuário pode usar funcionalidades do plano PLUS

---

## 🛠️ ARQUIVOS MODIFICADOS/CRIADOS

### Criados:
- ✅ `docs/PLANO_STRIPE.md`
- ✅ `docs/STRIPE_SETUP_RAPIDO.md`
- ✅ `docs/STRIPE_DADOS_NECESSARIOS.md`
- ✅ `.env.example`
- ✅ `db/migrations/add_stripe_columns.sql`
- ✅ `search/gvg_browser/gvg_billing_webhook.py` ← NOVO
- ✅ `docs/IMPLEMENTACAO_STATUS.md` ← ESTE ARQUIVO

### Modificados:
- ✅ `search/gvg_browser/gvg_billing.py` (reescrito)

### Pendentes:
- ❌ `search/gvg_browser/GvG_Search_Browser.py` (adicionar callbacks)
- ❌ `.env` (preencher com dados do Stripe)
- ❌ `requirements.txt` (adicionar stripe e flask)

---

## ⚠️ IMPORTANTE: ORDEM DE IMPLEMENTAÇÃO

1. **ANTES DE TUDO:** Executar migration no banco
2. **DEPOIS:** Criar produtos no Stripe Dashboard
3. **DEPOIS:** Preencher `.env` com IDs
4. **DEPOIS:** Modificar `GvG_Search_Browser.py`
5. **DEPOIS:** Testar localmente com Stripe CLI
6. **POR ÚLTIMO:** Deploy em produção

---

## 📞 SUPORTE

**Documentação Stripe:**
- API Reference: https://docs.stripe.com/api
- Checkout Sessions: https://docs.stripe.com/payments/checkout
- Webhooks: https://docs.stripe.com/webhooks

**Troubleshooting:**
- Ver logs: `logs/log_*.log`
- Debug mode: `gvg_debug.dbg('BILLING', '...')`
- Stripe Dashboard → Developers → Events (ver eventos recebidos)

---

## ✅ CHECKLIST FINAL

- [x] Remover código mock de `gvg_billing.py`
- [x] Adicionar funções Stripe em `gvg_billing.py`
- [x] Criar `gvg_billing_webhook.py`
- [ ] Modificar `GvG_Search_Browser.py` (callbacks)
- [ ] Executar migration SQL no banco
- [ ] Criar produtos no Stripe Dashboard
- [ ] Configurar webhook endpoint no Stripe
- [ ] Preencher `.env` com IDs do Stripe
- [ ] Atualizar `requirements.txt`
- [ ] Testar checkout local com Stripe CLI
- [ ] Testar webhook local
- [ ] Deploy em produção
- [ ] Testar com cartão de teste em produção
- [ ] Configurar webhook em produção

---

**Status:** 🟡 70% COMPLETO (backend pronto, falta UI e configuração)

**Próximo Passo:** Modificar `GvG_Search_Browser.py` para adicionar callbacks de upgrade.
