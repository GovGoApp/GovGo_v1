

# Documento PNCP: ManualdeIntegraoPNCPVerso2.2.1.pdf

**Arquivo original:** `ManualdeIntegraoPNCPVerso2.2.1.pdf`  
**Tamanho:** 2.01 MB  
**Processado em:** 2025-07-16 20:49:19  
**Ferramenta:** Docling SUPER OTIMIZADO (PyPdfium + TableFormer FAST) + OpenAI GPT-4o  
**Tabelas encontradas:** 299  


---

## Manual de Integração

PNCP

Portal Nacional de Contratações Públicas

## Sumário

| 1. Objet                                                                                                                             | ...13   |
|--------------------------------------------------------------------------------------------------------------------------------------|---------|
| 2. Protocolo de Comunicação.......................         | .13     |
| 3. Acesso ao PNCP ..................................       | .13     |
| 3.1. Endereços de Acesso ....................              | .13     |
| 3.2. Autenticação/Autorização ..........                   | .13     |
| 4. Recomendações Iniciais....                                                                                                        | 14      |
| 4.1. Cadastro Inicial dos Órgãos/Entidades e suas Unidades .........                                                                 | 14      |
| 4.2. Manutenção dos Dados das Contratações Enviadas ....                                        | 15      |
| 5. Tabelas de Domínio............................                                               | 15      |
| 5.1. Instrumento Convocatório..................            | 15      |
| 5.2. Modalidade de Compra.......................           | .15     |
| 5.3. Modo de Disputa ....................                                                       | .16     |
| 5.4. Critério de Julgamento................................                                     | .16     |
| 5.5. Situação da Compra/Edital/Aviso ...............                                            | 16      |
| 5.6. Situação do Item da Compra/Edital/Aviso............                                        | 16      |
| 5.7. Tipo de Benefício ...........                                                              | 16      |
| 5.8. Situação do Resultado do Item da Compra/Edital/Aviso .......                               | 16      |
| 5.9. Tipo de Contrato.........................................                                  | .17     |
| 5.10. Tipo de Termo de Contrato...........................                                      | .17     |
| 5.11. Categoria do Processo ....................                                                | .17     |
| 5.12. Tipo de Documento...........................                                              | .18     |
| 5.13. Natureza Jurídica ......                             | .18     |
| 5.14. Porte da Empresa ............                        | .20     |
| 5.15. Amparo Legal........                                                                      | .20     |
| 5.15. Envio de arquivos pelas APIs de Documento .....................                           | .22     |
| 5.16. Categoria do Item do Plano de Contratações ................                               | ..22    |
| 6. Catálogo de Serviços (APIs) ................                                                                                      | .23     |
| 6.1. Serviços de Usuário ................                  | .23     |
| 6.1.1. Atualizar Usuário..........................         | 23      |
| Detalhes de Requisição................................     | .23     |
| Dados de entrada ......................................... | .23     |
| Dados de retorno..........................                 | 23      |
| Exemplo de Retorno............                             | 24      |

| Ma                                                                                                                           | PNCP– Versão 2.2.1
 24      |
|------------------------------------------------------------------------------------------------------------------------------|------|
| 6.1.2. Consultar Usuário por Id ...............................                         | 24   |
| Detalhes de Requisição............                                                      | 24   |
| Dados de entrada ........................          | 24   |
| Dados de retorno........................................                                | .25  |
| Exemplo de Retorno......................           | ..25 |
| Códigos de Retorno.....................................                                                                      | 26   |
| 6.1.3. Consultar Usuário por Login ou por CPF/CNPJ...........................                                                | 26   |
| Detalhes de Requisição............................                                                                           | 26   |
| Dados de entrada ..............                    | 26   |
| Dados de retorno..........................         | 27   |
| Exemplo de Retorno..............                   | 27   |
| Códigos de Retorno............                     | 28   |
| 6.1.4. Realizar Login de Usuário.................................                       | .28  |
| Detalhes de Requisição..........                   | .28  |
| Dados de entrada ................                  | .28  |
| Dados de retorno.......................            | .28  |
| Exemplo de Retorno...................              | .29  |
| Códigos de Retorno................                 | .29  |
| Códigos de Retorno...............                  | .29  |
| 6.2. Serviços de Órgão/Entidade..............................                           | .29  |
| Detalhes da Requisição.....................................                             | 30   |
| Dados de entrada ....................              | .30  |
| Dados de entrada ...................               | .30  |
| Exemplo de Retorno...........                      | 30   |
| Códigos de Retorno.............                    | .31  |
| 6.2.2. Consultar Órgão por Cnpj..................................                       | .31  |
| Detalhes da Requisição.............                | .31  |
| Detalhes da Requisição...............              | .31  |
| Dados de retorno.................................. | ..31 |
| Dados de retorno...............................    | ..32 |
| Códigos de Retorno.....................            | .32  |
| 6.2.3. Incluir Unidade ..............................                                   | .32  |
| Detalhes da Requisição.....................        | 33   |
| Dados de retorno..............................     | 33   |
| Dados de retorno.......                            | 33   |

| M                                                                                                                           | e Integração PNCP– Versão 2.2.1   |
|-----------------------------------------------------------------------------------------------------------------------------|-----------------------------------|
| Exemplo de Retorno..................              | .33                               |
| Códigos de Retorno.........                                                            | ..34                              |
| 6.2.4. Consultar Unidade ..................................                            | 34                                |
| Detalhes da Requisição................            | .34                               |
| Dddt                                                                                                                        | 3                                 |
| Dados de retorno................................  | .35                               |
| Códigos de Retorno.....................           | .37                               |
| .2.5. Consultar Unidades de um Órgão .............................                     | 37                                |
| Detalhes da Requisição........................................                         | .37                               |
| Dados de entrada ............................     | .37                               |
| Dados de retorno..............................    | .39                               |
| Exemplo de Retorno..................              | .41                               |
| Códigos de Retorno................                | 42                                |
| 6.3. Serviços de Compra/Edital/Aviso .......................                           | 43                                |
| 6.3.1. Inserir Compra/Edital/Aviso ..............................                      | .43                               |
| Detalhes de Requisição................            | 44                                |
| Dados de entrada ...........................      | .46                               |
| Dados de retorno.............................     | .49                               |
| Exemplo de Retorno..................              | ..49                              |
| Códigos de Retorno................                | ..50                              |
| 6.3.2. Retificar Compra/Edital/Aviso .............................                     | .50                               |
| Detalhes de Requisição.........................                                                                             | .51                               |
| Dados de entrada ...................              | 51                                |
| Códigos de Retorno..........                      | .53                               |
| 6.3.3. Retificar Parcialmente uma Compra/Edital/Aviso.....                             | .53                               |
| Detalhes de Requisição.............               | .54                               |
| Dados de entrada .............................    | ..54                              |
| Códigos de Retorno.............................                                        | .56                               |
| 6.3.4. Excluir Compra/Edital/Aviso......          | .56                               |
| Detalhes de Requisição..........................  | .57                               |
| Dados de entrada ................................ | 57                                |
| Códigos de Retorno.....................................                                | 57                                |
| .3.5. Consultar uma Compra/Edital/Aviso....................................            | .58                               |
| Detalhes de Requisição......................      | 58                                |
| Dados de entrada ..............................   | 58                                |

|                                                                                                                                    | anual de Integração PNCP– Versão 2.2.1   |
|------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| Dados de retorno.......                                                                       | .59                                      |
| 6.3.6. Inserir Documento a uma Compra/Edital/Aviso .......                                    | ...62                                    |
| Detalhes da Requisição...............                    | .63                                      |
| Dados de entrada ............                                                                 | 63                                       |
| Dados de retorno.............................            | .63                                      |
| Exemplo de Retorno............................           | .64                                      |
| Códigos de Retorno..............................                                                                                   | 64                                       |
| 6.3.7. Excluir Documento de uma Compra/Edital/Aviso.....                                      | 64                                       |
| Detalhes da Requisição......                             | .64                                      |
| Dados de entrada ....................................... | .65                                      |
| Códigos de Retorno....................................   | .65                                      |
| 6.3.8. Consultar Todos Documentos de uma Compra/Edital/Aviso...........................                                            | .65                                      |
| Detalhes da Requisição...........................                                                                                  | 66                                       |
| Dados de entrada ...........                             | 66                                       |
| Dados de retorno................................         | 66                                       |
| Códigos de Retorno......................                 | 67                                       |
| .3.9. Baixar Documento de uma Compra/Edital/Aviso .............                               | 67                                       |
| Detalhes da Requisição.................                  | 67                                       |
| Dados de entrada .................................       | 67                                       |
| Dados de retorno................                                                              | 68                                       |
| Códigos de Retorno........                                                                                                         | 68                                       |
| 6.3.10. Inserir Itens a uma Compra/Edital/Aviso ................                              | .68                                      |
| Detalhes de Requisição....................................                                    | 69                                       |
| Dados de entrada ...........................             | .69                                      |
| Dados de retorno..........................               | ..71                                     |
| Exemplo de Retorno.......................                | .71                                      |
| Códigos de Retorno....................                                                        | .71                                      |
| 6.3.11. Retificar Item de uma Compra/Edital/Aviso..................                           | ..71                                     |
| Detalhes de Requisição.......................            | .72                                      |
| Dados de entrada ................................        | ..72                                     |
| Códigos de Retorno......................                 | 74                                       |
| 6.3.12. Retificar parcialmente um Item de uma Compra/Edital/Aviso ...................                                              | 74                                       |
| Detalhes de Requisição.........................          | 74                                       |
| Dados de entrada .....................                                                        | 75                                       |
| Códigos de Retorno............................                                                                                     | 77                                       |

| Manual de Integração PNCP
 Versã
 313CltItdC/Editl/Ai                                                                                                                                        | egração PNCP– Versão 2.2.1
 77      |
|----------------------------------------------------------------------------------------------------------------------------------------|------|
| Detalhes de Requisição........................................                                    | 77   |
| Dados de entrada ..................                                                                                                    | 77   |
| Dados de retorno.............................                | 79   |
| Códigos de Retorno....................                                                                                                 | .80  |
| 6.3.14. Consultar Item de uma Compra/Edital/Aviso ...............                                                                      | ..80 |
| Detalhes de Requisição                                                                                                                 | .80  |
| Detalhes de Requisição.........................................                                   | 80   |
| Dados de entrada ...................................         | 80   |
| Dados de retorno...............................              | 82   |
| Códigos de Retorno......................................     | 83   |
| .3.15. Inserir Resultado do Item de uma Compra/Edital/Aviso ......................................                                     | .83  |
| Dados de entrada ..............................              | 83   |
| Dados de entrada ...................................         | 85   |
| Exemplo de Retorno.......................................    | 85   |
| Códigos de Retorno.......................................    | 85   |
| 3.16. Retificar Resultado do Item de uma Compra/Edital/Aviso .......                              | 86   |
| .3.16. Retificar Resultado do Item de uma Compra/Edital/Aviso ........                            | 86   |
| qç
 Dados de entrada                                                                                                                                        | 86   |
| Dados de entrada .................................           | 86   |
| Códigos de Retorno.......................................... | 88   |
| .3.17. Consultar Resultados de Item de uma Compra/Edital/Aviso ................................                                        | 88   |
| Dados de entrada                                                                                                                       | 89   |
| Dados de entrada ....................................        | 89   |
| Dados de retorno...........                                  | 90   |
| Códigos de Retorno.......................................... | .92  |
| Detalhes de Requisição                                                                                                                 | .93  |
| Dados de entrada ................................            | .93  |
| Dados de entrada ..........................................  | .93  |
| Códigos de Retorno.......................................... | .94  |
| Códigos de Retorno.........................................  | .96  |
| 3.19. Consultar Histórico da Compra........                  | .96  |
| Detalhes da Requisição..........................                                                  | .96  |
| Dados de entrada ......................................      | .97  |
| ados de etoo
 CódidRt                                                                                                                                        | 100  |
| Códigos de Retorno.............................              | 100  |

|                                                                                                                           | ração PNCP– Versão 2.2.1   |
|---------------------------------------------------------------------------------------------------------------------------|----------------------------|
| 6.4. Serviços de Ata ........................   | ...101                     |
| 6.4.1. Inserir Ata de Registro de Preço...................................           | ....101                    |
| Detalhes da Requisição......................                                         | .101                       |
| Dados de entrada .............................. | .101                       |
| Dados de retorno............................... | ..102                      |
| Exemplo de Retorno............................  | ....102                    |
| Códigos de Retorno............................. | .103                       |
| 6.4.2. Retificar Ata de Registro de Preço ...................                        | 103                        |
| Detalhes da Requisição...........               | .104                       |
| Dados de entrada ........................       | .104                       |
| Dados de retorno.............................   | .105                       |
| Exemplo de Retorno....................          | ..106                      |
| Códigos de Retorno...................           | .107                       |
| 6.4.3. Excluir Ata de Registro de Preço.........................                     | .107                       |
| Detalhes da Requisição..............            | .107                       |
| Dados de entrada .........................                                           | .107                       |
| Códigos de Retorno......................        | .108                       |
| 6.4.4. Consultar Todas as Atas de uma Compra ..........                              | .108                       |
| Detalhes da Requisição........................                                       | .109                       |
| Dados de entrada .......................                                             | .109                       |
| Dados de retorno....................                                                                                      | .110                       |
| 6.4.5. Consultar Ata de Registro de Preço ..............                             | ...110                     |
| Detalhes da Requisição............                                                   | .111                       |
| Dados de entrada ......................         | ..111                      |
| Dados de retorno....................            | ..112                      |
| 6.4.6. Inserir Documento de uma Ata ......................                           | ..112                      |
| Detalhes da Requisição.......                                                        | ...113                     |
| Dados de entrada .....................          | ...113                     |
| Dados de retorno............................... | ..114                      |
| Exemplo de Retorno............................. | ...114                     |
| Códigos de Retorno...........................   | ..114                      |
| 6.4.7. Excluir Documento de uma Ata ..................................               | .114                       |
| Detalhes da Requisição......................... | .115                       |
| Dados de entrada ..............                 | 115                        |
| Códigos de Retorno.................                                                  | 116                        |

|                                                                                                                          | ual de Integração PNCP– Versão 2.2.1   |
|--------------------------------------------------------------------------------------------------------------------------|----------------------------------------|
| 6.4.8. Consultar Todos os Documentos de uma Ata..............................                                            | ..116                                  |
| Detalhes da Requisição..................       | ......116                              |
| Dados de entrada ........................      | ..116                                  |
| Dados de retorno....................           | .117                                   |
| Códigos de Retorno.....................        | .118                                   |
| 6.4.9. Consultar Documento de uma Ata...........................                    | ..118                                  |
| Detalhes da Requisição..................................                                                                 | 118                                    |
| Dados de entrada .................             | .118                                   |
| Dados de retorno................               | .119                                   |
| Códigos de Retorno........................     | .119                                   |
| .4.10. Consultar Histórico da Ata ..........................................        | .119                                   |
| Detalhes da Requisição............             | ..120                                  |
| Dados de entrada ..................            | .120                                   |
| Dados de retorno..............                 | .121                                   |
| Códigos de Retorno............                 | .122                                   |
| 6.5. Serviços de Contrato..........................................                 | .123                                   |
| 6.5.1. Inserir Contrato ...........                                                                                      | .123                                   |
| Detalhes de Requisição.........                | .124                                   |
| Dados de entrada ......................................                             | .124                                   |
| Dados de retorno..........................     | ..127                                  |
| Exemplo de Retorno.......                      | ..127                                  |
| Códigos de Retorno...........................                                       | .127                                   |
| 6.5.2. Retificar Contrato ...........................                                                                    | .127                                   |
| Detalhes de Requisição.........................................                     | .127                                   |
| Dados de entrada ......................................                             | ..128                                  |
| Dados de retorno...........                                                         | .131                                   |
| Exemplo de Retorno...............              | ..131                                  |
| Códigos de Retorno............................                                                                           | .131                                   |
| 6.5.3. Excluir Contrato....................                                         | .131                                   |
| Detalhes de Requisição.................        | .132                                   |
| Dados de entrada ........................      | ..132                                  |
| Códigos de Retorno..........                                                        | .132                                   |
| 6.5.4. Inserir Documento a um Contrato......................................        | .132                                   |
| Detalhes da Requisição..................       | 133                                    |
| Dados de entrada ............................. | 133                                    |

|                                                                                                                               | ração PNCP– Versão 2.2.1   |
|-------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| Dados de retorno........................            | ..133                      |
| Exemplo de Retorno......                                                                 | ..134                      |
| Códigos de Retorno...................                                                    | 134                        |
| Detalhes da Requisição...............               | .134                       |
| Detalhes da Requisição................              | .134                       |
| Dados de entrada .......................            | ..135                      |
| Códigos de Retorno................                                                       | ..135                      |
| 6.5.6. Consultar Todos os Documentos de um Contrato ....................................                                      | .135                       |
| Detalhes da Requisição............................                                       | ..135                      |
| Dados de entrada .............................      | ....136                    |
| Dados de retorno.................................   | ....136                    |
| Códigos de Retorno............................                                           | ..136                      |
| 6.5.7. Consultar Documento de um Contrato ....                                           | ..136                      |
| Detalhes da Requisição.......                       | .137                       |
| Dados de entrada ..................                 | .137                       |
| Dados de retorno.....................               | ..137                      |
| Códigos de Retorno.................                 | ..137                      |
| 6.5.8. Consultar Contrato........................................                        | .138                       |
| 6.5.8. Consultar Contrato......                     | 138                        |
| Dados de entrada ........................................                                | ..138                      |
| Códigos de Retorno................................                                       | 143                        |
| Códigos de Retorno............................                                           | .143                       |
| 6.5.9. Consultar Histórico do Contrato...........................                        | .143                       |
| Detalhes da Requisição.........................................                          | ..143                      |
| Dados de entrada .....................................                                   | ..143                      |
| Dados de retorno.................                   | ..145                      |
| Códigos de Retorno.................                 | ..147                      |
| 6.6. Serviço de Termo de Contrato............................                            | ..148                      |
| 6.6.1. Inserir Termo de Contrato.........................................                | .148                       |
| Detalhes da Requisição.....................         | ..148                      |
| Dados de entrada ..........................         | ..149                      |
| Dados de retorno...............................     | .152                       |
| Exemplo de Retorno................................. | .152                       |
| Códigos de Retorno...........................       | 152                        |
| 6.6.2. Retificar Termo de Contrato............      | 152                        |

|                                                                                                                              | nual de Integração PNCP– Versão 2.2.1   |
|------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| Detalhes da Requisição........................................                          | .....153                                |
| Dados de entrada .............................     | ......153                               |
| Dados de retorno..............................     | ..156                                   |
| Exemplo de Retorno.........................        | .156                                    |
| Códigos de Retorno.........................        | ..156                                   |
| 6.6.3. Excluir Termo de Contrato.........................................               | ...156                                  |
| Detalhes da Requisição............                 | .157                                    |
| Dados de entrada ..........................        | .157                                    |
| Códigos de Retorno....................                                                  | ..157                                   |
| 6.6.4. Consultar um Termo de Contrato ..........................                        | ...157                                  |
| Detalhes da Requisição........................     | ...158                                  |
| Dados de entrada ...                                                                    | .158                                    |
| Códigos de Retorno..........                       | .158                                    |
| 6.6.5. Consultar Todos os Termos de um Contrato ........                                | .159                                    |
| Detalhes da Requisição.................................                                 | 159                                     |
| Dados de entrada ............                                                           | .160                                    |
| Códigos de Retorno.                                                                                                          | .160                                    |
| Formato do Retorno .................                                                                                         | 161                                     |
| 6.6.6. Inserir Documento a um Termo de Contrato..........                               | .161                                    |
| Detalhes da Requisição.......................                                           | .162                                    |
| Dados de entrada ......                                                                                                      | 162                                     |
| Dados de retorno..............                                                          | .162                                    |
| Exemplo de Retorno..........................................                            | .163                                    |
| Códigos de Retorno...........................                                                                                | .163                                    |
| 6.6.7. Excluir Documento de um Termo de Contrato.....                                   | ...163                                  |
| Detalhes da Requisição.........................                                         | ..163                                   |
| Dados de entrada .........                         | .164                                    |
| Códigos de Retorno............................                                                                               | ..164                                   |
| 6.6.8. Consultar Todos os Documentos de um Termo de Contrato .........................                                       | .164                                    |
| Detalhes da Requisição...................          | ..165                                   |
| Dados de entrada ............................      | ..165                                   |
| Dados de retorno.................................. | 165                                     |
| Códigos de Retorno....................             | 166                                     |
| 6.6.9. Consultar Documento de um Termo de Contrato .................                    | 166                                     |
| Detalhes da Requisição.........                    | 166                                     |

| Manual de Integr                                                                                                                    | nual de Integração PNCP– Versão 2.2.1   |
|-------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| Dados de entrada ............................                                                  | ...166                                  |
| Dados de retorno.............                             | ..167                                   |
| Códigos de Retorno.......................................                                                                           | 167                                     |
| 6.7. Serviços de Plano de Contratações ............                                                                                 | 167                                     |
| 6.7.1. Inserir Plano de Contratações ..................                                        | 167                                     |
| Detalhes de Requisição.....................               | 167                                     |
| Dados de entrada ..........................               | 168                                     |
| Dados de retorno.................................         | 170                                     |
| Códigos de Retorno.......................                 | 170                                     |
| 6.7.2. Excluir Plano de Contratações ............................                                                                   | .170                                    |
| Detalhes de Requisição..................................                                       | .171                                    |
| Dados de entrada ........................................                                      | .171                                    |
| Códigos de Retorno....................                    | .171                                    |
| 6.7.3. Consultar Plano por Órgão e Ano....................................                     | .172                                    |
| Detalhes de Requisição..............................                                           | ..172                                   |
| Dados de entrada .............................            | .172                                    |
| Dados de retorno...........................               | .172                                    |
| Códigos de Retorno.................................       | .173                                    |
| 6.7.4. Consultar Plano das Unidades por Órgão e Ano ......                                     | .173                                    |
| Detalhes de Requisição.....                                                                                                         | .173                                    |
| Dados de entrada .....................                    | .173                                    |
| Dados de retorno........................                  | .174                                    |
| Códigos de Retorno.......................                                                      | .175                                    |
| 6.7.5. Consultar Valores de Planos de Contratação de um Órgão por Categoria........                                                 | .175                                    |
| Detalhes de Requisição.......................................                                                                       | ..175                                   |
| Dados de entrada .......................                  | ..175                                   |
| Dados de retorno........................                  | .176                                    |
| Códigos de Retorno.............................                                                | .176                                    |
| 7.6. Consultar Plano de Contratação Consolidado (Plano de Contratações de uma Unidad
 no) ..............................                                                                                                                                     | de e 
 176                                         |
| Detalhes de Requisição..............................                                           | .176                                    |
| Detalhes de Requisição.........................................                                | .176                                    |
| Dados de entrada ................................                                              | .177                                    |
| Dados de retorno.....................................     | .178                                    |
| 6.7.7. Consultar Valores de um Plano de Contratação por Categoria....................................                               | 178                                     |
| Detalhes de Requisição..................................1 | 178                                     |
| Detalhes de Requisição...............................     | 178                                     |

|                                                                                                                                | nual de Integração PNCP– Versão 2.2.1   |
|--------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| Dados de entrada ...................................                                      | ......178                               |
| Dados de retorno..................                   | ........179                             |
| Códigos de Retorno........                                                                | .179                                    |
| 6.7.8. Inserir Itens de Plano de Contratação ...........                                  | .179                                    |
| Detalhes de Requisição............                   | .180                                    |
| Dados de entrada .............................       | ..181                                   |
| Dados de retorno....................                 | .182                                    |
| Exemplo de Retorno..............................                                          | .182                                    |
| Códigos de Retorno..........                                                                                                   | ..182                                   |
| .7.9. Consultar Itens do Plano de Contratações de uma Unidade e Ano ...................                                        | ..183                                   |
| Detalhes de Requisição............                   | ...183                                  |
| Dados de entrada .....................................                                    | ..183                                   |
| Dados de retorno...................                  | .183                                    |
| Códigos de Retorno............                       | .185                                    |
| 6.7.10. Retificar Parcialmente Item de Plano de Contratação ..........................                                         | 186                                     |
| Detalhes de Requisição......................                                              | .186                                    |
| Dados de entrada ..................                  | .186                                    |
| Códigos de Retorno..............                     | .188                                    |
| 6.7.11. Retificar Parcialmente Itens de um Plano de Contratação ......................                                         | .188                                    |
| Detalhes de Requisição........                       | .188                                    |
| Dados de entrada ..                                                                                                            | .189                                    |
| Códigos de Retorno.......................                                                 | .191                                    |
| 6.7.12. Excluir Item de Plano de Contratação...........                                   | .191                                    |
| Detalhes de Requisição.................                                                                                        | .192                                    |
| Dados de entrada ............................        | ...192                                  |
| Códigos de Retorno.........................                                               | ..192                                   |
| 6.7.13. Excluir Itens de um Plano de Contratação .............                            | ..193                                   |
| Detalhes de Requisição....................................                                | ..193                                   |
| Dados de entrada ................................... | .193                                    |
| Códigos de Retorno.............                      | ..193                                   |
| Códigos de Retorno............................       | ..194                                   |
| qpg
 DtlhdRiiã                                                                                                                                | .194                                    |
| Dados de entrada .............................       | .194                                    |
| Dados de retorno........                             | 194                                     |
| Códigos de Retorno.......................................                                 | 194                                     |

| 7Sup   |   196 |
|--------|-------|
| 7. S   |    96 |

## 1. Objetivo

Este documento contempla as orientações para realizar a integração de sistemas externos com as API REST do PNCP (Portal Nacional de Contratações Públicas).

## 2. Protocolo de Comunicação

O protocolo de comunicação utilizado é o REST - Representational State Tdransfer/ HTTP 1.1 e os dados trafegados utilizam a notação JSON - JavaScript Object Notation. Arquivos JSON enviados para o Portal devem ser codificados em UTF-8.

## 3. Acesso ao PNCP

## 3.1. Endereços de Acesso

A invocação dos serviços será realizada através das URLs citadas abaixo, conforme requisitos de segurança detalhados na seção seguinte.

## ● Ambiente de Homologação Externa

- ○ Portal: https://treina.pncp.gov.br
- ○ Documentação Técnica (Serviços): https://treina.pncp.gov.br/api/pncp/swaggerui/index.html?configUrl=/pncp-api/v3/api-docs/swagger-config
- ○ Serviços (${BASE\_URL}): https://treina.pncp.gov.br/api/pncp

## ● Ambiente de Produção

- ○ Portal: https://pncp.gov.br
- ○ Documentação Técnica (Serviços): https://pncp.gov.br/api/pncp/swaggerui/index.html?configUrl=/pncp-api/v3/api-docs/swagger-config
- ○ Serviços (${BASE\_URL}): https://pncp.gov.br/api/pncp

Nota: ${BASE\_URL} será utilizada nos exemplos de requisições citados neste documento. É a URL base para acesso aos serviços disponíveis no PNCP.

## 3.2. Autenticação/Autorização

O acesso ao Portal de consultas é público. Já as APIs de manutenção (serviços de inserção, retificação ou exclusão de dados) requerem autenticação/autorização.

As plataformas digitais que fornecerão os dados para publicação, representando os órgãos públicos e entidades, deverão realizar credenciamento junto ao Ministério da Economia, quando receberão login e senha para acesso. A plataforma digital é responsável pela guarda e confidencialidade das suas credenciais.

Qualquer usuário pode alterar sua própria senha, seguindo as seguintes regras:

- ● A senha deve conter no mínimo 16 caracteres válidos e no máximo 64 caracteres.
- ● A senha não pode conter o login do usuário.
- ● A senha não pode conter um nome de usuário.
- ● A senha não pode conter nomes do e-mail do usuário.
- ● A senha não pode conter sequências de 3 ou mais do mesmo caractere.
- ● A senha não pode conter sequências de 4 ou mais caracteres crescentes.
- ● A senha não pode conter sequências de 4 ou mais caracteres decrescentes.
- ● Caracteres "brancos" no início e fim da senha serão desprezados (a senha pode conter caracteres "brancos" entre outros caracteres).

A plataforma usuária deverá se autenticar com login e senha para obter um JSON Web Token (JWT). Utilizando esse token, a plataforma poderá acessar os serviços disponíveis, até a expiração do mesmo (prazo de 1 hora a partir da sua geração). Um único token é necessário para a plataforma durante sua validade e, uma vez expirado, uma nova autenticação será necessária para obter um novo token.

