# Plano de Integração com Stripe - GovGo

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Por que Stripe?](#por-que-stripe)
3. [Arquitetura da Integração](#arquitetura-da-integração)
4. [Fluxo de Pagamento do Usuário](#fluxo-de-pagamento-do-usuário)
5. [Passo a Passo da Implementação](#passo-a-passo-da-implementação)
6. [Stripe Elements (Formulário de Cartão)](#stripe-elements-formulário-de-cartão)
7. [Backend: gvg_billing.py](#backend-gvg_billingpy)
8. [Webhooks](#webhooks)
9. [Segurança](#segurança)
10. [Testes](#testes)
11. [Deploy e Produção](#deploy-e-produção)

---

## 🎯 Visão Geral

O **Stripe** é uma plataforma de pagamentos online completa que permite aceitar cartões de crédito, débito, PIX, boleto e outros métodos de pagamento. É amplamente utilizado globalmente e oferece:

- ✅ **API REST bem documentada**
- ✅ **SDKs oficiais** (Python, Ruby, Node.js, PHP, Java, Go, .NET)
- ✅ **Webhooks robustos** com assinatura HMAC
- ✅ **Suporte a assinaturas recorrentes** (perfeito para nosso modelo de planos)
- ✅ **Dashboard completo** para gerenciamento
- ✅ **Modo de teste (sandbox)** sem necessidade de aprovação
- ✅ **Suporte a múltiplas moedas** (incluindo BRL)
- ✅ **Stripe Elements** (componentes seguros para coletar dados de cartão sem PCI compliance)
- ✅ **Forte no Brasil** via integrações locais

---

## 💡 Por que Stripe?

### Vantagens sobre Pagar.me:
1. **API mais padronizada e madura**
2. **Melhor documentação e exemplos**
3. **SDKs oficiais atualizados constantemente**
4. **Webhooks mais confiáveis** (retry automático com backoff exponencial)
5. **Dashboard mais intuitivo**
6. **Stripe Elements** (formulário de cartão seguro e já pronto)
7. **Suporte internacional** (caso o GovGo cresça para outros países)

### Métodos de Pagamento Suportados no Brasil:
- 💳 **Cartões** (Visa, Mastercard, Amex, Elo, Hipercard)
- 📱 **PIX** (via Stripe Brazil)
- 🧾 **Boleto** (geração automática)
- 🍎 **Apple Pay** / **Google Pay** (automático quando habilitado)

---

## 🏗️ Arquitetura da Integração

### Estrutura de Módulos (Simplificada - 100% Python)

```
search/gvg_browser/
├── gvg_billing.py           # ⭐ TODA lógica Stripe aqui (Checkout Session, Subscription, Webhook)
├── gvg_limits.py            # (Já existe) Limites por plano
├── gvg_usage.py             # (Já existe) Agregador de métricas
└── GvG_Search_Browser.py    # (Atualizar) UI Modal + Callbacks
```

**✅ Sem pasta `gateway/`**
**✅ Sem JavaScript/assets**
**✅ 100% Python**

Toda integração Stripe fica em `gvg_billing.py` e toda UI em `GvG_Search_Browser.py`.

### Fluxo de Dados (100% Python - Stripe Checkout Session)

```
┌─────────────────────────────┐
│   Usuário clica "Upgrade"   │
│   no Modal Planos (GSB)     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Callback Python (GSB)      │
│  chama gvg_billing.py       │
│  create_checkout_session()  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  gvg_billing.py             │
│  stripe.checkout.Session    │
│  .create(...)               │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Stripe API retorna         │
│  checkout_url               │
│  (ex: checkout.stripe.com)  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  GSB redireciona usuário    │
│  para checkout_url          │
│  (página hospedada Stripe)  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Usuário preenche cartão    │
│  NA PÁGINA DO STRIPE        │
│  - Número, validade, CVV    │
│  - Formulário seguro        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Stripe processa pagamento  │
│  - Autoriza cartão          │
│  - Cria subscription        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Stripe redireciona para    │
│  success_url ou cancel_url  │
│  (de volta ao GovGo)        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Stripe envia Webhook       │
│  POST /billing/webhook      │
│  - checkout.session.        │
│    completed                │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  gvg_billing.py             │
│  - Valida HMAC              │
│  - Atualiza user_settings   │
│  - plan_id → novo plano     │
└─────────────────────────────┘
```

**🎯 Diferença chave**: Usuário **sai do site** por alguns segundos para preencher cartão na **página segura do Stripe**, depois **volta automaticamente**.

---

## 🎬 Fluxo de Pagamento do Usuário

### Experiência do Usuário (UX)

1. **Modal Planos** (já existente)
   - Usuário vê 4 planos: FREE, PLUS, PRO, CORP
   - Cada plano mostra: Preço, Limites, Consumo atual
   - Botão "Upgrade" em cada plano

2. **Clique em "Upgrade"**
   - Modal Planos fecha
   - Python callback em `GvG_Search_Browser.py` chama `gvg_billing.create_checkout_session()`
   - Recebe `checkout_url` do Stripe
   - **Redireciona usuário** para página do Stripe (nova aba ou mesma janela)

3. **Página de Pagamento do Stripe**
   - Usuário é redirecionado para `https://checkout.stripe.com/c/pay/cs_xxx...`
   - Formulário **profissional e seguro** criado pelo Stripe
   - Preenche:
     - Número do cartão
     - Validade (MM/AA)
     - CVV
     - CEP
   - Dados **nunca passam pelo servidor GovGo** (PCI compliance automático)
   - Validação automática (número válido, data futura, CVV correto)

4. **Confirmação de Pagamento**
   - Usuário clica "Assinar" na página do Stripe
   - Stripe processa pagamento (autorização do banco)
   - Feedback visual do próprio Stripe: "Processando... ⏳"

5. **Resultado**
   - ✅ **Sucesso**: 
     - Stripe redireciona para `https://www.govgo.com.br/checkout/success`
     - GovGo exibe mensagem "Upgrade realizado!"
     - Badge atualiza para "PLUS" (via webhook)
   - ❌ **Erro**: 
     - Stripe exibe mensagem na própria página (ex: "Cartão recusado")
     - Usuário pode tentar novamente ou clicar "Voltar" para `cancel_url`

---

## 🚀 Passo a Passo da Implementação

### **Fase 1: Setup Inicial**

#### 1.1. Criar Conta Stripe
1. Acesse [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. Cadastre-se (email/senha)
3. **Não precisa ativar conta real para testar** (modo test já está disponível!)

#### 1.2. Obter Chaves API

**Passo 1**: Acesse [https://dashboard.stripe.com/test/apikeys](https://dashboard.stripe.com/test/apikeys)

**Passo 2**: Copie as chaves:

| Chave | Formato | Onde Usar | Exemplo |
|-------|---------|-----------|---------|
| **Secret key** (test) | `sk_test_...` | Backend Python (NUNCA commitar!) | `sk_test_51ABC123...` |
| **Publishable key** (test) | `pk_test_...` | ❌ Não usar (sem JavaScript) | - |

**⚠️ IMPORTANTE**: 
- **Secret key** é a única que você precisa!
- Mantenha secreta (nunca commitar no git)
- Use apenas no backend Python

#### 1.3. Configurar `.env`

Adicione ao arquivo `.env` (crie se não existir):

```env
# Stripe (Modo Test)
STRIPE_SECRET_KEY=sk_test_SUA_CHAVE_AQUI

# Stripe Price IDs (copiar após criar produtos)
STRIPE_PRICE_PLUS=
STRIPE_PRICE_PRO=
STRIPE_PRICE_CORP=

# Stripe Webhook Secret (copiar após criar webhook)
STRIPE_WEBHOOK_SECRET=

# URL base do site (para success/cancel URLs)
BASE_URL=http://localhost:8050
```

**✅ Adicione `.env` ao `.gitignore`**:
```bash
echo ".env" >> .gitignore
```

#### 1.4. Instalar Biblioteca Python

```bash
pip install stripe
```

Adicionar ao `requirements.txt`:
```
stripe>=7.0.0
```

---

### **Fase 2: UI no GvG_Search_Browser.py (100% Python)**

#### Callback para Redirecionar ao Stripe Checkout

No `GvG_Search_Browser.py`, adicionar callback que redireciona ao clicar em "Upgrade":

```python
@app.callback(
    Output('url', 'href'),  # Componente dcc.Location para redirecionamento
    [Input({'type': 'upgrade-btn', 'plan_code': ALL}, 'n_clicks')],
    [State('store-auth', 'data')],
    prevent_initial_call=True
)
def redirect_to_stripe_checkout(n_clicks_list, auth_data):
    """Redireciona para página de pagamento do Stripe ao clicar em Upgrade."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    # Identificar qual botão foi clicado
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    plan_code = json.loads(trigger_id)['plan_code']
    
    user = auth_data.get('user', {})
    uid = user.get('uid')
    email = user.get('email')
    name = user.get('name')
    
    if not uid:
        raise PreventUpdate
    
    # Criar Checkout Session no Stripe via gvg_billing
    from gvg_billing import create_checkout_session
    
    result = create_checkout_session(
        user_id=uid,
        plan_code=plan_code,
        email=email,
        name=name
    )
    
    if 'error' in result:
        # Exibir toast de erro (adicionar Output para notificação)
        print(f"Erro ao criar checkout: {result['error']}")
        raise PreventUpdate
    
    # Redirecionar para página do Stripe
    checkout_url = result['checkout_url']
    return checkout_url
```

#### Adicionar componente dcc.Location (se não existir)

```python
# No layout principal do GvG_Search_Browser.py
app.layout = html.Div([
    dcc.Location(id='url', refresh=True),  # Para redirecionamento
    # ... resto do layout
])
```

#### Páginas de Sucesso e Cancelamento

Adicionar rotas simples para quando usuário voltar do Stripe:

```python
# Callback para exibir página de sucesso
@app.callback(
    Output('main-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/checkout/success':
        return html.Div([
            html.H2('✅ Pagamento Confirmado!', style={'color': 'green'}),
            html.P('Seu plano foi atualizado com sucesso.'),
            html.A('Voltar para busca', href='/', className='btn btn-primary')
        ], style={'textAlign': 'center', 'padding': '50px'})
    
    elif pathname == '/checkout/cancel':
        return html.Div([
            html.H2('❌ Pagamento Cancelado', style={'color': 'orange'}),
            html.P('Você cancelou o processo de upgrade.'),
            html.A('Voltar para busca', href='/', className='btn btn-secondary')
        ], style={'textAlign': 'center', 'padding': '50px'})
    
    else:
        # Página principal (busca)
        return [
            # ... layout normal
        ]
```

---

### **Fase 3: Backend - gvg_billing.py**

Reescrever `gvg_billing.py` **removendo funções mock** e adicionando integração Stripe com **Checkout Session**:

```python
"""Camada Billing com Stripe (Checkout Session + Subscription + Webhook)."""

import os
import stripe
from typing import Dict, Any, List, Optional
from gvg_database import db_fetch_all, db_fetch_one, db_execute
from gvg_debug import debug_log as dbg

# Configurar Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Mapa de planos -> Price IDs do Stripe
PLAN_PRICE_MAP = {
    'PLUS': os.getenv('STRIPE_PRICE_PLUS'),
    'PRO': os.getenv('STRIPE_PRICE_PRO'),
    'CORP': os.getenv('STRIPE_PRICE_CORP'),
}

# =============================
# Funções de Planos
# =============================
def get_system_plans() -> List[Dict[str, Any]]:
    """Busca planos ativos do banco."""
    sql = """
    SELECT id, code, name, (price_month_brl * 100)::int AS price_cents, 'month' AS billing_period,
           limit_consultas_per_day, limit_resumos_per_day, limit_boletim_per_day, limit_favoritos_capacity
      FROM public.system_plans
     WHERE active = true
     ORDER BY price_month_brl ASC, id ASC
    """
    rows = db_fetch_all(sql, ctx="BILLING.get_system_plans")
    return [dict(r) if isinstance(r, dict) else {
        'id': r[0], 'code': r[1], 'name': r[2], 'price_cents': r[3], 'billing_period': r[4],
        'limit_consultas_per_day': r[5], 'limit_resumos_per_day': r[6], 
        'limit_boletim_per_day': r[7], 'limit_favoritos_capacity': r[8]
    } for r in rows]


def get_user_settings(user_id: str) -> Dict[str, Any]:
    """Busca configurações e plano do usuário."""
    if not user_id:
        return _fallback_free()
    
    sql = """
    SELECT us.user_id, sp.code AS plan_code, sp.name AS plan_name,
           sp.limit_consultas_per_day, sp.limit_resumos_per_day, 
           sp.limit_boletim_per_day, sp.limit_favoritos_capacity,
           us.gateway_customer_id, us.gateway_subscription_id
      FROM public.user_settings us
      JOIN public.system_plans sp ON sp.id = us.plan_id
     WHERE us.user_id = %s
    """
    row = db_fetch_one(sql, (user_id,), as_dict=True, ctx="BILLING.get_user_settings")
    
    if not row:
        return _fallback_free()
    
    return {
        'user_id': user_id,
        'plan_code': row['plan_code'],
        'plan_name': row['plan_name'],
        'gateway_customer_id': row.get('gateway_customer_id'),
        'gateway_subscription_id': row.get('gateway_subscription_id'),
        'limits': {
            'consultas': row['limit_consultas_per_day'],
            'resumos': row['limit_resumos_per_day'],
            'boletim_run': row['limit_boletim_per_day'],
            'favoritos': row['limit_favoritos_capacity'],
        }
    }


def _fallback_free() -> Dict[str, Any]:
    """Retorna configuração FREE padrão."""
    return {
        'user_id': '',
        'plan_code': 'FREE',
        'plan_name': 'Free',
        'gateway_customer_id': None,
        'gateway_subscription_id': None,
        'limits': {
            'consultas': 5,
            'resumos': 1,
            'boletim_run': 1,
            'favoritos': 10,
        }
    }


# =============================
# Stripe: Checkout Session (Principal)
# =============================
def create_checkout_session(
    user_id: str,
    plan_code: str,
    email: str,
    name: str
) -> Dict[str, Any]:
    """Cria Checkout Session para redirecionar usuário à página do Stripe.
    
    Esta é a função PRINCIPAL para upgrade de plano.
    Retorna checkout_url para redirecionar o usuário.
    """
    price_id = PLAN_PRICE_MAP.get(plan_code.upper())
    if not price_id:
        return {'error': f'Plano {plan_code} não encontrado'}
    
    # URL base do site
    base_url = os.getenv('BASE_URL', 'http://localhost:8050')
    success_url = f"{base_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/checkout/cancel"
    
    try:
        session = stripe.checkout.Session.create(
            customer_email=email,  # Stripe cria ou reutiliza customer automaticamente
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',  # Recorrência mensal
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'internal_user_id': user_id,
                'plan_code': plan_code,
                'user_name': name
            }
        )
        
        dbg('STRIPE', f"Checkout Session criado: {session.id} user={user_id} plan={plan_code}")
        
        return {
            'checkout_url': session.url,
            'session_id': session.id
        }
        
    except stripe.error.StripeError as e:
        dbg('STRIPE', f"Erro ao criar Checkout Session: {e}")
        return {'error': str(e)}


# =============================
# Stripe: Subscription (Admin)
# =============================
def cancel_subscription(user_id: str) -> Dict[str, Any]:
    """Cancela assinatura do usuário."""
    settings = get_user_settings(user_id)
    subscription_id = settings.get('gateway_subscription_id')
    
    if not subscription_id:
        return {'error': 'Nenhuma assinatura ativa'}
    
    try:
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        dbg('STRIPE', f"Subscription cancelada: {subscription_id}")
        
        return {'status': 'canceled', 'ends_at': subscription.current_period_end}
        
    except stripe.error.StripeError as e:
        dbg('STRIPE', f"Erro ao cancelar subscription: {e}")
        return {'error': str(e)}


# =============================
# Webhook Handler
# =============================
def verify_webhook(payload: str, signature: str) -> Dict[str, Any]:
    """Verifica assinatura HMAC do webhook Stripe."""
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET não configurado")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )
        
        dbg('STRIPE', f"Webhook verificado: {event['type']} id={event['id']}")
        
        return {
            'event_type': event['type'],
            'event_id': event['id'],
            'data': event['data']['object']
        }
        
    except stripe.error.SignatureVerificationError as e:
        dbg('STRIPE', f"Webhook signature inválida: {e}")
        raise ValueError("Invalid webhook signature")


def handle_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Processa evento do webhook."""
    event_type = event['event_type']
    data = event['data']
    
    if event_type == 'payment_intent.succeeded':
        # Pagamento bem-sucedido
        metadata = data.get('metadata', {})
        user_id = metadata.get('internal_user_id')
        plan_code = metadata.get('plan_code')
        
        if user_id and plan_code:
            upgrade_plan(user_id, plan_code)
            dbg('STRIPE', f"Upgrade aplicado: user={user_id} plan={plan_code}")
            return {'status': 'processed'}
    
    elif event_type == 'customer.subscription.created':
        # Assinatura criada
        subscription_id = data['id']
        metadata = data.get('metadata', {})
        user_id = metadata.get('internal_user_id')
        plan_code = metadata.get('plan_code')
        
        if user_id and plan_code:
            upgrade_plan(user_id, plan_code)
            return {'status': 'processed'}
    
    elif event_type == 'customer.subscription.deleted':
        # Assinatura cancelada -> downgrade para FREE
        subscription_id = data['id']
        # Buscar user_id pelo subscription_id
        sql = "SELECT user_id FROM public.user_settings WHERE gateway_subscription_id = %s"
        row = db_fetch_one(sql, (subscription_id,), ctx="BILLING.find_user_by_sub")
        
        if row:
            user_id = row[0] if not isinstance(row, dict) else row['user_id']
            upgrade_plan(user_id, 'FREE')
            return {'status': 'processed'}
    
    return {'status': 'ignored'}


# =============================
# Atualização de Plano
# =============================
def upgrade_plan(user_id: str, target_plan_code: str) -> Dict[str, Any]:
    """Atualiza plano do usuário no banco."""
    plan_id = _plan_code_to_id(target_plan_code)
    if not plan_id:
        return {'error': 'Plano inválido'}
    
    db_execute(
        """UPDATE public.user_settings 
           SET plan_id = %s, plan_status = 'active', plan_started_at = COALESCE(plan_started_at, now())
           WHERE user_id = %s""",
        (plan_id, user_id),
        ctx="BILLING.upgrade_plan"
    )
    
    dbg('BILLING', f"Plano atualizado: user={user_id} plan={target_plan_code}")
    return get_user_settings(user_id)


def _plan_code_to_id(plan_code: str) -> Optional[int]:
    """Converte código do plano para ID."""
    row = db_fetch_one(
        "SELECT id FROM public.system_plans WHERE code = %s AND active = true",
        (plan_code,),
        ctx="BILLING.plan_code_to_id"
    )
    if not row:
        return None
    return row[0] if not isinstance(row, dict) else row['id']


__all__ = [
    'get_system_plans', 
    'get_user_settings', 
    'create_payment_intent',
    'create_subscription',
    'cancel_subscription',
    'verify_webhook',
    'handle_webhook_event',
    'upgrade_plan'
]
```

---

### **Fase 5: Endpoint Flask para Webhook**

Como Dash não suporta endpoints POST nativamente, usar Flask para o webhook:

Arquivo: `gvg_billing_webhook.py`

```python
"""Flask app para receber webhooks do Stripe."""

from flask import Flask, request, jsonify
import os
from gvg_billing import verify_webhook, handle_webhook_event

webhook_app = Flask(__name__)

@webhook_app.route('/billing/webhook', methods=['POST'])
def stripe_webhook():
    """Endpoint que recebe eventos do Stripe."""
    payload = request.data.decode('utf-8')
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = verify_webhook(payload, sig_header)
        result = handle_webhook_event(event)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('WEBHOOK_PORT', 5001))
    webhook_app.run(port=port, debug=False)
```

**Rodar webhook separado**:
```bash
python gvg_billing_webhook.py
```

Ou **integrar com o Dash app** usando `DispatcherMiddleware`:

```python
# No GvG_Search_Browser.py (final do arquivo)

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from gvg_billing_webhook import webhook_app

# Combinar Dash + Flask
application = DispatcherMiddleware(app.server, {
    '/billing': webhook_app
})

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('localhost', 8050, application, use_reloader=True, use_debugger=True)
```

---

### **Fase 6: Webhooks - Configuração no Stripe**

#### 6.1. Criar Webhook Endpoint no Dashboard

1. Acesse [https://dashboard.stripe.com/test/webhooks](https://dashboard.stripe.com/test/webhooks)
2. Clique em **"Add endpoint"**
3. Preencha:
   - **Endpoint URL**: `https://www.govgo.com.br/billing/webhook`
   - **Events to send**: Selecione:
     - `checkout.session.completed` - Pagamento confirmado
     - `customer.subscription.created` - Assinatura criada
     - `customer.subscription.updated` - Assinatura atualizada
     - `customer.subscription.deleted` - Assinatura cancelada
     - `invoice.payment_succeeded` - Pagamento recorrente bem-sucedido
     - `invoice.payment_failed` - Pagamento recorrente falhou

4. Clique em **"Add endpoint"**
5. **Copie o "Signing secret"** (whsec_...) e adicione ao `.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_xxxxx
   ```

#### 6.2. Testar Localmente com Stripe CLI

```bash
# Instalar Stripe CLI (Windows)
# Baixar de: https://github.com/stripe/stripe-cli/releases

# Login
stripe login

# Escutar webhooks e encaminhar para localhost
stripe listen --forward-to localhost:5001/billing/webhook

# O CLI mostrará o webhook secret temporário:
# > Ready! Your webhook signing secret is whsec_xxxxx (^C to quit)

# Em outro terminal, disparar evento de teste:
stripe trigger checkout.session.completed
```

---

### **Fase 7: Criar Produtos e Preços no Stripe**

#### Passo a Passo com Screenshots:

**1. Acessar Products**
- Vá para [https://dashboard.stripe.com/test/products](https://dashboard.stripe.com/test/products)
- Clique em **"+ Create product"**

**2. Criar cada produto conforme `system_plans` do banco:**

Baseado no schema da sua BD (`system_plans`), você tem 4 planos:
- `FREE` (id=1) → **Não criar no Stripe** (sem cobrança)
- `PLUS` (id=2) → Criar no Stripe
- `PRO` (id=3) → Criar no Stripe
- `CORP` (id=4) → Criar no Stripe

---

#### **Produto 1: GovGo PLUS**

Preencha o formulário:

| Campo | Valor |
|-------|-------|
| **Name** | `GovGo PLUS` |
| **Description** | `Plano Plus com 20 consultas diárias, 20 resumos e 5 boletins` |
| **Pricing model** | ☑️ `Recurring` |
| **Price** | `R$ 49.00` (ou o valor da coluna `price_month_brl` no seu banco) |
| **Billing period** | `Monthly` |
| **Currency** | `BRL` |

Clique em **"Save product"**

**Copiar Price ID**:
- Após salvar, role até a seção **"Pricing"**
- Você verá um ID como `price_1ABC123...`
- Copie e adicione ao `.env`:
  ```env
  STRIPE_PRICE_PLUS=price_1ABC123xyz...
  ```

---

#### **Produto 2: GovGo PRO**

| Campo | Valor |
|-------|-------|
| **Name** | `GovGo PRO` |
| **Description** | `Plano Pro com 100 consultas diárias, 100 resumos e 10 boletins` |
| **Pricing model** | ☑️ `Recurring` |
| **Price** | `R$ 149.00` |
| **Billing period** | `Monthly` |
| **Currency** | `BRL` |

Copiar Price ID:
```env
STRIPE_PRICE_PRO=price_1DEF456xyz...
```

---

#### **Produto 3: GovGo CORP**

| Campo | Valor |
|-------|-------|
| **Name** | `GovGo CORP` |
| **Description** | `Plano Corporativo com 1000 consultas diárias, 1000 resumos e 100 boletins` |
| **Pricing model** | ☑️ `Recurring` |
| **Price** | `R$ 499.00` |
| **Billing period** | `Monthly` |
| **Currency** | `BRL` |

Copiar Price ID:
```env
STRIPE_PRICE_CORP=price_1GHI789xyz...
```

---

#### **Verificar no `.env`**

Seu `.env` deve ficar assim:

```env
# Stripe API
STRIPE_SECRET_KEY=sk_test_51ABC123...

# Price IDs (copiados do Dashboard)
STRIPE_PRICE_PLUS=price_1ABC123...
STRIPE_PRICE_PRO=price_1DEF456...
STRIPE_PRICE_CORP=price_1GHI789...

# Webhook (adicionar depois)
STRIPE_WEBHOOK_SECRET=whsec_...

# Base URL
BASE_URL=http://localhost:8050
```

---

#### **⚠️ IMPORTANTE: Sincronizar com o Banco**

Os preços que você definir no Stripe **devem corresponder** aos valores em `system_plans.price_month_brl`:

```sql
-- Verificar preços no banco
SELECT id, code, name, price_month_brl 
FROM public.system_plans 
WHERE active = true 
ORDER BY id;

-- Resultado esperado:
-- id | code | name       | price_month_brl
-- ---+------+------------+----------------
--  1 | FREE | Free       |           0.00
--  2 | PLUS | GovGo PLUS |          49.00
--  3 | PRO  | GovGo PRO  |         149.00
--  4 | CORP | GovGo CORP |         499.00
```

Se os valores forem diferentes, **atualize o banco** ou **ajuste no Stripe** para manter sincronizado!

---

## � Como Usar a API Stripe (Python)

### Inicialização

```python
import os
import stripe

# Configurar chave API (fazer UMA VEZ no início do módulo)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
```

### Principais Operações

#### 1. Criar Checkout Session (Upgrade de Plano)

```python
def create_checkout_session(user_id: str, plan_code: str, email: str) -> dict:
    """Cria sessão de checkout para upgrade."""
    
    # Mapear plano → Price ID do Stripe
    PLAN_PRICE_MAP = {
        'PLUS': os.getenv('STRIPE_PRICE_PLUS'),
        'PRO': os.getenv('STRIPE_PRICE_PRO'),
        'CORP': os.getenv('STRIPE_PRICE_CORP'),
    }
    
    price_id = PLAN_PRICE_MAP.get(plan_code)
    if not price_id:
        return {'error': 'Plano inválido'}
    
    # URLs de retorno
    base_url = os.getenv('BASE_URL', 'http://localhost:8050')
    success_url = f"{base_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/checkout/cancel"
    
    # Criar sessão
    session = stripe.checkout.Session.create(
        customer_email=email,
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        mode='subscription',  # Pagamento recorrente mensal
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'internal_user_id': user_id,
            'plan_code': plan_code
        }
    )
    
    return {
        'checkout_url': session.url,  # ⭐ Redirecionar usuário aqui
        'session_id': session.id
    }
```

**Uso no callback Dash**:
```python
@app.callback(
    Output('url', 'href'),
    Input('upgrade-btn', 'n_clicks'),
    State('store-auth', 'data')
)
def upgrade_click(n_clicks, auth_data):
    user = auth_data['user']
    result = create_checkout_session(
        user_id=user['uid'],
        plan_code='PLUS',
        email=user['email']
    )
    return result['checkout_url']  # Redireciona
```

#### 2. Cancelar Assinatura (Downgrade)

```python
def cancel_subscription(subscription_id: str) -> dict:
    """Cancela assinatura no fim do período."""
    
    subscription = stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=True  # Mantém acesso até fim do período
    )
    
    return {
        'status': 'canceled',
        'ends_at': subscription.current_period_end
    }
```

#### 3. Verificar Webhook (HMAC)

```python
def verify_webhook(payload: str, signature: str) -> dict:
    """Valida assinatura do webhook Stripe."""
    
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    event = stripe.Webhook.construct_event(
        payload,      # request.data (raw bytes)
        signature,    # request.headers['Stripe-Signature']
        webhook_secret
    )
    
    return {
        'event_type': event['type'],
        'event_id': event['id'],
        'data': event['data']['object']
    }
```

#### 4. Processar Eventos do Webhook

```python
def handle_webhook_event(event: dict) -> dict:
    """Processa eventos do Stripe."""
    
    event_type = event['event_type']
    data = event['data']
    
    if event_type == 'checkout.session.completed':
        # Pagamento confirmado - ativar plano
        metadata = data.get('metadata', {})
        user_id = metadata.get('internal_user_id')
        plan_code = metadata.get('plan_code')
        subscription_id = data.get('subscription')
        customer_id = data.get('customer')
        
        # Atualizar banco de dados
        from gvg_billing import upgrade_plan
        upgrade_plan(user_id, plan_code)
        
        # Salvar IDs do Stripe
        db_execute("""
            UPDATE public.user_settings 
            SET gateway_customer_id = %s, gateway_subscription_id = %s
            WHERE user_id = %s
        """, (customer_id, subscription_id, user_id))
        
        return {'status': 'processed'}
    
    elif event_type == 'invoice.payment_succeeded':
        # Renovação mensal bem-sucedida
        subscription_id = data.get('subscription')
        # Atualizar plan_renews_at no banco
        return {'status': 'processed'}
    
    elif event_type == 'invoice.payment_failed':
        # Pagamento falhou - notificar usuário
        subscription_id = data.get('subscription')
        # Enviar email de alerta
        return {'status': 'processed'}
    
    elif event_type == 'customer.subscription.deleted':
        # Assinatura cancelada - downgrade para FREE
        subscription_id = data['id']
        sql = "SELECT user_id FROM public.user_settings WHERE gateway_subscription_id = %s"
        row = db_fetch_one(sql, (subscription_id,))
        if row:
            user_id = row[0]
            upgrade_plan(user_id, 'FREE')
        return {'status': 'processed'}
    
    return {'status': 'ignored'}
```

### Mapeamento: Plano do Banco ↔ Price ID do Stripe

```python
# No gvg_billing.py
PLAN_PRICE_MAP = {
    'PLUS': os.getenv('STRIPE_PRICE_PLUS'),  # system_plans.id=2
    'PRO': os.getenv('STRIPE_PRICE_PRO'),    # system_plans.id=3
    'CORP': os.getenv('STRIPE_PRICE_CORP'),  # system_plans.id=4
}

# FREE (id=1) não está no mapa pois é gratuito
```

### Colunas Necessárias em `user_settings`

Verifique se existem no schema (vejo que **não existem** no schema atual):

```sql
-- Adicionar colunas para IDs do Stripe
ALTER TABLE public.user_settings 
ADD COLUMN IF NOT EXISTS gateway_customer_id text,
ADD COLUMN IF NOT EXISTS gateway_subscription_id text;

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_customer 
ON public.user_settings(gateway_customer_id);

CREATE INDEX IF NOT EXISTS idx_user_settings_gateway_subscription 
ON public.user_settings(gateway_subscription_id);
```

---

## �🔒 Segurança

### 1. Validação de Assinatura de Webhook (HMAC)

O Stripe assina cada webhook com HMAC-SHA256. **SEMPRE valide antes de processar**:

```python
def verify_webhook(payload: str, signature: str, secret: str):
    """Validação manual (sem usar SDK)."""
    import hmac
    import hashlib
    
    # O header Stripe-Signature tem formato: t=timestamp,v1=signature
    parts = dict(item.split('=') for item in signature.split(','))
    timestamp = parts.get('t')
    expected_sig = parts.get('v1')
    
    # Recriar assinatura
    signed_payload = f"{timestamp}.{payload}"
    computed_sig = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Comparação segura (evita timing attack)
    if not hmac.compare_digest(computed_sig, expected_sig):
        raise ValueError("Invalid signature")
    
    # Verificar timestamp (máximo 5 minutos de diferença)
    import time
    if abs(time.time() - int(timestamp)) > 300:
        raise ValueError("Timestamp too old")
```

### 2. Armazenamento Seguro de Chaves

**NUNCA commitar chaves no git!**

```env
# .env (ADICIONAR AO .gitignore)
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_PLUS=price_xxx
STRIPE_PRICE_PRO=price_yyy
STRIPE_PRICE_CORP=price_zzz
```

### 3. HTTPS Obrigatório em Produção

O Stripe **só envia webhooks para HTTPS**. No Render, já está configurado.

---

## 🧪 Testes

### Cartões de Teste do Stripe

| Número do Cartão | Resultado |
|------------------|-----------|
| `4242 4242 4242 4242` | ✅ Pagamento bem-sucedido |
| `4000 0025 0000 3155` | ⚠️ Requer 3D Secure (autenticação) |
| `4000 0000 0000 9995` | ❌ Cartão recusado (insufficient_funds) |

- **Validade**: Qualquer data futura (ex: 12/25)
- **CVV**: Qualquer 3 dígitos (ex: 123)
- **CEP**: Qualquer (ex: 12345-678)

### Testar Webhooks Localmente

```bash
# Terminal 1: Rodar app
python GvG_Search_Browser.py

# Terminal 2: Escutar webhooks
stripe listen --forward-to localhost:5001/billing/webhook

# Terminal 3: Disparar evento de teste
stripe trigger checkout.session.completed
```

---

## 🚀 Deploy e Produção

### 1. Ativar Conta Stripe (Produção)

Antes de ir para produção, você precisa:
1. Ativar sua conta no Stripe (fornecer dados fiscais/bancários)
2. Obter chaves de **produção** (live mode):
   - `STRIPE_SECRET_KEY=sk_live_xxx`
3. Recriar produtos/preços no modo **live**

### 2. Variáveis de Ambiente no Render

Adicionar no painel do Render:

```
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_yyy
STRIPE_PRICE_PLUS=price_aaa
STRIPE_PRICE_PRO=price_bbb
STRIPE_PRICE_CORP=price_ccc
BASE_URL=https://www.govgo.com.br
```

### 3. Webhook Endpoint (Produção)

Criar novo webhook endpoint apontando para:
```
https://www.govgo.com.br/billing/webhook
```

---

## 📚 Recursos Adicionais

### Documentação Oficial:
- API Reference: https://stripe.com/docs/api
- Python SDK: https://github.com/stripe/stripe-python
- Webhooks: https://stripe.com/docs/webhooks
- Checkout: https://stripe.com/docs/payments/checkout
- Subscriptions: https://stripe.com/docs/billing/subscriptions/overview

### Dashboard:
- Test mode: https://dashboard.stripe.com/test
- Live mode: https://dashboard.stripe.com/dashboard
- Webhooks: https://dashboard.stripe.com/webhooks
- Logs: https://dashboard.stripe.com/logs

### CLI:
- Documentação: https://stripe.com/docs/stripe-cli
- Download: https://github.com/stripe/stripe-cli/releases

---

## ✅ Checklist de Implementação

### Fase 1: Setup Stripe
- [ ] Criar conta Stripe (test mode)
- [ ] Instalar biblioteca: `pip install stripe`
- [ ] Obter chaves: Publishable Key (pk_test_...) e Secret Key (sk_test_...)
- [ ] Criar produtos/preços no Dashboard (PLUS, PRO, CORP)
- [ ] Copiar Price IDs para `.env`

### Fase 2: UI no GvG_Search_Browser.py (Python)
- [ ] Adicionar componente `dcc.Location(id='url')` no layout
- [ ] Callback para redirecionar ao Stripe Checkout ao clicar "Upgrade"
- [ ] Página de sucesso (`/checkout/success`)
- [ ] Página de cancelamento (`/checkout/cancel`)

### Fase 3: Backend no gvg_billing.py (Python)
- [ ] Remover todas as funções mock de `gvg_billing.py`
- [ ] Implementar `create_checkout_session()` (principal)
- [ ] Implementar `cancel_subscription()`
- [ ] Implementar `verify_webhook()` (validação HMAC)
- [ ] Implementar `handle_webhook_event()` (processar eventos)
- [ ] Atualizar `upgrade_plan()` para aplicar mudanças no banco

### Fase 4: Webhook (Python/Flask)
- [ ] Criar `gvg_billing_webhook.py` (Flask app)
- [ ] Endpoint POST `/billing/webhook`
- [ ] Integrar com Dash via DispatcherMiddleware (ou rodar separado)
- [ ] Configurar endpoint no Dashboard Stripe
- [ ] Copiar Webhook Secret para `.env`

### Fase 5: Testes
- [ ] Testar com cartões de teste (4242 4242 4242 4242)
- [ ] Testar webhooks localmente com Stripe CLI
- [ ] Validar fluxo completo: Modal → Pagamento → Webhook → Update DB
- [ ] Verificar badge do plano atualizando após pagamento

### Fase 6: Deploy
- [ ] Adicionar variáveis de ambiente no Render (.env)
- [ ] Deploy no Render (test mode)
- [ ] Ativar conta Stripe (produção)
- [ ] Recriar produtos em live mode
- [ ] Atualizar webhooks para produção (URL: https://www.govgo.com.br/billing/webhook)
- [ ] Deploy final (live mode)

---

## 🎯 Resumo da Arquitetura Simplificada (100% Python)

```
┌──────────────────────────────────────────────┐
│       GvG_Search_Browser.py (UI)             │
│  - Modal Planos (já existe)                  │
│  - Callback Python: redireciona para Stripe  │
│  - Página /checkout/success                  │
│  - Página /checkout/cancel                   │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│       gvg_billing.py (TUDO AQUI)             │
│  ✅ create_checkout_session()                │
│  ✅ cancel_subscription()                    │
│  ✅ verify_webhook()                         │
│  ✅ handle_webhook_event()                   │
│  ✅ upgrade_plan()                           │
│  ✅ get_system_plans()                       │
│  ✅ get_user_settings()                      │
│  ❌ Funções mock REMOVIDAS                   │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│      gvg_billing_webhook.py (Flask)          │
│  POST /billing/webhook                       │
│  - Recebe eventos do Stripe                  │
│  - Valida HMAC                               │
│  - Chama handle_webhook_event()              │
└──────────────────────────────────────────────┘
```

**✅ Sem pasta `gateway/`**
**✅ Sem `base.py`, `stripe_adapter.py`**
**✅ Sem JavaScript, sem `assets/`**
**✅ 100% Python**

Todo o código está em **2 arquivos apenas**:
1. `gvg_billing.py` - Lógica Stripe
2. `GvG_Search_Browser.py` - UI e callbacks

---

**Próximos Passos**: Começar pela Fase 1 (Setup Stripe) e seguir o checklist sequencialmente! 🎉
