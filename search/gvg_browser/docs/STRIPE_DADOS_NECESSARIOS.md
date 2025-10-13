# 📊 Resumo: Dados Stripe Necessários

## ✅ Checklist de Configuração

### 1. Chave API (Secret Key)
```
Onde: https://dashboard.stripe.com/test/apikeys
Formato: sk_test_51ABC123XYZ...
.env: STRIPE_SECRET_KEY=sk_test_51ABC123XYZ...
```

### 2. Criar Produtos (3 produtos)

#### GovGo PLUS
```
Onde: https://dashboard.stripe.com/test/products
Nome: GovGo PLUS
Preço: R$ 49,00 / mês
Recurring: ✅ Monthly
Price ID: price_1ABC...
.env: STRIPE_PRICE_PLUS=price_1ABC...
```

#### GovGo PRO
```
Nome: GovGo PRO
Preço: R$ 149,00 / mês
Recurring: ✅ Monthly
Price ID: price_1DEF...
.env: STRIPE_PRICE_PRO=price_1DEF...
```

#### GovGo CORP
```
Nome: GovGo CORP
Preço: R$ 499,00 / mês
Recurring: ✅ Monthly
Price ID: price_1GHI...
.env: STRIPE_PRICE_CORP=price_1GHI...
```

### 3. Webhook Endpoint
```
Onde: https://dashboard.stripe.com/test/webhooks
URL: https://www.govgo.com.br/billing/webhook
Events: 
  - checkout.session.completed
  - invoice.payment_succeeded
  - invoice.payment_failed
  - customer.subscription.deleted
Webhook Secret: whsec_123...
.env: STRIPE_WEBHOOK_SECRET=whsec_123...
```

### 4. Base URL
```
Dev: http://localhost:8050
Prod: https://www.govgo.com.br
.env: BASE_URL=http://localhost:8050
```

---

## 📋 Arquivo .env Completo

```env
# Stripe API
STRIPE_SECRET_KEY=sk_test_51ABC123XYZ...

# Products Price IDs
STRIPE_PRICE_PLUS=price_1ABC...
STRIPE_PRICE_PRO=price_1DEF...
STRIPE_PRICE_CORP=price_1GHI...

# Webhook
STRIPE_WEBHOOK_SECRET=whsec_123...

# App
BASE_URL=http://localhost:8050
```

---

## 🗄️ Banco de Dados

### Migration SQL
```sql
-- Adicionar colunas Stripe
ALTER TABLE public.user_settings 
ADD COLUMN IF NOT EXISTS gateway_customer_id text,
ADD COLUMN IF NOT EXISTS gateway_subscription_id text;

-- Índices
CREATE INDEX idx_user_settings_gateway_customer 
ON public.user_settings(gateway_customer_id);

CREATE INDEX idx_user_settings_gateway_subscription 
ON public.user_settings(gateway_subscription_id);
```

### Schema Atualizado (user_settings)
```
user_id                    uuid           PK
plan_id                    smallint       FK → system_plans(id)
gateway_customer_id        text           ⭐ NOVO (Customer Stripe)
gateway_subscription_id    text           ⭐ NOVO (Subscription Stripe)
plan_started_at            timestamptz
plan_renews_at             timestamptz
plan_status                text
trial_ends_at              timestamptz
next_plan_id               smallint       FK → system_plans(id)
```

---

## 🔗 Mapeamento: Banco ↔ Stripe

```
system_plans (Banco)        Stripe Products
───────────────────────     ───────────────────────────
id=1, code=FREE             (não criar - gratuito)
id=2, code=PLUS     ←────→  Product "GovGo PLUS" 
                            Price ID: price_1ABC...
id=3, code=PRO      ←────→  Product "GovGo PRO"
                            Price ID: price_1DEF...
id=4, code=CORP     ←────→  Product "GovGo CORP"
                            Price ID: price_1GHI...
```

---

## 🚀 Como Usar a API

### Importar e Configurar
```python
import os
import stripe

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
```

### Criar Checkout (Upgrade)
```python
session = stripe.checkout.Session.create(
    customer_email=user_email,
    line_items=[{
        'price': os.getenv('STRIPE_PRICE_PLUS'),
        'quantity': 1,
    }],
    mode='subscription',
    success_url=f"{base_url}/checkout/success",
    cancel_url=f"{base_url}/checkout/cancel",
    metadata={
        'internal_user_id': user_id,
        'plan_code': 'PLUS'
    }
)

# Redirecionar usuário para:
redirect_url = session.url
```

### Cancelar Subscription
```python
subscription = stripe.Subscription.modify(
    subscription_id,
    cancel_at_period_end=True
)
```

### Validar Webhook
```python
event = stripe.Webhook.construct_event(
    request.data,                         # payload
    request.headers['Stripe-Signature'],  # signature
    os.getenv('STRIPE_WEBHOOK_SECRET')    # secret
)
```

---

## 📚 Documentação

- **Setup Rápido**: `docs/STRIPE_SETUP_RAPIDO.md`
- **Plano Completo**: `docs/PLANO_STRIPE.md`
- **Migration SQL**: `db/migrations/add_stripe_columns.sql`
- **Exemplo .env**: `.env.example`

---

## ⚠️ Segurança

1. ✅ Nunca commitar `.env`
2. ✅ Adicionar ao `.gitignore`
3. ✅ Validar webhook HMAC sempre
4. ✅ Usar HTTPS em produção
5. ✅ Manter Secret Key secreta