A API de login (POST https://pncp.gov.br/api/pncp/v1/usuarios/login) retorna o JWT no cabeçalho (header) da resposta HTTP, especificamente no campo "Authorization", após o texto "Bearer". As requisições a APIs de manutenção de dados no PNCP requerem esse campo de cabeçalho idêntico para autenticação e autorização.

Quando da primeira publicação do sistema, a associação entre usuários e seus órgãos/entidades autorizados estará sendo feita pelo próprio usuário. Ou seja, a plataforma deverá informar ao sistema quais CNPJs ela representa e assim estará autorizada a enviar dados em nome destes. O sistema confiará na plataforma e ela será juridicamente responsável por quaisquer equívocos, intencionais ou acidentais.

## 4. Recomendações Iniciais

## 4.1. Cadastro Inicial dos Órgãos/Entidades e suas Unidades

A plataforma digital deverá ter cadastrado os órgãos/entidades e suas respectivas unidades compradoras antes de enviar os dados das contratações realizadas por estas.

Uma vez habilitada, a plataforma usuária deve realizar os seguintes passos:

- 1. Realizar Login
- 2. Verificar se o(s) órgão(s) desejados já estão cadastrados no PNCP*

- 3. Fornecer a lista de órgãos do PNCP pelos quais a sua plataforma está autorizada a enviar informações (serão associados ao seu usuário).
- 4. Cadastrar as unidades compradoras desses órgãos
- 5. Iniciar o envio das informações através dos serviços disponíveis

*Nota: O portal PNCP já possui, previamente cadastrados, os principais CNPJs da administração pública divulgados pela RFB. Caso não encontre o órgão desejado, favor inserir antes de seguir para o próximo passo.

## 4.2. Manutenção dos Dados das Contratações Enviadas

É de responsabilidade da plataforma usuária, a divulgação e devida manutenção dos dados enviados para o Portal, representando a realidade das contratações públicas em questão. Desta forma, foram definidos vários domínios que devem ser seguidos ao utilizar as APIs. Vale destacar os domínios que representam as diversas situações/estados destas contratações e que devem ser revisados sempre que houver mudanças nos dados previamente divulgados no PNCP. Com este objetivo, além das APIs de inclusão, estão disponíveis os serviços de retificação e exclusão dos metadados enviados.

## 5. Tabelas de Domínio

## 5.1. Instrumento Convocatório

- ● (código = 1) Edital: Instrumento convocatório utilizado no diálogo competitivo, concurso, concorrência, pregão, manifestação de interesse, pré-qualificação e credenciamento.
- ● (código = 2) Aviso de Contratação Direta: Instrumento convocatório utilizado na Dispensa com Disputa.
- ● (código = 3) Ato que autoriza a Contratação Direta: Instrumento convocatório utilizado na Dispensa sem Disputa ou na Inexigibilidade.

## 5.2. Modalidade de Compra

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

## 5.3. Modo de Disputa

- ● (código = 1) Aberto
- ● (código = 2) Fechado
- ● (código = 3) Aberto-Fechado
- ● (código = 4) Dispensa Com Disputa
- ● (código = 5) Não se aplica

## 5.4. Critério de Julgamento

- ● (código = 1) Menor preço
- ● (código = 2) Maior desconto
- ● (código = 3) Melhor técnica ou conteúdo artístico
- ● (código = 4) Técnica e preço
- ● (código = 5) Maior lance
- ● (código = 6) Maior retorno econômico
- ● (código = 7) Não se aplica

## 5.5. Situação da Compra/Edital/Aviso

- ● (código = 1) Divulgada no PNCP: Compra divulgada no PNCP. Situação atribuída na inclusão da compra.
- ● (código = 2) Revogada: Compra revogada conforme justificativa.
- ● (código = 3) Anulada: Compra revogada conforme justificativa.
- ● (código = 4) Suspensa: Compra suspensa conforme justificativa.

## 5.6. Situação do Item da Compra/Edital/Aviso

- ● (código = 1) Em Andamento: Item com disputa/seleção do fornecedor não finalizada. Situação atribuída na inclusão do item da compra
- ● (código = 2) Homologado: Item com resultado (fornecedor informado)
- ● (código = 3) Anulado/Revogado/Cancelado: Item cancelado conforme justificativa
- ● (código = 4) Deserto: Item sem resultado (sem fornecedores interessados)
- ● (código = 5) Fracassado: Item sem resultado (fornecedores desclassificados ou inabilitados)

## 5.7. Tipo de Benefício

- ● (código = 1) Participação exclusiva para ME/EPP
- ● (código = 2) Subcontratação para ME/EPP
- ● (código = 3) Cota reservada para ME/EPP
- ● (código = 4) Sem benefício
- ● (código = 5) Não se aplica

## 5.8. Situação do Resultado do Item da Compra/Edital/Aviso

- ● (código = 1) Informado: Que possui valor e fornecedor e marca oriundo do resultado da compra. Situação atribuída na inclusão do resultado do item da compra.
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

## 5.12. Tipo de Documento

## Tipos de documentos da compra:

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
- ○ (código = 10) DOD

## Tipos de documentos da ata:

- ● (código = 11) Ata de Registro de Preço

## Tipos de documentos de contrato:

- ● (código = 12) Contrato
- ● (código = 13) Termo de Rescisão
- ● (código = 14) Termo Aditivo
- ● (código = 15) Termo de Apostilamento
- ● (código = 17) Nota de Empenho

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

## Manual de Integração PNCP– Versão 2.2.1

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
- ● (código = 50) Lei 14.133/2021, Art. 74, Caput

Observação: o Amparo Legal selecionado deve estar em conformidade com a Modalidade de Compra selecionada, seguindo a relação abaixo:

| Código da Modalidade de Compra    | Código do Amparo Lega                                  |
|-----------------------------------|--------------------------------------------------------|
| 2                                 | 5                                                      |
| 3                                 |                                                        |
| 4                                 | 2                                                      |
| 5                                 | 2                                                      |
| 6                                 | 1                                                      |
| 7                                 | 1                                                      |
|                                   | 18; 19; 20; 21; 22; 23; 24; 25; 26; 27; 28; 29; 30; 31 |
|                                   |  
 32; 33; 34; 35; 36; 37; 38; 39; 40; 41; 42; 43; 44; 4                                                        |
| 9                                 | 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16; 17; 50         |
| 10                                | 49                                                     |
| 11                                | 48                                                     |
| 12                                | 47                                                     |

## 5.15. Envio de arquivos pelas APIs de Documento

Ao anexar um documento digital, complementando os metadados enviados, as seguintes extensões de arquivo serão aceitas para upload:

- ● pdf, txt, rtf, doc, docx, odt, sxw, zip, 7z , rar, dwg, dwt, dxf, dwf, dwfx, svg, sldprt, sldasm, dgn, ifc, skp, 3ds, dae, obj, rfa e rte .

Nota: O tamanho máximo aceito, por arquivo enviado, é de 30 MB (Megabytes).

## 5.16. Categoria do Item do Plano de Contratações

- ● (código = 1) Material
- ● (código = 2) Serviço
- ● (código = 3) Obras
- ● (código = 4) Serviços de Engenharia
- ● (código = 5) Soluções de TIC
- ● (código = 6) Locação de Imóveis

- ● (código = 7) Alienação/Concessão/Permissão
- ● (código = 8) Obras e Serviços de Engenharia

## 6. Catálogo de Serviços (APIs)

## 6.1. Serviços de Usuário

## 6.1.1. Atualizar Usuário

Serviço que permite alterar/atualizar os dados de um usuário. Disponível para o próprio usuário logado ou um usuário administrador.

Com esse serviço é possível que o usuário altere sua própria senha. Aqui também ele cadastra a lista de CNPJs de órgãos que está autorizado a divulgar informações.

## Detalhes de Requisição

| Endpoint                                                                                    | Método HTTP                                                                                 | Exemplo de Payload                                                                          |
|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| /v1/usuarios/{id}                                                                           | PUT                                                                                         | {
  "nome": "Fulano de Tal",
  "email": "fulano@example.com",
  "senha": "&1NaoCompartilho1Senha&",
  "entesAutorizados": ["10000000000003", "10000000
 }                                                                                             |
| Exemplo Requisição (cURL)                                                                   | Exemplo Requisição (cURL)                                                                   | Exemplo Requisição (cURL)                                                                   |
| curl -k -X PUT --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/5" -H | curl -k -X PUT --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/5" -H | curl -k -X PUT --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/5" -H |

## Dados de entrada

Nota: alimentar o parâmetro {id} na URL.

|   Id  | Campo            | Tipo        | Obrigatório    | Descrição                       |
|-------|------------------|-------------|----------------|---------------------------------|
|    1  | nome             | Texto (255) | Não            | Nome ou razão social do usuário |
|    2  | email            | Texto (255) | Não            | E-mail do usuário               |
|    3  | senha            | Texto (255) | Não            | Senha do usuário                |
|    4  | entesAutorizados | Vetor       | Sim            | Vetor/array com a lista de cnpj de 
 órgãos que o usuário possui acesso                                 |

## Dados de retorno

Não se aplica.

## Exemplo de Retorno

Retorno:

```
access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin, access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS access-control -allow -origin: * cache -control: no -cache,no-store,max-age=0,must-revalidate content -length: 0 date: ? expires: 0 pragma: no -cache strict -transport-security: max-age=? x-content -type-options: nosniff x-firefox -spdy: ? x-frame -options: DENY x-xss-protection: 1; mode=block
```

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.1.2. Consultar Usuário por Id

Serviço que permite consultar os dados de um usuário pelo id. Disponível para o próprio usuário logado ou um usuário administrador.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/usuarios/{id}         | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/5" -H 
 "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/5" -H 
 "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/5" -H 
 "accept: */*"                           |

## Dados de entrada

Nota: alimentar o parâmetro {id} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo    | T       | Tipo    | Obrigatório    | Descrição                |
|-------|----------|---------|---------|----------------|--------------------------|
|    1  | id       | Inteiro | Sim     | m              | Identificador do usuário |

## Dados de retorno

|   Id  | Campo            | Tipo        | Obrigatório    | Descrição                       |
|-------|------------------|-------------|----------------|---------------------------------|
|   1   | id               | Inteiro     | Sim            | Identificador do usuário        |
|   2   | login            | Texto (255) | Sim            | Login                           |
|   3   | nome             | Texto (255) | Sim            | Nome ou razão social do usuário |
|   4   | cpfCnpj          | Texto (14)  | Sim            | CNPJ ou CPF do usuário          |
|   5   | email            | Texto (255) | Sim            | E-mail do usuário               |
|   6   | administrador    | Booleano    | Sim            | Identifica se o usuário é um 
 administrador                                 |
|   7   | entesAutorizados | Lista       | Sim            | Lista de órgãos que o usuário 
 possui acesso                                 |
|   7.1 | id               | Inteiro     | Sim            | Identificador do órgão          |
|   7.2 | cnpj             | Texto (14)  | Sim            | CNPJ do órgão                   |
|   7.3 | razaoSocial      | Texto (255) | Sim            | Razão social do órgão           |

## Exemplo de Retorno

Retorno:

```
{ "id": 5, "login": "1b182cec-f639-11eb-9a03-0242ac130003", "nome": "Fulano de Tal", "cpfCnpj": "10000000001", "email": "fulano@example.com", "administrador": false, "entesAutorizados": [ { "id": 7, "cnpj": "10000000000003", "razaoSocial": "Organização Alfa" }, { "id": 9, "cnpj": "10000000000005", "razaoSocial": "Instituição Gama" } ] }
```

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.1.3. Consultar Usuário por Login ou por CPF/CNPJ

Serviço que permite consultar os dados de um usuário pelo Login ou por um CPF/CNPJ. Disponível para o próprio usuário logado ou um usuário administrador.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/usuarios              | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| url -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios" -H "accept: 
 */*"                           | url -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios" -H "accept: 
 */*"                           | url -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios" -H "accept: 
 */*"                           |

## Dados de entrada

Utilizar um dos dois parâmetros para pesquisa.

|   Id  | Campo    | Tipo       | Obrigatório    | Descrição                |
|-------|----------|------------|----------------|--------------------------|
|    1  | login    | Texto (255 |                | Identificador do usuário |
|    2  | cpfCnpj  | Texto (14) |                | CNPJ ou CPF do usuário   |

## Dados de retorno

| Id    | Campo             | Tipo              | Descrição                                   |
|-------|-------------------|-------------------|---------------------------------------------|
| 1     | Lista de usuários | Lista de usuários | Lista de usuários                           |
| 1.1   | id                | Inteiro           | Identificador do usuário                    |
| 1.2   | login             | Texto (255)       | Log                                         |
| 1.3   | nome              | Texto (255)       | Nome ou razão social do usuário             |
| 1.4   | cpfCnpj           | Texto (14)        | CNPJ ou CPF do usuário                      |
| 1.5   | email             | Texto (255)       | E-mail do usuário                           |
| 1.6   | administrador     | Booleano          | Identifica se o usuário é um administrador  |
| 1.7   | entesAutorizados  | Lista             | Lista de órgãos que o usuário possui acesso |
| 1.7.1 | id                | Inteiro           | Identificador do órgão                      |
| 1.7.2 | cnpj              | Texto (14)        | CNPJ do órgão                               |
| 1.7.3 | razaoSocial       | Texto (255)       | Razão social do órgão                       |

## Exemplo de Retorno

<!-- image -->

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.1.4. Realizar Login de Usuário

Serviço que recebe os dados para autenticação de um usuário e retorna um token de acesso. O token de acesso vai possibilitar ao usuário enviar informações que alimentam o PNCP.

## Detalhes de Requisição

| Endpoint                                                                                        | Método HTTP                                                                                     | Exemplo de Payload                                                                              |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| /v1/usuarios/login                                                                              | POST                                                                                            | {
  "login": "1b182cec-f639-11eb-9a03-0242ac130003",
  "senha": "&1NaoCompartilho1Senha&"
 }                                                                                                 |
| Exemplo Requisição (cURL)                                                                       | Exemplo Requisição (cURL)                                                                       | Exemplo Requisição (cURL)                                                                       |
| url -k -X POST --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/login" -H | url -k -X POST --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/login" -H | url -k -X POST --header "Authorization: Bearer access_token" "${BASE_URL}/v1/usuarios/login" -H |

## Dados de entrada

|   Id  | Campo    | Tipo        | Obrigatório    | Descrição        |
|-------|----------|-------------|----------------|------------------|
|    1  | login    | Texto (255) | Sim            | Login do usuário |
|    2  | senha    | Texto (255) | Sim            | Senha do usuário |

## Dados de retorno

|   Id  | Campo         | Tipo         | Descrição                                |
|-------|---------------|--------------|------------------------------------------|
|    1  | authorization | Texto (1024) | “Bearer” que identifica o tipo de token; |

## Exemplo de Retorno

access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin, access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

cache -control: no -cache,no-store,max-age=0,must-revalidate

Retorno: access-control -allow -credentials: true access-control -allow -origin: * authorization: Bearer access\_token content -length: 0 date: ? expires: 0 pragma: no -cache strict -transport-security: max-age=? x-content -type-options: ? x-firefox -spdy: ? x-frame -options: ?

x-xss-protection: ?; mode=?

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.2. Serviços de Órgão/Entidade

## 6.2.1. Incluir Órgão

Serviço que permite inserir um órgão/entidade.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos                | POST                      | {
  "cnpj": "10000000000003",
  "razaoSocial": "Orgao Exemplo",
  "poderId": "E",
  "esferaId": "F"
 }                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
|                           |                           |                           |

## Dados de entrada

Nota: a URL possui o parâmetro {cnpj}.

|   Id  | Campo       | Tipo        | Obrigatório    | Descrição             |
|-------|-------------|-------------|----------------|-----------------------|
|    1  | cnpj        | Texto (14)  | Sim            | Cnpj do órgão         |
|    2  | razaoSocial | Texto (100) | Sim            | Razão Social do órgão |
|    3  | poderId     | Texto (1)   | Sim            | Poder que o órgão está inserido; L 
 - Legislativo; E - Executivo; J -
 Judiciário; N - Não se aplica;                       |
|    4  | esferaId    | Texto (1)   | Sim            | J; p;
 Esfera do órgão; F - Federal; E -
 Estadual; M - Municipal; D -
 Distrital; N Não se aplica;                       |

## Dados de retorno

|   Id  | Campo    | Tipo        | Obrigatór   | Descrição                       |
|-------|----------|-------------|-------------|---------------------------------|
|    1  | location | Texto (255) | Sim         | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

access-control -allow -origin: *

cache -control: no -cache,no-store,max-age=0,must-revalidate content -length: 0

date: ?

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/1

```
expires: 0 pragma: no -cache strict -transport-security: max-age=? x-content -type-options: nosniff x-firefox -spdy: ? x-frame -options: DENY
```

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.2.2. Consultar Órgão por Cnpj

Serviço que permite consultar um órgão pelo seu Cnpj.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}         | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003" -H "accept: */*"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj} na URL.

|   Id  | Campo    | Tipo       |     | Obrigatório    | Descrição   |
|-------|----------|------------|-----|----------------|-------------|
|    1  | cnpj     | Texto (14) | Sim | Cnpj do órgã   | ão          |

## Dados de retorno

|   Id  | Campo       | Tipo        | Descrição             |
|-------|-------------|-------------|-----------------------|
|    1  | cnpj        | Texto (14)  | Cnpj do órgão         |
|    2  | razaoSocial | Texto (100) | Razão social do órgão |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.2.3. Incluir Unidade

Serviço que permite inserir uma unidade em um órgão/entidade. As unidades são divisões administrativas que realizam as compras e celebram os contratos. Todo órgão/entidade deverá ter cadastrado ao menos uma unidade no PNCP.

## Detalhes da Requisição

| Endpoint                                                      | Método HTTP                                                   | Exemplo de Payload                                            |
|---------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------------|
| /v1/orgaos/{cnpj}/unidades                                    | POST                                                          | {
  "codigoIBGE": "1000001",
  "codigoUnidade": "1",
  "nomeUnidade": "Unidade administrativa"
 }                                                               |
| Exemplo Requisição (cURL)                                     | Exemplo Requisição (cURL)                                     | Exemplo Requisição (cURL)                                     |
| curl -k -X POST --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/unidades" -H "accept: */*" -H "Content-Type:                                                               | curl -k -X POST --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/unidades" -H "accept: */*" -H "Content-Type:                                                               | curl -k -X POST --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/unidades" -H "accept: */*" -H "Content-Type:                                                               |
| curl -k -X POST --header "Authorization: Bearer access_token" | curl -k -X POST --header "Authorization: Bearer access_token" | curl -k -X POST --header "Authorization: Bearer access_token" |
| ${_}gpyp
 application/json" --data "@/home/objeto.json"                                                               | ${_}gpyp
 application/json" --data "@/home/objeto.json"                                                               | ${_}gpyp
 application/json" --data "@/home/objeto.json"                                                               |

## Dados de entrada

Nota: a URL possui o parâmetro {cnpj}.

|   Id  | Campo         | Tipo        | Obrigatório    | Descrição                 |
|-------|---------------|-------------|----------------|---------------------------|
|    1  | cnpj          | Texto (14)  | Sim            | Cnpj do órgão contratante |
|    2  | codigoIBGE    | Texto (7)   | Sim            | Código do município definido pelo 
 IBGE                           |
|    3  | codigoUnidade | Texto (30)  | Sim            | Código da unidade do 
 órgão/entidade (definido pelo 
 próprio órgão)                           |
|    4  | nomeUnidade   | Texto (100) | Sim            | Nome da unidade do 
 órgão/entidade                           |

## Dados de retorno

|   Id  | Campo    | Tipo        | Obrigató   | Descrição                       |
|-------|----------|-------------|------------|---------------------------------|
|    1  | location | Texto (255) | Sim        | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

access-control -allow -origin: *

cache -control: no -cache,no-store,max-age=0,must-revalidate content -length: 0

date: ?

expires: 0

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/unidades/1

pragma: no -cache strict -transport-security: max-age=?

x-content -type-options: nosniff x-firefox -spdy: ?

x-frame -options: DENY

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.2.4. Consultar Unidade

Serviço que permite consultar uma unidade pertencente a um órgão/entidade a partir de seu código.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/unidades/{codig
 oUnidade}                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/unidades/1" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/unidades/1" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/unidades/1" -H "accept: */*"                           |

## Dados de entrada

Nota: a URL possui o parâmetro {cnpj}.

|   Id  | Campo         | Tipo       | Obrigatório    | Descrição                 |
|-------|---------------|------------|----------------|---------------------------|
|    1  | cnpj          | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | codigoUnidade | Texto (30) | Sim            | g
 órgão/entidade (definido pelo 
 próprio órgão)                           |

## Dados de retorno

|   Id  | Campo               | Tipo        | Obrigatório    | Descrição                       |
|-------|---------------------|-------------|----------------|---------------------------------|
|  1    | id                  | Inteiro     | Sim            | Identificador do recurso criado |
|  2    | orgao               |             | Sim            | Agrupador dos dados do Órgão    |
|  2.1  | id                  | Inteiro     | Sim            | Identificador do Órgão          |
|  2.2  | cnpj                | Texto (14)  | Sim            | CNPJ do Órgão                   |
|  2.3  | razaoSocial         | Texto (100) | Sim            | Razão Social                    |
|  2.4  | cnpjEnteResponsavel | Texto (14)  |                | CNPJ do Ente Responsável
 Código do poder a que pertence                                 |
|  2.5  | poderId             | Texto       |                | L - Legislativo; E - Executivo; J -
 Judiciário
 Código da esfera a qe pertence                                 |
|  2.6  | esferaId            | Texto       |                | Órgão.
 F - Federal; E - Estadual; M -
 Municipal; D Distrital                                 |
|  2.7  | hashChaveAcesso     | Texto       |                | Hash da Chave de Acesso         |
|  2.8  | validado            | Boolean     |                | Indicador de validação          |
|  2.9  | dataValidacao       | Data/Hora   |                | Data de validação               |
|  2.1  | dataInclusao        | Data/Hora   |                | Data de inclusão                |
|  2.11 | dataAtualizacao     | Data/Hora   |                | Data de atualização             |
|  3    | codigoUnidade       | Texto (30)  | Sim            | órgão/entidade (definido pelo 
 próprio órgão)
 Nome da unidade do                                 |
|  4    |                     | Texto (100) | Sim            | Nome da unidade do 
 órgão/entidade                                 |
|  4    | nomeUnidade         |             |                | Agregador de dados do Município |
|  5.1  | id                  | Integer     | Sim            | Identificador do Município      |
|  5.2  | uf                  |             | Sim            | Agregador de dados da Unidade 
 Federativa                                 |

## Manual de Integração PNCP– Versão 2.2.1

| 5.2.1    | siglaUF          | Texto (2)    | Sim    | Sigla da Unidade Federativa     |
|----------|------------------|--------------|--------|---------------------------------|
| 5.2.2    | nomeUF           | Texto        | Sim    | Nome da Unidade Federativa      |
| 5.2.3    | dataHoraRegistro | Data/Hora    | Sim    | Data de registro                |
| 5.3      | nome             | Texto        | Sim    | Nome do Município               |
| 5.4      | codigoIbge       | Texto        |        | Código IBGE do Município        |
| 5.5      | dataHoraRegistro | Data/Hora    |        | Data de registro                |
| 6        | dataInclusao     | Data/Hora    |        | Data de inclusão do registro    |
| 7        | dataAtualizacao  | Data/Hora    |        | Data de atualização do registro |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.2.5. Consultar Unidades de um Órgão

Serviço que permite consultar unidades pertencentes a um órgão/entidade.

## Detalhes da Requisição

| Endpoint                   | Método HTTP               | Exemplo de Payload        |
|----------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/unidades | GET                       | Não se aplica             |
| Exemplo Requisição (cURL)  | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/unidades" -H "accept: */*"                            | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/unidades" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/unidades" -H "accept: */*"                           |

## Dados de entrada

Nota: a URL possui o parâmetro {cnpj}.

## Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo    | Tipo       | Obrigatório    | Descrição                 |
|-------|----------|------------|----------------|---------------------------|
|    1  | cnpj     | Texto (14) | Sim            | Cnpj do órgão contratante |

## Dados de retorno

| Id     | Campo               | Tipo              | Obrigatório       | Descrição                       |
|--------|---------------------|-------------------|-------------------|---------------------------------|
| 1      | Lista de Unidades   | Lista de Unidades | Lista de Unidades | Agrupador da lista de unidades  |
| 1.1    | id                  | Inteiro           | Sim               | Identificador do recurso criado |
| 1.2    | orgao               |                   | Sim               | Agrupador dos dados do Órgão    |
| 1.2.1  | id                  | Inteiro           | Sim               | Identificador do Órgão          |
| 1.2.2  | cnpj                | Texto (14)        | Sim               | CNPJ do Órgão                   |
| 1.2.3  | razaoSocial         | Texto (100)       | Sim               | Razão Social                    |
| 1.2.4  | cnpjEnteResponsavel | Texto (14)        |                   | CNPJ do Ente Responsáve
 Códidd                                 |
| 1.2.5  | poderId             | Texto             |                   | Órgão.
 L - Legislativo; E - Executivo; J -
 Judiciário                                 |
| 1.2.6  | esferaId            | Texto             |                   | Órgão.
 F - Federal; E - Estadual; M -
 Municipal; D - Distrital                                 |
| 1.2.7  | hhh                 |                   |                   | Hash da Chave de Acesso         |
| 1.2.7  | hashChaveAcesso     | Texto             |                   | Hash da Chave de Acesso         |
| 1.2.8  | validado            | Boolean           |                   | Indicador de validação          |
| 1.2.9  | dataValidacao       | Data/Hora         |                   | Data de validação               |
| 1.2.11 |                     |                   |                   | Data de inclusão                |
| 1.2.11 | dataAtualizacao     | Data/Hora         |                   | Data de atualização             |
| 1.3    | codigoUnidade       | Texto (30)        | Sim               | Código da unidade do 
 órgão/entidade (definido pelo 
 próprio órgão)                                 |
| 1.4    | nomeUnidade         | Texto (100)       | Sim               | órgão/entidade                  |
| 1.5    | municipio           |                   |                   | Agregador de dados do Município |
| 1.5.1  | id                  | Integer           | Sim               | Identificador do Município      |

Agregador de dados da Unidade

| 1.5.2    | uf               | uf        | Sim   | gg
 Federativa                                 |
|----------|------------------|-----------|-------|---------------------------------|
| 1.5.2.1  | siglaUF          | Texto (2) | Sim   | Sigla da Unidade Federativa     |
| 1.5.2.2  | nomeUF           | Texto     | Sim   | Nome da Unidade Federativa      |
| 1.5.2.3  | dataHoraRegistro | Data/Hora | Sim   | Data de registro                |
| 1.5.3    | nome             | Texto     | Sim   | Nome do Município               |
| 1.5.4    | codigoIbge       | Texto     |       | Código IBGE do Município        |
| 1.5.5    | dataHoraRegistro | Data/Hora |       | Data de registro                |
| 1.6      | dataInclusao     | Data/Hora |       | Data de inclusão do registro    |
| 1.7      | dataAtualizacao  | Data/Hora |       | Data de atualização do registro |

## Exemplo de Retorno

```
Retorno:
```

```
{ "id": 1, "orgao": { "id": 1, "cnpj": "10000000000003", "razaoSocial": "SECRETARIA MUNICIPAL DO BEM ESTAR SOCIAL", "cnpjEnteResponsavel": "", "poderId": "E", "esferaId": "F", "validado": false, "dataValidacao": null }, "codigoUnidade": "1", "nomeUnidade": "Unidade de compra e contrataçoes", "municipio": { "id": 1, "uf": { "siglaUF": "SP", "nomeUF": "São Paulo", "dataHoraRegistro": "2021-05-14T02:24:08.239+00:00" }, "nome": "Município Xpto", "codigoIbge": "0000001" , "dataHoraRegistro": "2021-06-17T18:09:18.634+00:00" }, "dataInclusao": "2021 -06 -24T23:40:44.491+00:00", "dataAtualizacao": "2021 -06 -24T23:40:44.491+00:00" }
```

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3. Serviços de Compra/Edital/Aviso

## 6.3.1. Inserir Compra/Edital/Aviso

Serviço que permite inserir uma compra pública (módulo compra/edital/aviso) no PNCP. O sistema exige o upload de um arquivo anexo à compra enviada.

As extensões permitidas para o arquivo anexo são listadas na seção: Tabelas de domíno Extensões de arquivo aceitos pelas APIs de Documento.

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload     |
|-------------|----------------|------------------------|
| /v1/orgaos/{cnpj}
 /compras             | POST           | {
 "codigoUnidadeCompradora": "1010"                        |
| 1/orgaos/{cnpj
 /compras             |                | codigoUnidadeCompradora: 1010,
 "tipoInstrumentoConvocatorioId": "1"                        |
|             |                | tipoInstrumentoConvocatorio
  "modalidadeId": "6",                        |
|             |                | p
  "modalidadeId": "6",                        |
|             |                | ,
  "modoDisputaId": "1",                        |
|             |                | p
  "numeroCompra": "1                        |
|             |                | p
  "anoCompra": 2022,                        |
|             |                | p,
  "numeroProcesso": "1/2021",                        |
|             |                | ,
 "objetoCompra": "Compra para exemplificar uso da aplicação
 "ifClt"""                        |
|             |                | jppp
 "informacaoComplementar":                        |
|             |                | "srp": false,          |
|             |                | g,
  "dataAberturaProposta": "2022-07-21T08:00:00",                        |
|             |                | p,
  "dataEncerramentoProposta": "2022-07-21T17:00:0                        |
|             |                | p
  "amparoLegalId": "1",                        |
|             |                | amparoLegalId: 1,
 "linkSistemaOrigem": "url do sistema de origem para envio                        |
|             |                | g
 proposta",                        |
|             |                | proposta,
  "itensCompra": [                        |
|             |                | proposta,
  "itensCompra":                        |
|             |                | {
 "numeroItem": 1                        |
|             |                | ,
 "materialOuServico": "S",                        |
|             |                | materialOuServico: S
 "tipoBeneficioId": "4",                        |
|             |                | tipoBeneficioId: 4,
 "incentivoProdutivoBasico": false                        |
|             |                | incentivoProdutivoBasico: false,
 "descricao": "Item para exemplificar uso da aplicação",                        |
|             |                | descricao: Item para ex
 "quantidade": 1000,                        |
|             |                | quantidade: 1000,
 "unidadeMedida": "Unidade"                        |
|             |                | unidadeMedida: Unidade,
 "valorUnitarioEstimado": 1.5001,                        |
|             |                | "valorTotal": 1500.00, |
|             |                | ,
 "criterioJulgamentoId": "1"                        |
|             |                |                        |
|             |                | {
 "numeroItem": 2                        |
|             |                | numeroItem: 2,
 "materialOuServico": "M                        |
|             |                | ,
 "tipoBeneficioId": "4",                        |
|             |                | tipoBeneficioId: 4,
 "incentivoProdutivoBasico": false,                        |
|             |                | incentivoProdutivoBasico: false,
 "descricao": "Item para exemplificar um material",                        |
|             |                | "quantidade":          |
|             |                | quadade0,
 "unidadeMedida": "Kilograma",                        |
|             |                | g,
 "valorUnitarioEstimado": 100.0000,                        |
|             |                | "valorTotal": 1000.00, |
|             |                | "valorTotal": 1000.00, |
|             |                | valorTotal: 1000.00,
 "criterioJulgamentoId": "1"                        |
|             |                | }
 ]                        |
| }
 Exemplo Requisição (cURL)             | }
 Exemplo Requisição (cURL)                | }
 Exemplo Requisição (cURL)                        |

Enviando como arquivo:

curl -k -X POST --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/compras" -H "accept: */*" -H "Content-Type: multipart/form-data " -H 'Titulo -Documento: nome\_do\_arquivo' -H 'Tipo-Documento-Id: 1' --form

‘compra=@”/home/objeto.json";type=application/json ’ --form ‘documento=@”arquivo.pdf” ’

Enviando como JSON:

curl -k -X POST --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/compras" -H "accept: */*" -H "Content-Type: multipart/form-data " -H 'Titulo -Documento: nome\_do\_arquivo' -H 'Tipo-Documento-Id: 1' --form 'compra=@ " { \"anoCompra\": 2021, \"itensCompra\": [ { \"numeroItem\": 1, \"materialOuServico\": \"M\", \"tipoBeneficioId\": \"1\", \"incentivoProdutivoBasico\": false, \"descricao\": \"string\", \"quantidade\": 1, \"unidadeMedida\": \"string\", \"valorUnitarioEstimado\": 1, \"valorTotal\": 1, \"criterioJulgamentoId\": \"1\" } ], \"tipoInstrumentoConvocatorioId\": \"1\", \"modalidadeId\": \"6\", \"modoDisputaId\": \"1\", \"numeroCompra\": \"1\", \"numeroProcesso\": \"1\", \"objetoCompra\": \"string\", \"informacaoComplementar\": \"string\", \"amparoLegalId\": 1, \"srp\": true, \"orcamentoSigiloso\": false, \"dataAberturaProposta\": \"2022-01-18T14:30:01\", \"dataEncerramentoProposta\": \"2022-0131T14:30:01\", \"codigoUnidadeCompradora\": \"1\", \"linkSistemaOrigem\": \"string\ " } " ;type=application/json ' --form 'documento=@"arquivo.pdf" '

## Exemplo Requisição (Java, usando Spring/RestTemplate)

//gerando headers da requisição

HttpHeaders headers = new HttpHeaders();

headers.setContentType(MediaType.MULTIPART\_FORM\_DATA);

headers.setBearerAuth(access\_token);

headers.add("Titulo-Documento", "tituloDocumento");

headers.add("Tipo-Documento-Id", "16");

//gerando body da requisição

MultiValueMap&lt;String, Object&gt; body = new LinkedMultiValueMap&lt;&gt;();

body.add("compra", new FileSystemResource ("/path/objetoCompra.json"));

body.add("documento", new FileSystemResource ("/path/arquivo.docx"));

//gerando entidade Http e usando RestTemplate para obter uma Response Entity HttpEntity&lt;MultiValueMap&lt;String, Object&gt;&gt; requestEntity = new HttpEntity&lt;&gt;(body, headers);

RestTemplate restTemplate = new RestTemplate();

ResponseEntity&lt;String&gt; response = restTemplate.postForEntity("${BASE\_URL}/v1/orgaos /10000000000003/compras", requestEntity, String.class);

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {Titulo-Documento} e {Titulo-Documento-id} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo             | Tipo         | Obrigatório    | Descrição                    |
|-------|-------------------|--------------|----------------|------------------------------|
|    1  | cnpj              | Texto (14)   | Sim            | Cnpj do órgão dono da compra |
|    2  | Titulo-Documento  | Texto (50)   | Sim            | Título do documento
 Código da tabela de dom                              |
|    3  | Tipo-Documento-Id | Inteiro      | Sim            | de documento
 Código da unidade compradora; A 
 unidade compradora deverá estar 
 cadastrada para o órgão dono da                              |
|     4 | codigoUnidadeCompr
 adora                   | Texto (20)   | Sim            | unidade compradora deverá estar 
 cadastrada para o órgão dono da 
 compra;
 Código da tabela de domínio Tipo                              |
|     5 | tipoInstrumentoConv
 ocatorioId                   | Inteiro      | Sim            | Código da tabela de domínio Tipo 
 de instrumento convocatório                              |
|    6  | modalidadeId      | Inteiro      | Sim            | Código da tabela de domínio 
 Modalidade                              |
|    7  | modoDisputaId     | Inteiro      | Sim            | Código da tabela de domínio Modo 
 de disputa                              |
|    8  | numeroCompra      | Texto (50)   | Sim            | p
 sistema de origem                              |
|    9  | anoCompra         | Inteiro      | Sim            | Ano da compra
 úd                              |
|   10  | numeroProcesso    | Texto (50)   | Sim            | Compra/Edital/Aviso no sistema de 
 origem                              |
|   11  | objetoCompra      | Texto (5120) | Sim            | Objeto da compra             |
|    12 | informacaoCompleme
 ntar                   | Texto (5120) | Não            | Informações complementares; Se 
 existir;                              |
|   13  | srp               | Boleano      | Sim            | Identifica se a compra trata-se de 
 um SRP (Sistema de registro de 
 preços)                              |
|   14  | orcamentoSigiloso | Boleano      | Sim            | Identifica se o orçamento é sigiloso
 true - Sigiloso; false - Não sigiloso;                              |

<!-- image -->

|   15  | dataAberturaProposta    | Data e Hora   | Obrigatório 
 para Tipo de 
 Instrumento 
 Convocatório 
 1 ou 2. Tipo 3 
 será 
 desprezado     | Informar a data e hora de início do 
 recebimento das propostas (pelo 
 horário de Brasília)                                     |
|-------|-------------------------|---------------|-----|-------------------------------------|
|  16   | dataEncerrame
 posta                         | Data e Hor    | 1 ou 2. Tipo 3 
 será 
 desprezado.     | encerramento do recebimento das
 propostas (pelo horário de Brasília)
 Códidblddíi                                     |
|  17   |                         |               |     | Código da tabela de domínio 
 Amparo Legal                                     |
|  18   | itensCompra             | Lista         | Sim | Lista de itens da compra            |
|  18.1 | numeroItem              | Inteiro       | Sim | Número do item na compra (único 
 e sequencial crescente)                                     |
|  18.2 | materialOuServico       | Texto (1)     | Sim | Domínio: M - Material; S - Serviço; |
|  18.3 | tipoBeneficioId         | Inteiro       | Sim | gp
 de benefício
 Incentivo fiscal PPB (Processo 
 Produtivo Básico); true Possui o                                     |
|  18.4 | incentivoProdutivoBa
 sico                         | Boleano       | Sim | Produtivo Básico); true - Possui o 
 incentivo; false - Não possui o 
 incentivo;
 d                                     |
|  18.5 | descricao               | Texto (2048)  | Sim | çpp
 serviço;
 Quantidade do item da compra.                                     |
|  18.6 | quantidade              | Decimal       | Sim | Quantidade do item da compra.
 Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                     |
|  18.7 | unidadeMedida           | Texto (30)    | Sim | Unidade de medida do item da 
 compra
 Valor unitário estimado para o item                                     |
|  18.8 | valorUnitarioEstimado   | Decimal       | Sim | Valor unitário estimado para o item 
 da compra. Precisão de 4 dígitos 
 decimais; Ex: 100.0000;                                     |

Valor total para compra tradicional .

|   18.9  | valorTotal           | Decimal     | Sim   | Precisão de 4 dígitos decimais; Ex: 
 100.0000;                             |
|---------|----------------------|-------------|-------|-----------------------------|
|    18.1 | criterioJulgamentoId | Inteiro     | Sim   | Código da tabela de domínio 
 Critério de julgamento
 URL para página/portal do sistema                             |
|    19   | linkSistemaOrigem    | Texto (512) | Não   | será exibida no Portal PNCP |

## Dados de retorno

|   Id  | Campo        | Tipo        | Obrigatório    | Descrição                       |
|-------|--------------|-------------|----------------|---------------------------------|
|    1  | compraUri    | Texto (255) | Sim            | Endereço http da compra criada. |
|    2  | documentoUri | Texto (255) | Sim            | Endereço http do documento 
 anexo à compra criado.                                 |

## Exemplo de Retorno

Retorno:

## Headers:

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

access-control -allow -origin: *

cache -control: no -cache,no-store,max-age=0,must-revalidate content -type: application/json

date: ?

expires: ?

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/compras/2022/1

pragma: no - cache

strict - transport-security: max-age=?

x-content - type-options: nosniff

x-firefox - spdy: ?

x-frame - options: DENY

x-xss-protection: 1; mode=block

## Body:

{

"compraUri": https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/compras/2022/1 ,

"documentoUri": https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/compras/2022/1/arquivos/1

}

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.2. Retificar Compra/Edital/Aviso

Serviço que permite retificar os dados de uma compra/edital/aviso. Este serviço será acionado por qualquer plataforma digital credenciada. Importante lembrar que na Retificação todas as informações terão que ser enviadas novamente, não apenas as que sofreram alteração. Fica impedida a retificação da compra/edital/aviso caso a mesma não possua documento/arquivo ativo vinculado a ela no PNCP.

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload   |
|-------------|----------------|----------------------|
| /v1/orgaos/{cnpj}/compr
 as/{ano}/{sequencial}             | PUT            | HTTP Exemplo de Payload
 T {
  "tipoInstrumentoConvocatorioId": "1",
  "modalidadeId": "1",
  "modoDisputaId": "1",
  "numeroCompra": "1",
  "numeroProcesso": "1/2021",
  "situacaoCompraId": "1",
  "objetoCompra": "Compra exemplo",
  "informacaoComplementar": "",
  "cnpjOrgaoSubRogado": "",
  "codigoUnidadeSubRogada": "",
  "srp": true,
  "orcamentoSigiloso": true,
  "dataAberturaProposta": "2021-07-21T08:00:00",
 "dtEtPt""202107                      |

curl -k -X PUT --header "Authorization: Bearer access\_token"

"${BASE\_URL}/v1/orgaos/10000000000003/compras/2021/1" -H "accept: */*" application/json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

-H "Content-Type:

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo              | Tipo         | Obrigatório    | Descrição                    |
|-------|--------------------|--------------|----------------|------------------------------|
|    1  | cnpj               | Texto (14)   | Sim            | Cnpj do órgão dono da compra |
|    2  | ano                | Inteiro      | Sim            | Ano da compra                |
|    3  | sequencial         | Inteiro      | Sim            | Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;
 Código da tabela de domínio Tipo                              |
|     4 | tipoInstrumentoConvo
 catorioId                    | Inteiro      | Sim            | de instrumento convocatório
 Códidtblddíi                              |
|    5  | modalidadeId       | Inteiro      | Sim            | Código da tabela de domínio 
 Modalidade                              |
|    6  | modoDisputaId      | Inteiro      | Sim            | Código da tabela de domínio Modo 
 de disputa                              |
|    7  | numeroCompra       | Texto (50)   | Sim            | Número da Compra/Edital/Aviso no 
 sistema de origem
 Núdd                              |
|    8  | numeroProcesso     | Texto (50)   | Sim            | Compra/Edital/Aviso no sistema de 
 origem
 Código da tabela de domínio                              |
|    9  | situacaoCompraId   | Inteiro      | Sim            | Código da tabela de domínio 
 Situação da Compra/Edital/Aviso                              |
|   10  | objetoCompra       | Texto (5120) | Sim            | Objeto da compra             |
|    11 | informacaoCompleme
 ntar                    | Texto (5120) | Não            | Informações complementares; Se 
 existir;                              |
|   12  | cnpjOrgaoSubRogado | CNPJ         | Não            | CNPJ do órgão subrogado.     |
|    13 | codigoUnidadeSubRog
 ada                    | String       | Não            | Código da unidade subrogada
 Identifica se a compra trata-se d                              |
|   14  | srp                | Boleano      | Sim            | Identifica se a compra trata-se de 
 um SRP (Sistema de registro de 
 preços)                              |
|   15  | orcamentoSigiloso  | Boleano      | Sim            | çg
 true - Sigiloso; false - Não sigiloso;                              |

|   16  | dataAberturaProposta    | Data e Hora   | para Tipo de 
 Instrumento 
 Convocatório 
 1 ou 2. Tipo 3 
 será 
 desprezado.
 Obiói     | Informar a data e hora de início do 
 recebimento das propostas (pelo 
 horário de Brasília)                           |
|-------|-------------------------|---------------|-----|---------------------------|
|    17 | posta                   | Data e Hora   | 1 ou 2. Tipo 3 
 será 
 desprezado.
 Sim     | Informar a data e hora de |
|   18  | amparoLegalId           | Inteiro       | Sim | Código da tabela de domínio 
 Amparo Legal
 URL para página/portal do sistema                           |
|   19  | linkSistemaOrigem       | Texto (512)   | Não | gpp
 recebimento de propostas. Esta url 
 será exibida no Portal PNCP                           |
|   20  | justificativa           | Texto (255)   | Não | retificação dos atributos da 
 compra.                           |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.3. Retificar Parcialmente uma Compra/Edital/Aviso

Serviço que permite retificar parcialmente os dados de uma compra/edital/aviso. Este serviço será acionado por qualquer plataforma digital credenciada. Na retificação parcial, você precisa enviar apenas as informações que sofreram alteração. Por exemplo, se você

desejar apenas atualizar a situação de uma compra, você deve informar apenas o atributo situacaoCompraId e ignorar todos os demais atributos. Fica impedida a retificação da compra/edital/aviso caso a mesma não possua documento/arquivo ativo vinculado a ela no PNCP.

## Detalhes de Requisição

| Endpoint                 | Método HTTP              | Exemplo de Payload       |
|--------------------------|--------------------------|--------------------------|
| /v1/orgaos/{cnpj}/compr
 as/{ano}/{sequencial}                          | PATCH                    | TTP Exemplo de Payload
 {
  "tipoInstrumentoConvocatorioId": "1",
  "modalidadeId": "1",
  "modoDisputaId": "1",
  "numeroCompra": "1",
  "numeroProcesso": "1/2021",
  "situacaoCompraId": "1",
  "objetoCompra": "Compra exemplo",
  "informacaoComplementar": "",
  "cnpjOrgaoSubRogado": "",
  "codigoUnidadeSubRogada": "",
  "srp": true,
  "orcamentoSigiloso": true,
  "dataAberturaProposta": "2021-07-21T08:00:00",
 "dataEncerramentoProposta": "2021-07-                          |
| xemplo Requisição (cURL) | xemplo Requisição (cURL) | xemplo Requisição (cURL) |

curl -k -X PATCH --header "Authorization: Bearer access\_token"

"${BASE\_URL}/v1/orgaos/10000000000003/compras/2021/1" -H "accept: */*" application/json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

-H "Content-Type:

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo              | Tipo         | Obrigatório    | Descrição                    |
|-------|--------------------|--------------|----------------|------------------------------|
|    1  | cnpj               | Texto (14)   | Sim            | Cnpj do órgão dono da compra |
|    2  | ano                | Inteiro      | Sim            | Ano da compra                |
|    3  | sequencial         | Inteiro      | Sim            | Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;
 Código da tabela de domínio Tipo                              |
|     4 | tipoInstrumentoConvo
 catorioId                    | Inteiro      | Não            | de instrumento convocatório
 Códidtblddíi                              |
|    5  | modalidadeId       | Inteiro      | Não            | Código da tabela de domínio 
 Modalidade                              |
|    6  | modoDisputaId      | Inteiro      | Não            | Código da tabela de domínio Modo 
 de disputa                              |
|    7  | numeroCompra       | Texto (50)   | Não            | Número da Compra/Edital/Aviso no 
 sistema de origem
 Núdd                              |
|    8  | numeroProcesso     | Texto (50)   | Não            | Compra/Edital/Aviso no sistema de 
 origem
 Código da tabela de domínio                              |
|    9  | situacaoCompraId   | Inteiro      | Não            | Código da tabela de domínio 
 Situação da Compra/Edital/Aviso                              |
|   10  | objetoCompra       | Texto (5120) | Não            | Objeto da compra             |
|    11 | informacaoCompleme
 ntar                    | Texto (5120) | Não            | Informações complementares; Se 
 existir;                              |
|   12  | cnpjOrgaoSubRogado | CNPJ         | Não            | CNPJ do órgão subrogado.     |
|    13 | codigoUnidadeSubRog
 ada                    | String       | Não            | Código da unidade subrogada
 Identifica se a compra trata-se d                              |
|   14  | srp                | Boleano      | Não            | Identifica se a compra trata-se de 
 um SRP (Sistema de registro de 
 preços)                              |
|   15  | orcamentoSigiloso  | Boleano      | Não            | çg
 true - Sigiloso; false - Não sigiloso;                              |

|   16  | dataAberturaProposta    | Data e Hora   | para Tipo de 
 Instrumento 
 Convocatório 
 1 ou 2. Tipo 3 
 será 
 desprezado.
 Obrigatório      | Informar a data e hora de início do 
 recebimento das propostas (pelo 
 horário de Brasília)                           |
|-------|-------------------------|---------------|-----|---------------------------|
|    17 | posta                   | Data e Hora   | Convocatório 
 1 ou 2. Tipo 3 
 será 
 desprezado.
 Não     | Informar a data e hora de |
|   18  | amparoLegalId           | Inteiro       | Não | Código da tabela de domínio 
 Amparo Legal
 URL para página/portal do sistema                           |
|   19  | linkSistemaOrigem       | Texto (512)   | Não | recebimento de propostas. Esta url 
 será exibida no Portal PNCP                           |
|   20  | justificativa           | Texto (255)   | Não | retificação dos atributos da 
 compra.                           |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.4. Excluir Compra/Edital/Aviso

Serviço que permite excluir uma compra/edital/aviso. Este serviço será acionado por qualquer plataforma digital credenciada. Não será possível excluir Compra com Ata ou Contrato ativo.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}                           | DELETE                    | {
  "justificativa": "motivo/justificativa para a exclusão 
 da compra"                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1" -H "accept: */*" -H "Content-Type:                           | curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1" -H "accept: */*" -H "Content-Type:                           | curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1" -H "accept: */*" -H "Content-Type:                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

| Id    | Campo         | Tipo        | Obrigatório    | Descrição                     |
|-------|---------------|-------------|----------------|-------------------------------|
| 1     | cnpj          | Texto (14)  | Sim            | Cnpj do órgão dono da compra  |
| 2     | ano           | Inteiro     | Sim            | Ano da compra                 |
|       |               |             |                | Sequencial da compra no PNCP; |
| 3     | sequencial    | Inteiro     | Sim            | qp
 inserida no PNCP;                               |
| 4     | justificativa | Texto (255) | Não            | Motivo/justificativa para exclusão 
 da compra.                               |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.5. Consultar uma Compra/Edital/Aviso

Serviço que permite consultar uma compra/edital/aviso. Este serviço será acionado por qualquer plataforma digital credenciada.

## Detalhes de Requisição

| Endpoint                  | Método H                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}                           | GET                       | Não se aplica             |                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| -k                        | "Authorization            | Bearer                    | access_token"             |
| _
 /orgaos/10000000000003/compras/2021/1" -H "accept: */*"                           | _
 /orgaos/10000000000003/compras/2021/1" -H "accept: */*"                           | _
 /orgaos/10000000000003/compras/2021/1" -H "accept: */*"                           | _
 /orgaos/10000000000003/compras/2021/1" -H "accept: */*"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

| Id    | Campo      | Tipo       | Obrigatório    | Descrição                     |
|-------|------------|------------|----------------|-------------------------------|
| 1     | cnpj       | Texto (14) | Sim            | Cnpj do órgão dono da compra  |
| 2     | ano        | Inteiro    | Sim            | Ano da compra                 |
|       |            |            |                | Sequencial da compra no PNCP; |
|       |            |            |                | Número sequencial gerado no 
 momento que a compra foi                               |
| 3     | sequencial | Inteiro    | Sim            | inserida no PNCP;             |

## Dados de retorno

| Id    | Campo                | Tipo         | Descrição                                     |
|-------|----------------------|--------------|-----------------------------------------------|
| 1     | numeroControlePNCP   | String       | Número de Controle PNCP da Compra             |
| 2     | numeroCompra         | Texto (50)   | Número da Compra no sistema de origem         |
| 3     | anoCompra            | Inteiro      | Ano da Compra                                 |
| 4     | processo             | Texto (50)   | Número do processo da Compra/Edital/Aviso no 
 sistema de origem                                               |
| 5     | tipoInstrumentoConvoc
 atorioId                      | Inteiro      | Código do instrumento convocatório da Compra  |
| 6     | tipoInstrumentoConvoc
 atorioNome                      | String       | Nome do instrumento convocatório da Compra    |
| 7     | modalidadeId         | Inteiro      | Código da Modalidade referente à Compra       |
| 8     | modalidadeNome       | String       | Modalidade referente à Compra                 |
| 9     | modoDisputaId        | Inteiro      | Código do modo de disputa referente à Compra  |
| 10    | modoDisputaNome      | String       | Modo de disputa referente à Compra            |
| 11    | situacaoCompraId     | Inteiro      | Código da situação da Compra                  |
| 12    | situacaoCompraNome   | Inteiro      | Situação da Compra                            |
| 13    | objetoCompra         | Texto (5120) | Descrição do Objeto referente à Compra        |
| 14    | informacaoComplemen
 tar                      | Texto (5120) | Informação Complementar do objeto referente à 
 Compra                                               |
|       | srp                  |              | Compra
 Identifica se a compra trata-se de um SRP (Sistema d                                               |
| 15    | srp                  | Boleano      | Agrupador com os dados do amparo lega         |
| 16.1  | amparoLegalNome      | Inteiro      | Amparo legal da tabela de domínio Amparo lega |
|       |                      | Tt(100)      | Descrição do Amparo legal da tabela de domínio 
 Amparo legal                                               |
| 16.2  | amparoLegalDescricao | Texto(100)   | Descrição do Amparo legal da tabela de domínio 
 Amparo legal                                               |
| 17    | indicadorOrcamentoSig
 iloso                      | Boleano      | Identifica se o orçamento é sigiloso; true - Sigiloso; 
 false - Não sigiloso;
 Vll iddCPiãdé 4                                               |
| 18    | valorTotalEstimado   | Decimal      | Valor total estimado da Compra. Precisão de a
 dígitos decimais; Ex: 100.0001;                                               |

|   19  | valorTotalHomologado    | Decimal     | Valor total homologado com base nos resultados 
 incluídos. Precisão de até 4 dígitos decimais; Ex: 
 100.0001;                                                  |
|-------|-------------------------|-------------|--------------------------------------------------|
|  20   | dataAberturaProposta    | Data e Hora | Data de abertura do recebimento 
 propostas(horário de Brasília)                                                  |
|  21   | dataEncerramentoProp
 osta                         | Data e Hora | Data de encerramento do recebimento de 
 propostas(horário de Brasília)                                                  |
|  22   | dataPublicacaoPncp      | Data        | Data da publicação da Compra no PNCP             |
|  23   | dataInclusao            | Data        | Data da inclusão do registro da Compra no PNCP   |
|  24   | dataAtualizacao         | Data        | Data da última atualização do registro da Compra |
|  25   | sequencialCompra        | Inteiro     | Sequencial da compra no PNCP; Número sequencia
 gerado no momento que a compra foi inserida no 
 PNCP;                                                  |
|  26   | orgaoEntidade           |             | Agrupador com os dados do Órgão/Entidad          |
|  26.1 | cnpj                    | String      | CNPJ do Órgão referente à Compra                 |
|  26.2 | razaosoci               | String      | Razão social do Órgão referente à Compra         |
|  26.3 | poderId                 | String      | L - Legislativo; E - Executivo; J - Judiciário
 CódidftÓã                                                  |
|  26.4 | esferaId                | String      | Código da esfera a que pertence o Órgão.
 F - Federal; E - Estadual; M - Municipal; D - Distrital                                                  |
|  27   | unidadeOrgao            |             | Agrupador com os dados da Unidade compradora 
 do Órgão                                                  |
|  27.1 | codigoUnidade           | String      | Código da Unidade Compradora pertencente ao Órgã |
|  27.2 | nomeUnidade             | String      | Nome da Unidade Compradora pertencente ao Órgão  |
|  27.3 | municipioId             | Inteiro     | Código IBGE do município                         |
|  27.4 | municipioNome           | String      | Nome do município                                |
|  27.5 | ufSigla                 | String      | Sigla da unidade federativa do município         |
|  27.6 | ufNome                  | String      | Nome da unidade federativa do município          |
|  28   | orgaoSubRogado          |             | Agrupador com os dados do Órgão/Entidad
 subrogado                                                  |

|   28.1  | cnpj              | String           | CNPJ do Órgão referente à Compra                  |
|---------|-------------------|------------------|---------------------------------------------------|
|    28.2 | razaosocial       | String           | Razão social do Órgão referente à Compra          |
|    28.3 | poderId           | String           | Código do poder a que pertence o Órgão.
 L - Legislativo; E - Executivo; J - Judiciário                                                   |
|    28.4 | esferaId          | String           | gqpg
 F - Federal; E - Estadual; M - Municipal; D - Distrital
 Agrupador com os dados da Unidade compradora 
 do Órgão subrogado                                                   |
|    29   | unidadeSubRogada  | unidadeSubRogada | Agrupador com os dados da Unidade compradora 
 do Órgão subrogado                                                   |
|    29.1 | codigoUnidade     | String           | Código da Unidade Compradora pertencente ao Órgão |
|    29.2 | nomeUnidade       | String           | Nome da Unidade Compradora pertencente ao Órgão   |
|    29.3 | municipioId       | Inteiro          | Código IBGE do município                          |
|    29.4 | municipioNome     | String           | Nome do município                                 |
|    29.5 | ufSigla           | String           | Sigla da unidade federativa do município          |
|    29.6 | ufNome            | String           | Nome da unidade federativa do município           |
|    30   | usuarioNome       | String           | Nome do Usuário/Sistema que enviou a compra       |
|    31   | linkSistemaOrigem | String           | URL para página/portal do sistema de origem da 
 compra para recebimento de propostas.                                                   |

## 6.3.6. Inserir Documento a uma Compra/Edital/Aviso

Serviço que permite inserir/anexar um documento/arquivo a uma Compra/Edital/Aviso. O sistema permite o upload de arquivos com as extensões listadas na seção: Tabelas de domínio Extensões de arquivo aceitos pelas APIs de Documento.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras/
 {ano}/{sequencial}/arquivo                           | POST                      | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| url -k -X POST --header "Authorization: Bearer access_token"
 ${BASEURL}/v1/orgaos/10000000000003/compras/2021/1/arquivos" H "accept: */*" H "Content                           | url -k -X POST --header "Authorization: Bearer access_token"
 ${BASEURL}/v1/orgaos/10000000000003/compras/2021/1/arquivos" H "accept: */*" H "Content                           | url -k -X POST --header "Authorization: Bearer access_token"
 ${BASEURL}/v1/orgaos/10000000000003/compras/2021/1/arquivos" H "accept: */*" H "Content                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo             | Tipo           | Obrigatório    | Descrição                    |
|-------|-------------------|----------------|----------------|------------------------------|
|    1  | cnpj              | Texto (14)     | Sim            | Cnpj do órgão dono da compra |
|    2  | ano               | Inteiro        | Sim            | Ano da compra                |
|    3  | sequencial        | Inteiro        | Sim            | Sequencial da compra no PNCP; 
 Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;                              |
|    4  | Titulo-Documento  | Texto (50)     | Sim            | Título do documento          |
|    5  | Tipo-Documento-Id | Inteiro        | Sim            | Código da tabela de domínio Tipo 
 de documento                              |
|    6  | arquivo           | String Binária | Sim            | String binária do arquivo    |

## Dados de retorno

|   Id  | Campo    | Tipo        | Descrição                       |
|-------|----------|-------------|---------------------------------|
|    1  | location | Texto (255) | Endereço http do recurso criado |

## Exemplo de Retorno

```
Retorno: access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin, access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS access-control -allow -origin: * cache -control: no -cache,no-store,max-age=0,must-revalidate content -length: 0 date: ? expires: 0 location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/compras/2021/1/arquivos/1 nome-bucket: ? pragma: no -cache strict -transport-security: max-age=? x-content -type-options: nosniff x-firefox -spdy: ? x-frame -options: DENY x-xss-protection: 1; mode=block
```

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.7. Excluir Documento de uma Compra/Edital/Aviso

Serviço que permite remover documento pertencente a um Edital.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras/
 {ano}/{sequencial}/arquivo
 s/{sequencialDocumento}                           | DELETE                    | {
  "justificativa": "Motivo/justificativa para exclusão 
 do documento da compra"
 }                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| l -k -X DELETE --header "Authorization: Bearer access_token"
 BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/arquivos/1" -H "accept: */* -H "Content                           | l -k -X DELETE --header "Authorization: Bearer access_token"
 BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/arquivos/1" -H "accept: */* -H "Content                           | l -k -X DELETE --header "Authorization: Bearer access_token"
 BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/arquivos/1" -H "accept: */* -H "Content                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} e {sequencialDocumento} na URL.

|   Id  | Campo              | Tipo        | Obrigatório    | Descrição                    |
|-------|--------------------|-------------|----------------|------------------------------|
|    1  | cnpj               | Texto (14)  | Sim            | Cnpj do órgão dono da compra |
|    2  | ano                | Inteiro     | Sim            | Ano da compra                |
|    3  | sequencial         | Inteiro     | Sim            | Sequencial da compra no PNCP; 
 Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;                              |
|     4 | sequencialDocument | Inteiro     | Sim            | PNCP; Número sequencial gerado 
 no momento que o documento foi 
 inserido no PNCP;                              |
|    5  | justificativa      | Texto (255) | Não            | Motivo/justificativa para exclusão 
 do documento da compra.                              |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | Delete                | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.8. Consultar Todos Documentos de uma Compra/Edital/Aviso

Serviço que permite consultar a lista de documentos pertencentes a um Edital.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}/arqu
 ivos                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/compras/2021/1/arquivos" -H "Accept: application/json”                           | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/compras/2021/1/arquivos" -H "Accept: application/json”                           | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASEURL}/v1/orgaos/10000000000003/compras/2021/1/arquivos" -H "Accept: application/json”                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

| Id    | Campo      | Tipo       | Obrigatório    | Descrição                     |
|-------|------------|------------|----------------|-------------------------------|
| 1     | cnpj       | Texto (14) | Sim            | Cnpj do órgão dono da compra  |
| 2     | ano        | Inteiro    | Sim            | Ano da compra                 |
|       |            |            |                | Sequencial da compra no PNCP; |
|       | il         |            |                | Número sequencial gerado no 
 momento que a compra foi                               |
| 3     | sequencial | Inteiro    | Sim            | inserida no PNCP;             |

## Dados de retorno

|   Id  | Campo               | Tipo    | Descrição                                    |
|-------|---------------------|---------|----------------------------------------------|
|   1   | Documentos          | Lista   | Lista de documentos                          |
|   1.1 | sequencialDocumento | Inteiro | Número sequencial atribuído ao arquivo       |
|   1.2 | url                 | Texto   | URL para download do arquivo                 |
|   1.3 | tipoDocumentoId     | Inteiro | Código do tipo de documento conforme PNCP    |
|   1.4 | tipoDocumentoNome   | Texto   | Nome do tipo de documento conforme PNCP      |
|   1.5 | titulo              | Texto   | Título referente ao arquivo                  |
|   1.6 | dataPublicacaoPncp  | Data    | Data de publicação do arquivo no portal PNCP |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.9. Baixar Documento de uma Compra/Edital/Aviso

Serviço que permite baixar um documento específico pertencente a uma compra.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras
 /{ano}/{sequencial}/arquiv
 os/{sequencialDocumento}                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/arquivos/1" -H "Accept: application/pd                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/arquivos/1" -H "Accept: application/pd                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/arquivos/1" -H "Accept: application/pd                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} e {sequencialDocumento} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo              | Tipo       | Obrigatório    | Descrição                    |
