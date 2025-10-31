-- Criação das tabelas ATA, PCA e ITEM_PCA (datas como TEXT)
-- Executar no Supabase (sem índices por ora)

CREATE TABLE IF NOT EXISTS public.ata (
  numero_controle_pncp_ata           text PRIMARY KEY,
  numero_controle_pncp_compra        text,
  numero_ata_registro_preco          text,
  ano_ata                            text,
  data_assinatura                    text,
  vigencia_inicio                    text,
  vigencia_fim                       text,
  data_cancelamento                  text,
  cancelado                          boolean,
  objeto_contratacao                 text,
  cnpj_orgao                         text,
  nome_orgao                         text,
  codigo_unidade_orgao               text,
  nome_unidade_orgao                 text,
  usuario                            text,
  data_publicacao_pncp               text,
  data_inclusao                      text,
  data_atualizacao                   text,
  created_at                         timestamptz DEFAULT now()
);

-- Colunas adicionais (idempotente) para refletir payload: subrogação e atualização global
ALTER TABLE public.ata ADD COLUMN IF NOT EXISTS data_atualizacao_global text;
ALTER TABLE public.ata ADD COLUMN IF NOT EXISTS cnpj_orgao_subrogado text;
ALTER TABLE public.ata ADD COLUMN IF NOT EXISTS nome_orgao_subrogado text;
ALTER TABLE public.ata ADD COLUMN IF NOT EXISTS codigo_unidade_orgao_subrogado text;
ALTER TABLE public.ata ADD COLUMN IF NOT EXISTS nome_unidade_orgao_subrogado text;

CREATE TABLE IF NOT EXISTS public.pca (
  id_pca_pncp                        text PRIMARY KEY,
  orgao_entidade_cnpj                text,
  orgao_entidade_razao_social        text,
  codigo_unidade                     text,
  nome_unidade                       text,
  ano_pca                            text,
  id_usuario                         text,
  data_publicacao_pncp               text,
  data_inclusao                      text,
  data_atualizacao                   text,
  created_at                         timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.item_pca (
  id_pca_pncp                        text NOT NULL REFERENCES public.pca(id_pca_pncp) ON DELETE CASCADE,
  numero_item                        text NOT NULL,
  categoria_item_pca_nome            text,
  classificacao_catalogo_id          text,
  nome_classificacao_catalogo        text,
  classificacao_superior_codigo      text,
  classificacao_superior_nome        text,
  pdm_codigo                         text,
  pdm_descricao                      text,
  codigo_item                        text,
  descricao_item                     text,
  unidade_fornecimento               text,
  quantidade_estimada                numeric,
  valor_unitario                     numeric,
  valor_total                        numeric,
  valor_orcamento_exercicio          numeric,
  data_desejada                      text,
  unidade_requisitante               text,
  grupo_contratacao_codigo           text,
  grupo_contratacao_nome             text,
  data_inclusao                      text,
  data_atualizacao                   text,
  created_at                         timestamptz DEFAULT now(),
  CONSTRAINT item_pca_pkey PRIMARY KEY (id_pca_pncp, numero_item)
);
