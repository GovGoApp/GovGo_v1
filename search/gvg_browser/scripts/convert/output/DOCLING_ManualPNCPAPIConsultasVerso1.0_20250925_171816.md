Manual das APIs de

Consultas

PNCP

Portal Nacional de Contratações Públicas

## Sumário

| Sumário                                                                                                                           | .......................... 1   |
|-----------------------------------------------------------------------------------------------------------------------------------|--------------------------------|
| 1. Objetivo...............................................................................................................        | ... 3                          |
| Protocolo de Comunicação .....................................................................................................    | .... 3                         |
| 3. Acesso ao PNCP ....................................................................                                            | .... 3                         |
| 3.1. Endereços de Acesso.............................................................................................             | ...... 3                       |
| 4. Recomendações Iniciais ....................................................                                                    | . 4                            |
| .1. Composição do Número de Controle PNCP de PCA/Contratação/Ata/Contrato............                                             | .. 4                           |
| ➢ Número de Controle do PCA.....................                                                                                  | .. 4                           |
| Núme                                                                                                                              | .... 4                         |
|                                                                                                                                   | ....... 4                      |
| Número de Controle d                                                                                                              | ..... 4                        |
| 5. Tabelas de Domínio......................................................................................................       | ..... 6                        |
| 5.1. Instrumento Convocatório.......................................................................................              | ....... 6                      |
| 5.2. Modalidade de Contratação........................................................................................            | ....... 6                      |
| 5.3. Modo de Disputa ..................................................................................................           | .. 6                           |
| 5.4. Critério de Julgamento.....................................................................................................  | ... 6                          |
| 5.5. Situação da Contratação .................................................................................................... | .... 7                         |
| 5.6. Situação do Item da Contratação .....................................................................................        | .... 7                         |
| 5.7. Tipo de Benefício.............................................................................                               | ... 7                          |
| 5.8. Situação do Resultado do Item da Contratação.........................................................                        | .. 7                           |
| 5.9. Tipo de Contrato........................................................................                                     | ... 7                          |
| 5.10. Tipo de Termo de Contrato.................................................................................                  | ... 8                          |
| 5.11. Categoria do Processo .........................................................................................             | .... 8                         |
| 5.12. Tipo de Documento ...................................................................................................       | .... 8                         |
| 5.13. Natureza Jurídica .....................................................................................................     | .. 9                           |
| 5.14. Porte da Empresa.......................................................................................................     | ... 11                         |
| 5.15. Amparo Legal .............................................................................................................  | ... 11                         |
| 5.16. Categoria do Item do Plano de Contratações ............................................................                     | .. 13                          |
| 5.17. Identificador de Usuário............................................................................................        | .... 13                        |
| . Catálogo de Serviços (APIs) ..........................................................................................          | .. 13                          |
| .1. Consultar Itens de PCA por Ano, idUsuario e Classificação Superior.................................                           | 13                             |
| Detalhes de Requisição .........................................................................................................  | 13                             |
| Dados de entrada .....................................................................................                            | 14                             |
| Dados de retorno .............                                                                                                    | 14                             |

| Manual PN                                                                                                                                  | Manual PNCP API Consultas – Versão 1.   |
|--------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| Códigos de Retorno................................................                                                                         | . 16                                    |
| 6.2. Consultar Itens de PCA por Ano e Classificação Superior..............................................                                 | . 16                                    |
| Detalhes de Requisição .........................................................................................................           | . 16                                    |
| Dados de entrada .............................................................................................................             | . 17                                    |
| Dados de retorno ..................................................................................................................        | . 17                                    |
| Códigos de Retorno..............................................................                                                           | 19                                      |
| .3. Serviço Consultar Contratações por Data de Publicação................................................                                  | 19                                      |
| Detalhes de Requisição .........................................................................................................           | 19                                      |
| Dados de entrada ................................................................................................................          | 20                                      |
| Dados de retorno ....................................................................................................                      | 21                                      |
| Códigos de Retorno.................................................................................................                        | 23                                      |
| .4. Serviço Consultar Contratações com Período de Recebimento de Propostas em Ab                                                           | 24                                      |
| Detalhes de Requisição .........................................................................................................           | 24                                      |
| Dados de entrada .................................................................................................................         | 24                                      |
| Dados de retorno ..................................................................................................................        | 25                                      |
| Códigos de Retorno...............................................................................................................          | 28                                      |
| 6.4.1 - Observação:....................................................................................................                    | 28                                      |
| 5. Serviço Consultar Atas de Registro de Preço por Período de Vigência ..........................                                          | 29                                      |
| Detalhes da Requisição ............................................................                                                        | 29                                      |
| Dados de entrada ......................................                                                                                    | 30                                      |
| Dados de retorno ..............................................................................................................            | 30                                      |
| Códigos de Retorno........................................................................................................                 | 32                                      |
| 6.6. Serviço Consultar Contratos por Data de Publicação .....................................                                              | 33                                      |
| Detalhes de Requisição ......................................................................................................              | 33                                      |
| Dados de entrada ..............................................................................................................            | 34                                      |
| Dados de retorno .................................................................................................................         | 34                                      |
| Códigos de Retorno............................................................................................................             | 37                                      |
| 7. Suporte .....................................................                                                                           | 39                                      |
| Glossário................................................................................................................................. | 39                                      |

## 1. Objetivo

Este documento contempla as orientações para consultas aos dados de contratações, alienação de bens móveis e imóveis, atas de registro de preços e contratos realizados no âmbito da Lei n° 14.133/2021 .

## 2. Protocolo de Comunicação

As consultas serão realizadas por meio de API (Application Programme Interface) que utiliza o protocolo de comunicação REST - Representational State Transfer/ HTTP 1.1 cujos dados trafegados utilizam a notação JSON - JavaScript Object Notation .

## 3. Acesso ao PNCP

## 3.1. Endereços de Acesso

A invocação dos serviços será realizada através das URLs citadas abaixo, conforme requisitos de segurança detalhados na seção seguinte.

##  Ambiente de Produtivo

- ○ Portal: https://pncp.gov.br
- ○ Documentação Técnica (Serviços): https://pncp.gov.br/api/consulta/swaggerui/index.html
- ○ Serviços (${BASE\_URL}): https://pncp.gov.br/api/consulta

Nota: ${BASE\_URL} será utilizada nos exemplos de requisições citados neste documento. É a URL base para acesso aos serviços disponíveis no PNCP.

## 4. Recomendações Iniciais

## 4.1. Composição do Número de Controle PNCP de PCA/Contratação/Ata/Contrato

O PNCP gera automaticamente um identificador, que é um número de controle, no qual utiliza-se para reconhecer todas as demais transações realizadas para aquele registro.

Atualmente encontram -se disponíveis: plano de contratações anual (PCA) , contratação (licitação ou contratação direta), ata de registro de preços ou contrato , conforme a composição abaixo:

## ➢ Número de Controle do PCA

(id pca pncp) (Máscara 99999999999999-0-999999/9999.)

Cada PCA receberá um número de controle composto por:

- · CNPJ do Órgão/Entidade do PCA (14 dígitos)
- · Dígito "0" - marcador que indica tratar-se de um plano de contratação anual
- · Número sequencial do Plano no PNCP *
- · Ano do Plano (4 dígitos)

## ➢ Número de Controle da Contratação

(id contratação pncp) (Máscara: 99999999999999-1-999999/9999.)

Cada contratação receberá um número de controle composto por:

- · CNPJ do Órgão/Entidade da contratação (14 dígitos)
- · Dígito "1" - marcador que indica tratar-se de uma contratação
- · Número sequencial da contratação no PNCP *
- · Ano da contratação (4 dígitos)

## ➢ Número de Controle da Ata

(id ata pncp) (Máscara: 99999999999999-1-999999/9999-999999.)

Cada ata receberá um número de controle composto por:

- · Número de Controle PNCP da Contratação (24 dígitos)
- · Número sequencial da ata no PNCP *

## ➢ Número de Controle do Contrato

(id contrato pncp) (Máscara: 99999999999999-2-999999/9999.)

Cada contrato receberá um número de controle composto por:

- · CNPJ do Órgão/Entidade do Contrato (14 dígitos)
- · Dígito "2" - marcador que indica tratar-se de um contrato
- · Número sequencial do contrato no PNCP *
- · Ano do contrato (4 dígitos)
- * O número PNCP será gerado sequencialmente com 6 dígitos e reiniciado a cada mudança de ano.

## 4.2 . Dados de Retorno padronizados

Ao realizar consultas para obter dados do Planos Anuais de Contratações – PCA e Contratações , a API realizará o procedimento de busca por esses dados e ao final será retornado o total de registros encontrados, o total de páginas necessárias para a obtenção de todos os registros, o número da página que a consulta foi realizada e o total de páginas restantes .

Essas informações são essenciais para tornar a entrega dos dados mais rápida possível, evitando demora ou até mesmo interrupção da entrega dos pacotes contendo os a informações solicitadas por parte do servidor de arquivos do PNCP.

## ➢ Dados de retorno

|   Id  | Campo            | Tipo    | Descrição                                     |
|-------|------------------|---------|-----------------------------------------------|
|    1  | data             | Vetor   | Vetor com os dados dos registros encontrados  |
|    2  | totalRegistros   | Inteiro | Total de registros encontrados                |
|    3  | totalPaginas     | Inteiro | Total de páginas necessárias para a obtenção  de todos os registros                                               |
|    4  | numeroPagina     | Inteiro | Número da página que a consulta foi realizada |
|    5  | paginasRestantes | Inteiro | Total de páginas restantes                    |
|    6  | empty            | Boleano | Indicador se o atributo data está vazio       |

## 5. Tabelas de Domínio

A seguir são encontradas informações sobre as tabelas de domínio , ou seja, listas dados de interesse que contem valores fixos, usados em várias consultas que tem o intuito de auxiliar na realização e consultas.

## 5.1. Instrumento Convocatório

- ● (código = 1) Edital: Instrumento convocatório utilizado no diálogo competitivo, concurso, concorrência, pregão, manifestação de interesse, pré-qualificação e credenciamento.
- ● (código = 2) Aviso de Contratação Direta: Instrumento convocatório utilizado na Dispensa com Disputa.
- ● (código = 3) Ato que autoriza a Contratação Direta: Instrumento convocatório utilizado na Dispensa sem Disputa ou na Inexigibilidade.