|-------|--------------------|------------|----------------|------------------------------|
|    1  | cnpj               | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    2  | ano                | Inteiro    | Sim            | Ano da compra                |
|    3  | sequencial         | Inteiro    | Sim            | Sequencial da compra no PNCP; 
 Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;                              |
|     4 | sequencialDocument | Inteiro    | Sim            | PNCP; Número sequencial gerado 
 no momento que o documento fo
 inserido no PNCP;                              |

## Dados de retorno

Id

Campo

1

string

## Códigos de Retorno

Código HTTP

200

400

422

OK

Bad Request

Unprocessable Entity

500

Internal Server Error

Tipo

Sucesso

Erro

Erro

Erro

## 6.3.10. Inserir Itens a uma Compra/Edital/Aviso

Serviço para inserir um ou vários itens a uma compra/edital/aviso. Os itens podem ser inseridos de duas formas: ao inserir uma compra, pode já informar a lista de itens a ser inserida. Alternativamente pode usar o presente serviço para adicionar um ou vários itens a uma compra existente. Fica impedida a inclusão de itens caso a compra/edital/aviso não possua documento/arquivo ativo vinculado a ela no PNCP.

Tipo

String

Mensagem

Descrição string do arquivo

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload   |
|-------------|----------------|----------------------|
| /v1/orgaos/{cnpj}
 /compras/{ano}
 /{sequencial}/itens             | POST           | py
 [
  {
  "numeroItem": 1,
  "materialOuServico": "M",
  "tipoBeneficioId": "4",
  "incentivoProdutivoBasico": false,
  "descricao": "Item exemplificativo",
  "quantidade": 100,
  "unidadeMedida": "Unidade",
  "valorUnitarioEstimado": 1.00,
  "valorTotal": 100.00,
 "criterioJulgamentoId": "1"                      |

## Exemplo Requisição (cURL)

curl -k -X POST --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/compras/2021/1/itens" -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

<!-- image -->

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo                    | Tipo         | Obrigatório    | Descrição                           |
|-------|--------------------------|--------------|----------------|-------------------------------------|
|    1  | cnpj                     | Texto (14)   | Sim            | Cnpj do órgão dono da compra        |
|    2  | ano                      | Inteiro      | Sim            | Ano da compra
 Sequencial da compra                                     |
|    3  | sequencial               | Inteiro      | Sim            | Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;
 Número do item na compra (único                                     |
|    4  | numeroItem               | Inteiro      | Sim            | e sequencial crescente)             |
|    5  | materialOuServico        | Texto (1)    | Sim            | Domínio: M - Material; S - Serviço; |
|    6  | tipoBeneficioId          | Inteiro      | Sim            | Código da tabela de domínio Tipo 
 de benefício                                     |
|    7  | incentivoProdutivoBasico | Boleano      | Sim            | Produtivo Básico); true - Possui o 
 incentivo; false - Não possui o 
 incentivo;
 Descrição para o produto ou                                     |
|    8  | descricao                | Texto (2048) | Sim            | Descrição para o produto ou 
 serviço;
 Quantidade do item da compra. 
 Piãd4 díitdiiE                                     |
|    9  | quantidade               | Decimal      | Sim            | Quantidade do item da compra. 
 Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                     |
|   10  | unidadeMedida            | Texto (30)   | Sim            | Unidade de medida do item da 
 compra                                     |
|   11  | valorUnitarioEstimado    | Decimal      | Sim            | Valor unitário estimado. Precisão 
 de 4 dígitos decimais; Ex: 100.0000;
 Valor total para compra tradicional                                     |
|   12  | valorTotal               | Decimal      | Sim            | pp
 Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                     |
|   13  | criterioJulgamentoId     | Inteiro      | Sim            | Código da tabela de domínio 
 Critério de julgamento                                     |

## Dados de retorno

|   Id  | Campo    | Tipo        | Obrig   | Descrição                       |
|-------|----------|-------------|---------|---------------------------------|
|    1  | location | Texto (255) | Sim     | Endereço http do recurso criado |

## Exemplo de Retorno

| Retorno                        | Retorno                                                                               |
|--------------------------------|---------------------------------------------------------------------------------------|
| [ "https://treina.pncp.gov.br/ | "https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/compras/2021/1/itens/1" |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.11 . Retificar Item de uma Compra/Edital/Aviso

Serviço para retificar um item de uma compra/edital/aviso. Ou utilizado para alterar a situação do item conforme tabela de domínio de situação do item da compra. Importante lembrar que na Retificação todas as informações terão que ser enviadas novamente, não apenas as que sofreram alteração. Fica impedida a retificação do item caso a compra/edital/aviso não possua documento/arquivo ativo vinculado a ela no PNCP.

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload   |
|-------------|----------------|----------------------|
| /v1/orgaos/{cnpj}
 /compras/{ano}
 /{sequencial}
 /itens/{numeroItem}             | PUT            | {
  "numeroItem": 2,
  "materialOuServico": "M",
  "tipoBeneficioId": "4",
  "incentivoProdutivoBasico": false,
  "descricao": "Item exemplificativo 2",
  "quantidade": 100,
  "unidadeMedida": "Unidade",
  "valorUnitarioEstimado": 10.00,
  "valorTotal": 1000.00,
  "situacaocompraitemid": "1",
 "criterioJlgamentoId""1"                      |

## Exemplo Requisição (cURL)

curl -k -X PUT --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/compras/2021/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" -data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano}, {sequencial} e {numeroItem} na URL.

<!-- image -->

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo                    | Tipo         | Obrigatório    | Descrição                           |
|-------|--------------------------|--------------|----------------|-------------------------------------|
|    1  | cnpj                     | Texto (14)   | Sim            | Cnpj do órgão dono da compra        |
|    2  | ano                      | Inteiro      | Sim            | Ano da compra                       |
|    3  | sequencial               | Inteiro      | Sim            | Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP
 Número do item na compra (único                                     |
|    4  | numeroItem               | Inteiro      | Sim            | e sequencial crescente)             |
|    5  | materialOuServico        | Texto (1)    | Sim            | Domínio: M - Material; S - Serviço; |
|    6  | tipoBeneficioId          | Inteiro      | Sim            | Código da tabela de domínio Tipo 
 de benefício
 Incentivo fiscal PPB (Processo                                     |
|    7  | incentivoProdutivoBasico | Boleano      | Sim            | Incentivo fiscal PPB (Processo 
 Produtivo Básico); true - Possui o 
 incentivo; false - Não possui o 
 incentivo;                                     |
|    8  | descricao                | Texto (2048) | Sim            | Descrição para o produto ou 
 serviço;
 Quantidade do item da compra.
 Precisão de 4 dígitos decimais; Ex:                                     |
|    9  | quantidade               | Decimal      | Sim            | Quantidade do item da compra.
 Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                     |
|   10  | unidadeMedida            | Texto (30)   | Sim            | Unidade de medida                   |
|   11  | valorUnitarioEstimado    | Decimal      | Sim            | Valor unitário estimado. Precisão 
 de 4 dígitos decimais; Ex: 100.0000;
 Valor total para compra tradicional                                     |
|   12  | valorTotal               | Decimal      | Sim            | Valor total para compra tradicional.
 Precisão de 4 dígitos decimais; Ex: 
 100.0000;
 óddblddí                                     |
|   13  | situacaocompraitemid     | Inteiro      | Sim            | Situação do item da 
 Compra/Edital/Aviso
 Código da tabela de domínio                                     |
|   14  | criterioJulgamentoId     | Inteiro      | Sim            | Código da tabela de domínio 
 Critério de julgamento                                     |

15

justificativa

Texto (255)

Não

Motivo/justificativa para a retificação dos atributos do item da compra.

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.12. Retificar parcialmente um Item de uma Compra/Edital/Aviso

Serviço para retificar parcialmente um item de uma compra/edital/aviso. Pode ser utilizado para alterar a situação do item conforme tabela de domínio de situação do item da compra.

Na retificação parcial, você precisa enviar apenas as informações que sofreram alteração. Por exemplo, se você desejar apenas atualizar a situação de um item, você deve informar apenas o atributo situacaoCompraItemId e ignorar todos os demais atributos. Fica impedida a retificação do item caso a compra/edital/aviso não possua documento/arquivo ativo vinculado a ela no PNCP.

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload   |
|-------------|----------------|----------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}/iten
 s/{numeroItem}             | PATCH          | {
  "materialOuServico": "M",
  "tipoBeneficioId": "1",
  "incentivoProdutivoBasico": true,
  "descricao": "string",
  "quantidade": 0,
  "unidadeMedida": "string",
  "valorUnitarioEstimado": 0,
  "valorTotal": 0,
  "situacaoCompraItemId": "1",
  "criterioJulgamentoId": "1",                      |

## Exemplo Requisição (cURL)

curl -k -X PATCH --header "Authorization: Bearer access\_token " "${BASE\_URL}/v1/orgaos /10000000000003/compras/2021/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" -data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano}, {sequencial} e {numeroItem} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo                    | Tipo         | Obrigatório    | Descrição                           |
|-------|--------------------------|--------------|----------------|-------------------------------------|
|    1  | cnpj                     | Texto (14)   | Sim            | Cnpj do órgão dono da compra        |
|    2  | ano                      | Inteiro      | Sim            | Ano da compra                       |
|    3  | sequencial               | Inteiro      | Sim            | momento que a compra foi 
 inserida no PNCP
 Núdit(ú                                     |
|    4  | numeroItem               | Inteiro      | Sim            | e sequencial crescente)             |
|    5  | materialOuServico        | Texto (1)    | Não            | Domínio: M - Material; S - Serviço; |
|    6  | tipoBeneficioId          | Inteiro      | Não            | Código da tabela de domínio Tipo 
 de benefício
 Incentivo fiscal PPB (Processo                                     |
|    7  | incentivoProdutivoBasico | Boleano      | Não            | Incentivo fiscal PPB (Processo 
 Produtivo Básico); true - Possui o 
 incentivo; false - Não possui o 
 incentivo;                                     |
|    8  | descricao                | Texto (2048) | Não            | çpp
 serviço;
 Quantidade do item da compra. 
 Precisão de 4 dígitos decimais; Ex:                                     |
|    9  | quantidade               | Decimal      | Não            | Quantidade do item da compra. 
 Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                     |
|   10  | unidadeMedida            | Texto (30)   | Não            | Unidade de medida                   |
|   11  | valorUnitarioEstimado    | Decimal      | Não            | Valor unitário estimado. Precisão 
 de 4 dígitos decimais; Ex: 100.0000
 Valor total para compra tradicional                                     |
|   12  | valorTotal               | Decimal      | Não            | Valor total para compra tradicional
 Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                     |
|   13  | situacaoCompraItemId     | Inteiro      | Não            | Situação do item da 
 Compra/Edital/Aviso
 Código da tabela de domínio                                     |
|   14  | criterioJulgamentoId     | Inteiro      | Não            | Código da tabela de domínio 
 Critério de julgamento                                     |

15

justificativa

Texto (255)

Não

Motivo/justificativa para a retificação dos atributos do item da compra.

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.13. Consultar Itens de uma Compra/Edital/Aviso

Serviço para recuperar os itens de uma compra/edital/aviso.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}
 /compras/{ano}
 /{sequencial}/itens                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objetojson"                           | curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objetojson"                           | curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objetojson"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo         | Tipo       | Descrição                    |
|-------|---------------|------------|------------------------------|
|    1  | cnpj          | Texto (14) | Cnpj do órgão dono da compra |
|    2  | ano           | Inteiro    | Ano da compra                |
|    3  | sequencial    | Inteiro    | Sequencial da compra no PNCP; Número sequencia
 gerado no momento que a compra foi inserida no 
 PNCP                              |
|    4  | pagina        | Inteiro    | Utilizado para paginação dos itens. Número da 
 página.                              |
|    5  | tamanhoPagina | Inteiro    | Utilizado para paginação dos itens. Quantidade 
 itens por página.                              |

## Dados de retorno

|   Id  | Campo                    | Tipo         | Descrição                                          |
|-------|--------------------------|--------------|----------------------------------------------------|
|  1    | Lista de Itens da 
 Compra                          |              | Agrupador da lista de itens da compra              |
|  1.1  | numeroItem               | Inteiro      | Número do item na compra (único e sequencial 
 crescente)                                                    |
|  1.2  | materialOuServico        | Texto (1)    | Domínio: M - Material; S - Serviço;                |
|  1.3  | tipoBeneficioId          | Inteiro      | Código da tabela de domínio Tipo de benefício      |
|  1.4  | incentivoProdutivoBasico | Boleano      | Incentivo fiscal PPB (Processo Produtivo Básico); 
 true - Possui o incentivo; false - Não possui o 
 incentivo;                                                    |
|  1.5  | descricao                | Texto (2048) | Descrição para o produto ou serviço;               |
|  1.6  | quantidad                | Decimal      | Quantidade do item da compra. Precisão de até 4 
 dígitos decimais; Ex: 1.0001;                                                    |
|  1.7  | unidadeMedida            | Texto (30)   | Unidade de medida                                  |
|  1.8  | valorUnitarioEstimado    | Decimal      | Valor unitário estimado. Precisão de até 4 dígitos 
 decimais; Ex: 100.0001;                                                    |
|  1.9  | valorTotal               | Decimal      | Valor total para compra tradicional. Precisão de at
 4 dígitos decimais; Ex: 100.0001;
 óddblddídd                                                    |
|  1.1  | situacaoCompraItemid     | Inteiro      | Código da tabela de domínio Situação do item da 
 Compra/Edital/Aviso                                                    |
|  1.11 | criterioJulgamentoId     | Inteiro      | Código da tabela de domínio Critério de julgamento |
|  1.12 | criterioJulgamentoNome   | Texto(30)    | Nome do Critério de Julgamento                     |
|  1.13 | dataInclusao             | Data         | Data de inclusão do registro do item no PNCP       |
|  1.14 | dataAtualizacao          | Data         | Data da última atualização do registro do item no 
 PNCP                                                    |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.14. Consultar Item de uma Compra/Edital/Aviso

Serviço para consultar um item específico de uma compra/edital/aviso.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| Endpoint 
 /v1/orgaos/{cnpj}
 /compras/{ano}
 /{sequencial}
 /itens/{numeroItem}                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" --
 data "@/home/objeto.json"                           | curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" --
 data "@/home/objeto.json"                           | curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" --
 data "@/home/objeto.json"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo      | Tipo       | Obrigatório    | Descrição                    |
|-------|------------|------------|----------------|------------------------------|
|    1  | cnpj       | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    2  | ano        | Inteiro    | Sim            | Ano da compra                |
|    3  | sequencial | Inteiro    | Sim            | inserida no PNCP             |
|    4  | numeroItem | Inteiro    | Sim            | Número do item na compra     |

## Dados de retorno

|   Id  | Campo                    | Tipo         | Descrição                                          |
|-------|--------------------------|--------------|----------------------------------------------------|
|    1  | numeroItem               | Inteiro      | Número do item na compra (único e sequencial 
 crescente)                                                    |
|    2  | materialOuServico        | Texto (1)    | Domínio: M - Material; S - Serviço;                |
|    3  | tipoBeneficioId          | Inteiro      | Código da tabela de domínio Tipo de benefício
 Incentivo fiscal PPB (Processo Produtivo Básico);                                                    |
|    4  | incentivoProdutivoBasico | Boleano      | Incentivo fiscal PPB (Processo Produtivo Básico); 
 true - Possui o incentivo; false - Não possui o 
 incentivo;                                                    |
|    5  | descricao                | Texto (2048) | Descrição para o produto ou serviço;               |
|    6  | quantidade               | Decimal      | Quantidade do item da compra. Precisão de até 4 
 dígitos decimais; Ex: 1.0001;                                                    |
|    7  | unidadeMedida            | Texto (30)   | Unidade de medida                                  |
|    8  | valorUnitarioEstimado    | Decimal      | Valor unitário estimado. Precisão de até 4 dígitos 
 decimais; Ex: 100.0001;
 Valor total para compra tradicionalPrecisão de até                                                    |
|    9  | valorTotal               | Decimal      | 4 dígitos decimais; Ex: 100.0001;
 Código da tabela de domínio Situação do item da                                                    |
|   10  | situacaoCompraItemid     | Inteiro      | Código da tabela de domínio Situação do item da 
 Compra/Edital/Aviso                                                    |
|   11  | criterioJulgamentoId     | Inteiro      | Código da tabela de domínio Critério de julgamento |
|   12  | criterioJulgamentoNome   | Texto(30)    | Nome do Critério de Julgamento                     |
|   13  | dataInclusao             | Data         | Data de inclusão do registro do item no PNCP       |
|   14  | dataAtualizacao          | Data         | Data da última atualização do registro do item no 
 PNCP                                                    |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.15. Inserir Resultado do Item de uma Compra/Edital/Aviso

Serviço para inserir o resultado do item de uma compra/edital/aviso. O resultado possui as informações do fornecedor/fornecedor vencedor e valores dos itens. Fica impedida a inclusão do resultado caso a compra/edital/aviso não possua documento/arquivo ativo vinculado a ela no PNCP .

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload   |
|-------------|----------------|----------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}/iten
 s/{numeroItem}/resultad
 os             | POST           | {
  "quantidadeHomologada": 1,
  "valorUnitarioHomologado": 100.00,
  "valorTotalHomologado": 100.00,
  "percentualDesconto": 0,
  "tipoPessoaId": "PJ",
  "niFornecedor": "10000000000010",
  "nomeRazaoSocialFornecedor": "Fornecedor para exemplo"
  "porteFornecedorId": 3,
  “naturezaJuridicaId”: “2062”,
  "codigoPais": "BRA",
  "indicadorSubcontratacao": false,                      |

## Exemplo Requisição (cURL)

curl -k -X POST --header "Authorization: Bearer access\_token"

"${BASE\_URL}/v1/orgaos/10000000000003/compras/2021/1/itens/1/resultados" -H "accept: */*" -H "Content -Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano}, {sequencial} e {numeroItem} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo                   | Tipo        | Obrigatório    | Descrição                    |
|-------|-------------------------|-------------|----------------|------------------------------|
|    1  | cnpj                    | Texto (14)  | Sim            | Cnpj do órgão dono da compra |
|    2  | ano                     | Inteiro     | Sim            | Ano da compra
 Sequencial da compra                              |
|    3  | sequencia               | Inteiro     | Sim            | qp
 no PNCP;                              |
|    4  | numeroItem              | Inteiro     | Sim            | Número do item na compra
 Quantidade do item homologada                              |
|    5  | quantidadeHomologada    | Decimal     | Sim            | Quantidade do item homologada 
 para o fornecedor. Precisão de 4 
 dígitos decimais; Ex: 1.0000;
 Valor unitário do item homologado                              |
|    6  | valorUnitarioHomologado | Decimal     | Sim            | para o fornecedor. Precisão de 4 
 dígitos decimais; Ex: 100.0000;
 Valor total do item homologado para                              |
|    7  | valorTotalHomologado    | Decimal     | Sim            | g
 decimais; Ex: 1000.0000;
 Percentual de descontoPrecisão de                              |
|    8  | percentualDesconto      | Decimal     | Não            | Percentual de desconto. Precisão d
 4 dígitos decimais; Ex: 10.0000;
 PJ - Pessoa jurídica; PF - Pessoa                              |
|    9  | tipoPessoaId            | Texto (2)   | Sim            | PJ - Pessoa jurídica; PF - Pessoa 
 física; PE - Pessoa estrangeira;
 Número de identificação do 
 fornecedor; CNPJ, CPF ou                              |
|   10  | niFornecedor            | Texto (30)  | Sim            | ç
 fornecedor; CNPJ, CPF ou 
 identificador de empresa 
 estrangeira;                              |
|    11 | nomeRazaoSocialFornece
 dor                         | Texto (100) | Sim            | Nome ou razão social do fornecedor
 Porte do fornecedor: 1 - ME; 2 - EPP;                              |
|   12  | porteFornecedorId       | Inteiro     | Não            | Porte do fornecedor: 1 - ME; 2 - EPP; 
 3 - Demais;
 Código da tabela de domínio                              |
|   13  | naturezaJuridicaId      | Inteiro     | Não            | Código da tabela de domínio 
 Natureza jurídica                              |

|   14  | codigoPais              | Texto (3)    | Não   | fornecedor; Ex: BRA - para 
 fornecedores do Brasil;
 Indicador de sub-contratação do    |
|-------|-------------------------|--------------|-------|---|
|   15  | indicadorSubcontratacao | Booleano     | Sim   | Indicador de sub-contratação do 
 item; false - Não haverá 
 subcontratação; true - Haverá 
 subcontratação de fornecedor;   |
|   16  | ordemClassificacaoSrp   | Inteiro      | Não   | Ordem de classificação do 
 fornecedor na licitação/compra
 dlddhl   |
|   17  | dataResultado           | Data         | Sim   | Data do resultado da homologação 
 do item   |

## Dados de retorno

|   Id  | Campo    | Tipo        | Descri                          |
|-------|----------|-------------|---------------------------------|
|    1  | location | Texto (255) | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

access-control -allow -origin: *

cache -control: no -cache,no-store,max-age=0,must-revalidate content -length: 0

date: ?

expires: ?

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/compras/2021/1/itens/1/resultados/1

pragma: no -cache strict -transport-security: max-age=?

x-content -type-options: nosniff x-firefox -spdy: ?

x-frame -options: DENY

x-xss-protection: ?; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.16. Retificar Resultado do Item de uma Compra/Edital/Aviso

Serviço para retificar um resultado do item de uma compra/edital/aviso, ou para alterar a situação de um resultado do item conforme tabela de domínio de situação do Resultado do item de uma compra. Importante lembrar que na Retificação todas as informações terão que ser enviadas novamente, não apenas as que sofreram alteração. Fica impedida a retificação do resultado caso a compra/edital/aviso não possua documento/arquivo ativo vinculado a ela no PNCP .

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload   |
|-------------|----------------|----------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}/iten
 s/{numeroItem}/resultad
 os/{sequencialResultado}             |                | uantidadeHomologada": 1,
 lorUnitarioHomologado": 100.00,
 lorTotalHomologado": 100.00,
 ercentualDesconto": 0,
 oPessoaId": "PJ",
 Fornecedor": "10000000000010",
 omeRazaoSocialFornecedor": "Fornecedor para exemplo",
 orteFornecedorId": 3,
 aturezaJuridicaId”: “2062”,
 digoPais": "BRA",
 dicadorSubcontratacao": false,
 demClassificacaoSrp": 1,
 ataResultado": "2021-07-26",
 ataCancelamento": "",                      |

## Exemplo Requisição (cURL)

curl -k -X PUT --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/compras/2021/1/itens/1/resultados" -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} , {numeroItem} e {sequencialResultado} na URL.

Manual de Integração PNCP– Versão 2.2.1

| Id    | Campo                  | Tipo        | Obrigatório    | Descrição                           |
|-------|------------------------|-------------|----------------|-------------------------------------|
| 1     | cnpj                   | Texto (14)  | Sim            | Cnpj do órgão dono da compra        |
| 2     | ano                    | Inteiro     | Sim            | Ano da compra
 Sequencial da compra n                                     |
| 3     | sequencial             | Inteiro     | Sim            | qp
 inserida no PNCP                                     |
| 4     | numeroItem             | Inteiro     | Sim            | e sequencial crescente)
 Sequencial do resultado do item da 
 compra no PNCP; Número 
 sequencial gerado no momento                                     |
| 5     | sequencialResultado    | Inteiro     | Sim            | sequencial gerado no momento 
 que o resultado do item foi inserido 
 no PNCP
 dddhld                                     |
| 6     | quantidadeHomologada   | Decimal     | Sim            | Quantidade do item homologada 
 para o fornecedor                                     |
| 7     | valorUnitarioHomologad | Decimal     |                | Valor unitário do item homologado 
 para o fornecedor. Precisão de 4 
 dígitos decimais; Ex: 1000000;                                     |
| 7     | o                      | Decimal     | Sim            | dígitos decimais; Ex: 100.0000;
 Valor total do item homologado                                     |
|       | valorTotalHomologado   | Decimal     | Sim            | para o fornecedor. Precisão de 4 
 dígitos decimais; Ex: 1000.0000;                                     |
| 8     | percentualDesconto     | Decimal     | Não            | de 4 dígitos decimais; Ex: 10.0000; |
| 9     | tipoPessoaId           | Texto (2)   | Sim            | física; PE - Pessoa estrangeira;
 Número de identificação do 
 fornecedor; CNPJ, CPF ou                                     |
| 10    | niFornecedor           | Texto (30)  | Sim            | fornecedor; CNPJ, CPF ou 
 identificador de empresa 
 estrangeira;                                     |
| 11    | edor                   | Texto (100) | Sim            | Nome ou razão social do 
 fornecedor
 Porte do fornecedor: 1 ME; 2                                     |
| 12    | porteFornecedorId      | Inteiro     | Não            | Porte do fornecedor: 1 - ME; 2 -
 EPP; 3 - Demais;                                     |

|   13  | naturezaJuridicaId      | Inteiro     | Não   | Código da tabela de domínio 
 Natureza jurídica
 Código ISO para o país do 
 fdEBRA    |
|-------|-------------------------|-------------|-------|---|
|   14  | codigoPais              | Texto (3)   | Não   | fornecedor; Ex: BRA - para 
 fornecedores do Brasil;
 Indicador de sub-contratação do 
 item; false - Não haverá 
 subcontratação; true - Haverá   |
|   15  | indicadorSubcontratacao | Booleano    | Sim   | item; false - Não haverá 
 subcontratação; true - Haverá 
 subcontratação de fornecedor;   |
|   16  | ordemClassificacaoSrp   | Inteiro     | Não   | Ordem de classificação do 
 fornecedor na licitação/compra   |
|   17  | dataResultado           | Data        | Sim   | Data do resultado da homologação 
 do item   |
|   18  | dataCancelamento        | Data e Hora | Não   | Data de cancelamento do resultado 
 item   |
|   19  | motivoCancelamento      | Texto (200) | Não   | Observação com o motivo do 
 cancelamento do resultado item   |
|    20 | situacaoCompraItemRes
 ultadoId                         | Inteiro     | Sim   | Código conforme tabela Situação 
 do Resultado do Item   |
|   21  | justificativa           | Texto (255) | Não   | Motivo/justificativa para a 
 retificação dos atributos do 
 resultado de um item da compra.   |

- ** Para cancelamento do Resultado informar situação do resultado igual a 2, data e motivo do cancelamento junto com os outros dados do resultado.

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | Up Date               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.17. Consultar Resultados de Item de uma Compra/Edital/Aviso

Serviço para recuperar os resultados cadastrados para um item de uma compra/edital/aviso.

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload   |
|-------------|----------------|----------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}/iten
 s/{numeroItem}/resultad
 os             | GET            | plica                |
