-- =========================================================================
-- Migration: Adicionar colunas Stripe em system_plans
-- =========================================================================
-- Data: 2025-10-14
-- Descrição: Adiciona product_id e price_id do Stripe na tabela system_plans
-- =========================================================================

-- Adicionar colunas para IDs do Stripe
ALTER TABLE public.system_plans 
ADD COLUMN IF NOT EXISTS stripe_product_id TEXT,
ADD COLUMN IF NOT EXISTS stripe_price_id TEXT;

-- Adicionar constraints (opcional mas recomendado)
ALTER TABLE public.system_plans
ADD CONSTRAINT system_plans_stripe_product_id_unique UNIQUE (stripe_product_id),
ADD CONSTRAINT system_plans_stripe_price_id_unique UNIQUE (stripe_price_id);

-- Criar índices para melhorar performance de buscas por IDs Stripe
CREATE INDEX IF NOT EXISTS idx_system_plans_stripe_product 
ON public.system_plans(stripe_product_id)
WHERE stripe_product_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_system_plans_stripe_price 
ON public.system_plans(stripe_price_id)
WHERE stripe_price_id IS NOT NULL;

-- Comentários nas colunas (documentação)
COMMENT ON COLUMN public.system_plans.stripe_product_id IS 
'ID do Product no Stripe (prod_...). Usado para consultar dados do produto.';

COMMENT ON COLUMN public.system_plans.stripe_price_id IS 
'ID do Price no Stripe (price_...). Usado para criar checkout e cobranças.';

-- =========================================================================
-- Popular com dados existentes (AJUSTE OS IDs CONFORME SEU STRIPE!)
-- =========================================================================

-- Plano PLUS
UPDATE public.system_plans
SET 
    stripe_product_id = 'prod_TDCTCkvSbX4EwI',
    stripe_price_id = 'price_1SGm4w07BrIy6xMU6KEi2GKG'
WHERE code = 'PLUS';

-- Plano PRO
UPDATE public.system_plans
SET 
    stripe_product_id = 'prod_TDCUWvlmb503lF',
    stripe_price_id = 'price_1SGm5f07BrIy6xMUIu9Cn1MW'
WHERE code = 'PRO';

-- Plano CORP
UPDATE public.system_plans
SET 
    stripe_product_id = 'prod_TDCVwbhfpMar99',
    stripe_price_id = 'price_1SGm6807BrIy6xMU0KBcDAUg'
WHERE code = 'CORP';

-- Plano FREE não tem IDs Stripe (NULL)
-- Nenhuma ação necessária

-- =========================================================================
-- Verificação
-- =========================================================================

-- Ver todos os planos com IDs Stripe
SELECT 
    id,
    code,
    name,
    price_month_brl,
    stripe_product_id,
    stripe_price_id,
    active
FROM public.system_plans
ORDER BY id;

-- Resultado esperado:
-- id | code | name      | price_month_brl | stripe_product_id      | stripe_price_id
-- ---|------|-----------|-----------------|------------------------|---------------------------
-- 1  | FREE | Gratuito  | 0.00            | NULL                   | NULL
-- 2  | PLUS | Plus      | 49.00           | prod_TDCTCkvSbX4EwI    | price_1SGm4w07BrIy6xMU6KEi2GKG
-- 3  | PRO  | Pro       | 199.00          | prod_TDCUWvlmb503lF    | price_1SGm5f07BrIy6xMUIu9Cn1MW
-- 4  | CORP | Corp      | 999.00          | prod_TDCVwbhfpMar99    | price_1SGm6807BrIy6xMU0KBcDAUg