## 5.2. Modalidade de Contratação

- ● (código = 1) Leilão - Eletrônico
- ● (código = 2) Diálogo Competitivo
- ● (código = 3) Concurso
- ● (código = 4) Concorrência - Eletrônica
- ● (código = 5) Concorrência - Presencial
- ● (código = 6) Pregão - Eletrônico
- ● (código = 7) Pregão - Presencial
- ● (código = 8) Dispensa de Licitação
- ● (código = 9) Inexigibilidade
- ● (código = 10) Manifestação de Interesse
- ● (código = 11) Pré-qualificação
- ● (código = 12) Credenciamento
- ● (código = 13) Leilão - Presencial

## 5.3. Modo de Disputa

- ● (código = 1) Aberto
- ● (código = 2) Fechado
- ● (código = 3) Aberto-Fechado
- ● (código = 4) Dispensa Com Disputa
- ● (código = 5) Não se aplica
- ● (código = 6) Fechado-Aberto

## 5.4. Critério de Julgamento

- ● (código = 1) Menor preço
- ● (código = 2) Maior desconto
- ● (código = 4) Técnica e preço
- ● (código = 5) Maior lance
- ● (código = 6) Maior retorno econômico
- ● (código = 7) Não se aplica

- ● (código = 8) Melhor técnica
- ● (código = 9) Conteúdo artístico

## 5.5. Situação da Contratação

- ● (código = 1) Divulgada no PNCP: Contratação divulgada no PNCP. Situação atribuída na inclusão da contratação .
- ● (código = 2) Revogada: Contratação revogada conforme justificativa.
- ● (código = 3) Anulada: Contratação revogada conforme justificativa.
- ● (código = 4) Suspensa: Contratação suspensa conforme justificativa.

## 5.6. Situação do Item da Contratação

- ● (código = 1) Em Andamento: Item com disputa/seleção do fornecedor/arrematante não finalizada. Situação atribuída na inclusão do item da contratação
- ● (código = 2) Homologado: Item com resultado (fornecedor/arrematante informado)
- ● (código = 3) Anulado/Revogado/Cancelado: Item cancelado conforme justificativa
- ● (código = 4) Deserto: Item sem resultado (sem fornecedores/arrematantes interessados)
- ● (código = 5) Fracassado: Item sem resultado (fornecedores/arrematantes desclassificados ou inabilitados)

## 5.7. Tipo de Benefício

- ● (código = 1) Participação exclusiva para ME/EPP
- ● (código = 2) Subcontratação para ME/EPP
- ● (código = 3) Cota reservada para ME/EPP
- ● (código = 4) Sem benefício
- ● (código = 5) Não se aplica

## 5.8. Situação do Resultado do Item da Contratação

- ● (código = 1) Informado: Que possui valor e fornecedor e marca oriundo do resultado da contratação. Situação atribuída na inclusão do resultado do item da contratação .
- ● (código = 2) Cancelado: Resultado do item cancelado conforme justificativa .

## 5.9. Tipo de Contrato

- ● (código = 1) Contrato (termo inicial): Acordo formal recíproco de vontades firmado entre as partes
- ● (código = 2) Comodato: Contrato de concessão de uso gratuito de bem móvel ou imóvel
- ● (código = 3) Arrendamento: Contrato de cessão de um bem por um determinado período mediante pagamento
- ● (código = 4) Concessão: Contrato firmado com empresa privada para execução de serviço público sendo remunerada por tarifa
- ● (código = 5) Termo de Adesão: Contrato em que uma das partes estipula todas as cláusulas sem a outra parte poder modificá-las
- ● (código = 6) Convênio: Acordos firmados entre as partes buscando a realização de um objetivo em comum
- ● (código = 7) Empenho: É uma promessa de pagamento por parte do Estado para um fim específico

- ● (código = 8) Outros: Outros tipos de contratos que não os listados
- ● (código = 9) Termo de Execução Descentralizada (TED): Instrumento utilizado para a descentralização de crédito entre órgãos/entidades da União
- ● (código = 10) Acordo de Cooperação Técnica (ACT): Acordos firmados entre órgãos visando a execução de programas de trabalho ou projetos
- ● (código = 11) Termo de Compromisso: Acordo firmado para cumprir compromisso estabelecido entre as partes
- ● (código = 12) Carta Contrato: Documento que formaliza e ratifica acordo entre duas ou mais partes nas hipóteses em que a lei dispensa a celebração de um contrato

## 5.10. Tipo de Termo de Contrato

- ● (código = 1) Termo de Rescisão: Encerramento é antes da data final do contrato.
- ● (código = 2) Termo Aditivo: Atualiza o contrato como um todo, podendo prorrogar, reajustar, acrescer, suprimir, alterar cláusulas e reajustar.
- ● (código = 3) Termo de Apostilamento: Atualiza o valor do contrato.

## 5.11. Categoria do Processo

- ● (código = 1) Cessão
- ● (código = 2) Compras
- ● (código = 3) Informática (TIC)
- ● (código = 4) Internacional
- ● (código = 5) Locação Imóveis
- ● (código = 6) Mão de Obra
- ● (código = 7) Obras
- ● (código = 8) Serviços
- ● (código = 9) Serviços de Engenharia
- ● (código = 10) Serviços de Saúde
- ● (código = 11) Alienação de bens móveis/imóveis

## 5.12. Tipo de Documento

Tipos de documentos da contratação:

- ● (código = 1) Aviso de Contratação Direta
- ● (código = 2) Edital
- ● Outros anexos:
- ○ (código = 3) Minuta do Contrato
- ○ (código = 4) Termo de Referência
- ○ (código = 5) Anteprojeto
- ○ (código = 6) Projeto Básico
- ○ (código = 7) Estudo Técnico Preliminar
- ○ (código = 8) Projeto Executivo
- ○ (código = 9) Mapa de Riscos
- ○ (código = 10) DFD

Tipos de documentos da ata de registro de preço:

- ● (código = 11) Ata de Registro de Preço

Tipos de documentos de contrato:

- ● (código = 12) Contrato

- ● (código = 13) Termo de Rescisão
- ● (código = 14) Termo Aditivo
- ● (código = 15) Termo de Apostilamento
- ● (código = 17) Nota de Empenho
- ● (código = 18) Relatório Final de Contrato

## ** Para outros documentos do processo usar o código 16.

## 5.13. Natureza Jurídica

## Código - Natureza jurídica

- ● 0000 -Natureza Jurídica não informada
- ● 1015 -Órgão Público do Poder Executivo Federal
- ● 1023 -Órgão Público do Poder Executivo Estadual ou do Distrito Federal
- ● 1031 -Órgão Público do Poder Executivo Municipal
- ● 1040 -Órgão Público do Poder Legislativo Federal
- ● 1058 -Órgão Público do Poder Legislativo Estadual ou do Distrito Federal
- ● 1066 -Órgão Público do Poder Legislativo Municipal
- ● 1074 -Órgão Público do Poder Judiciário Federal
- ● 1082 -Órgão Público do Poder Judiciário Estadual
- ● 1104 -Autarquia Federal
- ● 1112 -Autarquia Estadual ou do Distrito Federal
- ● 1120 -Autarquia Municipal
- ● 1139 -Fundação Pública de Direito Público Federal
- ● 1147 -Fundação Pública de Direito Público Estadual ou do Distrito Federal
- ● 1155 -Fundação Pública de Direito Público Municipal
- ● 1163 -Órgão Público Autônomo Federal
- ● 1171 -Órgão Público Autônomo Estadual ou do Distrito Federal
- ● 1180 -Órgão Público Autônomo Municipal
- ● 1198 -Comissão Polinacional
- ● 1210 -Consórcio Público de Direito Público (Associação Pública)
- ● 1228 -Consórcio Público de Direito Privado
- ● 1236 -Estado ou Distrito Federal
- ● 1244 -Município
- ● 1252 -Fundação Pública de Direito Privado Federal
- ● 1260 -Fundação Pública de Direito Privado Estadual ou do Distrito Federal
- ● 1279 -Fundação Pública de Direito Privado Municipal
- ● 1287 -Fundo Público da Administração Indireta Federal
- ● 1295 -Fundo Público da Administração Indireta Estadual ou do Distrito Federal
- ● 1309 -Fundo Público da Administração Indireta Municipal
- ● 1317 -Fundo Público da Administração Direta Federal
- ● 1325 -Fundo Público da Administração Direta Estadual ou do Distrito Federal
- ● 1333 -Fundo Público da Administração Direta Municipal
- ● 1341 -União
- ● 2011 -Empresa Pública
- ● 2038 -Sociedade de Economia Mista
- ● 2046 -Sociedade Anônima Aberta
- ● 2054 -Sociedade Anônima Fechada

- ● 2062 -Sociedade Empresária Limitada
- ● 2070 -Sociedade Empresária em Nome Coletivo
- ● 2089 -Sociedade Empresária em Comandita Simples
- ● 2097 -Sociedade Empresária em Comandita por Ações
- ● 2100 -Sociedade Mercantil de Capital e Indústria
- ● 2127 -Sociedade em Conta de Participação
- ● 2135 -Empresário (Individual)
- ● 2143 -Cooperativa
- ● 2151 -Consórcio de Sociedades
- ● 2160 -Grupo de Sociedades
- ● 2178 -Estabelecimento, no Brasil, de Sociedade Estrangeira
- ● 2194 -Estabelecimento, no Brasil, de Empresa Binacional Argentino-Brasileira
- ● 2216 -Empresa Domiciliada no Exterior
- ● 2224 -Clube/Fundo de Investimento
- ● 2232 -Sociedade Simples Pura
- ● 2240 -Sociedade Simples Limitada
- ● 2259 -Sociedade Simples em Nome Coletivo
- ● 2267 -Sociedade Simples em Comandita Simples
- ● 2275 -Empresa Binacional
- ● 2283 -Consórcio de Empregadores
- ● 2291 -Consórcio Simples
- ● 2305 -Empresa Individual de Responsabilidade Limitada (de Natureza Empresária)
- ● 2313 -Empresa Individual de Responsabilidade Limitada (de Natureza Simples)
- ● 2321 -Sociedade Unipessoal de Advocacia
- ● 2330 -Cooperativas de Consumo
- ● 2348 -Empresa Simples de Inovação - Inova Simples
- ● 2356 -Investidor Não Residente
- ● 3034 -Serviço Notarial e Registral (Cartório)
- ● 3069 -Fundação Privada
- ● 3077 -Serviço Social Autônomo
- ● 3085 -Condomínio Edilício
- ● 3107 -Comissão de Conciliação Prévia
- ● 3115 -Entidade de Mediação e Arbitragem
- ● 3131 -Entidade Sindical
- ● 3204 -Estabelecimento, no Brasil, de Fundação ou Associação Estrangeiras
- ● 3212 -Fundação ou Associação Domiciliada no Exterior
- ● 3220 -Organização Religiosa
- ● 3239 -Comunidade Indígena
- ● 3247 -Fundo Privado
- ● 3255 -Órgão de Direção Nacional de Partido Político
- ● 3263 -Órgão de Direção Regional de Partido Político
- ● 3271 -Órgão de Direção Local de Partido Político
- ● 3280 -Comitê Financeiro de Partido Político
- ● 3298 -Frente Plebiscitária ou Referendária
- ● 3301 -Organização Social (OS)
- ● 3328 -Plano de Benefícios de Previdência Complementar Fechada

