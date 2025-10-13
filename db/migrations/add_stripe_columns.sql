-- ================================================================
-- Migration: Adicionar colunas Stripe em user_settings
-- Data: 2025-10-10
-- Descrição: Colunas para armazenar IDs do Stripe (Customer e Subscription)
-- ================================================================

-- Adicionar colunas para gateway Stripe
ALTER TABLE public.user_settings 
ADD COLUMN IF NOT EXISTS gateway_customer_id text,
ADD COLUMN IF NOT EXISTS gateway_subscription_id text;

-- Comentários
COMMENT ON COLUMN public.user_settings.gateway_customer_id 
IS 'Customer ID do Stripe (cus_xxx...). Criado no primeiro upgrade.';

COMMENT ON COLUMN public.user_settings.gateway_subscription_id 
IS 'Subscription ID do Stripe (sub_xxx...). Criado quando usuário assina plano.';

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_customer 
ON public.user_settings(gateway_customer_id)
WHERE gateway_customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_subscription 
ON public.user_settings(gateway_subscription_id)
WHERE gateway_subscription_id IS NOT NULL;

-- Verificar resultado
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'user_settings' 
  AND column_name IN ('gateway_customer_id', 'gateway_subscription_id');

-- Resultado esperado:
-- column_name              | data_type | is_nullable
-- -------------------------+-----------+-------------
-- gateway_customer_id      | text      | YES
-- gateway_subscription_id  | text      | YES
