# 🚀 GUIA RÁPIDO: INSTALAR E TESTAR STRIPE

## 📦 1. INSTALAR DEPENDÊNCIAS

```powershell
# Navegar para o diretório do projeto
cd "c:\Users\Haroldo Duraes\Desktop\Scripts\GovGo\v1"

# Instalar Stripe e Flask
pip install stripe>=7.0.0 flask>=3.0.0

# Ou instalar tudo do requirements.txt
pip install -r requirements.txt
```

---

## 🗄️ 2. EXECUTAR MIGRATION NO BANCO

**Abrir Supabase SQL Editor:**
1. Acessar: https://supabase.com/dashboard
2. Selecionar seu projeto GovGo
3. Ir em: SQL Editor → New Query

**Executar SQL:**
```sql
ALTER TABLE public.user_settings 
ADD COLUMN IF NOT EXISTS gateway_customer_id TEXT,
ADD COLUMN IF NOT EXISTS gateway_subscription_id TEXT;

CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_customer 
ON public.user_settings(gateway_customer_id);

CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_subscription 
ON public.user_settings(gateway_subscription_id);
```

**Verificar:**
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'user_settings' 
  AND table_schema = 'public';
```

Deve aparecer `gateway_customer_id` e `gateway_subscription_id` como `text`.

---

## 🔑 3. CONFIGURAR STRIPE DASHBOARD

### 3.1 Criar Produtos

1. **Acessar:** https://dashboard.stripe.com/test/products
2. **Criar 3 produtos:**

**Produto 1: GovGo PLUS**
- Nome: `GovGo PLUS`
- Descrição: `Plano intermediário com mais consultas e resumos`
- Preço: `R$ 49,90` (ou valor desejado)
- Tipo: `Recurring` (Recorrente)
- Intervalo: `Monthly` (Mensal)
- Clicar em **Create Product**
- ✅ **ANOTAR** o Price ID (começa com `price_...`)

**Produto 2: GovGo PRO**
- Nome: `GovGo PRO`
- Descrição: `Plano profissional com limites expandidos`
- Preço: `R$ 99,90`
- Tipo: `Recurring`
- Intervalo: `Monthly`
- ✅ **ANOTAR** o Price ID

**Produto 3: GovGo CORP**
- Nome: `GovGo CORP`
- Descrição: `Plano corporativo com limites máximos`
- Preço: `R$ 199,90`
- Tipo: `Recurring`
- Intervalo: `Monthly`
- ✅ **ANOTAR** o Price ID

### 3.2 Copiar API Keys

1. **Acessar:** https://dashboard.stripe.com/test/apikeys
2. **Copiar:**
   - **Secret Key** (começa com `sk_test_...`)
   - ⚠️ **NUNCA** compartilhar essa chave!

### 3.3 Configurar Webhook (Local)

Para testes locais, usaremos o Stripe CLI (passo 4).

Para **produção**, depois de fazer deploy:
1. **Acessar:** https://dashboard.stripe.com/webhooks
2. **Add Endpoint**
3. **URL:** `https://seu-dominio.com/billing/webhook`
4. **Eventos:**
   - `checkout.session.completed`
   - `customer.subscription.deleted`
5. **Signing Secret:** ✅ **ANOTAR** (começa com `whsec_...`)

---

## 📝 4. PREENCHER .ENV

**Editar arquivo `.env` na raiz do projeto:**

```bash
# =====================================
# STRIPE - PAYMENT GATEWAY
# =====================================

# API Secret Key (Dashboard → Developers → API Keys)
STRIPE_SECRET_KEY=sk_test_COLE_AQUI_SUA_CHAVE_SECRETA

# Price IDs (Dashboard → Products)
STRIPE_PRICE_PLUS=price_COLE_AQUI_PRICE_ID_PLUS
STRIPE_PRICE_PRO=price_COLE_AQUI_PRICE_ID_PRO
STRIPE_PRICE_CORP=price_COLE_AQUI_PRICE_ID_CORP

# Webhook Secret (gerado pelo Stripe CLI para testes locais)
STRIPE_WEBHOOK_SECRET=whsec_SERÁ_GERADO_NO_PASSO_5

# URL do site
BASE_URL=http://localhost:8050

# Porta do webhook server (opcional, padrão: 5001)
WEBHOOK_PORT=5001
```

**Exemplo preenchido:**
```bash
STRIPE_SECRET_KEY=sk_test_51Abc123...xyz789
STRIPE_PRICE_PLUS=price_1Def456GhiJkl
STRIPE_PRICE_PRO=price_1Mno789PqrStu
STRIPE_PRICE_CORP=price_1Vwx012YzaBcd
STRIPE_WEBHOOK_SECRET=whsec_abc123...xyz789
BASE_URL=http://localhost:8050
```

---

## 🧪 5. TESTAR LOCALMENTE COM STRIPE CLI

### 5.1 Instalar Stripe CLI

**Windows (Scoop):**
```powershell
scoop install stripe
```

**Windows (Chocolatey):**
```powershell
choco install stripe-cli
```

**Manual (Download direto):**
https://github.com/stripe/stripe-cli/releases/latest

### 5.2 Login no Stripe CLI

```powershell
stripe login
```

Vai abrir o navegador para autorizar. Confirmar acesso.

### 5.3 Encaminhar Webhooks para Localhost

```powershell
stripe listen --forward-to localhost:5001/billing/webhook
```

**Output esperado:**
```
> Ready! Your webhook signing secret is whsec_abc123...xyz789 (^C to quit)
```

✅ **COPIAR** esse `whsec_...` e colar no `.env` como `STRIPE_WEBHOOK_SECRET`

⚠️ **DEIXAR ESSE TERMINAL RODANDO** (não fechar)