- ● 3999 -Associação Privada
- ● 4014 -Empresa Individual Imobiliária
- ● 4090 -Candidato a Cargo Político Eletivo
- ● 4120 -Produtor Rural (Pessoa Física)
- ● 5010 -Organização Internacional
- ● 5029 -Representação Diplomática Estrangeira
- ● 5037 -Outras Instituições Extraterritoriais
- ● 8885 -Natureza Jurídica não informada

## 5.14. Porte da Empresa

- ● (código = 1) ME: Microempresa
- ● (código = 2) EPP: Empresa de pequeno porte
- ● (código = 3) Demais: Demais empresas
- ● (código = 4) Não se aplica: Quando o fornecedor/arrematante for pessoa física.
- ● (código = 5) Não informado: Quando não possuir o porte da empresa.

## 5.15. Amparo Legal

- ● (código = 1) Lei 14.133/2021, Art. 28, I
- ● (código = 2) Lei 14.133/2021, Art. 28, II
- ● (código = 3) Lei 14.133/2021, Art. 28, III
- ● (código = 4) Lei 14.133/2021, Art. 28, IV
- ● (código = 5) Lei 14.133/2021, Art. 28, V
- ● (código = 6) Lei 14.133/2021, Art. 74, I
- ● (código = 7) Lei 14.133/2021, Art. 74, II
- ● (código = 8) Lei 14.133/2021, Art. 74, III, a
- ● (código = 9) Lei 14.133/2021, Art. 74, III, b
- ● (código = 10) Lei 14.133/2021, Art. 74, III, c
- ● (código = 11) Lei 14.133/2021, Art. 74, III, d
- ● (código = 12) Lei 14.133/2021, Art. 74, III, e
- ● (código = 13) Lei 14.133/2021, Art. 74, III, f
- ● (código = 14) Lei 14.133/2021, Art. 74, III, g
- ● (código = 15) Lei 14.133/2021, Art. 74, III, h
- ● (código = 16) Lei 14.133/2021, Art. 74, IV
- ● (código = 17) Lei 14.133/2021, Art. 74, V
- ● (código = 18) Lei 14.133/2021, Art. 75, I
- ● (código = 19) Lei 14.133/2021, Art. 75, II
- ● (código = 20) Lei 14.133/2021, Art. 75, III, a
- ● (código = 21) Lei 14.133/2021, Art. 75, III, b
- ● (código = 22) Lei 14.133/2021, Art. 75, IV, a
- ● (código = 23) Lei 14.133/2021, Art. 75, IV, b
- ● (código = 24) Lei 14.133/2021, Art. 75, IV, c
- ● (código = 25) Lei 14.133/2021, Art. 75, IV, d
- ● (código = 26) Lei 14.133/2021, Art. 75, IV, e
- ● (código = 27) Lei 14.133/2021, Art. 75, IV, f
- ● (código = 28) Lei 14.133/2021, Art. 75, IV, g

- ● (código = 29) Lei 14.133/2021, Art. 75, IV, h
- ● (código = 30) Lei 14.133/2021, Art. 75, IV, i
- ● (código = 31) Lei 14.133/2021, Art. 75, IV, j
- ● (código = 32) Lei 14.133/2021, Art. 75, IV, k
- ● (código = 33) Lei 14.133/2021, Art. 75, IV, l
- ● (código = 34) Lei 14.133/2021, Art. 75, IV, m
- ● (código = 35) Lei 14.133/2021, Art. 75, V
- ● (código = 36) Lei 14.133/2021, Art. 75, VI
- ● (código = 37) Lei 14.133/2021, Art. 75, VII
- ● (código = 38) Lei 14.133/2021, Art. 75, VIII
- ● (código = 39) Lei 14.133/2021, Art. 75, IX
- ● (código = 40) Lei 14.133/2021, Art. 75, X
- ● (código = 41) Lei 14.133/2021, Art. 75, XI
- ● (código = 42) Lei 14.133/2021, Art. 75, XII
- ● (código = 43) Lei 14.133/2021, Art. 75, XIII
- ● (código = 44) Lei 14.133/2021, Art. 75, XIV
- ● (código = 45) Lei 14.133/2021, Art. 75, XV
- ● (código = 46) Lei 14.133/2021, Art. 75, XVI
- ● (código = 47) Lei 14.133/2021, Art. 78, I
- ● (código = 48) Lei 14.133/2021, Art. 78, II
- ● (código = 49) Lei 14.133/2021, Art. 78, III
- ● (código = 50) Lei 14.133/2021, Art. 74, caput
- ● (Código = 51) Lei 14.284/2021, Art. 29, caput
- ● (Código = 52) Lei 14.284/2021, Art. 24 § 1º
- ● (Código = 53) Lei 14.284/2021, Art. 25 § 1º
- ● (Código = 54) Lei 14.284/2021, Art. 34
- ● (Código = 55) Lei 9.636/1998, Art. 11-C, I
- ● (Código = 56) Lei 9.636/1998, Art. 11-C, II
- ● (Código = 57) Lei 9.636/1998, Art. 24-C, I
- ● (Código = 58) Lei 9.636/1998, Art. 24-C, II
- ● (Código = 59) Lei 9.636/1998, Art. 24-C, III
- ● (Código = 60) Lei 14.133/2021, Art. 75, XVII
- ● (Código = 61) Lei 14.133/2021, Art. 76, I, a
- ● (Código = 62) Lei 14.133/2021, Art. 76, I, b
- ● (Código = 63) Lei 14.133/2021, Art. 76, I, c
- ● (Código = 64) Lei 14.133/2021, Art. 76, I, d
- ● (Código = 65) Lei 14.133/2021, Art. 76, I, e
- ● (Código = 66) Lei 14.133/2021, Art. 76, I, f
- ● (Código = 67) Lei 14.133/2021, Art. 76, I, g
- ● (Código = 68) Lei 14.133/2021, Art. 76, I, h
- ● (Código = 69) Lei 14.133/2021, Art. 76, I, i
- ● (Código = 70) Lei 14.133/2021, Art. 76, I, j
- ● (Código = 71) Lei 14.133/2021, Art. 76, II, a
- ● (Código = 72) Lei 14.133/2021, Art. 76, II, b
- ● (Código = 73) Lei 14.133/2021, Art. 76, II, c
- ● (Código = 74) Lei 14.133/2021, Art. 76, II, d

- ● (Código = 75) Lei 14.133/2021, Art. 76, II, e
- ● (Código = 76) Lei 14.133/2021, Art. 76, II, f
- ● (Código = 77) Lei 14.133/2021, Art. 75, XVIII
- ● (Código = 78) Lei 14.628/2023, Art. 4º
- ● (Código = 79) Lei 14.628/2023, Art. 12
- ● (Código = 80) Lei 14.133/2021, Art. 1º, § 2º

## 5.16 . Categoria do Item do Plano de Contratações

- ● (código = 1) Material
- ● (código = 2) Serviço
- ● (código = 3) Obras
- ● (código = 4) Serviços de Engenharia
- ● (código = 5) Soluções de TIC
- ● (código = 6) Locação de Imóveis
- ● (código = 7) Alienação/Concessão/Permissão
- ● (código = 8) Obras e Serviços de Engenharia

## 5.17. Identificador de Usuário

Para uso de algumas APIs pode ser necessário incluir o Identificador Único do portal ou sistema integrado (idUsuario). Essa informação pode ser encontrada acessando o sítio: Portais Integrados ao PNCP — Portal Nacional de Contratações Públicas PNCP (www.gov.br) e clicando em "Pesquisa ID" conforme imagem a seguir:

<!-- image -->

## 6. Catálogo de Serviços (APIs)

## 6.1 . Consultar Itens de PCA por Ano, idUsuario e Classificação Superior

Serviço que permite recuperar a lista de itens pertencentes a um determinado Plano de Contratações Anual (PCA) por determinado ano e usuário (Portais de Contratações), opcionalmente filtrando por ordem de classificação superior .

## Detalhes de Requisição

| Endpoint        | Método HTTP    | Exemplo de Payload   |
|-----------------|----------------|----------------------|
| /v1/pca/usuario | GET            | Não se aplica        |