| os          |                |                      |

## Exemplo Requisição (cURL)

curl -k -X GET --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/compras/2021/1/itens/1/resultados" -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} e {numeroItem} na URL.

|   Id  | Campo      | Tipo       | Obrigatório    | Descrição                    |
|-------|------------|------------|----------------|------------------------------|
|    1  | cnpj       | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    2  | ano        | Inteiro    | Sim            | Ano da compra                |
|    3  | sequencial | Inteiro    | Sim            | qg
 momento que a compra foi 
 inserida no PNCP                              |
|    4  | numeroItem | Inteiro    | Sim            | Número do item na compra (único 
 e sequencial crescente)                              |

## Dados de retorno

| Id    | Campo                   | Tipo                | Descrição                                         |
|-------|-------------------------|---------------------|---------------------------------------------------|
| 1     | Lista de Resultados     | Lista de Resultados | Agrupador de Resultados de um Item da Compra      |
| 1.1   | numeroItem              | Inteiro             | Número do item na compra (único e sequencial 
 crescente) a que está relacionado o Resultado                                                   |
| 1.2   | sequencialResultado     | Inteiro             | o resultado do item foi inserido no PNCP          |
| 1.3   | quantidadeHomologada    | Decimal             | Precisão de até 4 dígitos decimais; Ex: 1.0001;
 Valor unitário do item homologado para o                                                   |
| 1.4   | valorUnitarioHomologado | Decimal             | Valor unitário do item homologado para o 
 fornecedor. Precisão de até 4 dígitos decimais; Ex: 
 100.0001;                                                   |
| 1.5   | percentualDesconto      | Decimal             | Percentual de desconto. Precisão de até 4 dígitos 
 decimais; Ex: 10.0001;                                                   |
| 1.6   | tipoPessoa              | Texto (2)           | PJ - Pessoa jurídica; PF - Pessoa física; PE - Pessoa 
 estrangeira;                                                   |
| 1.7   | niFornecedor            | Texto (30)          | Número de identificação do fornecedor; CNPJ, CP
 ou identificador de empresa estrangeira;                                                   |
|       | nomeRazaoSocialFornece  |                     |                                                   |
| 1.8   | dor                     | Texto (10           | Nome ou razão social do fornecedor                |
| 1.9   | porteFornecedorId       | Inteiro             | Porte do fornecedor: 1 - ME; 2 - EPP; 3 - Demais; |
| 1.10  | porteFornecedorNome     | Texto(30)           | Texto porte do fornecedor                         |
| 1.11  | naturezaJuridicaId      | Inteiro             | Código da Natureza Jurídica do fornecedor         |
| 1.12  | naturezaJuridicaNome    | Texto (100)         | Natureza Jurídica do fornecedor                   |
| 1.13  | codigoPais              | Texto (3)           | Código ISO para o país do fornecedor; Ex: BRA - para 
 fornecedores do Brasil;                                                   |
| 1.14  | indicadorSubcontratacao | Booleano            | ndicador de sub-contratação do item; false - Não 
 haverá subcontratação; true - Haverá 
 ubcontratação de fornecedor;
 Ordem de classificação do fornecedor na                                                   |
| 1.15  | ordemClassificacaoSrp   | Inteiro             | ç
 licitação/compra                                                   |
| 1.16  | dataResultado           | Data                | Data do resultado da homologação do item          |
| 1.16  | dataResultado           | Data                | Data do resultado da homologação do item          |

|   1.17  | dataCancelamento    | Data e Hora    | Data de cancelamento do resultado item   |
|---------|---------------------|----------------|------------------------------------------|
|    1.18 | motivoCancelamento  | Texto (200)    | Observação com o motivo do cancelamento do 
 resultado item                                          |
|    1.19 | situacaoCompraItemResu
 ltadoId                     | Inteiro        | Código conforme tabela Situação do Resultado do 
 Item                                          |
|    1.2  | situacaoCompraItemResu
 ltadoNome                     | Texto(30)      | Texto situação conforme tabela Situação do 
 Resultado do Item                                          |
|    1.21 | dataInclusao        | Data e Hora    | Data da inclusão do registro do resultado do item 
 no PNCP                                          |
|    1.22 | dataAtualizacao     | Data e Hora    | Data da última atualização do registro do resultado 
 do item no PNCP                                          |
|    1.23 | numeroControlePNCPCo
 mpra                     | Texto(30)      | Número de Controle PNCP da Compra        |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.18. Consultar um Resultado específico de Item de uma Compra/Edital/Aviso

Serviço para consultar os dados de um resultado específico de um item da compra/edital/aviso.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}/iten
 s/{numeroItem}/resultad
 os/{sequencialResultado}                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens/1/resultados/1" -H "accept: */*" -H "Content-Type: 
 application/json" --data "@/home/objeto.json"                           | curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens/1/resultados/1" -H "accept: */*" -H "Content-Type: 
 application/json" --data "@/home/objeto.json"                           | curl -k -X GET --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/compras/2021/1/itens/1/resultados/1" -H "accept: */*" -H "Content-Type: 
 application/json" --data "@/home/objeto.json"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial}, {numeroItem} e {sequencialResultado} na URL.

|   Id  | Campo               | Tipo       | Obrigatório    | Descrição                    |
|-------|---------------------|------------|----------------|------------------------------|
|    1  | cnpj                | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    2  | ano                 | Inteiro    | Sim            | Ano da compra                |
|    3  | sequencial          | Inteiro    | Sim            | Sequencial da compra no PNCP; 
 Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP                              |
|    4  | numeroItem          | Inteiro    | Sim            | Número do item na compra (único 
 e sequencial crescente)
 Sequencial do resultado no PNCP;                              |
|    5  | sequencialResultado | Inteiro    | Sim            | q
 Sequencial do resultado no PNCP; 
 Número sequencial gerado no 
 momento que o resultado do item                              |

## Dados de retorno

| Id    | Campo                   | Tipo        | Descrição                                         |
|-------|-------------------------|-------------|---------------------------------------------------|
| 1     | numeroItem              | Inteiro     | Número do item na compra (único e sequencial 
 crescente) a que está relacionado o Resultado
 Sequencial do resultado do item da compra no                                                   |
| 2     | sequencialResultado     | Inteiro     | o resultado do item foi inserido no PNCP
 Quantidade do item homologada para o fornecedor                                                   |
| 3     | quantidadeHomologada    | Decimal     | Quantidade do item homologada para o fornecedor
 Precisão de até 4 dígitos decimais; Ex: 1.0001;
 Valor unitário do item homologado para o                                                   |
| 4     | valorUnitarioHomologado | Decima      | fornecedor. Precisão de até 4 dígitos decimais; Ex: 
 100.0001;
 Percentual de desconto. Precisão de até 4 dígitos                                                   |
| 5     | percentualDesconto      | Decima      | decimais; Ex: 10.0001;                            |
| 6     | tipoPessoa              | Texto (2)   | PJ - Pessoa jurídica; PF - Pessoa física; PE - Pessoa 
 estrangeira;                                                   |
| 7     | niForneced              | Texto (30)  | Número de identificação do fornecedor; CNPJ, CP
 ou identificador de empresa estrangeira;                                                   |
