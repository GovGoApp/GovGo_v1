-- View: public.vw_fornecedores_pendentes
-- Requisitos: a tabela public.empresa deve existir antes de criar esta view.
-- A view retorna apenas CNPJs de fornecedores com > 3 contratos e que ainda não
-- foram enriquecidos (ausentes em public.empresa ou com api_json IS NULL).

-- Dica de performance (opcional):
--   create index if not exists idx_contrato_ni_fornecedor on public.contrato(ni_fornecedor);
--   create index if not exists idx_contrato_razao_fornecedor on public.contrato(nome_razao_social_fornecedor);
--   create index if not exists idx_empresa_cnpj on public.empresa(cnpj);

create or replace view public.vw_fornecedores_pendentes as
with base as (
    select
        ct.ni_fornecedor::text as cnpj,
        ct.nome_razao_social_fornecedor as razao_social,
        count(*) as contrato_count
    from public.contrato ct
    where ct.ni_fornecedor ~ '^[0-9]{14}$'
    group by 1, 2
    having count(*) > 3
)
select
    b.cnpj,
    b.razao_social,
    b.contrato_count
from base b
left join public.empresa e
  on e.cnpj = b.cnpj
where e.cnpj is null
   or e.api_json is null
order by b.contrato_count desc;
