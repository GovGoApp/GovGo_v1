# 🗄️ CONFIGURAÇÃO SUPABASE PARA STRIPE

## ✅ O QUE EXECUTAR NO SUPABASE

Você precisa adicionar **2 colunas** na tabela `user_settings` para armazenar os IDs do Stripe.

---

## 📋 PASSO A PASSO

### 1. Acessar Supabase SQL Editor

1. Abrir: https://supabase.com/dashboard
2. Selecionar projeto: **GovGo** (hemztmtbejcbhgfmsvfq)
3. Menu lateral → **SQL Editor**
4. Clicar em **New Query**

---

### 2. Copiar e Executar SQL

**Cole este código no editor SQL:**

```sql
-- =============================
-- MIGRATION: Adicionar Colunas Stripe
-- =============================

-- Adicionar colunas para armazenar IDs do Stripe
ALTER TABLE public.user_settings 
ADD COLUMN IF NOT EXISTS gateway_customer_id TEXT,
ADD COLUMN IF NOT EXISTS gateway_subscription_id TEXT;

-- Criar índices para melhorar performance de buscas
CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_customer 
ON public.user_settings(gateway_customer_id);

CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_subscription 
ON public.user_settings(gateway_subscription_id);

-- Comentários nas colunas (documentação)
COMMENT ON COLUMN public.user_settings.gateway_customer_id IS 
'ID do Customer no Stripe (cus_...)';

COMMENT ON COLUMN public.user_settings.gateway_subscription_id IS 
'ID da Subscription ativa no Stripe (sub_...)';
```

**Clicar em RUN** (ou Ctrl+Enter)

---

### 3. Verificar se Deu Certo

**Executar query de verificação:**

```sql
-- Verificar se as colunas foram criadas
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'user_settings' 
  AND column_name LIKE 'gateway%'
ORDER BY column_name;
```

**Resultado esperado:**

| column_name               | data_type | is_nullable |
|---------------------------|-----------|-------------|
| gateway_customer_id       | text      | YES         |
| gateway_subscription_id   | text      | YES         |

✅ **Se apareceu essas 2 linhas, está PRONTO!**

---

### 4. (Opcional) Verificar Índices

```sql
-- Verificar se os índices foram criados
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'user_settings'
  AND indexname LIKE '%gateway%';
```

**Resultado esperado:**

| indexname                                    | indexdef |
|----------------------------------------------|----------|
| idx_user_settings_gateway_customer           | CREATE INDEX ... ON user_settings USING btree (gateway_customer_id) |
| idx_user_settings_gateway_subscription       | CREATE INDEX ... ON user_settings USING btree (gateway_subscription_id) |

---

## 🔍 O QUE ESSAS COLUNAS FAZEM?

### `gateway_customer_id` (TEXT)
- Armazena o **Customer ID** do Stripe (ex: `cus_abc123...`)
- Criado quando usuário faz primeiro pagamento
- Usado para:
  - Gerenciar assinaturas do usuário
  - Cancelar assinaturas
  - Histórico de pagamentos

### `gateway_subscription_id` (TEXT)
- Armazena o **Subscription ID** do Stripe (ex: `sub_xyz789...`)
- Criado quando pagamento é confirmado
- Usado para:
  - Cancelar assinatura (`cancel_subscription()`)
  - Verificar status da assinatura
  - Atualizar plano

---

## 🔄 FLUXO COMPLETO

```
[Usuário paga no Stripe]
    ↓
[Stripe cria Customer: cus_abc123...]
    ↓
[Stripe cria Subscription: sub_xyz789...]
    ↓
[Webhook envia evento: checkout.session.completed]
    ↓
[GovGo recebe evento com IDs]
    ↓
[gvg_billing.handle_webhook_event()]
    ↓
[upgrade_plan(user_id, plan_code, gateway_customer_id='cus_...', gateway_subscription_id='sub_...')]
    ↓
[UPDATE user_settings SET 
    plan_id = 2,
    gateway_customer_id = 'cus_abc123...',
    gateway_subscription_id = 'sub_xyz789...'
 WHERE user_id = 'test_123']
    ↓
[Usuário agora tem plano PLUS com IDs Stripe armazenados! ✅]
```

---

## ❓ PERGUNTAS FREQUENTES

### P: O que acontece se eu não executar essa migration?
**R:** O código vai dar erro ao tentar salvar os IDs do Stripe no banco:
```
ERROR: column "gateway_customer_id" of relation "user_settings" does not exist
```

### P: Posso executar esse SQL múltiplas vezes?
**R:** Sim! `IF NOT EXISTS` garante que não vai duplicar colunas/índices.

### P: Isso afeta dados existentes?
**R:** Não! Só adiciona 2 colunas novas (vazias). Usuários existentes continuam com `gateway_*` NULL.

### P: O que acontece com usuários FREE?
**R:** Nada. As colunas ficam NULL (vazio). Só são preenchidas quando usuário assina plano pago.

### P: Preciso adicionar algo mais no banco?
**R:** Não! Só isso. As tabelas `system_plans` e `user_settings` já existem com tudo necessário.

---

## ✅ CHECKLIST

- [ ] Acessei Supabase Dashboard
- [ ] Executei SQL de ADD COLUMN
- [ ] Executei SQL de CREATE INDEX
- [ ] Executei query de verificação
- [ ] Vi 2 colunas `gateway_*` retornadas
- [ ] ✅ Pronto para usar Stripe!

---

## 🚀 PRÓXIMO PASSO

Depois de executar isso no Supabase, você pode:

1. **Testar criação de checkout:**
   ```python
   from gvg_billing import create_checkout_session
   result = create_checkout_session('test_user', 'PLUS', 'teste@govgo.com.br')
   print(result['checkout_url'])
   ```

2. **Pagar com cartão teste** (4242 4242 4242 4242)

3. **Verificar no banco que IDs foram salvos:**
   ```sql
   SELECT user_id, plan_id, gateway_customer_id, gateway_subscription_id
   FROM public.user_settings
   WHERE user_id = 'test_user';
   ```

**Resultado esperado após pagamento:**
```
user_id   | plan_id | gateway_customer_id | gateway_subscription_id
----------|---------|---------------------|------------------------
test_user | 2       | cus_abc123...       | sub_xyz789...
```

✅ **Se aparecer isso, SUCESSO TOTAL!** 🎉
