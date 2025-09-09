# Planos e Limites — GovGo Search (Proposta)

Este documento consolida os planos (tipos de usuário), códigos, preços mensais propostos e limites de uso por funcionalidade.

> Observação: valores de preço são sugestão inicial e podem ser ajustados.

## Planos (nomenclatura e códigos)

| Plano       | Código      | Descrição breve              |
|-------------|-------------|------------------------------|
| Free        | FREE        | Uso básico para avaliação    |
| Premium     | PREMIUM     | Uso individual intensivo     |
| Pro         | PRO         | Equipes menores              |
| Enterprise  | ENTERPRISE  | Uso corporativo/alto volume  |

## Preços mensais (propostos)

| Plano      | Código     | Preço mensal (BRL) |
|------------|------------|--------------------|
| Free       | FREE       | R$ 0,00            |
| Premium    | PREMIUM    | R$ 49,00           |
| Pro        | PRO        | R$ 199,00          |
| Enterprise | ENTERPRISE | R$ 1.999,00        |

## Limites de uso por plano

Unidades e períodos por métrica:
- Consultas: quantidade por dia.
- Favoritos: capacidade total salva (limite superior).
- Boletim: frequência máxima de agendamentos automáticos por dia/semana (conforme o plano).
- Resumos: quantidade por dia/semana (conforme o plano).

| Métrica   | Free      | Premium | Pro     | Enterprise |
|-----------|-----------|---------|---------|------------|
| Consultas | 5/dia     | 30/dia  | 100/dia | 1000/dia   |
| Favoritos | 10        | 200     | 2000    | 20000      |
| Boletim   | 1x/semana | 4x/dia  | 10x/dia | 100x/dia   |
| Resumos   | 1x/semana | 40x/dia | 400x/dia| 4000x/dia  |

## Notas
- “Plano” é o nome sugerido para o “tipo de usuário”. Cada usuário possui um `plano_code` (FREE, PREMIUM, PRO ou ENTERPRISE).
- Os limites de Boletim e Resumos mesclam períodos distintos (dia/semana) conforme a característica do plano Free vs. pagos.
- Estes limites orientam validações no app (consultas/dia, capacidade de favoritos, agendamento de boletins e geração de resumos).

---

## Preço unitário por recurso (estimativa)

Para comparar planos, estimamos o preço unitário por “recurso” (nome proposto para agrupar as quatro atividades: Consultas, Favoritos, Boletim e Resumos).

Premissas de cálculo (aproximações):
- Mês com 30 dias.
- 1 semana ≈ 4,33 semanas/mês (média). Assim, 1x/semana ≈ 4,33 execuções/mês.
- Para métricas “/dia”: unidades mensais = limite_diário × 30.
- Para “Favoritos” (capacidade total), dividimos o preço mensal pela capacidade total para obter um custo mensal por favorito de capacidade.
- Arredondamento dos valores em reais para centavos.

Unidades mensais derivadas (para referência):

| Recurso  | Free       | Premium | Pro    | Enterprise |
|----------|------------|---------|--------|------------|
| Consultas (mês) | 5×30 = 150 | 30×30 = 900 | 100×30 = 3.000 | 1000×30 = 30.000 |
| Favoritos (cap.)| 10         | 200     | 2.000 | 20.000 |
| Boletim (mês)   | 1×4,33 ≈ 4,33 | 4×30 = 120 | 10×30 = 300 | 100×30 = 3.000 |
| Resumos (mês)   | 1×4,33 ≈ 4,33 | 40×30 = 1.200 | 400×30 = 12.000 | 4000×30 = 120.000 |

Preços unitários por recurso e plano (R$/unidade):

| Plano      | Consultas | Favoritos | Boletim | Resumos |
|------------|-----------|-----------|---------|---------|
| Free       | R$ 0,00   | R$ 0,00   | R$ 0,00 | R$ 0,00 |
| Premium    | R$ 0,05   | R$ 0,25   | R$ 0,41 | R$ 0,04 |
| Pro        | R$ 0,07   | R$ 0,10   | R$ 0,66 | R$ 0,02 |
| Enterprise | R$ 0,07   | R$ 0,10   | R$ 0,67 | R$ 0,02 |

Detalhamento do cálculo (exemplos):
- Premium Consultas: 49 / (30×30) = 49 / 900 = 0,0544 → R$ 0,05.
- Pro Boletim: 199 / (10×30) = 199 / 300 = 0,6633 → R$ 0,66.
- Enterprise Resumos: 1999 / (4000×30) = 1999 / 120.000 = 0,0167 → R$ 0,02.

> Observação: Para Free, “/semana” foi convertido para ≈4,33/mês; como o preço mensal é R$ 0,00, o preço unitário é R$ 0,00.

