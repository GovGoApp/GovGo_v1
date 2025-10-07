# Plano de Integração com Pagar.me

## 1. Cadastro e Homologação

* Criar conta PJ na **Pagar.me / Stone**.
* Enviar documentos (CNPJ, contrato social, conta bancária).
* Solicitar ativação do **PIX** (termo adicional).
* Ativar ambiente de **sandbox** para testes de desenvolvimento.

## 2. Estrutura de Billing e Planos

* Definir planos internos (Free, Plus, Pro, Corp).
* Criar planos correspondentes na Pagar.me via painel/API.
* Configurar trial, valores e periodicidade.
* Garantir correspondência entre IDs locais e IDs Pagar.me.

## 3. Arquitetura de Integração

* Criar módulo **`gateway_interface`** ou adaptador de gateway.
* Implementar modo **sandbox/produção** para alternar chaves de API.
* Usar chamadas REST seguras, com validação de resposta e erros.
* Armazenar no **Supabase** os vínculos (usuário ↔ plano ↔ assinatura).

## 4. Conexão via API

* Criar endpoints para:

  * **Assinaturas** (criar, cancelar, renovar).
  * **Pagamentos avulsos** (cartão, boleto, Pix).
  * **Consultas de status** (assinatura, fatura, transação).
* Configurar **webhooks** para receber eventos de pagamento.
* Criar endpoint `/webhook/pagarme` para tratar confirmações e falhas.
* Validar **assinaturas digitais dos webhooks** (HMAC ou chave pública).

## 5. Sincronização e Consistência

* Atualizar status das assinaturas e faturas a cada webhook recebido.
* Implementar **rotina de reconciliação** (verificação periódica via API).
* Testar cenários de pagamento, cancelamento e falha no sandbox.

## 6. Front‑end / Checkout

* Usar checkout **transparente/embutido** (tokenização de cartão).
* Coletar dados do cliente e enviar para o backend com segurança.
* Backend faz a cobrança e retorna status/links (boleto ou QR Pix).
* Exibir mensagens claras de sucesso, falha ou pendência.

## 7. Fluxo de Ativação e Controle de Acesso

* Após pagamento aprovado, **habilitar plano** no sistema.
* Se boleto/Pix, aguardar confirmação via webhook.
* Gerenciar renovações automáticas mensais.
* Validar limites de uso (função `ensure_capacity()`) conforme plano.

## 8. Operação e Monitoramento

* Monitorar logs de requisições API e respostas.
* Registrar eventos locais para auditoria.
* Configurar alertas para falhas críticas (ex: webhook não entregue).
* Verificar relatórios de liquidação e recebíveis.

## 9. Boas Práticas e Recomendações

* Testar amplamente em **sandbox** antes da produção.
* Fazer **soft‑launch** com poucos usuários pagantes.
* Desenvolver camada de abstração desde o início (futuro multi‑gateway).
* Armazenar **metadados Pagar.me** (ids, status, vencimentos) localmente.
* Implementar **reconciliação automática**.
* Controlar retries/backoff para evitar bloqueio por excesso de requisições.
* Documentar fluxos de assinatura, cancelamento e mudança de plano.
* Planejar contingência/migração futura (exportação de tokens e dados).