| Exemplo Requisição (cURL)                                                          | Exemplo Requisição (cURL)                                                                        |
|------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| curl -X 'GET' \                                                                    |                                                                                                  |
| 'https://pncp.gov.br/api/consulta/v1/pca/usuario?anoPca=2023&idUsuario=3&codigoCla | https://pncp.gov.br/api/consulta/v1/pca/usuario?anoPca=2023&idUsuario=3&codigoClassificacaoSuper |
| ior=979&pagina=1' \                                                                | ior=979&pagina=1' \                                                                              |
| -H 'accept: */*'                                                                   | cept: */*'                                                                                       |

## Dados de entrada

Nota: Alimentar o parâmetro {anoPca} , {idUsuario} e {pagina} na URL.

| Campo                       | Tipo        | Obrigatório    | Descrição   |
|-----------------------------|-------------|----------------|-------------|
| anoPca                      | Inteiro     | Sim            | Ano do PCA  |
| idUsuario                   | Inteiro     | Sim            | Número de identificação do usuário  (Sistema de Contratações Públicas) que  publicou a informação no Portal PNCP óddldl             |
| codigoClassificacaoSuperior | Texto (100) | Não            | pç Código da Classe do material ou Grupo  do serviço conforme catálogos de  matérias e serviços utilizados pelos             |
| pagina                      | Inteiro     | Sim            | Número da página que se deseja obter  os dados. Por padrão cada página contém no             |
| tamanhoPagina               | Inteiro     | Não            | os dados. Por padrão cada página contém no  máximo 500 registros, no entanto o  tamanho de registros em cada página  pode ser ajustado (até o limite de 500             |

## Dados de retorno

|   Id  | Campo                    | Tipo    | Descrição                                |
|-------|--------------------------|---------|------------------------------------------|
|    1  | orgaoEntidadeCnpj        | Texto   | CNPJ do Órgão pertencente ao PCA         |
|    2  | orgaoEntidadeRazaoSocial | Texto   | Razão Social do Órgão pertencente ao PCA |
|    3  | codigoUnidade            | Texto   | Código da Unidade Responsável do Órgão   |
|    4  | nomeUnidade              | Texto   | Nome da Unidade Responsável              |

|   5  | anoPca                      | Inteiro      | Ano do Plano de Contratações da Unidade     |
|------|-----------------------------|--------------|---------------------------------------------|
| 6    | idPcaPncp                   | Texto        | Número de Controle PNCP do PCA (id PCA PNCP |
| 7    | dataPublicacaoPncp          | Data         | Data da publicação do item do plano no PNCP |
| 8    |                             | Lista        | Lista de Itens do PCA da Unidade            |
| 8.1  | numeroItem                  | Inteiro      | Número do item no Plano (único e sequencial  crescente)                                             |
| 8.2  | categoriaItemPcaNome        | Texto        | domínio Categoria do Item do Plano de  Contratações Código da Indicação se Item é Material ou                                             |
| 8.3  | classificacaoCatalogoId     | Texto        | gç Serviço. Domínio: 1 - Material; 2 - Serviço;                                             |
| 8.4  | nomeClassificacaoCatalogo   | Texto        | Nome da Indicação se Item é Material ou Serviço Domínio: 1 - Material; 2 - Serviço;                                             |
| 8.5  | classificacaoSuperiorCodigo | Texto (100   | Código da Classe do material ou Grupo do  serviço conforme catálogo                                             |
| 8.6  | classificacaoSuperiorNome   | Texto (255   | Descrição da Classe do material ou Grupo do  serviço conforme catálogo                                             |
| 8.7  | pdmCodigo                   | Texto (1     | Código PDM referente ao material conforme o  CNBS                                             |
| 8.8  | pdmDescricao                | Texto (255)  | Descrição PDM referente ao material conforme o  CNBS Código do Material ou Serviço conforme o                                             |
| 8.9  | codigoItem                  | Texto (100)  | Código do Material ou Serviço conforme o  catálogo utilizado                                             |
| 8.1  | descricaoItem               | Texto (2048) | Descrição do material ou serviço conforme  catálogo utilizado                                             |
| 8.11 | unidadeFornecimento         | Texto        | Unidade de fornecimento                     |
| 8.12 | quantidadeEstimada          | Decimal      | Quantidade estimada do item do plano de  contratação (maior ou igual a zero). Precisão de  até 4 dígitos decimais; Ex: 10.0001;                                             |
| 8.13 | valorUnitario               | Decimal      | (g) ecisão de até 4 dígitos decimais; Ex: 100.0001; lor total do item (maior ou igual a zero)                                             |
| 8.14 | valorTotal                  | Decimal      | alor total do item (maior ou igual a zero).  recisão de até 4 dígitos decimais; Ex: 100.0001;                                             |

|   8.15  | valorOrcamentoExercicio    | Decimal   | Valor orçamentário estimado para o exercício  (maior ou igual a zero). Precisão de até 4 dígitos  decimais; Ex: 100.0001;                                  |
|---------|----------------------------|-----------|----------------------------------|
|    8.16 | dataDesejada               | Data      | Data desejada para a contratação |
|    8.17 | unidadeRequisitante        | Texto     | Nome da unidade requisitante     |
|    8.18 | grupoContratacaoCodigo     | Texto     | Código da Contratação Futura     |
|    8.19 | grupoContratacaoNome       | Texto     | Nome da Contratação Futura       |
|    8.2  | dataInclusao               | Data      | Data da inclusão do registro do item do plano no  PNCP                                  |
|    8.21 | dataAtualizacao            | Data      | Data da última atualização do registro do item do  plano                                  |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           204  | No Content            | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.2. Consultar Itens de PCA por Ano e Classificação Superior

Serviço que permite recuperar a lista de itens pertencentes a um determinado Plano de Contratações Anual (PCA), opcionalmente filtrando por ordem de classificação superior.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/pca/                  | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -X 'GET' \           | curl -X 'GET' \           | curl -X 'GET' \           |

'https://pncp.gov.br/api/consulta/v1/pca/?anoPca=2023&amp;codigoClassificacaoSuperior=979&amp;pagina=1' \ -H 'accept: */*'

## Dados de entrada

Nota: Alimentar o parâmetro {ano} na URL .

| Campo                       | Tipo        | Obrigatório    | Descrição   |
|-----------------------------|-------------|----------------|-------------|
| anoPca                      | Inteiro     | Sim            | Ano do PCA  |
| codigoClassificacaoSuperior | Texto (100) | Sim            | Código da Classe do material ou Grup do serviço conforme catálogos de  matérias e serviços utilizados pelos  portais de compras.             |
| pagina                      | Inteiro     | Sim            | pgqj os dados. Por padrão cada página contém no             |
| tamanhoPagina               | Inteiro     | Não            | or padrão cada página contém no  máximo 500 registros, no entanto o  amanho de registros em cada página  ode ser ajustado (até o limite de 500  egistros) com vistas a tornar a entrega             |

## Dados de retorno