|       | nomeRazaoSocialFornece  |             |                                                   |
| 8     | dor                     | Texto (100  | Nome ou razão social do fornecedor                |
| 9     | porteFornecedorId       | Inteiro     | Porte do fornecedor: 1 - ME; 2 - EPP; 3 - Demais; |
| 10    | porteFornecedorNome     | Texto(30)   | Texto porte do fornecedor                         |
| 11    | naturezaJuridicaId      | Inteiro     | Código da Natureza Jurídica do fornecedor         |
| 12    | naturezaJuridicaNome    | Texto (100) | Natureza Jurídica do fornecedor                   |
| 13    | codigoPais              | Texto (3)   | Código ISO para o país do fornecedor; Ex: BRA - para 
 fornecedores do Brasil;
 Indicador de subcontratação do item; false Não                                                   |
|       |                         | Texto (3)   | fornecedores do Brasil;
 Indicador de sub-contratação do item; false - Não 
 haverá subcontratação; true - Haverá                                                   |
| 14    | indicadorSubcontratacao | Booleano    | ndicador de subcontratação do item; false Não 
 haverá subcontratação; true - Haverá 
 ubcontratação de fornecedor;
 Ordem de classificação do fornecedor na                                                   |
| 15    | ordemClassificacaoSrp   | Inteiro     | licitação/compra                                  |
| 16    | dataResultado           | Data        | Data do resultado da homologação do item          |
| 17    | dataCancelamento        | Data e Hora | Data de cancelamento do resultado item            |

## Manual de Integração PNCP– Versão 2.2.1

|   18  | motivoCancelamento    | Texto (200)   | Observação com o motivo do cancelamento do 
 resultado item                                   |
|-------|-----------------------|---------------|-----------------------------------|
|    19 | situacaoCompraItemResu
 ltadoId                       | Inteiro       | Código conforme tabela Situação do Resultado do 
 Item                                   |
|    20 | situacaoCompraItemResu
 ltadoNome                       | Texto(30)     | Texto situação conforme tabela Situação do 
 Resultado do Item                                   |
|   21  | dataInclusao          | Data e Hora   | Data da inclusão do registro do resultado do item 
 no PNCP                                   |
|   22  | dataAtualizacao       | Data e Hora   | Data da última atualização do registro do resultado 
 do item no PNCP                                   |
|    23 | numeroControlePNCPCo
 mpra                       | Texto(30)     | Número de Controle PNCP da Compra |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.3.19. Consultar Histórico da Compra

Serviço que permite consultar todos os eventos de uma Compra específica, dos Itens, dos Resultados e de seus documentos/arquivos.

## Detalhes da Requisição

| Endpoint                  | Método                    | Exemplo de                | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compra
 s/{ano}/{sequencial}/hist
 orico                           | GET                       | Não se aplica             |                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl                      | --heade                   | Bearer                    | access_token"             |
| X GET header Authorization: Bearer access_token 
 v1/orgaos/10000000000003/compras/2021/1/historico" -H "accept: */*"                           | X GET header Authorization: Bearer access_token 
 v1/orgaos/10000000000003/compras/2021/1/historico" -H "accept: */*"                           | X GET header Authorization: Bearer access_token 
 v1/orgaos/10000000000003/compras/2021/1/historico" -H "accept: */*"                           | X GET header Authorization: Bearer access_token 
 v1/orgaos/10000000000003/compras/2021/1/historico" -H "accept: */*"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo         | Tipo       | Descrição                    |
|-------|---------------|------------|------------------------------|
|    1  | cnpj          | Texto (14) | Cnpj do órgão dono da compra |
|    2  | ano           | Inteiro    | Ano da compra                |
|    3  | sequencial    | Inteiro    | Sequencial da compra no PNCP; Número sequencia
 gerado no momento que a compra foi inserida no 
 PNCP                              |
|    4  | pagina        | Inteiro    | Utilizado para paginação dos itens. Número da 
 página.                              |
|    5  | tamanhoPagina | Inteiro    | Utilizado para paginação dos itens. Quantidade 
 itens por página.                              |

## Dados de retorno

| Id    | Campo                   | Tipo             | Descrição                                      |
|-------|-------------------------|------------------|------------------------------------------------|
| 1     | Lista de Eventos        | Lista de Eventos |                                                |
| 1.1   | compraOrgaoCnpj         | String           | Cnpj do órgão dono da compra                   |
| 1.2   | compraAno               | Inteiro          | Ano da compra                                  |
| 1.3   | compraSequencial        | Inteiro          | qp; q
 gerado no momento que a compra foi inserida no 
 PNCP;
 Data e hora da operação de inclusãoretificação ou                                                |
| 1.4   | ao                      | Data/Hora        | Data e hora da operação de inclusão, retificação ou 
 exclusão do recurso.                                                |
| 1.5   | tipoLogManutencao       | Inteiro          | Código do tipo de operação efetuada.           |
|       | tipoLogManutencaoNom    |                  | Nome da operação efetuada. Domínio:            |
| 1.6   | e                       | String           | pç
 0 - Inclusão; 1 - Retificação; 2 - Exclusão;                                                |
| 1.7   | categoriaLogManutencao  | Inteiro          | Código do tipo de recurso que sofreu a operação.
 Nome do recurso que sofreu a operação. Domínio:                                                |
|       | categoriaLogManutencao  |                  | Nome do recurso que sofreu a operação. Domínio:
 1 - Compra; 2 - Ata; 3 - Contrato; 4 - Item de Compra; 
 5 - Resultado de Item de Compra; 6 - Documento de 
 Compra; 7 - Documento de Ata; 8 - Documento de 
 Contrato; 9 - Termo de Contrato; 10 - Documento de 
 TdCtt;                                                |
| 1.8   | Nome                    | String           | Contrato; 9 Termo de Contrato; 10 Documento de 
 Termo de Contrato;
 Número do item na compraRetornado caso                                                |
| 1.9   | itemNumero              | Inteiro          | Número do item na compra. Retornado caso 
 categoriaLogManutencao = 4.                                                |
| 1.10  | itemResultadoNumero     | Inteiro          | Número do item da compra. Retornado caso 
 categoriaLogManutencao = 5.
 Sequencial do resultado do item da compra no PNCP                                                |
| 1.11  | itemResultadoSequencial | Inteiro          | qp
 Retornado caso categoriaLogManutencao = 5.
 Sequencial do documento da compra no PNCP                                                |
| 1.12  | documentoSequencial     | Inteiro          | Sequencial do documento da compra no PNCP. 
 Retornado caso categoriaLogManutencao = 6.
 dddf                                                |
| 1.13  | documentoTipo           | String           | Nome do tipo de documento conforme PNCP. 
 Retornado caso categoriaLogManutencao = 6.
 Título referente ao arquivo/documento. Retornado                                                |
| 1.14  | documentoTitulo         | String           | q
 caso categoriaLogManutencao = 6.                                                |
| 1.15  | usuarioNome             | String           | Nome do Usuário/Sistema que efetuou a operação |

## 1.16 justificativa

String

Motivo/Justificativa da operação de retificação ou exclusão do recurso.

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4. Serviços de Ata

## 6.4.1. Inserir Ata de Registro de Preço

Serviço que permite inserir uma ata de Registro de Preço no PNCP referente a uma compra.

## Detalhes da Requisição

| Endpoint                                                      | Método HTTP                                                   | Exemplo de Payload                                            |
|---------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------------|
| /v1/orgaos/{cnpj}/compra
 s/{anoCompra}/{sequenci
 alCompra}/atas                                                               | POST                                                          | {
  "numeroAtaRegistroPreco": "1/2021",
  "anoAta": 2021,
  "dataAssinatura": “2021-07-21",
  "dataVigenciaInicio": “2021-07-21",
  "dataVigenciaFim": “2022-07-21"
 }                                                               |
| Exemplo Requisição (cURL)                                     | Exemplo Requisição (cURL)                                     | Exemplo Requisição (cURL)                                     |
| curl -k -X POST --header "Authorization: Bearer access_token" | curl -k -X POST --header "Authorization: Bearer access_token" | curl -k -X POST --header "Authorization: Bearer access_token" |
| "${BASEURL}/1//10000000000003//2021/1/t" H "Atliti/j” H       | "${BASEURL}/1//10000000000003//2021/1/t" H "Atliti/j” H       | "${BASEURL}/1//10000000000003//2021/1/t" H "Atliti/j” H       |
| Content-Type: application/json -d {
 "numeroAtaRegistroPreco": "string"                                                               | Content-Type: application/json -d {
 "numeroAtaRegistroPreco": "string"                                                               | Content-Type: application/json -d {
 "numeroAtaRegistroPreco": "string"                                                               |
| "numeroAtaRegistroPreco": "string",
  "anoAta": 0,                                                               | "numeroAtaRegistroPreco": "string",
  "anoAta": 0,                                                               | "numeroAtaRegistroPreco": "string",
  "anoAta": 0,                                                               |
| "dataAssinatura": "2021-07-27",
  "dataVigenciaInicio": "2021-07-27",                                                               | "dataAssinatura": "2021-07-27",
  "dataVigenciaInicio": "2021-07-27",                                                               | "dataAssinatura": "2021-07-27",
  "dataVigenciaInicio": "2021-07-27",                                                               |
| "dataVigenciaInicio": "2021-07-27",                           | "dataVigenciaInicio": "2021-07-27",                           | "dataVigenciaInicio": "2021-07-27",                           |
| "dataVigenciaInicio": "2021-07-27",
  "dataVigenciaFim": "2021-07-27"                                                               | "dataVigenciaInicio": "2021-07-27",
  "dataVigenciaFim": "2021-07-27"                                                               | "dataVigenciaInicio": "2021-07-27",
  "dataVigenciaFim": "2021-07-27"                                                               |
| dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               | dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               | dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| datagecaco: 00,
  "dataVigenciaFim": "2021-07-27"                                                               | datagecaco: 00,
  "dataVigenciaFim": "2021-07-27"                                                               | datagecaco: 00,
  "dataVigenciaFim": "2021-07-27"                                                               |
| dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               | dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               | dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               |
| dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               | dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               | dataVigenciaInicio: 20210727,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               | g,
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |
| g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               | g
  "dataVigenciaFim": "2021-07-27"                                                               |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra} e {sequencialCompra} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo              | Tipo       | Obrigatório    | Descrição                    |
|-------|--------------------|------------|----------------|------------------------------|
|    1  | cnpj               | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    2  | anoCompra          | Inteiro    | Sim            | Ano da compra                |
|    3  | sequencialCompra   | Inteiro    | Sim            | Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;                              |
|     4 | numeroAtaRegistro
 Preco                    | Texto (50  | Sim            | Número da ata no sistema de 
 origem                              |
|    5  | anoAta             | Inteiro    | Sim            | Ano da ata                   |
|    6  | dataAssinatura     | Data       | Sim            | Informar a data de assinatura da 
 ata                              |
|    7  | dataVigenciaInicio | Data       | Sim            | Informar a data de início de 
 vigência da ata                              |
|    8  | dataVigenciaFim    | Data       | Sim            | Informar a data de fim de vigência 
 da ata                              |

## Dados de retorno

|   Id  | Campo    | Tip         | Descriç                         |
|-------|----------|-------------|---------------------------------|
|    1  | location | Texto (255) | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

access-control -allow -origin: *

cache -control: no -cache,no-store,max-age=0,must-revalidate content -length: 0

date: ?

expires: ?

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/compras/2021/1/atas/1

pragma: no -cache strict -transport-security: max-age=?

x-content -type-options: nosniff x-firefox -spdy: ?

x-frame -options: DENY

x-xss-protection: ?; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           401  | Unauthorized          | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4.2. Retificar Ata de Registro de Preço

Serviço que permite retificar os dados de uma ata de Registro de Preço.

Importante lembrar que na Retificação todas as informações terão que ser enviadas novamente, não apenas as que sofreram alteração.

## Detalhes da Requisição

| Endpoint    | Método 
 HTTP           | Exemplo de Payload                          |
|-------------|-----------|---------------------------------------------|
| /v1/orgaos/{cnpj}/compras/{anoC
 ompra}/{sequencialCompra}/atas
 /{sequencialAta}             | PUT       | Para retificação dos dados da ata informe todos 
 os campos.
 {
  "numeroAtaRegistroPreco": "1/2021",
  "anoAta": 2021,
  "dataAssinatura": “2021-07-01",
  "dataInicioVigencia": “2021-07-01",
  "dataFimVigencia": “2022-07-01",
  "justificativa": "motivo/justificativa para retificação 
 da ata"
 }                                             |
|             | Exemplo R | cancelamento da ata"
 }
 Exemplo Requisição (cURL)                                             |
|             |           | {
  "numeroAtaRegistroPreco": "1/2021",
  "anoAta": 2021,
  "dataAssinatura": “2021-07-01",
  "dataInicioVigencia": “2021-07-01",
  "dataFimVigencia": “2022-07-01",                                             |
|             |           | ,
  "dataInicioVigencia": “2021-07-01",
 "dataFimVigencia": “2022-07-01"                                             |
|             |           | "dataInicioVigencia": “2021-07-01",
  "dataFimVigencia": “2022-07-01",
  "justificativa": "motivo/justificativa para retificação 
 da ata"                                             |
|             |           | g
  "dataFimVigencia": “2022-07-01",
 "cancelado": true                                             |
|             |           | cancelado: true,
  "dataCancelamento": "20210801",                                             |
|             |           | ,
  "justificativa": "motivo/justificativa para                                             |
|             |           | justificativa: motivo/justificativa para 
 cancelamento da ata"                                             |
|             |           | jj
 cancelamento da ata"                                             |
|             |           | cancelamento da ata"                        |
|             |           | cancelamento da ata
 }                                             |
|             |           | "numeroAtaRegistroPreco": "1/2021",         |
|             |           | "anoAta": 2021,
 "dataAssinatura": “20210701"                                             |
|             |           | ,
  "dataInicioVigencia": “2021-07-01",                                             |
|             |           | dataInicioVigencia: 20210701,
 "dataFimVigencia": “2022-07-01",                                             |
|             |           | "cancelado": true,                          |
|             |           | ,
  "dataCancelamento": "20210801",                                             |
|             |           | "justificativa": "motivo/justificativa para |
|             |           | jjp
 cancelamento da ata"                                             |
|             |           | jjp
 cancelamento da ata"                                             |

## curl -X 'PUT' \

- 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas/1' \ -H 'accept: */*' \
- -H 'Authorization: Bearer &lt;TOKEN\_AUTORIZACAO&gt;' \
- -H 'Content -Type: application/json' \
- -d '@/home/objeto.json'

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra}, {sequencialCompra} e {sequencialAta} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo              | Tipo        | Obrigatório    | Descrição                    |
|-------|--------------------|-------------|----------------|------------------------------|
|    1  | cnpj               | Texto (14)  | Sim            | Cnpj do órgão dono da compra |
|    2  | anoCompra          | Inteiro     | Sim            | Ano da compra                |
|    3  | sequencialCompra   | Inteiro     | Sim            | Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;
 Sequencial da ata no PNCP; 
 Número sequencial gerado no                              |
|    4  | sequencialAta      | Inteiro     | Sim            | Número sequencial gerado no 
 momento que a ata foi inserida no 
 PNCP;                              |
|     5 | numeroAtaRegistro
 Preco                    | Texto (50)  | Sim            | Número da ata no sistema de 
 origem                              |
|    6  | anoAta             | Inteiro     | Sim            | Ano da ata                   |
|    7  | dataAssinatura     | Data        | Sim            | ata
 fddiíid                              |
|    8  | dataInicioVigencia | Data        | Sim            | Informar a data de início de 
 vigência da ata
 Informar a data de fim de vigênci                              |
|    9  | dataFimVigencia    | Data        | Sim            | g
 da ata
 Indicdor de cncelmento dt;                              |
|   10  | cancelado          | Booleano    | Não            | Indicador de cancelamento da ata; 
 se omitido, assume valor “Falso” 
 Informar a data de cancelamento                              |
|   11  | dataCancelamento   | Data        | Não            | da ata caso o indicador de 
 cancelamento seja verdadeiro                              |
|   12  | justificativa      | Texto (255) | Não            | Motivo/justificativa para a 
 retificação dos atributos da ata.                              |

## Dados de retorno

|   Id  | Campo    | Tipo    | Descrição                                       |
|-------|----------|---------|-------------------------------------------------|
|    1  |          | JSON    | ados da Ata de Registro de Preço após alteração |

## Exemplo de Retorno

Retorno (headers HTTP):

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

access-control -allow -origin: * cache -control: no -cache,no-store,max-age=0,must-revalidate connection: keep-alive content -type: application/json date: Tue,27 Jul 2021 22:50:21 GMT expires: 0 keep-alive: timeout=60 pragma: no -cache transfer -encoding: chunked x-content -type-options: nosniff x-frame -options: DENY x-xss-protection: 1; mode=block Retorno (corpo da requisição) { "numeroAtaRegistroPreco": "1/2021", "anoAta": 2021, "dataAssinatura": "2021 -07 -27", "dataVigenciaInicio": "2021-07-27", "dataVigenciaFim": "2022-07-27", "dataCancelamento": null, "cancelado": false, "dataPublicacaoPncp": "2021-07-27T19:45:57.969+00:00", "dataInclusao": "2021 -07 -27T19:45:57.969+00:00", "dataAtualizacao": "2021 -07 -27T22:50:20.352+00:00", "sequencialAta": 1, "numeroControlePNCP": "00394460000141 -1 -000001/2021 -000001", "orgaoEntidade": { "cnpj": "00394460000141", "razaoSocial": "Ministério da Economia", "poderId": "E", "esferaId": "F" }, "orgaoSubRogado": null, "unidadeOrgao": { "ufNome": "Distrito Federal", "ufSigla": "DF", "municipioId": 5570, "municipioNome": "Brasília", "codigoUnidade": "1", "nomeUnidade": "Unidade de serviços" }, "unidadeSubRogada": null, "modalidadeNome": "Leilão", "objetoCompra": "Teste Teste", "informacaoComplementarCompra": "slfkweofndfejf" }

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           401  | Unauthorized          | Erro    |
|           404  | Not Found             | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4.3. Excluir Ata de Registro de Preço

Serviço que permite remover uma ata de Registro de Preço.

## Detalhes da Requisição

| Endpoint                 | Método HTTP              | Exemplo de Payload       |
|--------------------------|--------------------------|--------------------------|
| /v1/orgaos/{cnpj}/compra
 s/{anoCompra}/{sequenci
 alCompra}/atas/{sequenc
 ialAta}                          | DELETE                   | {
  "justificativa": "motivo/justificativa para exclusão da 
 ata"
 }                          |
| xemplo Requisição (cURL) | xemplo Requisição (cURL) | xemplo Requisição (cURL) |
| url -X 'DELETE' \
 htt//llht8080/i/1//234234//2021/1/t/1' \                          | url -X 'DELETE' \
 htt//llht8080/i/1//234234//2021/1/t/1' \                          | url -X 'DELETE' \
 htt//llht8080/i/1//234234//2021/1/t/1' \                          |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra}, {sequencialCompra} e {sequencialAta} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo            | Tipo        | Obrigatório    | Descrição                    |
|-------|------------------|-------------|----------------|------------------------------|
|    1  | cnpj             | Texto (14)  | Sim            | Cnpj do órgão dono da compra |
|    2  | anoCompra        | Inteiro     | Sim            | Ano da compra                |
|    3  | sequencialCompra | Inteiro     | Sim            | Sequencial da compra no PNCP; 
 Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;                              |
|    4  | sequencialAta    | Inteiro     | Sim            | Número sequencial gerado no 
 momento que a ata foi inserida no 
 PNCP;
 Motivo/justificativa para a exclusão                              |
|    5  | justificativa    | Texto (255) | Não            | Motivo/justificativa para a exclusão 
 da ata.                              |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           204  | No Content            | Sucesso |
|           401  | Unauthorized          | Erro    |
|           404  | Not Found             | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4.4. Consultar Todas as Atas de uma Compra

Serviço que permite recuperar as atas de Registro de Preço de uma compra.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras/{anoCo
 mpra}/{sequencialCompra}/atas                           | GET                       |                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| url -X 'GET' \
 https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas' \
 -H 'accept: */*'                           | url -X 'GET' \
 https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas' \
 -H 'accept: */*'                           | url -X 'GET' \
 https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas' \
 -H 'accept: */*'                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra} e {sequencialCompra} na URL.

| Id    | Campo     | Tipo       | Obrigatório    | Descrição                     |
|-------|-----------|------------|----------------|-------------------------------|
| 1     | cnpj      | Texto (14) | Sim            | Cnpj do órgão dono da compra  |
| 2     | anoCompra | Inteiro    | Sim            | Ano da compra                 |
|       |           |            |                | Sequencial da compra no PNCP; |
|       |           |            |                | Número sequencial gerado no 
 momento que a compra foi                               |

## Dados de retorno

|    Id  | Campo                  | Tipo       | Descrição                                     |
|--------|------------------------|------------|-----------------------------------------------|
|   1    | Atas                   | Atas       | Agrupador da lista de atas                    |
|   1.1  | numeroAtaRegistroPreco | Texto (50) | Número da Ata no sistema de origem            |
|   1.2  | anoAta                 | Inteiro    | Ano da Ata                                    |
|   1.3  | dataAssinatura         | Data       | Data de assinatura da Ata                     |
|   1.4  | dataVigenciaInicio     | Data       | Data de início de vigência da Ata             |
|   1.5  | dataVigenciaFim        | Data       | Data de fim de vigência da Ata                |
|   1.6  | dataCancelamento       | Data       | Data de cancelamento da Ata                   |
|   1.7  | cancelado              | Booleano   | Indicador de cancelamento da Ata              |
|   1.8  | dataPublicacaoPncp     | Data       | Data da publicação da Ata no PNCP             |
|   1.9  | dataInclusao           | Data       | Data da inclusão do registro da Ata no PNC    |
|   1.1  | dataAtualizacao        | Data       | Data da última atualização do registro da Ata |
|   1.11 | sequencialAta          | Inteiro    | Número sequencial da Ata, gerado pelo PNCP    |
|   1.12 | numeroControle         | String     | Número de Controle PNCP da Ata                |
|   1.13 | localCompra            | String     | Município e Estado referente à Compra         |
|   1.14 | orgaoCompra            | String     | Órgão referente à Compra                      |
|   1.15 | orgaoSubRogadoCompra   | String     | Órgão sub rogado referente à Compra           |
|   1.16 | modalidadeNome         | String     | Modalidade referente à Compra                 |
|   1.17 | objetoCompra           | String     | Descrição do Objeto referente à Compra        |
| 118    | informacaoComplementarCo
 mpra                        |            | Informação Complementar do objeto referente 
 Compra                                               |

## 6.4.5. Consultar Ata de Registro de Preço

Serviço que permite recuperar uma ata específica.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras/{anoC
 ompra}/{sequencialCompra}/atas
 /{sequencialAta}                           | GET                       |                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -X 'GET' \
  'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas/1' \
  -H 'accept: */*'                           | curl -X 'GET' \
  'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas/1' \
  -H 'accept: */*'                           | curl -X 'GET' \
  'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas/1' \
  -H 'accept: */*'                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra}, {sequencialCompra} e {sequencialAta} na URL.

|   Id  | Campo            | Tipo       | Obrigatório    | Descrição                    |
|-------|------------------|------------|----------------|------------------------------|
|    1  | cnpj             | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    2  | anoCompra        | Inteiro    | Sim            | Ano da compra                |
|    3  | sequencialCompra | Inteiro    | Sim            | momento que a compra foi inserida no 
 PNCP;
 Sequencial da ata no PNCP; Número                              |
|    4  | sequencialAta    | Inteiro    | Sim            | Sequencial da ata no PNCP; Número 
 sequencial gerado no momento que a 
 ata foi inserida no PNCP;                              |

## Dados de retorno

|   Id  | Campo                  | Tipo       | Descrição                                   |
|-------|------------------------|------------|---------------------------------------------|
|    1  | numeroAtaRegistroPreco | Texto (50) | Número da Ata no sistema de origem          |
|    2  | anoAta                 | Inteiro    | Ano da Ata                                  |
|    3  | dataAssinatura         | Data       | Data de assinatura da Ata                   |
|    4  | dataVigenciaInicio     | Data       | Data de início de vigência da Ata           |
|    5  | dataVigenciaFim        | Data       | Data de fim de vigência da Ata              |
|    6  | dataCancelamento       | Data       | Data de cancelamento da Ata                 |
|    7  | cancelado              | Booleano   | Indicador de cancelamento da Ata            |
|    8  | dataPublicacaoPncp     | Data       | Data da publicação da Ata no PNCP           |
|    9  | dataInclusao           | Data       | Data da inclusão do registro da Ata no PNCP |
|   10  | dataAtualizacao        | Data       | Data da última atualização do registro da A |
|   11  | sequencialAta          | Inteiro    | Número sequencial da Ata, gerado pelo PNCP  |
|   12  | numeroControle         | String     | Número de Controle PNCP da Ata              |
|   13  | localCompra            | String     | Município e Estado referente à Compra       |
|   14  | orgaoCompra            | String     | Órgão referente à Compra                    |
|   15  | orgaoSubRogadoCompra   | String     | Órgão sub rogado referente à Compra         |
|   16  | modalidadeNome         | String     | Modalidade referente à Compra               |
|   17  | objetoCompra           | String     | Descrição do Objeto referente à Compra      |
|    18 | informacaoComplementarC
 ompra                        | String     | Informação Complementar do objeto referente à 
 Compra                                             |

## 6.4.6. Inserir Documento de uma Ata

Serviço que permite inserir/anexar documento/arquivo a uma Ata. O sistema permite o upload de arquivos com as extensões listadas na seção: Tabelas de domínio - Extensões de arquivos aceitos pelas APIs de Documento.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras/{anoCo
 mpra}/{sequencialCompra}/atas/{s
 equencialAta}/arquivos                           | POST                      |                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| rl -X 'POST' \
 https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas/1/arquivos' 
 H 'accept: */*' \                           | rl -X 'POST' \
 https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas/1/arquivos' 
 H 'accept: */*' \                           | rl -X 'POST' \
 https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/compras/2021/1/atas/1/arquivos' 
 H 'accept: */*' \                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra}, {sequencialCompra} e {sequencialAta} na URL.

|   Id  | Campo            | Tipo           | Obrigatório    | Descrição                    |
|-------|------------------|----------------|----------------|------------------------------|
|    1  | cnpj             | Texto (14)     | Sim            | Cnpj do órgão dono da compra |
|    2  | anoCompra        | Inteiro        | Sim            | Ano da compra                |
|    3  | sequencialCompra | Inteiro        | Sim            | Sequencial da compra no PNCP; 
 Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;                              |
|    4  | sequencialAta    | Inteiro        | Sim            | Número sequencial gerado no 
 momento que a ata foi inserida no 
 PNCP;                              |
|    5  | Titulo-Documento | Texto (50)     | Sim            | Título do documento          |
|    6  | Tipo-Documento   | Inteiro        | Sim            | Código da tabela de domínio Tipo 
 de documento                              |
|    7  | arquivo          | String Binária | Sim            | String binária do arquivo    |

## Dados de retorno

|   Id  | Campo    |             | De                              |
|-------|----------|-------------|---------------------------------|
|    1  | location | Texto (255) | Endereço http do recurso criado |

## Exemplo de Retorno

access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin, access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

cache -control: no -cache,no-store,max-age=0,must-revalidate location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos/1

Retorno: access-control -allow -credentials: true access-control -allow -origin: * content -length: 0 date: ? expires: 0 nome-bucket: ? pragma: no -cache strict -transport-security: max-age=? x-content -type-options: nosniff x-firefox -spdy: ?

x-frame -options: DENY

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           401  | Unauthorized          | Erro    |
|           404  | Not Found             | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4.7. Excluir Documento de uma Ata

Serviço que permite remover um documento em uma ata específica.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras/{anoCom
 pra}/{sequencialCompra}/atas/{sequ
 encialAta}/arquivos/{sequencialDocu
 mento}                           | DELETE                    | {
  "justificativa": "motivo/justificativa para 
 exclusão do documento da ata"
 }                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos/1" -H "accept: */* -H 
 "Content-Type: application/pdf"                           | curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos/1" -H "accept: */* -H 
 "Content-Type: application/pdf"                           | curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos/1" -H "accept: */* -H 
 "Content-Type: application/pdf"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra}, {sequencialCompra}, {sequencialAta} e {sequencialDocumento} na URL.

|   Id  | Campo               | Tipo        | Obrigatório    | Descrição                    |
|-------|---------------------|-------------|----------------|------------------------------|
|    1  | cnpj                | Texto (14)  | Sim            | Cnpj do órgão dono da compra |
|    2  | anoCompra           | Inteiro     | Sim            | Ano da compra                |
|    3  | sequencialCompra    | Inteiro     | Sim            | Sequencial da compra no PNCP; 
 Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;
 Sil dtPNCP                              |
|    4  | sequencialAta       | Inteiro     | Sim            | Número sequencial gerado no 
 momento que a ata foi inserida no 
 PNCP;
 Sequencial do documento da ata 
 no PNCP; Número sequencial                              |
|    5  | sequencialDocumento | Inteiro     | Sim            | q
 gerado no momento que o 
 documento da ata foi inserido no 
 PNCP;
 Motivo/justificativa para a exclusão                              |
|    6  | justificativa       | Texto (255) | Não            | Motivo/justificativa para a exclusão 
 do documento da ata.                              |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           204  | No Content            | Sucesso |
|           400  | Bad Request           | Erro    |
|           401  | Unauthorized          | Erro    |
|           404  | Not Found             | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4.8. Consultar Todos os Documentos de uma Ata

Serviço que permite consultar a lista de documentos pertencentes a uma ata específica.

## Detalhes da Requisição

| Endpoint                                                                      | Método HTTP                                                                   | Exemplo de Payload                                                            |
|-------------------------------------------------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| /v1/orgaos/{cnpj}/compras/{anoCo
 mpra}/{sequencialCompra}/atas/{s
 equencialAta}/arquivos                                                                               | GET                                                                           |                                                                               |
| Exemplo Requisição (cURL)                                                     | Exemplo Requisição (cURL)                                                     | Exemplo Requisição (cURL)                                                     |
| curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Acce                                                                               | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Acce                                                                               | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Acce                                                                               |
| curl k X GET header Authorization: Bearer access_token
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Accept:                                                                               | curl k X GET header Authorization: Bearer access_token
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Accept:                                                                               | curl k X GET header Authorization: Bearer access_token
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Accept:                                                                               |
| "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Acc | "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Acc | "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos" -H "Acc |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra}, {sequencialCompra} e {sequencialAta} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo            | Tipo       | Obrigatório    | Descrição                    |
|-------|------------------|------------|----------------|------------------------------|
|    1  | cnpj             | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    2  | anoCompra        | Inteiro    | Sim            | Ano da compra                |
|    3  | sequencialCompra | Inteiro    | Sim            | Sequencial da compra no PNCP; 
 Número sequencial gerado no 
 momento que a compra foi 
 inserida no PNCP;                              |
|    4  | sequencialAta    | Inteiro    | Sim            | q
 Número sequencial gerado no 
 momento que a ata foi inserida no 
 PNCP;                              |

## Dados de retorno

|   Id  | Campo               | Tipo    | Descrição                                    |
|-------|---------------------|---------|----------------------------------------------|
|   1   | Documentos          | Lista   | Lista de documentos                          |
|   1.1 | sequencialDocumento | Inteiro | Número sequencial atribuído ao arquivo       |
|   1.2 | url                 | Texto   | URL para download do arquivo                 |
|   1.3 | tipoDocumentoId     | Inteiro | Código do tipo de documento conforme PNCP    |
|   1.4 | tipoDocumentoNome   | Texto   | Nome do tipo de documento conforme PNCP      |
|   1.5 | titulo              | Texto   | Título referente ao arquivo                  |
|   1.6 | dataPublicacaoPncp  | Data    | Data de publicação do arquivo no portal PNCP |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           404  | Not Found             | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4.9. Consultar Documento de uma Ata

Serviço que permite consultar um documento específico pertencente a uma ata.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        | e Payload                 |
|---------------------------|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras/{anoComp
 ra}/{sequencialCompra}/atas/{sequen
 cialAta}/arquivos/{sequencialDocume
 nto}                           | GET                       |                           |                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos/1" -H "                           | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos/1" -H "                           | curl -k -X GET --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/compras/2021/1/atas/1/arquivos/1" -H "                           | "Accept:                  |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {anoCompra}, {sequencialCompra}, {sequencialAta} e {sequencialDocumento} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo            | Tipo       | Obrigatório    | Descrição                    |
|-------|------------------|------------|----------------|------------------------------|
|    1  | cnpj             | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    2  | anoCompra        | Inteiro    | Sim            | Ano da compra                |
|    3  | sequencialCompra | Inteiro    |                | qg
 momento que a ata foi inserida no 
 PNCP;
 Sequencial do documento da ata 
 no PNCP; Número sequencial 
 gerado no momento que o                              |
|    4  | sequencialAta    |            | Sim            | q
 no PNCP; Número sequencial 
 gerado no momento que o 
 documento da ata foi inserido no                              |

## Dados de retorno

|   Id  | Campo    | Tipo           | Descrição                 |
|-------|----------|----------------|---------------------------|
|    1  | arquivo  | String Binária | String binária do arquivo |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           404  | Not Found             | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.4.10. Consultar Histórico da Ata

Serviço que permite consultar todos os eventos de uma ata específica e de seus documentos/arquivos.

## Detalhes da Requisição

| Endpoint                  | Método HTT                | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/compras/
 {ano}/{sequencial}/atas/{se
 quencialAta}/historico                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| earer access_token" 
 " H "t*/*"                           | der "Auth                 | Bearer                    |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} e {sequencialAta} na URL.

|   Id  | Campo         | Tipo       | Descrição                    |
|-------|---------------|------------|------------------------------|
|    1  | cnpj          | Texto (14) | Cnpj do órgão dono da compra |
|    2  | ano           | Inteiro    | Ano da compra                |
|    3  | sequencial    | Inteiro    | Sequencial da compra no PNCP |
|    4  | sequencialAta | Inteiro    | Sequencial da Ata no PNCP    |
|    5  | pagina        | Inteiro    | Utilizado para paginação dos itens. Número da 
 página.                              |
|    6  | tamanhoPagina | Inteiro    | Utilizado para paginação dos itens. Quantidade 
 itens por página.                              |

## Dados de retorno

| Id    | Campo                   | Tipo      | Descrição                                      |
|-------|-------------------------|-----------|------------------------------------------------|
| 1     | Lista de Eventos        |           |                                                |
| 1.1   | compraOrgaoCnpj         | String    | Cnpj do órgão dono da compra                   |
| 1.2   | compraAno               | Inteiro   | Ano da compra                                  |
| 1.3   | compraSequencial        | Inteiro   | Sequencial da compra no PNCP; Número sequencia
 gerado no momento que a compra foi inserida no 
 PNCP;
 Data e hora da operação de inclusãoretificação ou                                                |
|       | logManutencaoDataInclus |           | Data e hora da operação de inclusão, retificação ou 
 lãd                                                |
| 1.4   | ao                      | Data/Hora | exclusão do recurso.                           |
| 1.5   | tipoLogManutencao       | Inteiro   | Código do tipo de operação efetuada.           |
|       | tipoLogManutencaoNom    |           | Nome da operação efetuada. Domínio:            |
| 1.6   | e                       | String    | pç
 0 - Inclusão; 1 - Retificação; 2 - Exclusão;                                                |
| 1.7   | categoriaLogManutencao  | Inteiro   | Código do tipo de recurso que sofreu a operação.
 Nome do recurso que sofreu a operação. Domínio:
 1 - Compra; 2 - Ata; 3 - Contrato; 4 - Item de Compra; 
 5 - Resultado de Item de Compra; 6 - Documento de 
 Compra; 7 - Documento de Ata; 8 - Documento de                                                |
| 1.8   | Nome                    | String    | Termo de Contrat                               |
| 1.10  | numeroAtaRegistroPreco  | String    | Número da Ata                                  |
| 1.10  | numeroAtaRegistroPreco  | String    | Número da Ata                                  |
| 1.11  | documentoAtaSequencial  | Inteiro   | Retornado caso categoriaLogManutencao = 7.
 NdiddfPNCP                                                |
| 1.12  | documentoAtaTipo        | String    | Retornado caso categoriaLogManutencao = 7.
 ílfid                                                |
| 1.13  | documentoAtaTitulo      | String    | q
 caso categoriaLogManutencao = 7.                                                |
| 1.14  | usuarioNome             | String    | Nome do Usuário/Sistema que efetuou a operação |
| 1.14  | usuarioNome             | String    | Nome do Usuário/Sistema que efetuou a operação |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5. Serviços de Contrato

## 6.5.1. Inserir Contrato

Serviço que permite incluir um contrato. Este serviço será acionado por qualquer plataforma digital credenciada.

## Detalhes de Requisição

| Endpoint                  | Método HTTP    | Exemplo de Payload   |
|---------------------------|----------------|----------------------|
| /v1/orgaos/{cnpj}/contrat | POST           | P Exemplo de Payload
 {
  "cnpjCompra": "10000000000003",
  "anoCompra": 2021,
  "sequencialCompra": 1,
  "tipoContratoId": 1,
  "numeroContratoEmpenho": "1",
  "anoContrato": 2021,
  "processo": "1/2021",
  "categoriaProcessoId": 2,
  "receita": false,
  "codigoUnidade": "1",
  "niFornecedor": "10000000000010",
  "tipoPessoaFornecedor": "PJ",
  "nomeRazaoSocialFornecedor": "Fornecedor do 
 Teste I",
  "niFornecedorSubContratado": "",
  "tipoPessoaFornecedorSubContratado": "",
  "nomeRazaoSocialFornecedorSubContratado": "",
  "objetoContrato": "Contrato para exemplificar uso                      |

## Exemplo Requisição (cURL)

curl -k -X POST --header "Authorization: Bearer access\_token " "${BASE\_URL}/v1/orgaos /10000000000003/contratos" -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj} na URL.

|   Id  | Campo                | Tipo        | Obrigatório    | Descrição                    |
|-------|----------------------|-------------|----------------|------------------------------|
|    1  | cnpj                 | Texto (14)  | Sim            | Cnpj do órgão contratante    |
|    2  | cnpjCompra           | Texto (14)  | Sim            | Cnpj do órgão dono da compra |
|    3  | anoCompra            | Inteiro     | Sim            | Ano da compra                |
|    4  | sequencialCompra     | Inteiro     | Sim            | Número sequencial da compra 
 (gerado pelo PNCP)
 Código da tabela de domínio Tip                              |
|    5  | tipoContratoId       | Inteiro     | Sim            | gp
 de contrato
 Número do contrato ou empenho 
 fdi                              |
|     6 | numeroContratoEmpe
 nho                      | Texto (50)  | Sim            | p
 com força de contrato no sistema 
 de origem                              |
|    7  | anoContrato          | Inteiro     | Sim            | Ano do contrato              |
|    8  | processo             | Texto (50)  | Sim            | Número do processo           |
|    9  | categoriaProcessoId  | Inteiro     | Sim            | Categoria
 RitdTRit                              |
|   10  | receita              | Boleano     | Sim            | False - Despesa;
 Código da unidade contratante; A                              |
|   11  | codigoUnidade        | Texto (20)  | Sim            | unidade deverá estar cadastrada 
 para o órgão contratante;
 Número de identificação do 
 fornecedor; CNPJ, CPF ou                              |
|   12  | niFornecedor         | Texto (30)  | Sim            | identificador de empresa 
 estrangeira;
 PJ - Pessoa jurídica; PF - Pessoa                              |
|   13  | tipoPessoaFornecedor | Texto (2)   | Sim            | PJ - Pessoa jurídica; PF - Pessoa 
 física; PE - Pessoa estrangeira;                              |
|    14 | nomeRazaoSocialForn
 ecedor                      | Texto (100) | Sim            | Nome ou razão social do 
 fornecedor                              |
|    15 | niFornecedorSubContr
 atado                      | Texto (30)  | Não            | Número de identificação do 
 fornecedor subcontratado; CNPJ, 
 CPF ou identificador de empresa 
 estrangeira; Somente em caso de 
 subcontratação;                              |

PJ - Pessoa jurídica; PF - Pessoa física; PE

Pessoa estrangeira;

|   16 | tipoPessoaFornecedor
 SubContratado                     | Texto (2)      | Não   | Somente em caso de 
 subcontratação;
 Nome ou razão social do 
 fornecedor subcontratado; 
 Somente em caso de                                  |
|------|--------------------|----------------|-------|---------------------------------|
|   17 | nomeRazaoSocialForn
 ecedorSubContratado                    | Texto (100)    | Não   | fornecedor subcontratado; 
 Somente em caso de 
 subcontratação;                                 |
|  18  | objetoContrato     | Texto (5120)   | Sim   | Descrição do objeto do contrato |
|   19 | informacaoCompleme
 ntar                    | Texto (5120)   | Não   | Informações complementares; Se 
 existir;                                 |
|  20  | valorInicial       | Decimal        | Sim   | Valor inicial do contrato. Precisão 
 de 4 dígitos decimais; Ex: 100.0000                                 |
|  21  | numeroParcelas     | Inteiro        | Sim   | Número de parcelas              |
|  22  | valorParcela       | Decimal        | Não   | Valor da parcela. Precisão de 4 
 dígitos decimais; Ex: 100.0000;                                 |
|  23  | valorGlobal        | Decimal        | Sim   | g; 
 de 4 dígitos decimais; Ex: 100.0000;
 Valor acumulado do contrato;                                 |
|  24  | valorAcumulado     | Decimal        | Não   | Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                 |
|  25  | dataAssinatura     | Data           | Sim   | Data de assinatura do contrato
 Data de início de vigência do                                 |
|  26  | dataVigenciaInicio | Data           | Sim   | Data de início de vigência do 
 contrato
 Dtdtéidiêid                                 |
|  27  | datavigenciaFim    | Data           | Sim   | Data do término da vigência do 
 contrato                                 |
|  28  | identificadorCipi  | String(512)    | Não   | Identificador do contrato no 
 Cadastro Integrado de Projetos de 
 Investimento                                 |
|  29  | urlCipi            | String(8 a 14) | Não   | Url com informações do contrato 
 no sistema de Cadastro Integrado 
 de Projetos de Investimento                                 |

## Dados de retorno

|   Id  | Campo    | Tipo        | Obrig   | Descrição                       |
|-------|----------|-------------|---------|---------------------------------|
|    1  | location | Texto (255) | Sim     | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control - allow - credentials: true

access-control - allow - headers: Content - Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control - allow - methods: GET,PUT,POST,DELETE,OPTIONS

access-control - allow - origin: *

cache - control: no - cache,no-store,max-age=0,must-revalidate

content - length: 0

date: ?

expires: 0

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/contratos/2021/1

pragma: no - cache

strict - transport-security: max-age=?

x-content - type-options: nosniff

x-firefox - spdy: ?

x-frame - options: DENY

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.2. Retificar Contrato

Serviço que permite retificar um contrato. Este serviço será acionado por qualquer plataforma digital credenciada. Importante lembrar que na Retificação todas as informações terão que ser enviadas novamente, não apenas as que sofreram alteração.

## Detalhes de Requisição

Nota: alimentar os parâmetros {cnpj}, {ano} e {sequencial} na URL.

| Endpoint                 | Método HTTP              | Exemplo de Payload                                |
|--------------------------|--------------------------|---------------------------------------------------|
| /v1/orgaos/{cnpj}/contrat
 os/{ano}/{sequencial}                          | PUT                      | Exemplo de Payload
 {
  "cnpjCompra": "10000000000003",
  "anoCompra": 2021,
  "sequencialCompra": 1,
  "tipoContratoId": 1,
  "numeroContratoEmpenho": "1",
  "processo": "1/2021",
  "categoriaProcessoId": 2,
  "receita": false,
  "codigoUnidade": "1",
  "cnpjOrgaoSubRogado": "",
  "codigoUnidadeSubRogada": "",
  "niFornecedor": "10000000000010",                                                   |
|                          |                          | "anoCompra": 2021,
 l                                                   |
|                          |                          | p
  "sequencialCompra": 1,                                                   |
|                          |                          | "tipoContratoId": 1,                              |
|                          |                          | "numeroContratoEmpenho": "1",                     |
|                          |                          | "processo": "1/2021",                             |
|                          |                          | "categoriaProcessoId": 2,                         |
|                          |                          | "receita": false,                                 |
|                          |                          | "codigoUnidade": "1",                             |
|                          |                          | "cnpjOrgaoSubRogado": "",                         |
|                          |                          | "codigoUnidadeSubRogada": "",                     |
|                          |                          | "niFornecedor": "10000000000010",                 |
|                          |                          | "tipoPessoaFornecedor": "PJ",                     |
|                          |                          | p
  "nomeRazaoSocialFornecedor": "For                                                   |
|                          |                          | "niFornecedorSubContratad                         |
|                          |                          | "tipoPessoaFornecedorSubContratado": "",          |
|                          |                          | "nomeRazaoSocialFornecedorSubContratado": "",     |
|                          |                          | "objetoContrato": "Contrato para exemplificar uso |
|                          |                          | da API de retificação no PNCP.",                  |
|                          |                          | "informacaoComplementar": "",                     |
|                          |                          | p
  "valorInicial": 10000.00,                                                   |
|                          |                          | "numeroParcelas": 2,                              |
|                          |                          | "valorParcela": 5000.00,                          |
|                          |                          | "valorGlobal": 10000.00,                          |
|                          |                          | "valorAcumulado": 10000.00,                       |
|                          |                          | "dataAssinatura": "2021-07-21",                   |
|                          |                          | "dataVigenciaInicio": "2021-07-22",               |
|                          |                          | "dataVigenciaFim": "2021-07-23",                  |
|                          |                          | g
  "justificativa": "motivo/justificativa para a retificaçã                                                   |
|                          |                          | do contrato"                                      |
|                          |                          | “identificadorCipi”: “111.11-011”,                |
|                          |                          | p
  “urlCipi”: ” https://cipi.economia.gov.br/111.11-011”                                                   |
|                          |                          |                                                   |
| xemplo Requisição (cURL) | xemplo Requisição (cURL) | xemplo Requisição (cURL)                          |

curl -k -X PUT --header "Authorization: Bearer access\_token"

"${BASE\_URL}/v1/orgaos/10000000000003/contratos/2021/1" -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo                | Tipo       | Obrigatório    | Descrição                    |
|-------|----------------------|------------|----------------|------------------------------|
|    1  | cnpj                 | Texto (14) | Sim            | Cnpj do órgão contratante    |
|    2  | ano                  | Inteiro    | Sim            | Ano do contrato              |
|    3  | sequencial           | Inteiro    | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)                              |
|    4  | cnpjCompra           | Texto (14) | Sim            | Cnpj do órgão dono da compra |
|    5  | anoCompra            | Inteiro    | Sim            | Ano da compra                |
|    6  | sequencialCompra     | Inteiro    | Sim            | qp
 (gerado pelo PNCP)
 CódidtblddíiTid                              |
|    7  | tipoContratoId       | Inteiro    | Sim            | Código da tabela de domínio Tipo d
 contrato                              |
|     8 | numeroContratoEmpe
 nho                      | Texto (50) | Sim            | Número do contrato ou empenho 
 com força de contrato                              |
|    9  | processo             | Texto (50) | Sim            | Número do processo           |
|   10  | categoriaProcessoId  | Inteiro    | Sim            | Código da tabela de domínio 
 Categoria                              |
|   11  | receita              | Boleano    | Sim            | p
 False - Despesa;
 Código da unidade contratante; A 
 dddá dd                              |
|   12  | codigoUnidade        | Texto (20) | Sim            | Código da unidade contratante; A 
 unidade deverá estar cadastrada 
 para o órgão contratante;                              |
|   13  | cnpjOrgaoSubRogado   | Texto (14) | Não            | Cnpj do órgão sub-rogado; Somente 
 em caso de sub-rogação;                              |
|    14 | codigoUnidadeSubRog
 ada                      | Texto (20) | Não            | Código da unidade contratante subrogada; Somente em caso de subrogação;                              |
|   15  | niFornecedor         | Texto (30) | Sim            | ; J, 
 identificador de empresa 
 estrangeira;
 PJ PjídiPF Pfíi                              |
|   16  | tipoPessoaFornecedor | Texto (2)  | Sim            | PJ - Pessoa jurídica; PF - Pessoa física
 PE - Pessoa estrangeira;                              |

nomeRazaoSocialForn

|   17 | ecedor             | Texto (100)    | Sim    | Nome ou razão social do fornecedor   |
|------|--------------------|----------------|--------|--------------------------------------|
|   18 | niFornecedorSubCont
 atado                    | Texto (30)     | Não    | fornecedor subcontratado; CNPJ, CPF 
 ou identificador de empresa 
 estrangeira; Somente em caso de 
 subcontratação;
 PJ Pessoa jurídica; PF Pessoa física;                                      |
|   19 | tipoPessoaFornecedor
 SubContratado                    | Texto (2)      | Não    | PE - Pessoa estrangeira; Somente em 
 caso de subcontratação;
 Nome ou razão social do fornecedor 
 subcontratado; Somente em caso de                                      |
|   20 | nomeRazaoSocialForn
 ecedorSubContratado                    | Texto (100)    | Não    | subcontratado; Somente em caso de 
 subcontratação;                                      |
|  21  | objetoContrato     | Texto (5120)   | Sim    | Descrição do objeto do contrato      |
|   22 | informacaoComplem
 ntar                    | Texto (5120)   | Não    | Informações complementares; Se 
 existir;                                      |
|  23  | valorInicial       | Decimal        | Sim    | Valor inicial do contrato; Precisão de 
 4 dígitos decimais; Ex: 100.0000;                                      |
|  24  | numeroParcelas     | Inteiro        | Sim    | Número de parcelas                   |
|  25  | valorParcela       | Decimal        | Não    | Valor da parcela; Precisão de 4 
 dígitos decimais; Ex: 100.0000;
 Valor global do contrato; Precisão de                                      |
|  26  | valorGlobal        | Decimal        | Sim    | Valor global do contrato; Precisão de 
 4 dígitos decimais; Ex: 100.0000;
 Valor acumulado do contrato;                                      |
|  27  | valorAcumulado     | Decimal        | Não    | Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                      |
|  27  | valorAcumulado     | Decimal        | Não    | 100.0000;                            |
|  29  | dataVigenciaInicio | Data           | Sim    | Data de início de vigência do 
 contrato                                      |
|  30  | dataVigenciaFim    | Data           | Sim    | Data do término da vigência do 
 contrato
 ff                                      |
|  31  | justificativa      | Texto (255)    |        | contrato
 Motivo/justificativa para a retificação 
 dos atributos do contrato                                      |

Identificador do contrato no

|   32  | identificadorCipi    | String(512)    | Não   | Cadastro Integrado de Projetos de 
 Investimento                          |
|-------|----------------------|----------------|-------|--------------------------|
|   33  | urlCipi              | String(8 a 14) | Não   | Projetos de Investimento |

## Dados de retorno

|   Id  | Campo    | Tipo        | brigat   | Descrição                       |
|-------|----------|-------------|----------|---------------------------------|
|    1  | location | Texto (255) | Sim      | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

cache -control: no -cache,no-store,max-age=0,must-revalidate location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/contratos/2021/1

access-control -allow -origin: * content -length: 0 date: ? expires: 0 pragma: no -cache strict -transport-security: max-age=? x-content -type-options: nosniff x-firefox -spdy: ? x-frame -options: DENY

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.3. Excluir Contrato

Serviço que permite remover um contrato. Este serviço será acionado por qualquer plataforma digital credenciada. Não será possível excluir o Contrato com Termo ativo.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{an
 o}/{sequencial}                           | DELETE                    | {
  "justificativa": "motivo/justificativa para 
 exclusão do contrato"
 }                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| url -k -X DELETE --header "Authorization: Bearer access_token" 
 ${BASEURL}/v1/orgaos/10000000000003/contratos/2021/1" H "accept: */*"                           | url -k -X DELETE --header "Authorization: Bearer access_token" 
 ${BASEURL}/v1/orgaos/10000000000003/contratos/2021/1" H "accept: */*"                           | url -k -X DELETE --header "Authorization: Bearer access_token" 
 ${BASEURL}/v1/orgaos/10000000000003/contratos/2021/1" H "accept: */*"                           |

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo         | Tipo        | Obrigatório    | Descrição                 |
|-------|---------------|-------------|----------------|---------------------------|
|    1  | cnpj          | Texto (14)  | Sim            | Cnpj do órgão contratante |
|    2  | ano           | Inteiro     | Sim            | Ano do contrato           |
|    3  | sequencial    | Inteiro     | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)                           |
|    4  | justificativa | Texto (255) | Não            | Motivo/justificativa para exclusão 
 do contrato.                           |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.4. Inserir Documento a um Contrato

Serviço que permite inserir um documento/arquivo a um contrato. O sistema permite o upload de arquivos com as extensões listadas na seção: Tabelas de domínio - Extensões de arquivos aceitos pelas APIs de Documento.

## Detalhes da Requisição

| Endpoint                                                                                        | Método HTTP                                                                                     | Exemplo de Payload                                                                              |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}/{
 sequencial}/arquivos                                                                                                 | POST                                                                                            | Não se aplica                                                                                   |
| Exemplo Requisição (cURL)                                                                       | Exemplo Requisição (cURL)                                                                       | Exemplo Requisição (cURL)                                                                       |
| curl -k -X POST --header "Authorization: Bearer access_token" 
 "${BASEURL}/1//10000000000003//2021/1/i" H "*/*" H "C                                                                                                 | curl -k -X POST --header "Authorization: Bearer access_token" 
 "${BASEURL}/1//10000000000003//2021/1/i" H "*/*" H "C                                                                                                 | curl -k -X POST --header "Authorization: Bearer access_token" 
 "${BASEURL}/1//10000000000003//2021/1/i" H "*/*" H "C                                                                                                 |
| _
 ${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos" -H "accept: */*" -H "Content                                                                                                 | _
 ${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos" -H "accept: */*" -H "Content                                                                                                 | _
 ${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos" -H "accept: */*" -H "Content                                                                                                 |
| Type: multipart/form-data" -H "Titulo-Documento: Contrato-2021-1" -H "Tipo-Documento-Id: 12" -F | Type: multipart/form-data" -H "Titulo-Documento: Contrato-2021-1" -H "Tipo-Documento-Id: 12" -F | Type: multipart/form-data" -H "Titulo-Documento: Contrato-2021-1" -H "Tipo-Documento-Id: 12" -F |

## Dados de entrada

|   Id  | Campo             | Tipo       | Obrigatório    | Descrição                 |
|-------|-------------------|------------|----------------|---------------------------|
|    1  | cnpj              | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | ano               | Inteiro    | Sim            | Ano do contrato           |
|    3  | sequencial        | Inteiro    | Sim            | Número sequencial gerado no 
 momento que o contrato foi 
 inserido no PNCP;                           |
|    4  | Titulo-Documento  | Texto (50) | Sim            | Título do documento       |
|    5  | Tipo-Documento-Id | Inteiro    | Sim            | Código da tabela de domínio Tipo 
 de documento                           |

## Dados de retorno

|   Id  | Campo    | Tipo        | brigat   | Descrição                       |
|-------|----------|-------------|----------|---------------------------------|
|    1  | location | Texto (255) | Sim      | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

access-control -allow -origin: *

cache -control: no -cache,no-store,max-age=0,must-revalidate content -length: 0

date: ?

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/contratos/2021/1/arquivos/1

expires: 0 nome-bucket: ? pragma: no -cache strict -transport-security: max-age=? x-content -type-options: nosniff x-firefox -spdy: ? x-frame -options: DENY

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.5. Excluir Documento do Contrato

Serviço que permite remover um documento pertencente a um contrato específico.

## Detalhes da Requisição

| Endpoint                           | Método HTTP               | Exemplo de Payload        |
|------------------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}/{s
 equencial}/arquivos/{sequencialDocu
 mento}                                    | DELETE                    | {
  "justificativa": "motivo/justificativa para 
 exclusão do documento do contrato"
 }                           |
| Exemplo Requisição (cURL)          | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| uthorization: Bearer access_token" | --header                  | earer ac                  |

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano}, {sequencial} e {sequencialDocumento} na URL.

|   Id  | Campo               | Tipo        | Obrigatório    | Descrição                 |
|-------|---------------------|-------------|----------------|---------------------------|
|    1  | cnpj                | Texto (14)  | Sim            | Cnpj do órgão contratante |
|    2  | ano                 | Inteiro     | Sim            | Ano do contrato           |
|    3  | sequencial          | Inteiro     | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)                           |
|    4  | sequencialDocumento | Inteiro     | Sim            | Número sequencial do documento 
 do contrato (gerado pelo PNCP)                           |
|    5  | justificativa       | Texto (255) | Não            | Motivo/justificativa para exclusão 
 do documento do contrato.                           |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.6. Consultar Todos os Documentos de um Contrato

Serviço que permite consultar a lista de documentos pertencentes a um contrato específico.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}/{
 sequencial}/arquivos                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos" -H "accept: */*"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} na URL.

| Id    | Campo      | Tipo      | Obrigatório    | Descrição                       |
|-------|------------|-----------|----------------|---------------------------------|
| 1     | cnpj       | Texto (14 | Sim            | Cnpj do órgão contratante       |
| 2     | ano        | Inteiro   | Sim            | Ano do contrato                 |
|       |            |           |                | Sequencial do contrato no PNCP; |
|       |            |           |                | Número sequencial gerado no 
 momento que o contrato foi                                 |
| 3     | sequencial | Inteiro   | Sim            | inserido no PNCP;               |

## Dados de retorno

|   Id  | Campo               | Tipo    | Descrição                                    |
|-------|---------------------|---------|----------------------------------------------|
|   1   | Documentos          | Lista   | Lista de documentos                          |
|   1.1 | sequencialDocumento | Inteiro | Número sequencial atribuído ao arquivo       |
|   1.2 | url                 | Texto   | URL para download do arquivo                 |
|   1.3 | tipoDocumentoNome   | Texto   | Nome do tipo de documento conforme PNCP      |
|   1.4 | titulo              | Texto   | Título referente ao arquivo                  |
|   1.5 | dataPublicacaoPncp  | Data    | Data de publicação do arquivo no portal PNCP |
|   1.6 | uri                 | Texto   | URI para download do arquivo                 |
|   1.7 | cnpj                | Texto   | Cnpj do órgão contratante                    |
|   1.8 | anoCompra           | Inteiro | Ano da compra associada ao Contrato          |
|   1.9 | sequencialCompra    | Inteiro | Sequencial da compra no PNCP; Número 
 sequencial gerado no momento que a compra 
 foi inserida no PNCP                                              |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.7. Consultar Documento de um Contrato

Serviço que permite consultar um documento específico pertencente a um contrato.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contrato
 s/{ano}/{sequencial}/arqui
 vos/{sequencialDocument
 o}                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos/1" -H "Accept: */*”                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos/1" -H "Accept: */*”                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/arquivos/1" -H "Accept: */*”                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} e {sequencialDocumento} na URL.

|   Id  | Campo               | Tipo       | Obrigatório    | Descrição                 |
|-------|---------------------|------------|----------------|---------------------------|
|    1  | cnpj                | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | ano                 | Inteiro    | Sim            | Ano do contrato           |
|    3  | sequencial          | Inteiro    | Sim            | momento que o contrato foi 
 inserido no PNCP;
 Sequencial do documento no 
 PNCP; Número sequencial gerado                           |
|    4  | sequencialDocumento | Inteiro    | Sim            | no momento que o documento fo
 inserido no PNCP;                           |

## Dados de retorno

| Id     | Campo    | Tipo              | Descrição         |
|--------|----------|-------------------|-------------------|
| string | String   | string do arquivo | string do arquivo |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.8. Consultar Contrato

Serviço que permite consultar um contrato específico.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{
 ano}/{sequencial}                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}" -H "accept: */*"                           |

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo      | Tipo       | Obrigatório    | Descrição                 |
|-------|------------|------------|----------------|---------------------------|
|    1  | cnpj       | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | ano        | Inteiro    | Sim            | Ano do contrato           |
|    3  | sequencial | Inteiro    | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)                           |

## Dados de retorno

| Id    | Campo              | Tipo         | Descriçã                                             |
|-------|--------------------|--------------|------------------------------------------------------|
| 1     | numeroControlePN
 CP                    | String       | Número de controle PNCP do contrato                  |
| 2     | sequencialContrato |              | Número sequencial do contrato (gerado pelo PNCP)     |
| 3     | numeroControlePN
 CPCompra                    | String       | Número de controle PNCP da compra relacionada        |
| 4     | numeroContratoEm
 penho                    | Texto (50)   | Número do contrato ou empenho com força de contrato  |
| 5     | anoContrato        | Inteiro      | Ano do contrato                                      |
| 6     | tipoContrato       |              | Agrupador com os dados do tipo de contrato           |
| 6.1   | Id                 | Inteiro      | Código da tabela de domínio Tipo de contrato         |
| 6.2   | Nome               | String       | Nome do Tipo de Contrato                             |
| 7     | process            | Texto (50)   | Número do processo                                   |
| 8     | categoriaProcesso  |              | Agrupador com os dados da categoria do process       |
| 8.1   | Id                 | Inteiro      | Código da tabela de domínio Categoria                |
| 8.2   | Nome               | String       | Nome da Categoria do processo                        |
| 9     | receita            | Boleano      | Receita ou despesa: True - Receita; False - Despesa; |
| 10    | objetoContrato     | Texto (5120) | Descrição do objeto do contrato                      |
| 11    | informacaoComple
 mentar                    | Texto (5120) | Informações complementares; Se existir               |
| 12    | orgaoEntidade      |              | Agrupador com os dados do Órgão/Entidade             |
| 12.1  | cnpj               | String       | CNPJ do Órgão referente à Contrato                   |
| 12.2  | razaosocia         | String       | Razão social do Órgão referente à Contrato           |
| 12.3  | poderId            | String       | Código do poder a que pertence o Órgão.
 L - Legislativo; E - Executivo; J - Judiciário                                                      |
| 12.4  | esferaId           | String       | Código da esfera a que pertence o Órgão.
 F - Federal; E - Estadual; M - Municipal; D - Distrital
 Agrupador com os dados da Unidade executora do                                                      |
|       |                    |              | Agrupador com os dados da Unidade executora do 
 Órgão                                                      |

|   13.1  | codigoUnidade    | String           | Código da Unidade Executora pertencente ao Órg   |
|---------|------------------|------------------|--------------------------------------------------|
|    13.2 | nomeUnidade      | String           | Nome da Unidade Executora pertencente ao Órgão   |
|    13.3 | municipioId      | Inteiro          | Código IBGE do município                         |
|    13.4 | municipioNome    | String           | Nome do município                                |
|    13.5 | ufSigla          | String           | Sigla da unidade federativa do município         |
|    13.6 | ufNome           | String           | Nome da unidade federativa do município          |
|    14   | orgaoSubRogado   |                  | Agrupador com os dados do Órgão/Entidade 
 subrogado                                                  |
|    14.1 | cnpj             | String           | CNPJ do Órgão referente à Contrato               |
|    14.2 | razaosocial      | String           | Razão social do Órgão referente à Contrato       |
|    14.3 | poderId          | String           | Código do poder a que pertence o Órgão.
 L - Legislativo; E - Executivo; J - Judiciário                                                  |
|    14.4 | esferaId         | String           | gqpg
 F - Federal; E - Estadual; M - Municipal; D - Distrital
 Agrupador com os dados da Unidade Executora do                                                  |
|    15   | unidadeSubRogada | unidadeSubRogada | Agrupador com os dados da Unidade Executora do 
 Órgão subrogado                                                  |
|    15.1 | codigoUnidade    | String           | Código da Unidade Executora pertencente ao Órgã  |
|    15.2 | nomeUnidade      | String           | Nome da Unidade Executora pertencente ao Órgão   |
|    15.3 | municipioId      | Inteiro          | Código IBGE do município                         |
|    15.4 | municipioNome    | String           | Nome do município                                |
|    15.5 | ufSigla          | String           | Sigla da unidade federativa do município         |
|    15.6 | ufNome           | String           | Nome da unidade federativa do município          |
|    16   | tipoPessoa       | Texto (2)        | PJ - Pessoa jurídica; PF - Pessoa física; PE - Pessoa 
 estrangeira;                                                  |
|    17   | iFd              | 30               | Número de identificação do fornecedor; CNPJ, CPF ou 
 identificador de empresa estrangeira;                                                  |
|    18   | nomeRazaoSocialFo
 rnecedor                  | Texto (100)      | Nome ou razão social do fornecedo                |

| 19   | tipoPessoaSubContr
 atada                     | Texto (2)   | PJ - Pessoa jurídica; PF - Pessoa física; PE - Pessoa 
 estrangeira; Somente em caso de subcontratação;                                                |
|------|--------------------|-------------|------------------------------------------------|
| 20   | niFornecedorSubCo
 ntratado                    | Texto (30)  | Número de identificação do fornecedor subcontratado; 
 CNPJ, CPF ou identificador de empresa estrangeira; 
 Somente em caso de subcontratação;                                                |
| 21   | nomeFornecedorSu
 bContratado                    | Texto (100) | Nome ou razão social do fornecedor subcontratado; 
 Somente em caso de subcontratação;                                                |
| 22   | valorInicia        | Decima      | ecimais; Ex: 100.0001;                         |
| 23   | numeroParcelas     | Inteiro     | Número de parcelas                             |
| 24   | valorParcela       | Decima      | Valor da parcela. Precisão de até 4 dígitos decimais; Ex
 100.0001;                                                |
| 25   | valorGlobal        | Decimal     | Valor global do contrato. Precisão de até 4 dígitos 
 decimais; Ex: 1000001;                                                |
| 26   | valorAcumulado     | Decimal     | Valor acumulado do contrato. Precisão de até 4 dígitos 
 decimais; Ex: 100.0001;                                                |
| 27   | dataAssinatura     | Data        | Data de assinatura do contrato                 |
| 28   | dataVigenciaInicio | Data        | Data de início de vigência do contra           |
| 29   | dataVigenciaFim    | Data        | Data do término da vigência do contrato        |
| 30   | numeroRetificacao  | Inteiro     | Número de retificações; Número de vezes que este 
 egistro está sendo alterado;                                                |
| 31   | usuarioNome        | String      | Nome do sistema/portal que enviou o contrato   |
| 32   | dataPublicacaoPncp | Data/Hora   | Data de publicação do contrato no PNCP         |
| 33   | dataAtualizacao    | Data/Hora   | Data da última atualização do contrato no PNCP |
|      | identificadorCipi  |             | dentificador do contrato no Cadastro Integrado de 
 rojetos de Investimento                                                |
| 34   |                    | String      | Projetos de Investimento
 Url com informações do contrato no sistema de Cadastr                                                |
| 35   | urlCipi            | String      | ç
 Integrado de Projetos de Investimento                                                |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.5.9. Consultar Histórico do Contrato

Serviço que permite consultar todos os eventos de um Contrato específico, eventos dos seus Termos e dos documentos/arquivos do Contrato e seus Termos.

## Detalhes da Requisição

| Endpoint                          | Método HTTP                       | Exemplo de Payload                |
|-----------------------------------|-----------------------------------|-----------------------------------|
| /v1/orgaos/{cnpj}/contrat
 os/{ano}/{sequencial}/his
 torico                                   | GET                               | Não se aplica                     |
| Exemplo Requisição (cURL)         | Exemplo Requisição (cURL)         | Exemplo Requisição (cURL)         |
| "Authorization: Bearer access_tok | "Authorization: Bearer access_tok | "Authorization: Bearer access_tok |
| curl 
 "${BASEU                                   | ader "Auth                        | Bearer                            |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo         | Tipo       | Obrigatório    | Descrição                      |
|-------|---------------|------------|----------------|--------------------------------|
|    1  | cnpj          | Texto (14) | Sim            | Cnpj do órgão dono do contrato |
|    2  | ano           | Inteiro    | Sim            | Ano do contrato                |
|    3  | sequencial    | Inteiro    | Sim            | Sequencial do contrato no PNCP |
|    4  | pagina        | Inteiro    | Não            | Utilizado para paginação dos itens
 Número da página.                                |
|    5  | tamanhoPagina | Inteiro    | Não            | Utilizado para paginação dos itens. 
 Quantidade itens por página.                                |

## Dados de retorno

| Id    | Campo                   | Tipo                    | Descrição                                           |
|-------|-------------------------|-------------------------|-----------------------------------------------------|
| 1     | Lista de Eventos        | Lista de Eventos        | Lista de Eventos                                    |
| 1.1   | contratoOrgaoCnpj       | String                  | Cnpj do órgão dono do contrato                      |
| 1.2   | contratoAno             | Inteiro                 | Ano da contrato                                     |
| 1.3   | contratoSequencial      | Inteiro                 | Sequencial do contrato no PNCP                      |
|       | logManutencaoDataInclus | logManutencaoDataInclus | Data e hora da operação de inclusão, retificação ou |
| 1.4   | ao                      | Data/Hora               | exclusão do recurso.                                |
| 1.5   | tipoLogManutencao       | Inteiro                 | Código do tipo de operação efetuada.                |
|       | tipoLogManutencaoNo     | tipoLogManutencaoNo     | Nome da operação efetuada. Domínio:                 |
| 1.6   | e                       | String                  | 0 - Inclusão; 1 - Retificação; 2 - Exclusão;        |
| 1.7   | categoriaLogManutencao  | Inteiro                 | Código do tipo de recurso que sofreu a operação.
 Nome do recurso que sofreu a operação. Domínio:                                                     |
| 1.8   | Nome                    | String                  | Compra; 7 - Documento de Ata; 8 - Documento de 
 Contrato; 9 - Termo de Contrato; 10 - Documento de 
 Termo de Contrato;
 Sequencial do termo do contrato no PNCP.                                                     |
| 1.9   | sequencialTermoContrato | Inteiro                 | Retornado caso categoriaLogManutencao = 9.
 Número do termo do contratoRetornado caso                                                     |
|       | sequencialDocumentoCo   | sequencialDocumentoCo   | Sequencial do documento do contrato no PNCP         |
| 1.11  | ntrato                  | Inteiro                 | Retornado caso categoriaLogManutencao = 8.          |
| 1.12  | tituloDocumentoContrato | String                  | Título referente ao arquivo/documento do contrato. 
 Retornado caso categoriaLogManutencao = 8.
 Sequencial do documento do termo do contrato no                                                     |
| 1.13  | sequencialDocumentoTe
 moContrato                         | Inteiro                 | Sequencial do documento do termo do contrato no 
 PNCP. Retornado caso categoriaLogManutencao = 
 10.
 Títlfti/dtdtd                                                     |
| 1.13  | moContrato              | Inteiro                 | 10.
 Título referente ao arquivo/documento do termo do 
 contrato. Retornado caso categoriaLogManutencao = 
 10                                                     |
| 114   | titlDtTC                | titlDtTC                | 10.                                                 |
| 1.15  | usuarioNome             | String                  | Nome do Usuário/Sistema que efetuou a operação      |

## 1.16 justificativa

String

Motivo/Justificativa da operação de retificação ou exclusão do recurso.

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.6. Serviço de Termo de Contrato

## 6.6.1. Inserir Termo de Contrato

Serviço que permite inserir um termo de contrato a um contrato. O termo pode ser um termo aditivo, um termo de rescisão ou um termo de apostilamento.

## Detalhes da Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload                        |
|-------------|----------------|-------------------------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}
 /{sequencial}/termos             | POST           | P Exemplo de Payload
 {
  "tipoTermoContratoId": 2,
  "numeroTermoContrato": "1",
  "objetoTermoContrato": "Termo de contrato 
 para exemplificar uso da API.",
  "dataAssinatura": "2021-07-22",
  "qualificacaoAcrescimoSupressao": false,
  "qualificacaoVigencia": false,
  "qualificacaoFornecedor": false,
  "qualificacaoReajuste": false,
  "qualificacaoInformativo": true,
  "informativoObservacao": "Registro 
 exemplificativo.",
  "niFornecedor": "12345678000190",
  "TipoPessoaFornecedor": "PJ",
  "nomeRazaoSocialFornecedor": "Fornecedor 
 de teste",                                           |
|             |                | tipoTermoContratoId: 2,
  "numeroTermoContrato": "1",                                           |
|             |                | "objetoTermoContrato": "Termo de contrato |
|             |                | objetoTermoContrato: Termo de contrato 
 para exemplificar uso da API.",                                           |
|             |                | pp,
  "dataAssinatura": "2021-07-22",                                           |
|             |                | "qualificacaoAcrescimoSupressao": false,  |
|             |                | "qualificacaoVigencia": false,            |
|             |                | qg
  "qualificacaoFornecedor": false,                                           |
|             |                | q
  "qualificacaoReajuste": false,                                           |
|             |                | qj
  "qualificacaoInformativo": true,                                           |
|             |                | q,
  "informativoObservacao": "Registro                                           |
|             |                | exemplificativo.",                        |
|             |                | "niFornecedor": "12345678000190",         |
|             |                | "TipoPessoaFornecedor": "PJ",             |
|             |                | "nomeRazaoSocialFornecedor": "Fornecedor  |
|             |                | de teste",                                |
|             |                | "niFornecedorSubContratado": "",          |
|             |                | "TipoPessoaFornecedorSubContratado": "",  |
|             |                | p
  "nomeRazaoSocialFornecedorSubContratado":                                           |
|             |                | ",                                        |
|             |                | fundamentoLegal: ,
 "valorAcrescido": 0                                           |
|             |                | "numeroParcelas": 0,                      |
|             |                | "valorParcela": 0,                        |
|             |                | "valorGlobal": 0,                         |
|             |                | "prazoAditadoDias": 0,                    |
|             |                | p
  "dataVigenciaInicio": "2021-07-23",                                           |
|             |                | "dataVigenciaFim": "2021-07-24"           |
|             |                | "dataVigenciaFim": "2021-07-24"
 }                                           |
|             |                | g                                         |
|             |                | }                                         |

## Exemplo Requisição (cURL)

curl -k -X POST --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos/10000000000003/contratos/2021/1/termos" -H "accept: */*" -H "Content-

Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: a URL possui os parâmetros {cnpj}, {ano} e {sequencial}.

Manual de Integração PNCP– Versão 2.2.1

|   Id  | Campo                   | Tipo         | Obrigatório    | Descrição                   |
|-------|-------------------------|--------------|----------------|-----------------------------|
|    1  | cnpj                    | Texto (14)   | Sim            | Cnpj do órgão contratante   |
|    2  | ano                     | Inteiro      | Sim            | Ano do contrato             |
|    3  | sequencial              | Inteiro      | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)
 óddblddí                             |
|    4  | tipoTermoContratoId     | Inteiro      | Sim            | de termo de contrato        |
|    5  | numeroTermoContrato     | Texto (50)   | Sim            | Número do termo de contrato |
|    6  | objetoTermoContrato     | Texto (5120) | Sim            | Descrição do objeto do termo de 
 contrato                             |
|    7  | dataAssinatura          | Date         | Sim            | Data de assinatura do termo de 
 contrato                             |
|     8 | qualificacaoAcrescimoSu
 pressao                         | Boleano      | Sim            | Identifica se o termo aditivo terá 
 acréscimo ou supressão.                             |
|    9  | qualificacaoVigencia    | Boleano      | Sim            | alteração na vigência e número de 
 parcelas.
 Identifica se o termo aditivo terá                             |
|   10  | qualificacaoFornecedor  | Boleano      | Sim            | alteração do fornecedor.
 Idtifitditilt                             |
|   11  | qualificacaoReajuste    | Boleano      | Sim            | Identifica se o termo aditivo altera 
 valor unitário do item do contrato                             |
|   12  | qualificacaoInformativo | Boleano      | Sim            | Identifica se o termo aditivo tem 
 alguma observação.                             |
|   13  | niFornecedor            | Texto (30)   | Não            | Número de identificação do 
 fornecedor; CNPJ, CPF ou 
 identificador de empresa 
 estrangeira;                             |
|   14  | tipoPessoaFornecedor    | Texto (2)    | Não            | J j; 
 física; PE - Pessoa estrangeira;
 Nãil d                             |
|    15 | nomeRazaoSocialFornec
 edor                         | Texto (100)  | Não            | Nome ou razão social do 
 fornecedor                             |

|   16 | niFornecedorSubContrat
 ado                        | Texto (30)    | Não   | Número de identificação do 
 fornecedor subcontratado; CNPJ, 
 CPF ou identificador de empresa 
 estrangeira; Somente em caso de 
 subcontratação;                             |
|------|-----------------------|---------------|-------|-----------------------------|
|   17 | TipoPessoaFornecedorS
 ubContratado                       | Texto (2)     | Não   | PJ - Pessoa jurídica; PF - Pessoa 
 física; PE - Pessoa estrangeira; 
 Somente em caso de 
 subcontratação;                             |
|   18 | nomeRazaoSocialForne
 edorSubContratado                       | Texto (100)   | Não   | Somente em caso de 
 subcontratação;                             |
|  19  | informativoObservacao | Texto (5120)  | Não   | Observação do termo aditivo |
|  20  | fundamentoLegal       | Texto (5120)  | Não   | Fundamento legal do termo de 
 contrato                             |
|  21  | valorAcrescido        | Decimal       | Não   | Valor acrescido ao contrato 
 original; Precisão de 4 dígitos 
 decimais; Ex: 100.0000;                             |
|  22  | numeroParcelas        | Inteiro       | Não   | Número de parcelas; Precisão de 4 
 dígitos decimais; Ex: 100.0000;                             |
|  23  | valorParcela          | Decimal       | Não   | dígitos decimais; Ex: 100.0000;
 Valor global do termo de contrato; 
 Valor da parcela x Número de 
 lPiãd4 díi                             |
|  24  | valorGlobal           | Decimal       | Não   | g
 Valor da parcela x Número de 
 parcelas; Precisão de 4 dígitos 
 decimais; Ex: 100.0000;                             |
|  25  | prazoAditadoDias      | Inteiro       | Não   | Prazo aditado em dias       |
|  26  | dataVigenciaInicio    | Date          | Não   | Data de início de vigência do 
 contrato
 Dtdtéidiêid                             |
|  27  | dataVigenciaFim       | Date          | Não   | Data do término da vigência do 
 contrato                             |

## Dados de retorno

|   Id  | Campo    | Tipo        | brigat   | Descrição                       |
|-------|----------|-------------|----------|---------------------------------|
|    1  | location | Texto (255) | Sim      | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control - allow - credentials: true

access-control - allow - headers: Content - Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control - allow - methods: GET,PUT,POST,DELETE,OPTIONS

access-control - allow - origin: *

cache - control: no - cache,no-store,max-age=0,must-revalidate

content - length: 0

date: ?

expires: 0

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/contratos/2021/1/termos/1

pragma: no - cache

strict - transport-security: max-age=?

x-content - type-options: nosniff

x-firefox - spdy: ?

x-frame - options: DENY

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.6.2. Retificar Termo de Contrato

Serviço que permite retificar um termo de contrato. O termo pode ser um termo aditivo, um termo de rescisão ou um termo de apostilamento. Importante lembrar que na Retificação todas as informações terão que ser enviadas novamente, não apenas as que sofreram alteração.

## Detalhes da Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload   |
|-------------|----------------|----------------------|
| /v1/orgaos/{cnpj}/contratos/{an
 o}/{sequencial}/termos/{sequen
 cialTermoContrato}             | PUT            | P Exemplo de Payload
 {
  "tipoTermoContratoId": 2,
  "numeroTermoContrato": "1",
  "objetoTermoContrato": "Termo de contrato 
 para exemplificar uso da API.",
  "dataAssinatura": "2021-07-22",
  "qualificacaoAcrescimoSupressao": false,
  "qualificacaoVigencia": false,
  "qualificacaoFornecedor": false,
  "qualificacaoReajuste": false,
  "qualificacaoInformativo": true,
  "informativoObservacao": "Exemplo de 
 retificação.",
  "niFornecedor": "12345678000190",
  "TipoPessoaFornecedor": "PJ",
  "nomeRazaoSocialFornecedor": "Fornecedor de 
 teste",                      |

## Exemplo Requisição (cURL)

curl -k -X PUT --header "Authorization: Bearer access\_token"

"${BASE\_URL}/v1/orgaos/10000000000003/contratos/2021/1/termos/1" -H "accept: */*" -H "Content-

Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: a URL possui os parâmetros {cnpj}, {ano}, {sequencial} e {sequencialTermoContrato}.

|   Id  | Campo                   | Tipo         | Obrigatório    | Descrição                   |
|-------|-------------------------|--------------|----------------|-----------------------------|
|    1  | cnpj                    | Texto (14)   | Sim            | Cnpj do órgão contratante   |
|    2  | ano                     | Inteiro      | Sim            | Ano do contrato             |
|    3  | sequencial              | Inteiro      | Sim            | (gerado pelo PNCP)
 Núil dtd                             |
|     4 | sequencialTermoContra
 to                         | Inteiro      | Sim            | q
 contrato (gerado pelo PNCP)
 Código da tabela de domínio Tipo                             |
|    5  | tipoTermoContratoId     | Inteiro      | Sim            | de termo de contrato        |
|    6  | numeroTermoContrato     | Texto (50)   | Sim            | Número do termo de contrato |
|    7  | objetoTermoContrato     | Texto (5120) | Sim            | Descrição do objeto do termo de 
 contrato                             |
|     8 | qualificacaoAcrescimoS
 upressao                         | Boleano      | Sim            | Identifica se o termo aditivo terá 
 acréscimo ou supressão.                             |
|    9  | qualificacaoVigencia    | Boleano      | Sim            | alteração na vigência e número de 
 parcelas.
 Identifica se o termo aditivo terá                             |
|   10  | qualificacaoFornecedor  | Boleano      | Sim            | alteração do fornecedor.
 Idifidiil                             |
|   11  | qualificacaoReajuste    | Boleano      | Sim            | Identifica se o termo aditivo altera 
 valor unitário do item do contrato                             |
|   12  | qualificacaoInformativo | Boleano      | Sim            | Identifica se o termo aditivo tem 
 alguma observação.                             |
|   13  | dataAssinatura          | Date         | Sim            | contrato
 Número de identificação do 
 fornecedor; CNPJCPF ou                             |
|   14  | niFornecedor            | Texto (30)   | Não            | Número de identificação do 
 fornecedor; CNPJ, CPF ou 
 identificador de empresa 
 estrangeira;                             |
|   15  | tipoPessoaFornecedor    | Texto (2)    | Não            | PJ Pessoa jurídica; PF Pessoa 
 física; PE - Pessoa estrangeira;
 Nome ou razão social do                             |
|    16 | nomeRazaoSocialFornec
 edor                         | Texto (100)  | Não            | Nome ou razão social do 
 fornecedor                             |

|   17 | niFornecedorSubContra
 tado                        | Texto (30)    | Não   | ç
 fornecedor subcontratado; CNPJ, 
 CPF ou identificador de empresa 
 estrangeira; Somente em caso de 
 subcontratação;                             |
|------|-----------------------|---------------|-------|-----------------------------|
|   18 | p
 ubContratado                       | Texto (2)     | Não   | física; PE - Pessoa estrangeira; 
 Somente em caso de 
 subcontratação;
 Nome ou razão social do                             |
|   19 | nomeRazaoSocialForne
 edorSubContratado                       | Texto (100)   | Não   | Somente em caso de 
 subcontratação;                             |
|  20  | informativoObservacao | Texto (5120)  | Não   | Observação do termo aditivo |
|  21  | fundamentoLegal       | Texto (5120)  | Não   | Fundamento legal do termo de 
 contrato                             |
|  22  | valorAcrescido        | Decimal       | Não   | Valor acrescido ao contrato 
 original; Precisão de 4 dígitos 
 decimais; Ex: 100.0000;                             |
|  23  | numeroParcelas        | Inteiro       | Não   | Número de parcelas          |
|  24  | valorParcela          | Decimal       | Não   | p
 dígitos decimais; Ex: 100.0000;
 Valor global do termo de contrato
 VldlNúd                             |
|  25  | valorGlobal           | Decimal       | Não   | Valor da parcela x Número de 
 parcelas; Precisão de 4 dígitos 
 decimais; Ex: 100.0000;                             |
|  26  | prazoAditadoDias      | Inteiro       | Não   | Prazo aditado em dias       |
|  27  | dataVigenciaInicio    | Date          | Não   | Data de início de vigência do 
 contrato                             |
|  28  | dataVigenciaFim       | Date          | Não   | Data do término da vigência do 
 contrato
 Mti/jtifiti                             |
|  29  | justificativa         | Texto (255)   | Não   | Motivo/justificativa para a 
 retificação dos atributos do termo 
 do contrato.                             |

## Dados de retorno

|   Id  | Campo    | Tipo        | brigat   | Descrição                       |
|-------|----------|-------------|----------|---------------------------------|
|    1  | location | Texto (255) | Sim      | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control - allow - credentials: true

access-control - allow - headers: Content - Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control - allow - methods: GET,PUT,POST,DELETE,OPTIONS

access-control - allow - origin: *

cache - control: no - cache,no-store,max-age=0,must-revalidate

content - length: 0

date: ?

expires: 0

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/contratos/2021/1/termos/1

pragma: no - cache

strict - transport-security: max-age=?

x-content - type-options: nosniff

x-firefox - spdy: ?

x-frame - options: DENY

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.6.3. Excluir Termo de Contrato

Serviço que permite remover um termo de contrato. O termo pode ser um termo aditivo, um termo de rescisão ou um termo de apostilamento.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}
 /{sequencial}/termos
 /{sequencialTermoContrato}                           | DELETE                    | {
  "justificativa": "motivo/justificativa para 
 exclusão do termo do contrato"
 }                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/contratos/2021/1/termos/1" -H "accept: */*"                           | curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/contratos/2021/1/termos/1" -H "accept: */*"                           | curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/contratos/2021/1/termos/1" -H "accept: */*"                           |

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano}, {sequencial} e {sequencialTermoContrato} na URL.

