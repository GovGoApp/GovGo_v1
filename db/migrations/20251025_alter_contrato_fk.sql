-- Ajuste de FK: contrato deve referenciar contratacao(numero_controle_pncp)
-- pelo campo contrato.numero_controle_pncp_compra (id da contratação).

ALTER TABLE IF EXISTS public.contrato
  DROP CONSTRAINT IF EXISTS contrato_numero_controle_pncp_fkey;

-- Opcional: criar índice para acelerar as verificações/joins por compra
CREATE INDEX IF NOT EXISTS idx_contrato_numero_controle_pncp_compra
  ON public.contrato (numero_controle_pncp_compra);

ALTER TABLE IF EXISTS public.contrato
  ADD CONSTRAINT contrato_numero_controle_pncp_compra_fkey
  FOREIGN KEY (numero_controle_pncp_compra)
  REFERENCES public.contratacao(numero_controle_pncp);