### 5.4 Iniciar Webhook Server (Novo Terminal)

```powershell
cd "c:\Users\Haroldo Duraes\Desktop\Scripts\GovGo\v1\search\gvg_browser"
python gvg_billing_webhook.py
```

**Output esperado:**
```
🚀 Webhook server running on http://localhost:5001/billing/webhook
📊 Health check: http://localhost:5001/billing/health
```

### 5.5 Testar Health Check

Em outro terminal ou navegador:
```powershell
curl http://localhost:5001/billing/health
```

**Output esperado:**
```json
{"status": "healthy", "service": "gvg_billing_webhook"}
```

---

## 🎮 6. TESTAR CHECKOUT FLOW

### 6.1 Iniciar Aplicação Dash (Novo Terminal)

```powershell
cd "c:\Users\Haroldo Duraes\Desktop\Scripts\GovGo\v1\search\gvg_browser"
python GvG_Search_Browser.py
```

### 6.2 Testar Função de Checkout (Python)

Abrir Python interativo:
```powershell
python
```

Testar criação de checkout:
```python
from gvg_billing import create_checkout_session

result = create_checkout_session(
    user_id='test_user_123',
    plan_code='PLUS',
    email='teste@govgo.com.br',
    name='Usuário Teste'
)

print(result)
# Deve retornar: {'checkout_url': 'https://checkout.stripe.com/...', 'session_id': 'cs_test_...'}
```

### 6.3 Testar Pagamento no Stripe

1. **Copiar** o `checkout_url` do resultado acima
2. **Colar** no navegador
3. **Preencher dados:**
   - Email: qualquer email de teste
   - Cartão: `4242 4242 4242 4242`
   - Data: qualquer data futura (ex: 12/34)
   - CVC: qualquer 3 dígitos (ex: 123)
   - Nome: qualquer nome
4. **Clicar em Pay**

### 6.4 Verificar Webhook Recebido

No terminal do Stripe CLI, você deve ver:
```
[200] POST http://localhost:5001/billing/webhook [evt_abc123...]
```

No terminal do webhook server:
```
INFO:WEBHOOK:Evento processado: checkout.session.completed [evt_abc123...]
```

### 6.5 Verificar Banco de Dados

No Supabase SQL Editor:
```sql
SELECT user_id, plan_id, gateway_customer_id, gateway_subscription_id
FROM public.user_settings
WHERE user_id = 'test_user_123';
```

Deve mostrar:
- `plan_id`: 2 (PLUS)
- `gateway_customer_id`: `cus_...`
- `gateway_subscription_id`: `sub_...`

---

## 🔥 7. SIMULAR EVENTOS MANUALMENTE

### Simular Checkout Completo
```powershell
stripe trigger checkout.session.completed
```

### Simular Cancelamento
```powershell
stripe trigger customer.subscription.deleted
```

### Ver Logs do Webhook
Todos os eventos são registrados em `logs/log_YYYYMMDD_HHMM.log`

---

## ✅ CHECKLIST DE TESTE

- [ ] `pip install stripe flask` executado
- [ ] Migration SQL executada no Supabase
- [ ] 3 produtos criados no Stripe Dashboard
- [ ] Price IDs anotados
- [ ] API Secret Key copiada
- [ ] `.env` preenchido com IDs
- [ ] Stripe CLI instalado e logado
- [ ] `stripe listen` rodando
- [ ] Webhook server rodando (porta 5001)
- [ ] Health check respondendo
- [ ] `create_checkout_session()` retorna URL válida
- [ ] Pagamento teste com cartão 4242... funciona
- [ ] Webhook recebido e processado (log no terminal)
- [ ] Database atualizado com gateway IDs
- [ ] Plano do usuário atualizado para PLUS

---

## ❌ TROUBLESHOOTING

### Erro: "STRIPE_SECRET_KEY não configurado"
✅ **Solução:** Adicionar `STRIPE_SECRET_KEY=sk_test_...` no `.env`

### Erro: "Price ID não configurado para plano PLUS"
✅ **Solução:** Adicionar `STRIPE_PRICE_PLUS=price_...` no `.env`

### Erro: "Missing signature" no webhook
✅ **Solução:** `stripe listen` deve estar rodando e `STRIPE_WEBHOOK_SECRET` no `.env`

### Webhook não recebe eventos
✅ **Solução:**
1. Verificar `stripe listen` está rodando
2. Verificar webhook server está na porta 5001
3. Verificar `.env` tem `WEBHOOK_PORT=5001` (ou porta correta)

### Database não atualiza após pagamento
✅ **Solução:**
1. Ver logs do webhook: `logs/log_*.log`
2. Verificar migration foi executada (colunas gateway_* existem)
3. Testar `handle_webhook_event()` manualmente

---

## 📚 PRÓXIMOS PASSOS

Após testar localmente:
1. **Modificar `GvG_Search_Browser.py`** para adicionar botões de upgrade
2. **Testar UI completo** (clicar no botão, redirecionar, pagar, retornar)
3. **Deploy em produção**
4. **Configurar webhook em produção** no Stripe Dashboard
5. **Trocar para chaves de produção** (`sk_live_...`)

---

## 🆘 SUPORTE

**Documentação Stripe:**
- Quickstart: https://docs.stripe.com/checkout/quickstart
- Test Cards: https://docs.stripe.com/testing
- CLI Reference: https://docs.stripe.com/stripe-cli

**Logs do Sistema:**
- Webhook: `logs/log_*.log`
- Dash App: Console onde rodou `python GvG_Search_Browser.py`
- Stripe CLI: Console onde rodou `stripe listen`

**Verificar eventos no Dashboard:**
https://dashboard.stripe.com/test/events