|   Id  | Campo         | Tipo        | Obrigatório    | Descrição                 |
|-------|---------------|-------------|----------------|---------------------------|
|    1  | cnpj          | Texto (14)  | Sim            | Cnpj do órgão contratante |
|    2  | ano           | Inteiro     | Sim            | Ano do contrato           |
|    3  | sequencia     | Inteiro     | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)                           |
|     4 | sequencialTermoCo
 ntrato               | Inteiro     | Sim            | Número sequencial do termo de 
 contrato (gerado pelo PNCP)                           |
|    5  | justificativa | Texto (255) | Não            | Motivo/justificativa para exclusão 
 do termo do contrato.                           |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.6.4. Consultar um Termo de Contrato

Serviço que permite recuperar um termo de contrato.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}
 /{sequencial}/termos
 /{sequencialTermoContrato}                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
|                           |                           |                           |

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano}, {sequencial} e {sequencialTermoContrato} na URL.

|   Id  | Campo      | Tipo       | Obrigatório    | Descrição                 |
|-------|------------|------------|----------------|---------------------------|
|    1  | cnpj       | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | ano        | Inteiro    | Sim            | Ano do contrato           |
|    3  | sequencial | Inteiro    | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)                           |
|     4 | sequencialTermoCo
 ntrato            | Inteiro    | Sim            | Número sequencial do termo de 
 contrato (gerado pelo PNCP)                           |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## Formato do Retorno

