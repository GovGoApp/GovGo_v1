# 🚀 Guia Rápido: Configuração Stripe

## 📋 Checklist de Dados Necessários

### 1️⃣ Chave API (Secret Key)
- **Onde obter**: https://dashboard.stripe.com/test/apikeys
- **Formato**: `sk_test_51ABC123...` (começa com `sk_test_` em modo test)
- **Onde usar**: Variável `STRIPE_SECRET_KEY` no `.env`
- **Segurança**: ⚠️ NUNCA commitar! Manter em `.env` (adicionar ao `.gitignore`)

### 2️⃣ Price IDs dos Produtos
Você precisa criar **3 produtos** no Stripe (um para cada plano pago):

| Plano no Banco | Stripe Product | Price ID |
|----------------|----------------|----------|
| `PLUS` (id=2) | GovGo PLUS | `price_xxx...` |
| `PRO` (id=3) | GovGo PRO | `price_yyy...` |
| `CORP` (id=4) | GovGo CORP | `price_zzz...` |

**Criar em**: https://dashboard.stripe.com/test/products

**Configurar**:
- **Pricing model**: Recurring (recorrente)
- **Billing period**: Monthly (mensal)
- **Currency**: BRL (Real)
- **Prices**: Sincronizar com `system_plans.price_month_brl`

**Copiar**: Após criar cada produto, copiar o **Price ID** e adicionar ao `.env`

### 3️⃣ Webhook Secret
- **Onde obter**: https://dashboard.stripe.com/test/webhooks
- **Quando criar**: Após criar o endpoint webhook no Stripe
- **Endpoint URL**: `https://www.govgo.com.br/billing/webhook` (produção) ou `http://localhost:5001/billing/webhook` (local)
- **Formato**: `whsec_123abc...` (começa com `whsec_`)
- **Onde usar**: Variável `STRIPE_WEBHOOK_SECRET` no `.env`

### 4️⃣ Base URL
- **Desenvolvimento**: `http://localhost:8050`
- **Produção**: `https://www.govgo.com.br`
- **Onde usar**: Variável `BASE_URL` no `.env`
- **Para que serve**: Stripe redireciona para `{BASE_URL}/checkout/success` após pagamento

---

## 📝 Arquivo `.env` Final

```env
# Stripe
STRIPE_SECRET_KEY=sk_test_51ABC123XYZ...
STRIPE_PRICE_PLUS=price_1DEF456...
STRIPE_PRICE_PRO=price_1GHI789...
STRIPE_PRICE_CORP=price_1JKL012...
STRIPE_WEBHOOK_SECRET=whsec_345MNO...

# App
BASE_URL=http://localhost:8050
```

---

## 🔄 Sincronização: Banco ↔ Stripe

### Tabela `system_plans` (Banco)
```sql
SELECT id, code, name, price_month_brl 
FROM public.system_plans 
WHERE active = true;
```

**Resultado**:
```
id | code | name       | price_month_brl
---+------+------------+----------------
 1 | FREE | Free       |           0.00  → Não criar no Stripe
 2 | PLUS | GovGo PLUS |          49.00  → Criar com R$ 49,00
 3 | PRO  | GovGo PRO  |         149.00  → Criar com R$ 149,00
 4 | CORP | GovGo CORP |         499.00  → Criar com R$ 499,00
```

### Produtos no Stripe (Dashboard)
```
Product: GovGo PLUS
├─ Price: R$ 49,00 / mês
└─ Price ID: price_xxx... → STRIPE_PRICE_PLUS

Product: GovGo PRO
├─ Price: R$ 149,00 / mês
└─ Price ID: price_yyy... → STRIPE_PRICE_PRO

Product: GovGo CORP
├─ Price: R$ 499,00 / mês
└─ Price ID: price_zzz... → STRIPE_PRICE_CORP
```

---

## 🛠️ Comandos Úteis

### Instalar biblioteca Stripe
```bash
pip install stripe
```

### Testar conexão com Stripe (Python)
```python
import os
import stripe

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Listar produtos
products = stripe.Product.list(limit=10)
for product in products.data:
    print(f"{product.name}: {product.id}")

# Listar preços
prices = stripe.Price.list(limit=10)
for price in prices.data:
    print(f"{price.id}: {price.unit_amount/100} {price.currency}")
```

### Testar webhook localmente (Stripe CLI)
```bash
# Instalar: https://github.com/stripe/stripe-cli/releases

# Login
stripe login

# Escutar webhooks
stripe listen --forward-to localhost:5001/billing/webhook

# Disparar evento de teste
stripe trigger checkout.session.completed
```

---

## ⚠️ Importante

1. **Modo Test vs Live**:
   - Test: `sk_test_...`, `pk_test_...`, `price_test_...`
   - Live: `sk_live_...`, `pk_live_...`, `price_live_...`

2. **Segurança**:
   - Nunca commitar `.env`
   - Adicionar ao `.gitignore`
   - Usar variáveis de ambiente no servidor (Render, Heroku, etc.)

3. **Webhook**:
   - Obrigatório para confirmar pagamentos
   - Validar assinatura HMAC sempre
   - Usar HTTPS em produção

4. **Price IDs**:
   - São diferentes entre test e live mode
   - Recriar produtos ao migrar para produção
   - Atualizar `.env` com novos IDs

---

## 📚 Links Úteis

- Dashboard Test: https://dashboard.stripe.com/test/dashboard
- API Keys: https://dashboard.stripe.com/test/apikeys
- Products: https://dashboard.stripe.com/test/products
- Webhooks: https://dashboard.stripe.com/test/webhooks
- Documentação: https://stripe.com/docs/api
- Python SDK: https://github.com/stripe/stripe-python
