-- Create table to store per-result logs for each user prompt
CREATE TABLE IF NOT EXISTS public.user_results (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    user_id uuid NOT NULL,
    prompt_id bigint NOT NULL,
    numero_controle_pncp text NOT NULL,
    rank integer NOT NULL,
    similarity numeric,
    valor numeric,
    data_encerramento_proposta text,
    CONSTRAINT user_results_prompt_fkey FOREIGN KEY (prompt_id)
        REFERENCES public.user_prompts (id)
        ON DELETE CASCADE,
    CONSTRAINT user_results_numero_controle_fkey FOREIGN KEY (numero_controle_pncp)
        REFERENCES public.contratacao (numero_controle_pncp)
        ON UPDATE CASCADE ON DELETE NO ACTION
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_user_results_user_prompt ON public.user_results (user_id, prompt_id);
CREATE INDEX IF NOT EXISTS idx_user_results_numero_controle ON public.user_results (numero_controle_pncp);