```
{ "unidade": { dados da unidade }, "fornecedor": { dados do fornecedor }, "niFornecedor": "string", "tipoPessoa": "PJ", "processo": "string", "contrato": { dados do contrato }, "tipoTermoContrato": { dados do tipo do termo de contrato }, "sequencialTermoContrato": 0, "fornecedorSubContratado": { dados do fornecedor subcontratado }, "unidadeSubrogada": { dados da unidade subrogada }, "dataVigenciaInicio": "yyyy -mm -dd", "orgaoEntidade": { dados do órgão do contrato }, "dataInclusao": "yyyy -mm -ddThh:mm:ss", "excluido": boolean, "compra": { dados da compra }, "informativoObservacao": "string", "prazoAditadoDias": 0, "qualificacaoAcrescimoSupressao": boolean, "qualificacaoVigencia": boolean, "qualificacaoFornecedor": boolean, "tipoPessoaSubContratada": "string", "numeroTermoContrato": "string", "objetoTermoContrato": "string", "nomeRazaoSocialFornecedor": "string", "informacaoComplementar": "string", "niFornecedorSubContratado": "string", "nomeFornecedorSubContratado": "string", "numeroContratoEmpenho": "string", "dataAssinatura": "yyyy -mm -dd", "dataVigenciaFim": "yyyy -mm -dd", "dataAtualizacao": "yyyy -mm -ddThh:mm:ss", "valorAcrescido": 0, "fundamentoLegal": "string", "valorParcela": 0, "valorGlobal": 0, "numeroParcelas": 0, "orgaoSubrogado": { dados do órgão subrogado }, "dataPublicacaoPncp": "yyyy -mm -ddThh:mm:ss" }
```

## 6.6.5. Consultar Todos os Termos de um Contrato

Serviço que permite recuperar a lista de termos de um contrato.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}/{s
 equencial}/termos                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| on: Bearer access_token" "${BASE_URL}/v1/orgaos
 H "*/*"                           | on: Bearer access_token" "${BASE_URL}/v1/orgaos
 H "*/*"                           | on: Bearer access_token" "${BASE_URL}/v1/orgaos
 H "*/*"                           |

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo      | Tipo       | Obrigatório    | Descrição                 |
|-------|------------|------------|----------------|---------------------------|
|    1  | cnpj       | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | ano        | Inteiro    | Sim            | Ano do contrato           |
|    3  | sequencial | Inteiro    | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)                           |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## Formato do Retorno

```
[ { "unidade": { dados da unidade }, "fornecedor": { dados do fornecedor }, "niFornecedor": "string", "tipoPessoa": "PJ", "processo": "string", "contrato": { dados do contrato }, "tipoTermoContrato": { dados do tipo do termo de contrato }, "sequencialTermoContrato": 0, "fornecedorSubContratado": { dados do fornecedor subcontratado }, "unidadeSubrogada": { dados da unidade subrogada }, "dataVigenciaInicio": "yyyy -mm -dd", "orgaoEntidade": { dados do órgão do contrato }, "dataInclusao": "yyyy -mm -ddThh:mm:ss", "excluido": boolean, "compra": { dados da compra }, "informativoObservacao": "string", "prazoAditadoDias": 0, "qualificacaoAcrescimoSupressao": boolean, "qualificacaoVigencia": boolean, "qualificacaoFornecedor": boolean, "tipoPessoaSubContratada": "string", "numeroTermoContrato": "string", "objetoTermoContrato": "string", "nomeRazaoSocialFornecedor": "string", "informacaoComplementar": "string", "niFornecedorSubContratado": "string", "nomeFornecedorSubContratado": "string", "numeroContratoEmpenho": "string", "dataAssinatura": "yyyy -mm -dd", "dataVigenciaFim": "yyyy -mm -dd", "dataAtualizacao": "yyyy -mm -ddThh:mm:ss", "valorAcrescido": 0, "fundamentoLegal": "string", "valorParcela": 0, "valorGlobal": 0, "numeroParcelas": 0, "orgaoSubrogado": { dados do órgão subrogado }, "dataPublicacaoPncp": "yyyy -mm -ddThh:mm:ss" } ]
```

## 6.6.6. Inserir Documento a um Termo de Contrato

Serviço que permite inserir um documento/arquivo a um termo de contrato. O sistema permite o upload de arquivos com as extensões listadas na seção: Tabelas de domínio - Extensões de arquivos aceitos pelas APIs de Documento.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}/{sequen
 cial}/termos/{sequencialTermo}/arquivos                           | POST                      | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| rl -k -X POST --header "Authorization: Bearer access_token" 
 AS0000000000003202i**                           | rl -k -X POST --header "Authorization: Bearer access_token" 
 AS0000000000003202i**                           | rl -k -X POST --header "Authorization: Bearer access_token" 
 AS0000000000003202i**                           |
| url k X POST header Authorization: Bearer access_token 
 ${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/termos/1/arquivos" -H "accept: */*" -H                           | url k X POST header Authorization: Bearer access_token 
 ${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/termos/1/arquivos" -H "accept: */*" -H                           | url k X POST header Authorization: Bearer access_token 
 ${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/termos/1/arquivos" -H "accept: */*" -H                           |
| {}gqp
 "Content-Type: multipart/form-data" -H "Titulo-Documento: TermoContrato-2021-1" -H "Tipo                           | {}gqp
 "Content-Type: multipart/form-data" -H "Titulo-Documento: TermoContrato-2021-1" -H "Tipo                           | {}gqp
 "Content-Type: multipart/form-data" -H "Titulo-Documento: TermoContrato-2021-1" -H "Tipo                           |
| ContentType: multipart/formdata H TituloDocumento: TermoContrato20211 H Tipo
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           | ContentType: multipart/formdata H TituloDocumento: TermoContrato20211 H Tipo
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           | ContentType: multipart/formdata H TituloDocumento: TermoContrato20211 H Tipo
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           |
| yppp
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           | yppp
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           | yppp
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           |
| yppp
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           | yppp
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           | yppp
 Documento-Id: 14" -F "arquivo=@TermoContrato-2021-1.pdf;type=application/pdf"                           |

## Dados de entrada

|   Id  | Campo            | Tipo       | Obrigatório    | Descrição                 |
|-------|------------------|------------|----------------|---------------------------|
|    1  | cnpj             | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | ano              | Inteiro    | Sim            | Ano do contrato           |
|    3  | sequencial       | Inteiro    | Sim            | Sequencial do contrato no PNCP; 
 Número sequencial gerado no 
 momento que o contrato foi 
 inserido no PNCP;
 Sequencial do termo de contrato                           |
|    4  | sequencialTermo  | Inteiro    | Sim            | gerado no momento que o termo 
 de contrato foi inserido no PNCP;                           |
|    5  | Titulo-Documento | Texto (50) | Sim            | Título do documento       |

## Dados de retorno

|   Id  | Campo    | Tipo        | Ob   | Descrição                       |
|-------|----------|-------------|------|---------------------------------|
|    1  | location | Texto (255) | Sim  | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

access-control -allow -credentials: true access-control -allow -headers: Content -Type,Authorization,X-Requested-With,Content-Length,Accept,Origin,

access-control -allow -methods: GET,PUT,POST,DELETE,OPTIONS

access-control -allow -origin: *

cache -control: no -cache,no-store,max-age=0,must-revalidate content -length: 0

date: ?

location: https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/contratos/2021/1/termos/1/arquivos/1

expires: 0 nome-bucket: ? pragma: no -cache strict -transport-security: max-age=? x-content -type-options: nosniff x-firefox -spdy: ? x-frame -options: DENY

x-xss-protection: 1; mode=block

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           201  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.6.7. Excluir Documento de um Termo de Contrato

Serviço que permite remover um documento/arquivo pertencente a um termo de contrato específico.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}/{
 sequencial}/termos/{sequencialTer
 mo}/arquivos/{sequencialDocumen
 to}                           | DELETE                    | {
  "justificativa": "motivo/justificativa para 
 exclusão do documento do termo do 
 contrato"
 }                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
|                           |                           |                           |

## Dados de entrada

Nota: alimentar os parâmetros {cnpj}, {ano}, {sequencial}, {sequencialTermo} e {sequencialDocumento} na URL.

|   Id  | Campo               | Tipo        | Obrigatório    | Descrição                 |
|-------|---------------------|-------------|----------------|---------------------------|
|    1  | cnpj                | Texto (14)  | Sim            | Cnpj do órgão contratante |
|    2  | ano                 | Inteiro     | Sim            | Ano do contrato           |
|    3  | sequencial          | Inteiro     | Sim            | Número sequencial do contrato 
 (gerado pelo PNCP)                           |
|    4  | sequencialTermo     | Inteiro     | Sim            | Número sequencial do termo de 
 contrato (gerado pelo PNCP)                           |
|    5  | sequencialDocumento | Inteiro     | Sim            | Número sequencial do documento 
 do contrato (gerado pelo PNCP)                           |
|    6  | justificativa       | Texto (255) | Não            | Motivo/justificativa para exclusão do 
 documento do termo do contrato                           |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.6.8. Consultar Todos os Documentos de um Termo de Contrato

Serviço que permite consultar a lista de documentos pertencentes a um termo de contrato específico.

## Detalhes da Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}/{sequen
 cial}/termos/{sequencialTermo}/arquivos                           | GET                       | Não se aplica             |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/termos/1/arquivos" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/termos/1/arquivos" -H "accept: */*"                           | curl -k -X GET --header "Authorization: Bearer access_token" 
 "${BASE_URL}/v1/orgaos/10000000000003/contratos/2021/1/termos/1/arquivos" -H "accept: */*"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} e {sequencialTermo} na URL.

|   Id  | Campo           | Tipo       | Obrigatório    | Descrição                 |
|-------|-----------------|------------|----------------|---------------------------|
|    1  | cnpj            | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | ano             | Inteiro    | Sim            | Ano do contrato           |
|    3  | sequencial      | Inteiro    | Sim            | Número sequencial gerado no 
 momento que o contrato foi 
 inserido no PNCP;
 Sequencial do termo de contrato                           |
|    4  | sequencialTermo | Inteiro    | Sim            | inserido no PNCP;
 Sequencial do termo de contrato
 no PNCP; Número sequencial 
 gerado no momento que o termo                           |

## Dados de retorno

|   Id  | Campo               | Tipo    | Descrição                                    |
|-------|---------------------|---------|----------------------------------------------|
|   1   | Documentos          | Lista   | Lista de documentos                          |
|   1.1 | sequencialDocumento | Inteiro | Número sequencial atribuído ao arquivo       |
|   1.2 | url                 | Texto   | URL para download do arquivo                 |
|   1.3 | tipoDocumentoNome   | Texto   | Nome do tipo de documento conforme PNCP      |
|   1.4 | titulo              | Texto   | Título referente ao arquivo                  |
|   1.5 | dataPublicacaoPncp  | Data    | Data de publicação do arquivo no portal PNCP |
|   1.6 | uri                 | Texto   | URI para download do arquivo                 |
|   1.7 | cnpj                | Texto   | Cnpj do órgão contratante                    |
|   1.8 | anoCompra           | Inteiro | Ano da compra associada ao Termo de 
 Contrato                                              |

|     |         | Sequencial da compra no PNCP; Número 
 sequencial gerado no momento que a com                      |
|-----|---------|----------------------|
| 0.9 | Inteiro | foi inserida no PNCP |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.6.9. Consultar Documento de um Termo de Contrato

Serviço que permite consultar um documento específico pertencente a um termo de contrato.

## Detalhes da Requisição

| Endpoint                                                   | Méto
 do 
 HTTP                                                            | Exem
 plo de 
 Paylo
 ad                                                            |
|------------------------------------------------------------|------------------------------------------------------------|------------------------------------------------------------|
| /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/termos/{sequencialTermo}/arquiv
 os/{sequencialDocumento}                                                            | GET                                                        | Não se 
 aplica                                                            |
| Exemplo Requisição (cURL)                                  | Exemplo Requisição (cURL)                                  | Exemplo Requisição (cURL)                                  |
| url -k -X GET --header "Authorization: Bearer accesstoken" | url -k -X GET --header "Authorization: Bearer accesstoken" | url -k -X GET --header "Authorization: Bearer accesstoken" |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} , {sequencialTermo} e {sequencialDocumento} na URL.

|   Id  | Campo      | Tipo       | Obrigatório    | Descrição                 |
|-------|------------|------------|----------------|---------------------------|
|    1  | cnpj       | Texto (14) | Sim            | Cnpj do órgão contratante |
|    2  | ano        | Inteiro    | Sim            | Ano do contrato           |
|    3  | sequencial | Inteiro    | Sim            | Sequencial do contrato no PNC
 Número sequencial gerado no                           |

## Manual de Integração PNCP– Versão 2.2.1

|   4  | sequencialTermo     | Inteiro    | Sim   | q
 inserido no PNCP;
 Sequencial do termo de contrato 
 no PNCP; Número sequencial 
 gerado no momento que o termo    |
|------|---------------------|------------|-------|---|
|   4  | sequencialDocumento | Inteiro    | Sim   | no momento que o documento fo
 inserido no PNCP;   |

## Dados de retorno

| Id     | Campo    | Tipo    | Descrição         |
|--------|----------|---------|-------------------|
| string | String   | ring st | string do arquivo |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7. Serviços de Plano de Contratações

## 6.7.1. Inserir Plano de Contratações

Serviço que permite inserir um plano de contratações de um ano de uma respectiva unidade no PNCP. O serviço requer que seja enviado pelo menos um item e o limite máximo de recebimento é de 1000 itens. Este serviço requer autenticação para ser acionado.

## Detalhes de Requisição

| Endpoint              | Método HTTP    | Exemplo de Payload   |
|-----------------------|----------------|----------------------|
| /v1/orgaos/{cnpj}/pca | POST           | {
  "codigoUnidade": "170456",
  "anoPca": 2022,
  "itensPlano": [
 {                      |

|    |    | "numeroItem": 1,
 "tiItP                                          |
|----|----|------------------------------------------|
|    |    | "categoriaItemPca": "1
 "l""1"                                          |
|    |    | "catalogo": "1",
 "classificacaoCatalogo":                                          |
|    |    | classificacaoCatalogo: 1,
 "classificacaoSuperiorCodigo": "7510"                                          |
|    |    | g,
  "classificacaoSuperiorCodigo": "7510",                                          |
|    |    | pg,
  " classificacaoSuperiorNome": "Artigos para                                          |
|    |    | "codigoItem": "468205"                   |
|    |    | "descricao": " Apontador Lápis",         |
|    |    | pp,
  "unidadeFornecimento": "Caixa 100 unidades"                                          |
|    |    | "quantidade": 500,                       |
|    |    | "valorUnitario": 50,00,                  |
|    |    | "valorOrcamentoExercicio": 25000,00,     |
|    |    | "renovacaoContrato": false,              |
|    |    | "dataDesejada": "2022-05-15",            |
|    |    | j,
 "unidadeRequisitante": "Departamento                                          |
|    |    | "unidadeRequisitante": "Departamen       |
|    |    | Administrativo,
 "grupoContratacaoCodigo": "",                                          |
|    |    | gpg,
 "grupoContratacaoNome": ""                                          |
|    |    | "grupoCon
 }                                          |
|    |    | },
 {                                          |
|    |    | {
 "numeroItem": 2                                          |
|    |    | ,
 "categoriaItemPca": "2",                                          |
|    |    | g
 "catalogo": "1",                                          |
|    |    | g,
 "classificacaoCatalogo": "2",                                          |
|    |    | classificacaoSuperiorCodigo: 547,
 " classificacaoSuperiorNome": "Serviço de                                          |
|    |    | acabamento e finalização dos edifícios", |
|    |    | acabamento e finalização dos edifícios", |
|    |    | g
  "descricao": " Troca Filtro - Veículo Automotivo",                                          |
|    |    | "unidadeFornecimento": "UNIDADE",        |
|    |    | "quantidade": 10,                        |
|    |    | q,
 "valorUnitario": 50,00,                                          |
|    |    | "valorTotal": 500,00,                    |
|    |    | aooa500,00,
  "valorOrcamentoExercicio": 500,00,                                          |
|    |    | "dataDesejada": "2022-07-10",
 "unidadeRequisitante": "Departamento Logístico"                                          |
|    |    | j
 "unidadeRequisitante": "Departamento Logístico"                                          |
|    |    | qpg
 "grupoContratacaoCodigo": "",                                          |
|    |    | gpg,
 "grupoContratacaoNome": ""                                          |
|    |    | }                                        |
|    |    | ]
 }                                          |

curl -k -X POST --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/pca " -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj} na URL.

|   1  | cnpj                        | Texto (14)    | Sim   | Cnpj do órgão a que a unidade do 
 PCA está vinculada
 Código da unidade; Unidade 
 deverá estar cadastrada para o                          |
|------|-----------------------------|---------------|-------|-------------------------|
| 2    | codigoUnidade               | Texto (20)    | Sim   | Código da unidade; Unidade 
 deverá estar cadastrada para o 
 órgão;                         |
| 3    | anoPca                      | Inteiro       | Sim   | Ano do PCA              |
| 4    | itensPlano                  | Lista         | Sim   | Lista de itens do Plano |
| 4.1  | numeroItem                  | Inteiro       | Sim   | Número do item no Plano (único e 
 sequencial crescente)
 Código da tabela de domínio 
 Categoria do Item do Plano de                         |
| 4.2  | categoriaItemPca            | Inteiro       | Sim   | g
 Categoria do Item do Plano de 
 Contratações
 Catálogo de materiais e/ ou                         |
| 4.3  | catalogo                    | Inteiro       | Sim   | CNBS (Catálogo Nacional de Bens 
 e Serviços); 2 - Outros;                         |
| 4.4  | classificacaoCatalogo       | Inteiro       | Sim   | Indica se é Material ou Serviço. 
 Domínio: 1 - Material; 2 - Serviço;
 Código da Classe do material ou 
 Grupo do serviço conforme                         |
| 4.5  | classificacaoSuperiorCodigo | Texto (100)   | Sim   | Grupo do serviço conforme 
 catálogo
 Descrição da Classe do material o                         |
| 4.6  | classificacaoSuperiorNome   | Texto (255)   | Sim   | Descrição da Classe do material ou 
 Grupo do serviço conforme 
 catálogo
 ódifil                         |
| 4.7  | pdmCodigo                   | Texto (100)   | Não   | Código PDM referente ao material 
 conforme o CNBS                         |
| 4.8  | pdmDescricao                | Texto (255)   | Não   | Descrição PDM referente ao 
 material conforme o CNBS                         |
| 4.9  | codigoItem                  | Texto (100)   | Não   | Código do Material ou Serviço 
 conforme o catálogo utilizado                         |
| 4.1  | descricao                   | Texto (2048)  | Não   | Descrição do material ou serviço 
 conforme catálogo utilizado                         |
| 4.11 | unidadeFornecimento         | Texto (255)   | Sim   | Unidade de fornecimento |

| 4.12               | quantidade              | Decimal
 (17,4)                     | Sim         | p
 (maior ou igual a zero). Precisão d
 4 dígitos decimais; Ex: 100.0000;
 Valor unitário do item (maior ou 
 igual a zero)Precisão de 4 dígitos                                  |
|--------------------|-------------------------|--------------------|-------------|---------------------------------|
| 4.13               | valorUnitario           | (17,4)             | Sim         | igual a zero). Precisão de 4 dígitos 
 decimais; Ex: 100.0000;
 Valor total do item (maior ou igua
 a zero)Precisão de 4 dígitos                                 |
| 4.14               | valorTotal              | Decimal
 (17,4)                    | Sim         | a zero). Precisão de 4 dígitos 
 decimais; Ex: 100.0000;
 Valor orçamentário estimado para 
 o exercício (maior ou igual a zero)                                 |
| 4.15               | valorOrcamentoExercicio | Decimal
 (17,4)                    | Sim         | o exercício (maior ou igual a zero)
 Precisão de 4 dígitos decimais; Ex
 100.0000;                                 |
| 4.16               | dataDesejada            | Date               | Sim         | Data desejada para a contrataçã |
| 4.17               | unidadeRequisitante     | Texto (255)        | Sim         | Nome da unidade requisitante    |
| 4.18               | grupoContratacaoCodigo  | Texto (100)        | Não         | Código da Contratação Futura    |
| 4.19               | grupoContratacaoNome    | Texto (255)        | Não         | Nome da Contratação Futura      |
| Dados de retorno   | Dados de retorno        | Dados de retorno   |             |                                 |
| Id                 | Campo                   | Tipo               | Obrigatório | Descrição                       |
| 1                  | location                | Texto (255)        | Sim         | Endereço http do recurso criado |
| Códigos de Retorno | Códigos de Retorno      | Códigos de Retorno |             |                                 |
| Código H           | TTP                     | Mensagem           | Mensagem    | Tipo                            |
| 200                | Created                 |                    |             | Sucesso                         |
| 400                | Bad Request             | ad Request         | ad Request  | Erro                            |
| 422                | Unprocessable Ent       |                    |             | Erro                            |

## 6.7.2. Excluir Plano de Contratações

Serviço que permite excluir um plano de contratações específico de uma unidade. Este serviço requer autenticação para ser acionado .

## Detalhes de Requisição

| Endpoint                                 | Método 
 HTTP                           | Exemplo de Payload        |
|------------------------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/pca/{ano}/{sequencial} | DELETE                    | {
  "justificativa": "motivo/justificativa para 
 a exclusão do plano"
 }                           |
| Exemplo Requisição (cURL)                | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/pca/2021/1" -H "accept: */*" -H "Content-Type: 
 application/json"                                          | curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/pca/2021/1" -H "accept: */*" -H "Content-Type: 
 application/json"                           | curl -k -X DELETE --header "Authorization: Bearer access_token"
 "${BASE_URL}/v1/orgaos/10000000000003/pca/2021/1" -H "accept: */*" -H "Content-Type: 
 application/json"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo         | Tipo        | Obrigatório    | Descrição   |
|-------|---------------|-------------|----------------|-------------|
|    1  | cnpj          | Texto (14)  | Sim            | Cnpj do órgão a que a unidade do 
 PCA está vinculada             |
|    2  | ano           | Inteiro     | Sim            | Ano do PCA  |
|    3  | sequencial    | Inteiro     | Sim            | qg
 momento que o plano da unidade
 foi inserido no PNCP             |
|    4  | justificativa | Texto (255) | Não            | Motivo/justificativa para exclusão 
 do plano             |

## Códigos de Retorno

|   Código HTTP  | Mensagem             | Tipo    |
|----------------|----------------------|---------|
|           200  | OK                   | Sucesso |
|           400  | Bad Request          | Erro    |
|           422  | Unprocessable Entity | Erro    |

## 6.7.3. Consultar Plano por Órgão e Ano

Serviço que permite consultar o plano de contratações anual específico de um determinado órgão.

## Detalhes de Requisição

| Endpoint                                | Método 
 HTTP                           | Exemplo de Payload        |
|-----------------------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/pca/{ano}/consolidado | GET                       | Não se aplica             |
| Exemplo Requisição (cURL)               | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/consolidado' 
 \ -H 'accept: */*'                                         | curl -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/consolidado' 
 \ -H 'accept: */*'                           | curl -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/consolidado' 
 \ -H 'accept: */*'                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj} e {ano} na URL.

|   Id  | Campo    | Tipo       | Obrigatório    | Descrição     |
|-------|----------|------------|----------------|---------------|
|    1  | cnpj     | Texto (14) | Sim            | Cnpj do órgão |
|    2  | ano      | Inteiro    | Sim            | Ano do PCA    |

## Dados de retorno

|   Id  | Campo       | Tipo    | Descrição                    |
|-------|-------------|---------|------------------------------|
|    1  | cnpj        | Texto   | CNPJ do órgão                |
|    2  | razaoSocial | Texto   | Razão Social do órgão        |
|    3  | esfera      | Texto   | Esfera do órgão              |
|    4  | poder       | Texto   | Poder do órgão               |
|    5  | anoPca      | Inteiro | Ano do Plano de Contratações |
|    6  | quantidade  | Decimal 
 (17,4)         | Quantidade total de itens do plano do órgão 
 (somatório da qtde de itens de todos os planos                              |

|    |                    |        | das unidades). Precisão de até 4 dígitos decimais; 
 Ex: 10.0001;                                               |
|----|--------------------|--------|-----------------------------------------------|
| 7  | valorTotal         | (17,4) | Valor total do plano do órgão (somatório do valor 
 total dos planos das unidades). Precisão de até 4 
 dígitos decimais; Ex: 100.0001;                                               |
| 8  | dataPublicacaoPncp | Data   | Data da publicação do primeiro plano de unidade
 no PNCP                                               |
| 9  | dataAtualizacao    | Data   | Data da última atualização do registro de PCA |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.4. Consultar Plano das Unidades por Órgão e Ano

Serviço que permite consultar os dados dos planos de contratações das unidades de um órgão específico em determinado ano.

## Detalhes de Requisição

| Endpoint                                             | Endpoint                                             | Método 
 HTTP                          | Exemplo de Payload       |
|------------------------------------------------------|------------------------------------------------------|--------------------------|--------------------------|
| /v1/orgaos/{cnpj}/pca/{ano}/consolidado/unidades GET | /v1/orgaos/{cnpj}/pca/{ano}/consolidado/unidades GET | GET                      | Não se aplica            |
| xemplo Requisição (cURL)                             | xemplo Requisição (cURL)                             | xemplo Requisição (cURL) | xemplo Requisição (cURL) |
| curl 
 'https                                                      |                                                      | 'GET'                    | \                        |
| 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/consolidado/unidades' \ -
 H 'accept: */*'                                                      | 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/consolidado/unidades' \ -
 H 'accept: */*'                                                      | 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/consolidado/unidades' \ -
 H 'accept: */*'                          | 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/consolidado/unidades' \ -
 H 'accept: */*'                          |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo         | Tipo       | Obrigatório    | Descrição   |
|-------|---------------|------------|----------------|-------------|
|    1  | cnpj          | Texto (14) | Sim            | Cnpj do órgão a que a unidade do 
 PCA está vinculada             |
|    2  | ano           | Inteiro    | Sim            | Ano do PCA  |
|    3  | pagina        | Inteiro    | Não            | Número da página com os registros 
 a serem recuperados             |
|    4  | tamanhoPagina | Inteiro    | Não            | Quantidade de registros por página 
 a serem recuperados             |

## Dados de retorno

| Id    | Campo              | Tipo    | Descrição                                     |
|-------|--------------------|---------|-----------------------------------------------|
| 1     |                    | Lista   | Lista de PCAs por Unidade                     |
| 1.1   | cnpj               | Texto   | CNPJ do órgão                                 |
| 1.2   | razaoSocial        | Texto   | Razão Social do órgão                         |
| 1.3   | esfera             | Texto   | Esfera do órgão                               |
| 1.4   | poder              | Texto   | Poder do órgão                                |
| 1.5   | codigoUnidad       | Texto   | Código da Unidade Responsável                 |
| 1.6   | nomeUnidade        | Texto   | Nome da Unidade Responsável                   |
| 1.7   | anoPca             | Inteiro | Ano do Plano de Contratações                  |
| 1.8   | sequencialPca      | Inteiro | gerado no momento que o plano de 
 contratações da unidade foi inserido no PNCP
 Número de Controle PNCP do Plano (id pca                                               |
| 1.9   | numeroControlePNCP | Texto   | Número de Controle PNCP do Plano (id pca 
 PNCP)                                               |
| 1.10  | dataPublicacaoPncp | Data    | Data da publicação da Ata no PNCP             |
| 1.11  | dataAtualizacao    | Data    | Data da última atualização do registro da Ata |
|       | quantidade         | Decimal 
 (174)         | Quantidade de itens do plano. Precisão de até 4 
 dígitos decimais; Ex: 100001;                                               |
| 113   | valorTotal         | Decimal 
 (174)         | Valor total do plano. Precisão de até 4 dígitos 
 decimais; Ex: 100.0001;                                               |
| 1.13  | valorTotal         | Decimal 
 (17,4)         | Valor total do plano. Precisão de até 4 dígitos 
 decimais; Ex: 100.0001;                                               |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.5. Consultar Valores de Planos de Contratação de um Órgão por Categoria

Serviço que permite consultar a quantidade de itens e o valor total dos itens por categoria de item dos planos de contratações de um órgão específico em determinado ano, opcionalmente filtrando por uma dada Categoria de Item.

## Detalhes de Requisição

| Endpoint                                         | Endpoint                                                          | Método 
 HTTP                                                                   | Exemplo de Payload                                                |
|--------------------------------------------------|-------------------------------------------------------------------|-------------------------------------------------------------------|-------------------------------------------------------------------|
| /v1/orgaos/{cnpj}/pca/{ano}/valorcategoriaitem G | /v1/orgaos/{cnpj}/pca/{ano}/valorcategoriaitem G                  | GET                                                               | Não se aplica                                                     |
| xemplo Requisição (cURL)                         | xemplo Requisição (cURL)                                          | xemplo Requisição (cURL)                                          | xemplo Requisição (cURL)                                          |
| curl -X 'GET' \ 'https://treina.pn               | s://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022 | s://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022 | s://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022 |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj} e {ano} na URL.

|   Id  | Campo         | Tipo       | Obrigatório    | Descrição   |
|-------|---------------|------------|----------------|-------------|
|    1  | cnpj          | Texto (14) | Sim            | Cnpj do órgão a que a unidade do 
 PCA está vinculada             |
|    2  | ano           | Inteiro    | Sim            | Ano do PCA  |
|    3  | categoriaItem | Inteiro    | Não            | Código da categoria do item 
 conforme tabela de domínio             |

## Dados de retorno

|   Id  | Campo             | Tipo    | Descrição                                  |
|-------|-------------------|---------|--------------------------------------------|
|   1   |                   | Lista   | Lista de informações                       |
|   1.1 | categoriaItemNome | Texto   | Nome da categoria do item conforme tabela de 
 domínio Categoria do Item do Plano de 
 Contratações                                            |
|   1.2 | quantidadeItens   | Decimal 
 (17,4)         | Quantidade de itens do plano por categoria |
|   1.3 | valorTotal        | Decimal 
 (17,4)         | Valor total por categoria                  |
|   1.4 | categoriaItemId   | Inteiro | Código da categoria do item conforme tabela de 
 domínio Categoria do Item do Plano de 
 Contratações                                            |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.6. Consultar Plano de Contratação Consolidado (Plano de Contratações de uma Unidade e Ano)

Serviço que permite consultar um plano de contratações específico de uma unidade em determinado ano .

## Detalhes de Requisição

| Endpoint    | Método    | Exemplo de Payload   |
|-------------|-----------|----------------------|
|             | HTTP      | Exemplo de Payload   |

| /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/consolidado GET    | /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/consolidado GET    | GET                       | Não se aplica             |      |
|-------------------------------------------------------------|-------------------------------------------------------------|---------------------------|---------------------------|------|
| Exemplo Requisição (cURL)                                   | Exemplo Requisição (cURL)                                   | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |      |
| curl                                                        | -X                                                          | 'GET'                     |                           | \    |
| 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/1/consolidado' 
 'accept: */*'                                                             | 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/1/consolidado' 
 'accept: */*'                                                             | 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/1/consolidado' 
 'accept: */*'                           | 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/1/consolidado' 
 'accept: */*'                           | \ -H |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo      | Tipo       | Obrigatório    | Descrição   |
|-------|------------|------------|----------------|-------------|
|    1  | cnpj       | Texto (14) | Sim            | Cnpj do órgão a que a unidade do 
 PCA está vinculada             |
|    2  | ano        | Inteiro    | Sim            | Ano do PCA  |
|    3  | sequencial | Inteiro    | Sim            | q; 
 Número sequencial gerado no 
 momento que o plano da unidade 
 foi inserido no PNCP             |

## Dados de retorno

|   Id  | Campo              | Tipo    | Descrição                                   |
|-------|--------------------|---------|---------------------------------------------|
|    1  | cnpj               | Texto   | CNPJ do Órgão                               |
|    2  | codigoUnidade      | Texto   | Código da Unidade Responsável               |
|    3  | nomeUnidade        | Texto   | Nome da Unidade Responsável                 |
|    4  | anoPca             | Inteiro | Ano do Plano de Contratações                |
|    5  | numeroControlePNCP | Texto   | Número de Controle PNCP do Plano da Unidade |
|    6  | quantidade         | Decimal 
 (17,4)         | Quantidade de itens do Plano da Unidade. 
 Precisão de até 4 dígitos decimais; Ex: 10.0001;                                             |
|    7  | valorTotal         | Decimal 
 (17,4)         | da Unidade. Precisão de até 4 dígitos decimais; 
 Ex: 100.0001;                                             |
|    8  | dataPublicacaoPncp | Data    | Data da publicação do Plano no PNCP         |
|    9  | dataAtualizacao    | Data    | Data da última atualização do Plano         |

|   10  | usuario    | String    | Nome do Usuário/Sistema que enviou a compra   |
|-------|------------|-----------|-----------------------------------------------|
|   11  | municipio  | String    | Município da Unidade Responsável              |
|   12  | uf         | String    | Sigla da unidade federativa da Unidade 
 Responsável                                               |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.7. Consultar Valores de um Plano de Contratação por Categoria

Serviço que permite consultar a quantidade de itens e o valor total dos itens por categoria de item dos planos de contratações de uma Unidade específica em determinado ano, opcionalmente filtrando por uma dada Categoria de Item.

## Detalhes de Requisição

| Endpoint                                                        | Método 
 HTTP                           | Exemplo de Payload        |
|-----------------------------------------------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/valorcategoriaitem GET | GET                       | Não se aplica             |
| Exemplo Requisição (cURL)                                       | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
|                                                                 |                           |                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj} e {ano} na URL.