|   Id  | Campo                    | Tipo    | Descrição                                   |
|-------|--------------------------|---------|---------------------------------------------|
|   1   | orgaoEntidadeCnpj        | Texto   | CNPJ do Órgão                               |
|   2   | orgaoEntidadeRazaoSocial | Texto   | Razão Social do Órgão                       |
|   3   | codigoUnidade            | Texto   | Código da Unidade Responsável               |
|   4   | nomeUnidade              | Texto   | Nome da Unidade Responsável                 |
|   5   | anoPca                   | Inteiro | Ano do Plano de Contratações da Unidade     |
|   6   | idPcaPncp                | Texto   | Número de Controle PNCP do PCA (id PCA PNCP |
|   7   | dataPublicacaoPncp       | Data    | Data da publicação do item do plano no PNCP |
|   8   |                          | Lista   | Lista de Itens do PCA da Unidade            |
|   8.1 | numeroItem               | Inteiro | Número do item no Plano (único e sequencial |

## crescente)

|   8.2  | categoriaItemPcaNome        | Texto        | Nome categoria do item conforme tabela de  domínio Categoria do Item do Plano de  Contratações                                  |
|--------|-----------------------------|--------------|----------------------------------|
|   8.3  | classificacaoCatalogoId     | Texto        | Código da Indicação se Item é Material ou  Serviço. Domínio: 1 - Material; 2 - Serviço; Nome da Indicação se Item é Material ou Servi                                  |
|   8.4  | nomeClassificacaoCatalogo   | Texto        | çç Domínio: 1 - Material; 2 - Serviço;                                  |
|   8.5  | classificacaoSuperiorCodigo | Texto (100)  | gp serviço conforme catálogo                                  |
|   8.6  | classificacaoSuperiorNome   | Texto (255   | Descrição da Classe do material ou Grupo do  serviço conforme catálogo                                  |
|   8.7  | pdmCodigo                   | Texto (100   | Código PDM referente ao material conforme o  CNBS                                  |
|   8.8  | pdmDescricao                | Texto (255   | Descrição PDM referente ao material conforme  CNBS                                  |
|   8.9  | codigoItem                  | Texto (100   | Código do Material ou Serviço conforme o  catálogo utilizado                                  |
|   8.1  | descricaoItem               | Texto (2048) | Descrição do material ou serviço conforme  catálogo utilizado                                  |
|   8.11 | unidadeFornecimento         | Texto        | Unidade de fornecimento          |
|   8.12 | quantidadeEstimada          | Decimal      | Quantidade estimada do item do plano de  contratação (maior ou igual a zero). Precisão de  até 4 dígitos decimais; Ex: 10.0001; Vliáidi(iil )                                  |
|   8.13 | valorUnitario               | Decimal      | Valor unitário do item (maior ou igual a zero). Precisão de até 4 dígitos decimais; Ex: 100.0001; ll dl                                  |
|   8.14 | valorTotal                  | Decimal      | Valor total do item (maior ou igual a zero).  recisão de até 4 dígitos decimais; Ex: 100.0001; Valor orçamentário estimado para o exercício                                  |
|   8.15 | valorOrcamentoExercicio     | Decimal      | çp maior ou igual a zero). Precisão de até 4 dígitos  ecimais; Ex: 100.0001;                                  |
|   8.16 | dataDesejada                | Data         | Data desejada para a contratação |
|   8.17 | unidadeRequisitante         | Texto        | Nome da unidade requisitante     |

|   8.18  | grupoContratacaoCodigo    | Texto    | Código da Contratação Futura   |
|---------|---------------------------|----------|--------------------------------|
|    8.19 | grupoContratacaoNome      | Texto    | Nome da Contratação Futura     |
|    8.2  | dataInclusao              | Data     | Data da inclusão do registro do item do plano no  PNCP                                |
|    8.21 | dataAtualizacao           | Data     | Data da última atualização do registro do item do  plano                                |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           204  | No Content            | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3. Serviço Consultar Contratações por Data de Publicação

Serviço que permite consultar contratações publicadas no PNCP por um período informado . Junto à data inicial e data final informadas deverá ser informado o código da Modalidade da Contratação (vide tabela XXX). Opcionalmente poderá ser informado código do Modo de Disputa da Contratação (vide tabela XXX) , código do IBGE do Município, sigla da Unidade Federativa da Unidade Administrativa do Órgão, CNPJ do Órgão/Entidade, código da Unidade Administrativa do Órgão/Entidade ou código de identificação do Usuário (Sistema de Contratações Públicas que publicou a Contratação) para refinar a consulta.

## Detalhes de Requisição

| Endpoint                    | Método HTTP               | Exemplo de Payload          | Exemplo de Payload          | Exemplo de Payload          |
|-----------------------------|---------------------------|-----------------------------|-----------------------------|-----------------------------|
| /v1/contratacoes/publicacao | GET                       | /v1/contratacoes/publicacao | /v1/contratacoes/publicacao | /v1/contratacoes/publicacao |
| Exemplo Requisição (cURL)   | Exemplo Requisição (cURL) | Exemplo Requisição (cURL)   | Exemplo Requisição (cURL)   | Exemplo Requisição (cURL)   |

curl -X 'GET' \

'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?dataInicial=20230801&amp;dataFinal=2023 0802&amp;codigoModalidadeContratacao=8&amp;uf=DF&amp;codigoMunicipioIbge=5300108&amp;cnpj=000593110001 26&amp;codigoUnidadeAdministrativa=194035&amp;idUsuario=3&amp;pagina=1' \

-H 'accept: */*'

## Dados de entrada

Nota: Dados a serem enviados no cabeçalho da requisição .

| Campo                       | Tipo    | Obrigatório    | Descrição   |
|-----------------------------|---------|----------------|-------------|
| dataInicial                 | Data    | Sim            | Data inicial do período a ser consultado  no formato AAAAMMDD. Dtfil dídltd             |
| dataFinal                   | Data    | Sim            | Data final do período a ser consultado  no formato AAAAMMDD.             |
| codigoModalidadeContratacao | Inteiro | Sim            | Código da tabela de domínio referente  a Modalidade da Contratação             |
| codigoModoDisputa           | Inteiro | Não            | Código da tabela de domínio referente  a Modo de Disputa             |
| uf                          | String  | Não            | Sigla da Unidade Federativa referente  Unidade Administrativa do órgão             |
| codigoMunicipioIbge         | String  | Não            | Código IBGE do Município da Unidade  Administrativa Cnpj do órgão originário da             |
|                             | String  | Não            | contratação informado na inclusão  (proprietário da contratação) Código da Unidade Administrativa do  Órgão originário da contratação             |
| codigoUnidadeAdministrativa | String  | Não            | (pp contratação) Identificado do sistema usuário  (Sistema de Contratações Públicas) que             |
| idUsuario                   | Inteiro | Não            | (Sistema de Contratações Públicas) que  publicou a contratação. Número da página que se deseja obter             |
| pagina                      | inteiro | Sim            | Número da página que se deseja obte os dados.             |

tamanhoPagina

Inteiro

Não

Por padrão cada página contém no máximo 50 registros, no entanto o tamanho de registros em cada página pode ser ajustado (até o limite de 500 registros) com vistas a tornar a entrega de dados mais rápida .

| Dados de retorno   | Dados de retorno   | Dados de retorno   | Dados de retorno                                  |
|--------------------|--------------------|--------------------|---------------------------------------------------|
| Id                 | Campo              | Tipo               | Descrição                                         |
| 1                  | numeroControlePNCP | String             | Número de Controle PNCP da Contratação (i Contratação PNCP)                                                   |
| 2                  | numeroCompra       | Texto (50)         | Número da Contratação no sistema de origem        |
| 3                  | anoCompra          | Inteiro            | Ano da Contratação                                |
| 4                  | processo           | Texto (50)         | Número do processo de Contratação no sistema de  origem                                                   |
| 5                  | tipoInstrumentoConvoc atorioId                    | Inteiro            | Código do instrumento convocatório da Contratação |
| 6                  | tipoInstrumentoConvoc atorioNome                    | String             | Nome do instrumento convocatório da Contratação   |
| 7                  | modalidadeId       | Inteiro            | Código da Modalidade referente à Contratação      |
| 8                  | modalidadeNome     | String             | Modalidade referente à Contratação                |
| 9                  | modoDisputaId      | Inteiro            | Código do modo de disputa referente à Contratação |
| 10                 | modoDisputaNome    | String             | Modo de disputa referente à Contratação           |
| 11                 | situacaoCompraId   | Inteiro            | Código da situação da Contratação                 |
| 12                 | situacaoCompraNome | Inteiro            | Situação da Contratação                           |
| 13                 | objetoCompra       | Texto (5120)       | Descrição do Objeto referente à Contratação       |
| 14                 | informacaoComplemen tar                    | Texto (5120)       | Informação Complementar do objeto referente à  Contratação                                                   |
| 15                 | srp                | Boleano            | Contratação Identifica se a compra trata-se de um SRP (Sistema d registro de preços)                                                   |
| 16                 | l                  |                    | Dados do amparo lega                              |
| 16.1               | codigo             | Inteiro            | Código do Amparo Lega                             |

|   16.2  | nome                 | String      | Nome do Amparo Legal                               |
|---------|----------------------|-------------|----------------------------------------------------|
|    16.3 | descricao            | String      | Descrição do Amparo lega                           |
|    17   | valorTotalEstimado   | Decimal     | dígitos decimais; Ex: 100.0001; Obs: Retornará valor  zero (0) se atributo orcamentoSigiloso for true e o item  não possuir resultado. Valor total homologado com base nos resultados                                                    |
|    18   | valorTotalHomologado | Decimal     | g incluídos. Precisão de até 4 dígitos decimais; Ex:  100.0001; Dtdbtdbitdt                                                    |
|    19   | dataAberturaProposta | Data e Hora | (horário de Brasília)                              |
|    20   | dataEncerramentoProp osta                      | Data e Ho   | Data de encerramento do recebimento de proposta (horário de Brasília)                                                    |
|    21   | dataPublicacaoPncp   | Data        | Data da publicação da Contratação no PNCP          |
|    22   | dataInclusao         | Data        | Data da inclusão do registro da Contratação no PNC |
|    23   | dataAtualizacao      | Data        | Data da última atualização do registro da Contrata |
|    24   | sequencialCompr      | Inteir      | Sequencial da Contratação no PNCP; Número  sequencial gerado no momento que a contratação fo inserida no PNCP;                                                    |
|    25   | orgaoEntidade        |             | Dados do Órgão/Entidade                            |
|    25.1 | cnpj                 | String      | CNPJ do Órgão referente à Contratação              |
|    25.2 | razaosocial          | String      | Razão social do Órgão referente à Contratação      |
|    25.3 | poderId              | String      | Código do poder a que pertence o Órgão. L - Legislativo; E - Executivo; J - Judiciário                                                    |
|    25.4 | esferaId             | String      | gqpg F - Federal; E - Estadual; M - Municipal; D - Distrital                                                    |
|    26   | unidadeOrgao         |             | Dados da Unidade Administrativa                    |
|    26.1 | codigoUnidade        | String      | Código da Unidade Administrativa pertencente ao  Órgão                                                    |
|    26.2 | nomeUnidade          | String      | Nome da Unidade Administrativa pertencente ao  Órgão                                                    |
|    26.3 | codigoIbge           | Inteiro     | Código IBGE do município                           |
|    26.3 | codigoIbge           | Inteiro     | Código IBGE do município                           |

|   26.4  | municipioNome           | String           | Nome do município                                    |
|---------|-------------------------|------------------|------------------------------------------------------|
|    26.5 | ufSigla                 | String           | Sigla da unidade federativa do município             |
|    26.6 | ufNome                  | String           | Nome da unidade federativa do município              |
|    27   | orgaoSubRogado          |                  | Dados do Órgão/Entidade subrogado                    |
|    28.1 | cnpj                    | String           | CNPJ do Órgão referente à Contratação                |
|    28.2 | razaosocial             | String           | Razão social do Órgão referente à Contratação        |
|    28.3 | poderId                 | String           | Códgo do podea que petece o Ógão. L - Legislativo; E - Executivo; J - Judiciário Ó                                                      |
|    28.4 | esferaId                | String           | Código da esfera a que pertence o Órgão. F - Federal; E - Estadual; M - Municipal; D - Distrital Dados da Unidade Administrativa do Órgão                                                      |
|    29   | unidadeSubRogada        | unidadeSubRogada | Dados da Unidade Administrativa do Órgão  subrogado                                                      |
|    29.1 | codigoUnidade           | String           | Código da Unidade Administrativa pertencente ao  Órgão subrogado Nome da Unidade Administratia pertencente ao                                                      |
|    29.2 | nomeUnidade             | String           | Nome da Unidade Administrativa pertencente ao  Órgão subrogado                                                      |
|    29.3 | codigoIbge              | Inteiro          | Código IBGE do município                             |
|    29.4 | municipioNome           | String           | Nome do município                                    |
|    29.5 | ufSigla                 | String           | Sigla da unidade federativa do município             |
|    29.6 | ufNome                  | String           | Nome da unidade federativa do município              |
|    30   | usuarioNome             | String           | Nome do Usuário/Sistema que enviou a Contratação     |
|    31   | linkSistemaOrigem       | String           | URL para página/portal do sistema de origem da  contratação para recebimento de propostas.                                                      |
|    32   | justificativaPresencial | String           | Justificativa pela escolha da modalidade presencial. |
|    32   | justificativaPresencial | String           | Justificativa pela escolha da modalidade presencial. |

## Códigos de Retorno

|   Código HTTP  | ensagem    | Tipo    |
|----------------|------------|---------|
|           200  | OK         | Sucesso |
|           204  | No Content | Sucesso |

|   400  | Bad Request           | Erro   |
|--------|-----------------------|--------|
|   422  | Unprocessable Entity  | Erro   |
|   500  | Internal Server Error | Erro   |

## 6.4. Serviço Consultar Contratações com Período de Recebimento de Propostas em Aberto

Serviço que permite consultar contratações publicadas no PNCP por um período informado. Opcionalmente poderá ser informado o código da Modalidade da Contratação código do IBGE do Município, sigla da Unidade Federativa da Unidade Administrativa do Órgão, CNPJ do Órgão/Entidade, código da Unidade Administrativa do Órgão/Entidade ou código de identificação do Usuário (Sistema de Contratações Públicas que publicou a Contratação) para refinar a consulta.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/contratacoes/proposta | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| rl -k -X ‘GET’ \          | rl -k -X ‘GET’ \          | rl -k -X ‘GET’ \          |

## Dados de entrada

Nota: Dados a serem enviados no cabeçalho da requisição.

| Campo                       | Tipo    | Obrigatório    | Descrição   |
|-----------------------------|---------|----------------|-------------|
| dataFinal                   | Data    | Sim            | Data final do período a ser consultado  no formato AAAAMMDD.             |
| codigoModalidadeContratacao | Inteiro | Sim            | Código da tabela de domínio  Modalidade da Contratação             |

| uf                 | uf                              | String    |                                      |
|--------------------|---------------------------------|-----------|--------------------------------------|
| codigoMunicipioIbg | String                          | N         | Administrativa                       |
| cnpj               | cnpj                            | Nã        | (proprietário da contratação)        |
| codigoUnida        | odigoUnidadeAdministrativa      | ng        | contratação)                         |
| idUsuari           | dUsuario                        | Não       | publicou a contratação.              |
| pagina             | inteiro                         | Sim       | Número da página que se deseja obter  os dados. Por padrão cada página contém no  máximo 500 registros, no entanto o                                      |
| tamanh             | hoPagina                        | Não       | máximo 500 registros, no entanto o  tamanho de registros em cada página  pode ser ajustado (até o limite de 500  registros) com vistas a tornar a entrega de dados mais rápida.                                      |
| Dados de retorno   | Dados de retorno                |           |                                      |
| Id                 | Campo                           | Tipo      | Descrição                            |
| 1                  | umeroControlePNCP               | String    | Contratação PNCP)                    |
| 2                  | numeroCompra                    | Texto     | origem                               |
| 3                  | processo                        | Tt(50     | Número do processo de Contratação no |
| 5                  | tipoInstrumentoConvocatorioId   | Id Inte   | Contratação                          |
|                    | tipoInstrumentoConvocatorioId   | oNome St  | g Contratação Nome do instrumento convocatório da                                      |
| 6                  | tipoInstrumentoConvocatorioNome | Nome Str  | ç Nome do instrumento convocatório da  Contratação                                      |

|   7  | modalidadeId             | Inteiro   | Código da Modalidade referente à  Contratação                                             |
|------|--------------------------|-----------|---------------------------------------------|
|  8   | modalidadeNome           | String    | Modalidade referente à Contratação          |
|  9   | modoDisputaId            | Inteiro   | Código do modo de disputa referente à  Contratação                                             |
| 10   | modoDisputaNome          | String    | Modo de disputa referente à Contratação     |
| 11   | situacaoCompraId         | Inteiro   | Código da situação da Contratação           |
| 12   | situacaoCompraNome       | Inteiro   | Situação da Contratação                     |
| 13   | objetoCompra             | (5120)    | Descrição do Objeto referente à Contratação |
| 14   | informacaoComplementar   | (5120)    | Informação Complementar do objeto  referente à Contratação                                             |
| 15   | srp                      | Boleano   | p (Sistema de registro de preços)                                             |
| 16   | amparoLegal              |           | Dados do amparo legal                       |
| 16.1 | codigo                   | Inteiro   | Código do Amparo Legal                      |
| 16.2 | nome                     | String    | Nome do Amparo Legal                        |
| 16.3 | descricao                | String    | Descrição do Amparo legal Valor total estimado da Contratação. Precis de até 4 dígitos decimais; Ex: 100.0001; Obs Retornará valor zero (0) se atributo                                             |
| 17   | valorTotalEstimado       | Decimal   | de até 4 dígitos decimais; Ex: 100.0001; Obs:  Retornará valor zero (0) se atributo  orcamentoSigiloso for true e o item não  possuir resultado. Valor total homologado com base nos                                             |
| 18   | valorTotalHomologado     | Decimal   | resultados incluídos. Precisão de até 4 dígitos  decimais; Ex: 100.0001; Data de abertura do recebimento de                                             |
| 19   | dataAberturaProposta     | Data e  Hora           | Data de abertura do recebimento de  propostas (horário de Brasília)                                             |
| 20   |                          | Hora Data e           | ata de encerramento do recebimento de  ropostas (horário de Brasília)                                             |
| 20   | dataEncerramentoProposta | Hora      | propostas (horário de Brasília)             |
| 21   | dataPublicacaoPncp       | Data      | Data da publicação da Contratação no PNCP   |
| 22   | dataInclusao             | Data      | Data da inclusão do registro da Contratação |

no PNCP

|   23  | dataAtualizacao    | Data    | Data da última atualização do registro da  Contratação                                          |
|-------|--------------------|---------|------------------------------------------|
|  24   | sequencialCompra   | Inteiro | Sequencial da Contratação no PNCP; Número  sequencial gerado no momento que a  contratação foi inserida no PNCP;                                          |
|  25   | orgaoEntidade      |         | Dados do Órgão/Entidade                  |
|  25.1 | cnpj               | String  | CNPJ do Órgão referente à Contratação Razão social do Órgão referente à                                          |
|  25.2 | razaosocial        | String  | Contratação Código do poder a que pertence o Órgão                                          |
|  25.3 | poderId            | String  | Código do poder a que pertence o Órgão. L - Legislativo; E - Executivo; J - Judiciário Código da esfera a que pertence o Órgão                                          |
|  25.4 | esferaId           | String  | F - Federal; E - Estadual; M - Municipal; D - Distrital                                          |
|  26   | unidadeOrgao       |         | Dados da Unidade Administrativa          |
|  26.1 | codigoUnidad       | String  | Código da Unidade Administrativa  pertencente ao Órgão                                          |
|  26.2 | nomeUnidade        | String  | Nome da Unidade Administrativa pertencen ao Órgão                                          |
|  26.3 | codigoIbge         | Inteiro | Código IBGE do município                 |
|  26.4 | municipioNome      | String  | Nome do município                        |
|  26.5 | ufSigla            | String  | Sigla da unidade federativa do município |
|  26.6 | ufNome             | String  | Nome da unidade federativa do município  |
|  27   | orgaoSubRogado     |         | Dados do Órgão/Entidade subrogado        |
|  28.1 | cnpj               | String  | CNPJ do Órgão referente à Contratação Ó                                          |
|  28.2 | razaosocial        | String  | Razão social do Órgão referente à  Contratação Ó                                          |
|  28.3 | poderId            | String  | Código do poder a que pertence o Órgão. L - Legislativo; E - Executivo; J - Judiciário                                          |
|  28.4 | esferaId           | String  | Código da esfera a que pertence o Órgão. |
|  28.4 | esferaId           | String  | Código da esfera a que pertence o Órgão. |

F -Federal; E -Estadual; M -Municipal; D Distrital

|   29  | unidadeSubRogada        |         | Dados da Unidade Administrativa do  Órgão subrogado                                          |
|-------|-------------------------|---------|------------------------------------------|
|  29.1 | codigoUnidade           | String  | Código da Unidade Administrativa  pertencente ao Órgão subrogado Nome da Unidade Administrativa pertence Óãbd                                          |
|  29.2 | nomeUnidade             | String  | Nome da Unidade Administrativa pertencente  ao Órgão subrogado                                          |
|  29.3 | codigoIbge              | Inteiro | Código IBGE do município                 |
|  29.4 | municipioNome           | String  | Nome do município                        |
|  29.5 | ufSigla                 | String  | Sigla da unidade federativa do município |
|  29.6 | ufNome                  | String  | Nome da unidade federativa do município  |
|  30   | usuarioNome             | String  | Nome do Usuário/Sistema que enviou a  Contratação                                          |
|  31   | linkSistemaOrigem       | String  | URL para página/portal do sistema de origem  da contratação para recebimento de  propostas.                                          |
|  32   | justificativaPresencial | String  | Justificativa pela escolha da modalidade  presencial.                                          |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           204  | No Content            | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4.1 -Observação:

Em adição ao serviço "6.4. Serviço Consultar Contratações com Período de Recebimento de Propostas em Aberto" mencionado neste manual, é importante destacar que o Portal Nacional de Contratações Públicas (PNCP) oferece uma gama ampla de

funcionalidades via API que permitem uma consulta detalhada sobre CONTRATAÇÕES. Estas funcionalidades estão minuciosamente descritas no Manual de Integração — Portal Nacional de Contratações Públicas - PNCP, disponível no site oficial www.gov.br. Abaixo, apresentamos uma lista com alguns exemplos de serviços disponíveis:

-  6.3.5. Consultar uma Contratação
-  6.3.8. Consultar Todos Documentos de uma Contratação
-  6.3.13. Consultar Itens de uma Contratação
-  6.3.14. Consultar Item de uma Contratação
-  6.3.17. Consultar Resultados de Item de uma Contratação
-  6.3.18. Consultar um Resultado específico de Item de uma Contratação
-  6.3.19. Consultar Histórico da Contratação
-  6.3.22. Consultar Imagens de um Item de Contratação

Recomendamos a leitura detalhada do Manual de Integração do PNCP para uma compreensão abrangente de todas as funcionalidades e possibilidades oferecidas pela API.

## 6.5. Serviço Consultar Atas de Registro de Preço por Período de Vigência

Serviço que permite consultar atas de registro de preços publicadas no PNCP por um período informado.

A partir da data inicial e data final informadas , serão recuperadas as atas cujo período de vigência coincida com o período informado. Opcionalmente poderá ser informado CNPJ do Órgão/Entidade, código da Unidade Administrativa do Órgão/Entidade ou número de identificação do Usuário (Portais de Contratações Públicas) .

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/atas                  | GET                       |                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |

| curl -X 'GET' \       | curl -X 'GET' \                                                                     |
|-----------------------|-------------------------------------------------------------------------------------|
| '${BASE_              | '${BASE_URL}/v1/atas?dataInicial=20230701&dataFinal=20230831&pagina=1 ' \           |
| -H 'accept            |                                                                                     |
| ou                    | ou                                                                                  |
| curl -X 'GET' \       | curl -X 'GET' \                                                                     |
| '${BASE_URL}/v1/atas? | '${BASE_URL}/v1/atas?                                                               |
| dataInicial=202       | icial=20231024&dataFinal=20241023&idUsuario=36&cnpjOrgao=00394429000100&pagina=1' \ |
| -H 'accept: */*       |                                                                                     |

## Dados de entrada

Nota: Dados a serem enviados no cabeçalho da requisição.

| Campo                       | Tipo    | Obrigatório    | Descrição   |
|-----------------------------|---------|----------------|-------------|
| dataInicial                 | Data    | Sim            | Data inicial do período a ser consultado no  formato AAAAMMDD.             |
| dataFinal                   | Data    | Sim            | Data final do período a ser consultado no  formato AAAAMMDD. Identificado do sistema usuário (Sistema             |
| idUsuario                   | Inteiro | Não            | Identificado do sistema usuário (Sistema  de Contratações Públicas) que publicou a  ata.             |
| cnpj                        | String  | Não            | Cnpj do órgão originário da contratação  informado na inclusão (proprietário da  contratação) ódddddd             |
| codigoUnidadeAdministrativa | String  | Não            | Órgão originário da contratação informad na inclusão (proprietário da contratação) Número da página que se deseja obter os             |
| pagina                      | Inteiro | Sim            | Número da página que se deseja obter os  dados.             |
| tamanhoPagina               | Inteiro | Não            | na inclusão (proprietário da contratação) Número da página que se deseja obter os  dados. Por padrão cada página contém no  máximo 500 registros, no entanto o  tamanho de registros em cada página pode  ser ajustado (até o limite de 500 registros)             |

## Dados de retorno

|   Id  | Campo    | Tipo    | Descrição                  |
|-------|----------|---------|----------------------------|
|    1  | Atas     | Agrupad | Agrupador da lista de atas |

|   1.1  | numeroControlePNCPAta    | String     | Número de Controle PNCP da Ata (id Ata PNCP   |
|--------|--------------------------|------------|-----------------------------------------------|
|   1.2  | numeroControlePNCPCompr  | String     | Contratação PNCP) que a ata está vinculada    |
|   1.3  | numeroAtaRegistroPreco   | Texto (50) | Número da Ata no sistema de origem            |
|   1.4  | anoAta                   | Inteiro    | Ano da Ata                                    |
|   1.5  | dataAssinatura           | Data       | Data de assinatura da Ata                     |
|   1.6  | vigenciaInicio           | Data       | Data de início de vigência da Ata             |
|   1.7  | vigenciaFim              | Data       | Data de fim de vigência da Ata                |
|   1.8  | dataCancelamento         | Data       | Data de cancelamento da Ata                   |
|   1.9  | cancelado                | Booleano   | Indicador de cancelamento da Ata              |
|   1.1  | dataPublicacaoPncp       | Data       | Data da publicação da Ata no PNCP             |
|   1.11 | dataInclusao             | Data       | Data da inclusão do registro da Ata no PNCP   |
|   1.12 | dataAtualizaca           | Data       | Data da última atualização do registro da Ata |
|   1.13 | objetoContratacao        | String     | Descrição do Objeto referente à Contratação   |
|   1.14 | cnpjOrgao                | String     | CNPJ do Órgão referente à Contratação         |
|   1.15 | nomeOrgao                | String     | Razão Social do Órgão referente à Contratação |
|   1.16 | codigoUnidadeOrgao       | String     | Código da Unidade Administrativa do Órgão  referente à Contratação                                               |
|   1.17 | nomeUnidadeOrgao         | String     | Nome da Unidade Administrativa do Órgão  referente à Contratação                                               |
|   1.18 | cnpjOrgaoSubrogado       | String     | CNPJ do Órgão subrogado referente à  Contratação Ó                                               |
|   1.19 | nomeOrgaoSubrogado       | String     | Razão Social do Órgão subrogado referente à  Contratação                                               |
|   1.2  | codigoUnidadeOrgaoSubrogad o                          | String     | Código da Unidade Administrativa subrogada do  Órgão subrogado referente à Contratação                                               |
|   1.21 | nomeUnidadeOrgaoSubrogad o                          | String     | Nome da Unidade Administrativa subrogada do  Órgão subrogado referente à Contratação                                               |

1.22

usuario

Nome do sistema usuário (Sistema de

String

Contratações Públicas) que publicou a ata.

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           204  | No Content            | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.1 -Observação:

Em adição ao serviço "6.5. Serviço Consultar Atas de Registro de Preço por Período de Vigência " mencionado neste manual, é importante destacar que o Portal Nacional de Contratações Públicas (PNCP) oferece uma gama ampla de funcionalidades via API que permitem uma consulta detalhada sobre CONTRATAÇÕES. Estas funcionalidades estão minuciosamente descritas no Manual de Integração — Portal Nacional de Contratações Públicas - PNCP, disponível no site oficial www.gov.br. Abaixo, apresentamos uma lista com alguns exemplos de serviços disponíveis:

-  6.4.4. Consultar Atas de Registro de Preço por Compra
-  6.4.8. Consultar Todos os Documentos de uma Ata
-  6.4.9. Consultar Documento de uma Ata

Recomendamos a leitura detalhada do Manual de Integração do PNCP para uma compreensão abrangente de todas as funcionalidades e possibilidades oferecidas pela API.

## 6.6. Serviço Consultar Contratos por Data de Publicação

Serviço que permite consultar contratos e/ou empenhos com força de contrato publicados no PNCP por um período informado. A partir da data inicial e data final informadas serão recuperados os contratos/empenhos publicados no período . Opcionalmente poderá ser informado CNPJ do Órgão/Entidade, código da Unidade Administrativa do Órgão/Entidade ou número de identificação do Usuário (Portais de Contratações Públicas) .

## Detalhes de Requisição

| Endpoint                                                                                  | Método HTTP                                                                               | Exemplo de Payload                                                                        |
|-------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| /v1/contratos                                                                             | GET                                                                                       | Não se aplica                                                                             |
| Exemplo Requisição (cURL)                                                                 | Exemplo Requisição (cURL)                                                                 | Exemplo Requisição (cURL)                                                                 |
| curl -k -X GET "${BASE_URL}/v1/contratos?dataInicial=20230801&dataFinal=20230831&pagina=1" / -H "accept: */*"                                                                                           | curl -k -X GET "${BASE_URL}/v1/contratos?dataInicial=20230801&dataFinal=20230831&pagina=1" / -H "accept: */*"                                                                                           | curl -k -X GET "${BASE_URL}/v1/contratos?dataInicial=20230801&dataFinal=20230831&pagina=1" / -H "accept: */*"                                                                                           |
| p ou                                                                                           | p ou                                                                                           | p ou                                                                                           |
| curl -k -X GET                                                                            | curl -k -X GET                                                                            | curl -k -X GET                                                                            |
| "${BASE_URL}/v1/contratos?dataInicial=20230801&dataFinal=20230831&cnpjOrgao=0039454400018 | "${BASE_URL}/v1/contratos?dataInicial=20230801&dataFinal=20230831&cnpjOrgao=0039454400018 | "${BASE_URL}/v1/contratos?dataInicial=20230801&dataFinal=20230831&cnpjOrgao=0039454400018 |
| 5&pagina=1" / H "*/*"                                                                                           | 5&pagina=1" / H "*/*"                                                                                           | 5&pagina=1" / H "*/*"                                                                                           |
| 5&pagina=1" / -H "accept: */*"                                                                                           | 5&pagina=1" / -H "accept: */*"                                                                                           | 5&pagina=1" / -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| 5&pagina=1" / H "accept: */*"                                                                                           | 5&pagina=1" / H "accept: */*"                                                                                           | 5&pagina=1" / H "accept: */*"                                                                                           |
| 5&pagina=1" / -H "accept: */*"                                                                                           | 5&pagina=1" / -H "accept: */*"                                                                                           | 5&pagina=1" / -H "accept: */*"                                                                                           |
| 5&pagina=1" / H "t*/*"                                                                                           | 5&pagina=1" / H "t*/*"                                                                                           | 5&pagina=1" / H "t*/*"                                                                                           |
| 5&pagina=1" / -H "accept: */*"                                                                                           | 5&pagina=1" / -H "accept: */*"                                                                                           | 5&pagina=1" / -H "accept: */*"                                                                                           |
| 5&pagina=1" / -H "accept: */*"                                                                                           | 5&pagina=1" / -H "accept: */*"                                                                                           | 5&pagina=1" / -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |
| pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           | pg -H "accept: */*"                                                                                           |

## Dados de entrada

Nota: Dados a serem enviados no cabeçalho da requisição.

| Campo                       | Tipo    | Obrigatório    | Descrição                          |
|-----------------------------|---------|----------------|------------------------------------|
| dataInicial                 | Data    | Sim            | Data inicial do período a ser consultado no  formato AAAAMMDD.                                    |
| dataFinal                   | Data    | Sim            | Data final do período a ser consultado no  formato AAAAMMDD. dóád                                    |
| cnpjOrgao                   | String  | Não            | Cnpj do órgão originário da contratação  informado na inclusão (proprietário do contrato) Código da Unidade Administrativa do                                    |
| codigoUnidadeAdministrativa | String  | Não            | g Órgão originário da contratação informado  na inclusão (proprietário do contrato) Identificado do sistema usuário (Sistema                                    |
| usuarioId                   | Inteiro | Não            | Identificado do sistema usuário (Sistema  de Contratações Públicas) que publicou o  contrato.                                    |
| pagina                      | Inteiro | Sim            | Número da página a ser requisitada |
| tamanhoPagina               | Inteiro | Não            | Número da página a ser requisitada Por padrão cada página contém no  máximo 500 registros, no entanto o  tamanho de registros em cada página pode  ser ajustado (até o limite de 500 registros)                                    |

## Dados de retorno

|   Id  | Campo                    | Tipo       | Descrição   |
|-------|--------------------------|------------|-------------|
|    1  | numeroControlePNCP       | String     | Número de controle PNCP do contrato (id  contrato PNCP)             |
|    2  | numeroControlePNCPCompra | String     | Número de controle PNCP da contratação  relacionada (id contratação PNCP)             |
|    3  | numeroContratoEmpenho    | Texto (50) | Número do contrato ou empenho com força d contrato             |

|   4  | anoContrato            | Inteiro      | Ano do contrato                             |
|------|------------------------|--------------|---------------------------------------------|
|  5   | sequencialContrato     | Inteiro      | Número sequencial do contrato (gerado pelo  PNCP)                                             |
|  6   | processo               | Texto (50)   | Número do processo                          |
|  7   | tipoContrato           |              | Dados do tipo de contrato                   |
|  7.1 | Id                     | Inteiro      | Código da tabela de domínio Tipo de contrat |
|  7.2 | Nome                   | String       | Nome do Tipo de Contrato                    |
|  8   | categoriaProcesso      |              | Dados da categoria do processo              |
|  8.1 | Id                     | Inteiro      | Código da tabela de domínio Categoria       |
|  8.2 | Nome                   | String       | Nome da Categoria do processo               |
|  9   | receita                | Boleano      | Receita ou despesa: True - Receita; False - Despesa;                                             |
| 10   | objetoContrato         | Texto (5120) | Descrição do objeto do contrato             |
| 11   | informacaoComplementar | Texto (5120) | Informações complementares; Se existir;     |
| 12   | orgaoEntidade          |              | Dados do Órgão/Entidade do Contrato         |
| 12.1 | cnpj                   | String       | CNPJ do Órgão referente à Contrato          |
| 12.2 | razaoSocial            | String       | Razão social do Órgão referente à Contrato  |
| 12.3 | poderId                | String       | L - Legislativo; E - Executivo; J - Judiciário Código da esfera a que pertence o Órgão. F - Federal; E - Estadual; M - Municipal; D -                                             |
| 12.4 | esferaId               | String       | Código da esfera a que pertence o Órgão. F - Federal; E - Estadual; M - Municipal; D - Distrital Ó                                             |
| 13   | unidadeOrgao           |              | Dados da Unidade executora do Órgão do  Contrato                                             |
| 13.1 | codigoUnidade          | String       | Código da Unidade Executora pertencente ao  Órgão                                             |
| 13.2 | nomeUnidade            | String       | Nome da Unidade Executora pertencente ao  Órgão                                             |
| 13.3 | codigoIbge             | Inteiro      | Código IBGE do município                    |

| 13.4    | municipioNome             | String      | Nome do município                        |
|---------|---------------------------|-------------|------------------------------------------|
| 13.5    | ufSigla                   | String      | Sigla da unidade federativa do município |
| 13.6    | ufNome                    | String      | Nome da unidade federativa do município  |
| 14      | orgaoSubRogado            |             | Dados do Órgão/Entidade subrogado do  Contrato                                          |
| 14.1    | cnpj                      | String      | CNPJ do Órgão referente à Contrato       |
| 14.2    | razaoSocial               | String      | Razão social do Órgão referente à Contrato Ó                                          |
| 14.3    | poderId                   | String      | L - Legislativo; E - Executivo; J - Judiciário Código da esfera a que pertence o Órgão. F - Federal; E - Estadual; M - Municipal; D -                                          |
| 14.4    | esferaId                  | String      | Código da esfera a que pertence o Órgão. F - Federal; E - Estadual; M - Municipal; D - Distrital Ó                                          |
| 15      | unidadeSubRogada          |             | Dados da Unidade Executora do Órgão  subrogado                                          |
| 15.1    | codigoUnidade             | String      | Código da Unidade Executora pertencente ao  Órgão                                          |
| 15.2    | nomeUnidade               | String      | Nome da Unidade Executora pertencente ao  Órgão                                          |
| 15.3    | codigoIbge                | Inteiro     | Código IBGE do munic                     |
| 15.4    | municipioNome             | String      | Nome do município                        |
| 15.5    | ufSigla                   | String      | Sigla da unidade federativa do município |
| 15.6    | ufNome                    | String      | Nome da unidade federativa do município  |
| 16      | tipoPessoa                | Texto (2)   | PJ - Pessoa jurídica; PF - Pessoa física; PE - Pessoa estrangeira; Número de identificação do                                          |
|         | tipoPessoa                | Texto (2)   | Pessoa estrangeira; Número de identificação do  fd/CNPJCPF                                          |
| 17      | niFornecedor              | Texto (30)  | fornecedor/arrematante; CNPJ, CPF ou  identificador de empresa estrangeira; Nome ou razão social do                                          |
| 18      | nomeRazaoSocialFornecedor | Texto (100) | Nome ou razão social do  fornecedor/arrematante PJ - Pessoa jurídica; PF - Pessoa física; PE -                                          |
| 19      | tipoPessoaSubContratada   | Texto (2)   | PJ - Pessoa jurídica; PF - Pessoa física; PE - Pessoa estrangeira; Somente em caso de  subcontratação;                                          |

|   20  | niFornecedorSubContratado    | Texto (30)   | Número de identificação do fornecedor  subcontratado; CNPJ, CPF ou identificador de  empresa estrangeira; Somente em caso de  subcontratação; Nome ou razão social do fornecedor                                                |
|-------|------------------------------|--------------|-----------------------------------------------|
|   21  | nomeFornecedorSubContratado  | Texto (100)  | Nome ou razão social do fornecedor  subcontratado; Somente em caso de  subcontratação; Vliiil dPiãdé 4                                               |
|   22  | valorInicial                 | Decima       | dígitos decimais; Ex: 100.0001;               |
|   23  | numeroParcelas               | Inteiro      | Número de parcelas                            |
|   24  | valorParcela                 | Decimal      | Valor da parcela. Precisão de até 4 dígitos  decimais; Ex: 100.0001;                                               |
|   25  | valorGlobal                  | Decima       | Valor global do contrato. Precisão de até 4  dígitos decimais; Ex: 100.0001;                                               |
|   26  | valorAcumulado               | Decimal      | Valor acumulado do contrato. Precisão de até 4  dígitos decimais; Ex: 100.0001;                                               |
|   27  | dataAssinatura               | Data         | Data de assinatura do contrato                |
|   28  | dataVigenciaInicio           | Data         | Data de início de vigência do contrato        |
|   29  | dataVigenciaFim              | Data         | Data do término da vigência do contrato       |
|   30  | numeroRetificacao            | Inteiro      | Número de retificações; Número de vezes que  este registro está sendo alterado;                                               |
|   31  | usuarioNome                  | String       | Nome do sistema/portal que enviou o contrato  |
|   32  | dataPublicacaoPncp           | Data/Hora    | Data de publicação do contrato no PNCP        |
|   33  | dataAtualizacao              | Data/Hora    | ata da última atualização do contrato no PNCP |
|   34  | identificadorCipi            | String       | dentificador do contrato no Cadastro Integrado  e Projetos de Investimento                                               |
|   35  | urlCipi                      | Sti          | e Projetos de Investimento rl com informações do contrato no sistema de  dddjdi                                               |
|   35  | urlCipi                      | String       | Cadastro Integrado de Projetos de Investiment |

## Códigos de Retorno

|   Código HTTP  |    | Mensagem    | Tipo    |
|----------------|----|-------------|---------|
|           200  | OK | Sucesso     | Sucesso |

## Manual PNCP API Consultas – Versão 1.0

|   204  | No Content            | Sucesso   |
|--------|-----------------------|-----------|
|   400  | Bad Request           | Erro      |
|   422  | Unprocessable Entity  | Erro      |
|   500  | Internal Server Error | Erro      |

## 6.6.1 -Observação:

Em adição ao serviço "6.6. Serviço Consultar Contratos por Data de Publicação" mencionado neste manual, é importante destacar que o Portal Nacional de Contratações Públicas (PNCP) oferece uma gama ampla de funcionalidades via API que permitem uma consulta detalhada sobre CONTRATAÇÕES. Estas funcionalidades estão minuciosamente descritas no Manual de Integração — Portal Nacional de Contratações Públicas -PNCP, disponível no site oficial www.gov.br. Abaixo, apresentamos uma lista com alguns exemplos de serviços disponíveis:

-  6.5.7. Consultar Documento de um Contrato
-  6.5.9. Consultar Contratos de uma Contratação

Recomendamos a leitura detalhada do Manual de Integração do PNCP para uma compreensão abrangente de todas as funcionalidades e possibilidades oferecidas pela API.

## 7. Suporte

Em caso de problemas durante o processo de integração do seu sistema com o PNCP, por favor entre em contato com a Central de Atendimento do Ministério da Gestão e da Inovação em Serviços Públicos (https://portaldeservicos.economia.gov.br) ou pelo telefone 0800 978 9001.

## 8. Glossário

O seguinte glossário fornece definições e explicações de termos e siglas específicos utilizados ao longo deste documento. O objetivo é esclarecer qualquer ambiguidade e ajudar o leitor a compreender melhor o conteúdo apresentado.

- ➢ API (Application Programming Interface): Interface de Programação de Aplicações. É um conjunto de rotinas e padrões estabelecidos por um software para a utilização das suas funcionalidades por programas que não pretendem envolver-se em detalhes da implementação do software, mas apenas usá-lo.
- ➢ CNBS (Catálogo Nacional de Bens e Serviços): Catálogo que lista e categoriza bens e serviços. Em muitos contextos, serve como uma referência padronizada para a classificação e descrição de itens. Mais informações em: https://www.gov.br/compras/ptbr/sistemas/conheca -o-compras/catalogo
- ➢ CNPJ (Cadastro Nacional da Pessoa Jurídica): É o registro de empresas e outras entidades na Receita Federal do Brasil.

- ➢ HTTP (Hypertext Transfer Protocol): Protocolo de Transferência de Hipertexto. É o protocolo fundamental da web, usado para transferir e exibir páginas da web, entre outros.
- ➢ JSON (JavaScript Object Notation): Notação de Objeto JavaScript. É um formato de intercâmbio de dados leve e de fácil leitura e escrita para seres humanos.
- ➢ ME/EPP: Microempresa e Empresa de Pequeno Porte. São categorias de empresas definidas pela legislação brasileira com base em seu faturamento.
- ➢ PDM (Padrão Descritivo de Material): Refere-se a um padrão ou modelo utilizado para descrever materiais de forma consistente e padronizada, facilitando a identificação, catalogação e gestão de materiais em diversos sistemas e contextos.
- ➢ PCA: plano de contratações anual definido na lei 14.133/2021
- ➢ PNCP (Portal Nacional de Contratações Públicas): sítio oficial estabelecido pela Lei 14133 para divulgação e gestão de contratações públicas no Brasil. Centraliza informações, editais e contratos, promovendo transparência e eficiência, e é gerido por um comitê nacional.
- ➢ REST (Representational State Transfer): Transferência de Estado Representacional. É um estilo arquitetural para desenvolvimento de serviços web. É caracterizado por um conjunto de restrições, incluindo um protocolo cliente/servidor sem estado e um conjunto padrão de métodos HTTP.
- ➢ SWAGGER: É uma ferramenta de software de código aberto usada para projetar, construir e documentar serviços web REST.
- ➢ TIC (Tecnologia da Informação e Comunicação): Refere-se a qualquer tecnologia que ajuda a produzir, manipular, armazenar, comunicar ou disseminar informação.
- ➢ URL (Uniform Resource Locator): Localizador Padrão de Recursos. É um endereço de um recurso na web.
- ➢ USUÁRIO: Em contextos de sistemas e aplicações, refere -se à pessoa ou entidade que utiliza o software ou sistema em questão.