|   Id  | Campo    | Tipo       | Obrigatório    | Descrição          |
|-------|----------|------------|----------------|--------------------|
|    1  | cnpj     | Texto (14) | Sim            | PCA está vinculada |

| 2    | ano           | Inteiro    | Sim    | Ano do PCA   |
|------|---------------|------------|--------|--------------|
| 3    | sequencial    | Inteiro    | Sim    | Número sequencial do PCA da 
 Unidade (gerado pelo PNCP)              |
|      | categoriaItem | Inteiro    | Não    | Categoria do Item do Plano de 
 Contratações              |

## Dados de retorno

|   Id  | Campo             | Tipo    | Descrição                                  |
|-------|-------------------|---------|--------------------------------------------|
|   1   |                   | Lista   | Lista de informações                       |
|   1.1 | categoriaItemNome | Texto   | Nome da categoria do item conforme tabela de 
 domínio Categoria do Item do Plano de 
 Contratações                                            |
|   1.2 | quantidadeItens   | Decimal 
 (17,4)         | Quantidade de itens do plano por categoria |
|   1.3 | valorTotal        | Decimal 
 (17,4)         | Valor total por categoria                  |
|   1.4 | categoriaItemId   | Inteiro | Código da categoria do item conforme tabela d
 domínio Categoria do Item do Plano de 
 Contratações                                            |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.8. Inserir Itens de Plano de Contratação

Serviço que permite inserir itens em um plano de contratação de um ano de uma respectiva unidade no PNCP. O serviço requer que seja enviado pelo menos um item e o limite

máximo de recebimento é de 1000 itens. Este serviço requer autenticação para ser acionado.

## Detalhes de Requisição

| Endpoint    | Método HTTP    | Exemplo de Payload                  |
|-------------|----------------|-------------------------------------|
| /v1/orgaos/{cnpj}
 //{}/{il}/it             | POST           | "numeroItem": 1,
 "categoriaItemPca": "1",
 "catalogo": "1",
 "classificacaoCatalogo": "1",
 "classificacaoSuperiorCodigo": 
 " classificacaoSuperiorNome": 
 critório",                                     |
|             |                | {
 "numeroItem": 1,
 "tiItP""1"                                     |
|             |                | "categoriaItemPca": "1"
 "tl""1"                                     |
|             |                | g
 "catalogo": "1",                                     |
|             |                | g,
 "classificacaoCatalogo": "1",                                     |
|             |                | g,
 "classificacaoSuperiorCodigo": "7510",                                     |
|             |                | classificacaoSuperiorCodigo: 7510,
  " classificacaoSuperiorNome": "Artigos para                                     |
|             |                | escritório",                        |
|             |                | escritório,
 "codigoItem": "468205                                     |
|             |                | g,
 "descricao": "Apontador Lápis",                                     |
|             |                | pp,
  "unidadeFornecimento": "Caixa 100 unidades"                                     |
|             |                | "quantidade": 500,                  |
|             |                | "valorUnitario": 50,00,             |
|             |                | "valorTotal": 25000,00,             |
|             |                | "valorOrcamentoExercicio": 25000,00 |
|             |                | "renovacaoContrato": false,         |
|             |                | ,
 "dataDesejada": "2022-05-15",                                     |
|             |                | j,
 "unidadeRequisitante": "Departame                                     |
|             |                | q
 Administrativo",                                     |
|             |                | dsao,
 "grupoContratacaoCodigo": "",                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | gp
 },                                     |
|             |                | },                                  |
|             |                | {
 "numeroItem": 2,                                     |
|             |                | ,
 "categoriaItemPca": "2",                                     |
|             |                | g
 "catalogo": "1",                                     |
|             |                | g
 "classificacaoCatalogo": "2",                                     |
|             |                | g,
 "classificacaoSuperiorCodigo": "547",                                     |
|             |                | classificacaoSuperiorNome: Serviço de 
 acabamento e finalização dos edifícios",                                     |
|             |                | pç
 acabamento e finalização dos edifícios",                                     |
|             |                | g,
 "descricao": "Pintura industrial"                                     |
|             |                | desccaotua dusta,
 "unidadeFornecimento": "UNIDADE",                                     |
|             |                | "quantidade": 10,                   |
|             |                | quantidade: 10,
 "valorUnitario": 5000                                     |
|             |                | ,,
 "valorTotal": 500,00,                                     |
|             |                | "valorOrcamentoExercicio": 500,00,  |
|             |                | "valorOrcamentoExercicio": 500,00,
 "dataDesejada": "20220710"                                     |
|             |                | daaesejada000,
 "unidadeRequisitante": "Departamento Logístico",                                     |
|             |                | j,
 "unidadeRequisitante": "Departamento Logístico",                                     |
|             |                | "grupoContratacaoCodigo": "",
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | ]                                   |
|             |                |                                     |
|             |                | }                                   |
|             |                | }                                   |
|             |                | }                                   |
|             |                | }                                   |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | g                                   |
|             |                | grupoContratacaoNome                |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | gg
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | grupoContratacaoNome: 
  }                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | ]                                   |
|             |                | ]                                   |
|             |                | cabamento e finalização dos edifícios
 "codigoItem": "1090",                                     |
|             |                | "descricao": "Pintura industrial",  |
|             |                | "unidadeFornecimento": "UNIDADE",   |
|             |                | "unidadeFornecimento": "UNIDADE",
 10                                     |
|             |                | unidadeFornecimento: UNIDADE,
 "quantidade": 10                                     |
|             |                | ,
 "quantidade": 10,                                     |
|             |                | "quantidade": 10,                   |
|             |                | quantidade: 10,
 "valorUnitario": 5000                                     |
|             |                | q
 "valorUnitario": 50,00,                                     |
|             |                | valorUnitario: 50,00,
 "valorTotal": 500,00,                                     |
|             |                | ,,
 "valorTotal": 500,00,                                     |
|             |                | ,,
 "valorTotal": 500,00,                                     |
|             |                | "valorOrcamentoExercicio": 500,00,  |
|             |                | "valorOrcamentoExercicio": 500,00,  |
|             |                | valorOrcamentoExercicio: 500,00,
 "dataDesejada": "2022-07-10",                                     |
|             |                | dataDesejada: 20220710,
 "unidadeRequisitante": "Departamento Logístico",                                     |
|             |                | j,
 "unidadeRequisitante": "Departamento Logístico",                                     |
|             |                | j,
 "unidadeRequisitante": "Departamento Logístico",                                     |
|             |                | qpg
 "grupoContratacaoCodigo": "",                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | gpg,
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                |                                     |
|             |                | }                                   |
|             |                | }                                   |
|             |                | }                                   |
|             |                | }                                   |
|             |                | }                                   |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                |                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }
 ]                                     |
|             |                | }                                   |
|             |                | gpg
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | "unidadeRequisitante": "Departamento Logístico"
 "grupoContratacaoCodigo": ""                                     |
|             |                | "grupoContratacaoCodigo": "",
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoCodigo": "",
 "CttN"""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | "unidadeRequisitante": "Departamento Logístico"
 "CttCdi"""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoCodigo: ,
 "grupoContratacaoNome": ""                                     |
|             |                | gpg,
 "grupoContratacaoNome": ""                                     |
|             |                | gpg,
 "grupoContratacaoNome": ""                                     |
|             |                | gpg,
 "grupoContratacaoNome": ""                                     |
|             |                | gpg,
 "grupoContratacaoNome": ""                                     |
|             |                | gpg,
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | grupoContratacaoNome: 
 }                                     |
|             |                | grupoContratacaoNome: 
  }                                     |
|             |                |                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | gg
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | gpg
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | gpg
 "grupoContratacaoNome": ""                                     |
|             |                | grupoContratacaoNome:               |
|             |                | gpg,
 "grupoContratacaoNome": ""                                     |
|             |                | "grupoContratacaoNome": ""
 }                                     |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |
|             |                | "grupoContratacaoNome": ""          |

## Exemplo Requisição (cURL)

curl -k -X POST --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/pca/2022/1/itens " -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo                       | Tipo         | Obrigatório    | Descrição   |
|-------|-----------------------------|--------------|----------------|-------------|
|   1   | cnpj                        | Texto (14)   | Sim            | Cnpj do órgão a que a unidade do 
 PCA está vinculada             |
|   2   | ano                         | Inteiro      | Sim            | Ano do PCA  |
|   3   | sequencial                  | Inteiro      | Sim            | qgp
 PNCP para o plano incluído             |
|   4   |                             | Lista        | Sim            | Lista de itens do Plano
 údilúi             |
|   4.1 | numeroItem                  | Inteiro      | Sim            | Número do item no Plano (único e 
 sequencial crescente)
 Código da tabela de domínio 
 CtidItdPld             |
|   4.2 | categoriaItemPca            | Inteiro      | Sim            | Código da tabela de domínio 
 Categoria do Item do Plano de 
 Contratações
 Catálogo de materiais e/ ou             |
|   4.3 | catalogo                    | Inteiro      | Sim            | serviços utilizado. Domínio: 1 -
 CNBS (Catálogo Nacional de Bens 
 e Serviços); 2 - Outros;             |
|   4.4 | classificacaoCatalogo       | Inteiro      | Sim            | Domínio: 1 - Material; 2 - Serviço;
 Código da Classe do material ou 
 Grupo do serviço conforme             |
|   4.5 | classificacaoSuperiorCodigo | Texto (100)  | Sim            | Grupo do serviço conforme 
 catálogo
 Descrição da Classe do material 
 ou Grupo do serviço conforme             |
|   4.6 | classificacaoSuperiorNome   | Texto (255)  | Sim            | ou Grupo do serviço conforme 
 catálogo
 Código PDM referente ao materia             |
|   4.7 | pdmCodigo                   | Texto (100)  | Não            | Código PDM referente ao material 
 conforme o CNBS             |
|   4.8 | pdmDescricao                | Texto (255)  | Não            | Descrição PDM referente ao 
 material conforme o CNBS
 Código do Material ou Serviço             |
|   4.9 | codigoItem                  | Texto (100)  | Sim            | Código do Material ou Serviço 
 conforme o catálogo utilizado             |
|   4.1 | descricao                   | Texto (2048) | Sim            | Descrição do material ou serviço 
 conforme catálogo utilizado             |

"

## Manual de Integração PNCP– Versão 2.2.1

|   4.11  | unidadeFornecimento     | Texto (255)    | Sim    | Unidade de fornecimento          |
|---------|-------------------------|----------------|--------|----------------------------------|
|    4.12 | quantidade              | Decimal 
 (17,4)                | Sim    | Quantidade (maior ou igual a 
 zero)                                  |
|    4.13 | valorUnitario           | Decimal 
 (17,4)                | Sim    | Valor unitário do item (maior ou 
 igual a zero)                                  |
|  414    | valorTotal              | Decimal 
 (17,4)                | Sim    | Valor total do item (maior ou igual 
 a zero)                                  |
|    4.15 | valorOrcamentoExercicio | Decimal 
 (17,4)                | Sim    | Valor orçamentário estimado para 
 o exercício (maior ou igual a zero)                                  |
|    4.16 | dataDesejada            | Date           | Sim    | Data desejada para a contratação |
|    4.17 | unidadeRequisitante     | Texto (255)    | Sim    | Nome da unidade requisitante     |
|    4.18 | grupoContratacaoCodigo  | Texto (100)    | Não    | Código da Contratação Futura     |
|    4.19 | grupoContratacaoNome    | Texto (255)    | Não    | Nome da Contratação Futura       |
|    4.19 | grupoContratacaoNome    | Texto (255)    | Não    | Nome da Contratação Futura       |

## Dados de retorno

|   Id  | Campo    | Tipo        | Obrigat   | Descrição                       |
|-------|----------|-------------|-----------|---------------------------------|
|    1  | location | Texto (255) | Sim       | Endereço http do recurso criado |

## Exemplo de Retorno

Retorno:

[

"

https://treina.pncp.gov.br/api/pncp/v1/orgaos/10000000000003/pca/2021/1/itens/1

]

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.9 . Consultar Itens do Plano de Contratações de uma Unidade e Ano

Serviço que permite recuperar a lista de itens pertencentes a um determinado Plano de Contratações Anual (PCA) de uma unidade em determinado ano, opcionalmente filtrando via Categoria do Item.

## Detalhes de Requisição

| Endpoint                                       | Método 
 HTTP                           | Exemplo de Payload        |
|------------------------------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens | GET                       | Não se aplica             |
| Exemplo Requisição (cURL)                      | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/1/itens' \ -H 
 'accept: */*'                                                | curl -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/1/itens' \ -H 
 'accept: */*'                           | curl -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/1/itens' \ -H 
 'accept: */*'                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

|   Id  | Campo         | Tipo       | Obrigatório    | Descrição   |
|-------|---------------|------------|----------------|-------------|
|    1  | cnpj          | Texto (14) | Sim            | Cnpj do órgão a que a unidade do 
 PCA está vinculada             |
|    2  | ano           | Inteiro    | Sim            | Ano do PCA  |
|    3  | sequencial    | Inteiro    | Sim            | Sequencial do PCA no PNCP; 
 Número sequencial gerado no 
 momento que o plano da unidade 
 foi inserido no PNCP             |
|    4  | categoria     | Inteiro    | Não            | Código da tabela de domínio 
 Categoria do Item do Plano de 
 Contratações             |
|    5  | pagina        | Inteiro    | Não            | Número da página com os registros 
 a serem recuperados             |
|    6  | tamanhoPagina | Inteiro    | Não            | Quantidade de registros por página 
 a serem recuperados             |

## Dados de retorno

|   1  |                             | Lista        | ista Itens de PCAs por Unidade   |
|------|-----------------------------|--------------|----------------------------------|
| 1.1  | cnpj                        | Texto        | CNPJ do Órgão                    |
| 1.2  | codigoUnidade               | Texto        | Código da Unidade Responsável    |
| 1.3  | nomeUnidade                 | Texto        | Nome da Unidade Responsável      |
| 1.4  | anoPca                      | Inteiro      | Ano do Plano de Contratações da Unidade
 úl dddd                                  |
| 1.5  | sequencialPca               | Inteiro      | pelo PNCP)
 Número do item no Plano (único e sequencial                                  |
| 1.6  | numeroItem                  | Inteiro      | crescente)
 Código da categoria do item conforme tabela de 
 díiCidIdPld                                  |
| 1.7  | categoriaItemPcaid          | Inteiro      | domínio Categoria do Item do Plano de 
 Contratações
 Nome da Indicação se Item é Material ou Serviç                                  |
| 1.8  | nomeClassificacao           | Texto        | çç
 Domínio: 1 - Material; 2 - Serviço;                                  |
| 1.9  | nomeCatalogo                | Texto        | utilizado. Domínio: 1 - CNBS (Catálogo Nacional 
 de Bens e Serviços); 2 - Outros;                                  |
| 1.1  | classificacaoSuperiorCodigo | Texto (100)  | Código da Classe do material ou Grupo do 
 serviço conforme catálogo                                  |
| 1.11 | classificacaoSuperiorNome   | Texto (255)  | Descrição da Classe do material ou Grupo do 
 serviço conforme catálogo
 CódiPDM fttil f                                  |
| 1.12 | pdmCodigo                   | Texto (100)  | Código PDM referente ao material conforme o 
 CNBS                                  |
| 1.13 | pdmDescricao                | Texto (255)  | Descrição PDM referente ao material conforme o 
 CNBS                                  |
| 1.14 | codigoItem                  | Texto (100)  | Código do Material ou Serviço conforme o 
 catálogo utilizado                                  |
| 1.15 | descricao                   | Texto (2048) | Descrição do material ou serviço conforme 
 catálogo utilizado                                  |
| 1.16 | unidadeFornecimento         | Texto        | Unidade de fornecimento          |
| 1.17 | quantidade                  | Decimal      | Quantidade do item do plano de contratação 
 (maior ou igual a zero). Precisão de até 4 dígitos 
 decimais; Ex: 10.0001;                                  |

|   1.18  | valorUnitario           | Decimal   | Valor unitário do item (maior ou igual a zero). 
 Precisão de até 4 dígitos decimais; Ex: 100.0001                                             |
|---------|-------------------------|-----------|---------------------------------------------|
|    1.19 | valorTotal              | Decimal   | (g)
 Precisão de até 4 dígitos decimais; Ex: 100.0001;
 Valor orçamentário estimado para o exercício                                             |
|    1.2  | valorOrcamentoExercicio | Decimal   | çp
 (maior ou igual a zero). Precisão de até 4 dígitos 
 decimais; Ex: 100.0001;                                             |
|    1.21 | dataDesejada            | Data      | Data desejada para a contratação            |
|    1.22 | unidadeRequisitante     | Texto     | Nome da unidade requisitante                |
|    1.23 | grupoContratacaoCodigo  | Texto     | Código da Contratação Futura                |
|    1.24 | grupoContratacaoNome    | Texto     | Nome da Contratação Futura                  |
|    1.25 | dataPublicacaoPncp      | Data      | Data da publicação do item do plano no PNCP |
|    1.26 | dataInclusao            | Data      | Data da inclusão do registro do item do plano no 
 PNCP
 Data da última atualização do registro do item do                                             |
|    1.27 | dataAtualizacao         | Data      | Data da última atualização do registro do item do 
 plano                                             |
|    1.28 | catalogoId              | Inteiro   | utilizado. Domínio: 1 - CNBS (Catálogo Nacional 
 de Bens e Serviços); 2 - Outros;
 Nome da categoria do item conforme tabela de                                             |
|    1.29 | categoriaItemPcaNome    | Inteiro   | Nome da categoria do item conforme tabela de 
 domínio Categoria do Item do Plano de 
 Contratações                                             |
|    1.3  | ClassificacaocatalogoId | Texto     | gç
 Serviço. Domínio: 1 - Material; 2 - Serviço;                                             |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | OK                    | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.10. Retificar Parcialmente Item de Plano de Contratação

Serviço que permite retificar um item específico de um plano de contratação no PNCP. Este serviço requer autenticação para ser acionado. Na retificação parcial, você precisa enviar apenas as informações que sofreram alteração. Por exemplo, se você desejar apenas atualizar a categoria de um item, você deve informar apenas o atributo categoriaItemPca e ignorar todos os demais atributos.

## Detalhes de Requisição

| Endpoint    | Método 
 HTTP   | Exemplo de Payload   |
|-------------|---|----------------------|
| g{pj}
 /pca/{ano}/{sequencial}/itens/{numeroItem}             |   | {
  "numeroItem": 2,
  "categoriaItemPca": "2",
  "catalogo": "1",
  "classificacaoCatalogo": "2",
  "classificacaoSuperiorCodigo": "547",
  " classificacaoSuperiorNome": "Serviço 
 de acabamento e finalização dos 
 edifícios",
  "codigoItem": "1090",
  "descricao": "Pintura industrial",
  "unidadeFornecimento": "UNIDADE",
  "quantidade": 10,
  "valorUnitario": 50,00,
 "valorTotal": 50000                      |

## Exemplo Requisição (cURL)

curl -k -X PATCH --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/pca/2022/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} e {numeroItem} na URL.

| Id    | Campo      | Tipo    | Obrigatório    | Descrição          |
|-------|------------|---------|----------------|--------------------|
| cn    | Texto (14) | Sim     | Sim            | PCA está vinculada |

|   2  | ano                       | Inteiro      | Sim    | Ano do PCA   |
|------|---------------------------|--------------|--------|--------------|
|   3  | sequencial                | Inteiro      | Sim    | Número sequencial gerado pelo 
 PNCP para o plano incluído
 Número do item no Plano (único e              |
|   4  | numeroItem                | Inteiro      | Não    | Número do item no Plano (único e 
 sequencial crescente)
 Código da tabela de domínio              |
|   5  | categoriaItemPca          | Inteiro      | Não    | Categoria do Item do Plano de 
 Contratações
 Catálogo de materiais e/ ou 
 serviços utilizado. Domínio: 1 -              |
|   6  | catalogo                  | Inteiro      | Não    | (g
 e Serviços); 2 - Outros;
 Indica se é Material ou Serviço.              |
|   7  | classificacaoCatalogo     | Inteiro      | Não    | Domínio: 1 - Material; 2 - Serviço
 óddldl              |
|   8  | classificacaoSuperiorC    | Texto (100)  | Não    | Código da Classe do material ou 
 Grupo do serviço conforme 
 catálogo
 Descrição da Classe do material              |
|   9  | classificacaoSuperiorNome | Texto (255)  | Não    | Descrição da Classe do material 
 ou Grupo do serviço conforme 
 catálogo              |
|  10  | pdmCodigo                 | Texto (100)  | Não    | Código PDM referente ao materia
 conforme o CNBS
 DiãPDM f              |
|  11  | pdmDescricao              | Texto (255)  | Não    | Descrição PDM referente ao 
 material conforme o CNBS
 CódidMtil Si              |
|  12  | codigoItem                | Texto (100)  | Não    | Código do Material ou Serviço 
 conforme o catálogo utilizado
 Diãdtil i              |
|  13  | descricao                 | Texto (2048) | Não    | Descrição do material ou serviço 
 conforme catálogo utilizado              |
|  14  | unidadeFornecimento       | Texto (255)  | Não    | Unidade de fornecimento
 Quantidade do item do plano              |
|  15  | quantidade                | Decimal 
 (17,4)              | Não    | (maior ou igual a zero). Precisão 
 de 4 dígitos decimais; Ex: 
 100.0000;              |
|  15  | quantidade                | (17,4)       | Não    | de 4 dígitos decimais; Ex: 
 100.0000;
 Valor unitário do item (maior ou              |
|  16  | valorUnitario             | Decimal 
 (17,4)              | Não    | Valor unitário do item (maior ou 
 igual a zero). Precisão de 4 dígitos 
 decimais; Ex: 100.0000;              |

|   17  | valorTotal              | Decimal 
 (17,4)              | Não   | Valor total do item (maior ou igua
 a zero). Precisão de 4 dígitos 
 decimais; Ex: 100.0000;                                  |
|-------|-------------------------|-------------|-------|----------------------------------|
|   18  | valorOrcamentoExercicio | Decimal 
 (17,4)             | Não   | Valor orçamentário estimado para 
 o exercício (maior ou igual a zero). 
 Precisão de 4 dígitos decimais; Ex: 
 100.0000;                                  |
|   19  | dataDesejada            | Date        | Não   | Data desejada para a contratação |
|   20  | unidadeRequisitante     | Texto (255) | Não   | Nome da unidade requisitante     |
|   21  | grupoContratacaoCodigo  | Texto (100) | Não   | Código da Contratação Futura     |
|   22  | grupoContratacaoNome    | Texto (255) | Não   | Nome da Contratação Futura       |
|   23  | justificativa           | Texto (255) | Não   | Motivo/justificativa para 
 retificação do item do plano                                  |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | Created               | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.11 . Retificar Parcialmente Itens de um Plano de Contratação

Serviço que permite retificar itens de um plano de contratação no PNCP. Este serviço requer autenticação para ser acionado. Na retificação parcial, você precisa enviar apenas as informações que sofreram alteração. Por exemplo, se você desejar apenas atualizar a categoria de um item, você deve informar apenas o atributo categoriaItemPca e ignorar todos os demais atributos.

## Detalhes de Requisição

| Endpoint          | Método HTTP    | Exemplo de Payload   |
|-------------------|----------------|----------------------|
| /v1/orgaos/{cnpj} | PATCH          | “lista”: [
 {                      |

## Exemplo Requisição (cURL)

curl -k -X PATCH --header "Authorization: Bearer access\_token" "${BASE\_URL}/v1/orgaos /10000000000003/pca/2022/1/itens" -H "accept: */*" -H "Content-Type: application/json" --data "@/home/objeto.json"

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

Id

Campo

Tipo

Obrigatório

Descrição

|   1  | cnpj                        | Texto (14)     | Sim   | Cnpj do órgão a que a unidad
 do PCA está vinculada                         |
|------|-----------------------------|----------------|-------|-------------------------|
| 2    | ano                         | Inteiro        | Sim   | Ano do PCA              |
| 3    | sequencial                  | Inteiro        | Sim   | Número sequencial gerado pe
 PNCP para o plano incluído                         |
| 4    | lista                       | Lista          | Sim   | Lista de Itens do Plano |
| 4.1  | numeroItem                  | Inteiro        | Sim   | e sequencial crescente)
 Código da tabela de domínio 
 Categoria do Item do Plano de                         |
| 4.2  | categoriaItemPca            | Inteiro        | Não   | Contratações
 Catálogo de materiais e/ ou 
 serviços utilizado. Domínio: 1                         |
| 4.3  | catalogo                    | Inteiro        | Não   | e Serviços); 2 - Outros;
 Idié Mil Si                         |
| 4.4  | classificacaoCatalogo       | Inteiro        | Não   | Indica se é Material ou Serviço. 
 Domínio: 1 - Material; 2 - Serviço
 Código da Classe do material ou                         |
| 4.5  | classificacaoSuperiorCodigo | Texto (100)    | Não   | pç
 catálogo
 Descrição da Classe do material 
 ou Grupo do serviço conforme                         |
| 4.6  | classificacaoSuperiorNome   | Texto (255)    | Não   | ou Grupo do serviço conforme 
 catálogo
 Código PDM referente ao                         |
| 4.7  | pdmCodigo                   | Texto (100)    | Não   | Código PDM referente ao 
 material conforme o CNBS                         |
| 4.8  | pdmDescricao                | Texto (255)    | Não   | Descrição PDM referente ao 
 material conforme o CNBS                         |
| 4.9  | codigoItem                  | Texto (100)    | Não   | Código do Material ou Serviç
 conforme o catálogo utilizad                         |
| 4.1  | descricao                   | Texto (2048)   | Não   | Descrição do material ou serviç
 conforme catálogo utilizado                         |
| 4.11 | unidadeFornecimento         | Texto (255)    | Não   | Unidade de fornecimento |
| 4.12 | quantidade                  | Decimal (17,4) | Não   | Qp
 (maior ou igual a zero). Precisã                         |

<!-- image -->

<!-- image -->

|                    |                         |                       |                       | de 4 dígitos decimais; Ex
 100.0000;                               |
|--------------------|-------------------------|-----------------------|-----------------------|-------------------------------|
| 4.13               | valorUnitario           | Decimal (17,4)        | Não                   | igual a zero). Precisão de 4 
 dígitos decimais; Ex: 100.0000
 Valor total do item (maior ou 
 igual a zero). Precisão de 4                               |
| 4.14               | valorTotal              |                       |                       | dígitos decimais; Ex: 100.000
 Valor orçamentário estimado 
 para o exercício (maior ou igu                               |
|                    | valorOrcamentoExercicio | Decimal (17,4         | Não                   | decimais; Ex: 100.0000;       |
| 4.17               | unidadeRequisitante     | Texto (255)           | Não                   | Nome da unidade requisitan    |
| 4.18               | d                       |                       | ã                     |                               |
| 4.18               | grupoContratacaoCodigo  | Texto (100            | Não                   | Código da Contratação Futura  |
| 4.1                | grupoContratacaoNome    | Texto (255)           | Não                   | Nome da Contratação Futura    |
| 5                  | ustificativa            | Texto (255            | Não                   | retificação dos itens do plan |
| Códigos de Retorno | Códigos de Retorno      | Códigos de Retorno    | Códigos de Retorno    | Códigos de Retorno            |
| Código HTTP        | Código HTTP             | Mensagem              | Mensagem              | Tipo                          |
| 200                | Created                 | Created               | Created               | Sucesso                       |
| 400                | Bad Request             | Bad Request           | Bad Request           | Erro                          |
| 422                | Unprocessable Entity    | Unprocessable Entity  | Unprocessable Entity  | Erro                          |
| 500                | Internal Server Error   | Internal Server Error | Internal Server Error | Erro                          |

## 6.7.12. Excluir Item de Plano de Contratação

Serviço que permite excluir um item específico de um plano de contratação no PNCP. Este serviço requer autenticação para ser acionado.

## Detalhes de Requisição

| Endpoint                  | Método 
 HTTP                           | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}
 /pca/{ano}/{sequencial}/itens/{numeroItem                           | DELETE                    | {
  "justificativa": ""
 }                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/pca/2022/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objeto.json"                           | curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/pca/2022/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objeto.json"                           | curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/pca/2022/1/itens/1" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objeto.json"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano}, {sequencial} e {numeroItem} na URL.

|   Id  | Campo         | Tipo        | Obrigatório    | Descrição   |
|-------|---------------|-------------|----------------|-------------|
|    1  | cnpj          | Texto (14)  | Sim            | Cnpj do órgão a que a unidade do 
 PCA está vinculada             |
|    2  | ano           | Inteiro     | Sim            | Ano do PCA  |
|    3  | sequencial    | Inteiro     | Sim            | Número sequencial gerado pelo 
 PNCP para o plano incluído
 NúdiPl(úi             |
|    4  | numeroItem    | Inteiro     | Sim            | Número do item no Plano (único e 
 sequencial crescente)             |
|    5  | justificativa | Texto (255) | Não            | Motivo/justificativa para exclusão 
 do item do plano             |

## Códigos de Retorno

|   Código HTTP  | Mensagem              | Tipo    |
|----------------|-----------------------|---------|
|           200  | Delete                | Sucesso |
|           400  | Bad Request           | Erro    |
|           422  | Unprocessable Entity  | Erro    |
|           500  | Internal Server Error | Erro    |

## 6.7.13. Excluir Itens de um Plano de Contratação

Serviço que permite excluir itens de um plano de contratação no PNCP. Este serviço requer autenticação para ser acionado.

## Detalhes de Requisição

| Endpoint                  | Método HTTP               | Exemplo de Payload        |
|---------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}
 pca/{ano}/{sequencial}/itens                           | DELETE                    | {
  "listaNumerosItens": [1, 2, 7, 89],
  "justificativa": ""                           |
| Exemplo Requisição (cURL) | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/pca/2022/1/itens" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objetojson"                           | curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/pca/2022/1/itens" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objetojson"                           | curl -k -X DELETE --header "Authorization: Bearer access_token" "${BASE_URL}/v1/orgaos
 /10000000000003/pca/2022/1/itens" -H "accept: */*" -H "Content-Type: application/json" --data 
 "@/home/objetojson"                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj}, {ano} e {sequencial} na URL.

| Ca                 | Campo                | Tipo               | Obrigatório        | Descrição                          |
|--------------------|----------------------|--------------------|--------------------|------------------------------------|
| c                  | pj                   | Texto (14)         | Sim                | Cnpj do órgão a que a unidade d
 PCA está vinculada                                    |
| 2                  | o                    | Inteiro            | Sim                | Ano do PCA                         |
|                    |                      |                    |                    | Número sequencial gerado pelo      |
| sequ               | quencial             | Inteiro            | Sim                | PNCP para o plano incluído         |
|                    |                      |                    |                    | Lista de números (únicos) dos      |
| li                 | NumerosItens         | Lista              | Sim                | itens do PCA a serem excluíd       |
| 5 j                |                      |                    |                    | Motivo/justificativa para exclusão |
| 5                  | justificativa        | 255)               | Não                | dos itens do plano                 |
| Códigos de Retorno | Códigos de Retorno   | Códigos de Retorno | Códigos de Retorno |                                    |
| Código HTTP        |                      | Mensagem           | Mensagem           | Tipo                               |
| 200                | Delete               |                    |                    | Sucesso                            |
| 400                | Bad Request          |                    |                    | Erro                               |
| 422                | Unprocessable Entity |                    |                    | Erro                               |

<!-- image -->

<!-- image -->

## 6.7.14 . Gerar arquivo CSV de Itens dos Planos por Órgão

Serviço que gera arquivo CSV contendo as informações de itens dos Planos de Contratações Anuais das Unidades associadas ao Órgão e Ano recebidos .

## Detalhes de Requisição

| Endpoint                        | Método 
 HTTP                           | Exemplo de Payload        |
|---------------------------------|---------------------------|---------------------------|
| /v1/orgaos/{cnpj}/pca/{ano}/csv | GET                       | Não se aplica             |
| Exemplo Requisição (cURL)       | Exemplo Requisição (cURL) | Exemplo Requisição (cURL) |
| url -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/csv' \ -H 
 accept: */*'                                 | url -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/csv' \ -H 
 accept: */*'                           | url -X 'GET' \ 'https://treina.pncp.gov.br/api/pncp/v1/orgaos/00394460000141/pca/2022/csv' \ -H 
 accept: */*'                           |

## Dados de entrada

Nota: alimentar o parâmetro {cnpj} e {ano} na URL.

|   Id  | Campo    | T         | Tipo    | Desc       |
|-------|----------|-----------|---------|------------|
|    1  | cnpj     | Texto (14 | Sim     | Cnpj do órgão a que a unidade do 
 PCA está vinculada            |
|    2  | ano      | Inteiro   | Sim     | Ano do PCA |

## Dados de retorno

|   Id  | Campo    | Tipo    | Descrição                    |
|-------|----------|---------|------------------------------|
|    1  | Texto    | Texto   | Arquivo texto em formato csv |

## Códigos de Retorno

|   Código HTTP  | Mensagem             | Tipo    |
|----------------|----------------------|---------|
|           200  | OK                   | Sucesso |
|           400  | Bad Request          | Erro    |
|           422  | Unprocessable Entity | Erro    |

500

Internal Server Error

Erro

## 7. Suporte

Em caso de problemas durante o processo de integração do seu sistema com o PNCP, por favor entre em contato com a Central de Atendimento do Ministério da Economia (https://portaldeservicos.economia.gov.br) ou pelo telefone 0800 978 9001.

Informações sobre Credenciamento e assuntos correlatos ao Ministério da Economia podem ser obtidas em https://www.gov.br/compras/pt-br/pncp .

