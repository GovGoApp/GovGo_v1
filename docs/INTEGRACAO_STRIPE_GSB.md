# 🔌 INTEGRAÇÃO STRIPE NO GvG_Search_Browser.py

## 📋 O QUE ADICIONAR NO GSB

Este documento mostra **exatamente** o que adicionar no `GvG_Search_Browser.py` para integrar pagamentos Stripe.

---

## ✅ PASSO 1: Adicionar Rota Webhook (Flask embutido)

O Dash roda sobre Flask! Podemos adicionar uma rota POST para o webhook do Stripe.

**Adicionar DEPOIS da inicialização do app Dash:**

```python
# No arquivo GvG_Search_Browser.py
# Procurar onde tem: app = Dash(__name__, ...)
# Logo DEPOIS, adicionar:

# =============================
# STRIPE WEBHOOK (Flask Route)
# =============================
@app.server.route('/billing/webhook', methods=['POST'])
def stripe_webhook():
    """
    Endpoint POST para receber webhooks do Stripe.
    O Dash usa Flask internamente (app.server é o Flask app).
    """
    from flask import request, jsonify
    from gvg_billing import verify_webhook, handle_webhook_event
    from gvg_debug import debug_log as dbg
    
    payload = request.data
    signature = request.headers.get('Stripe-Signature')
    
    if not signature:
        dbg('WEBHOOK', 'Requisição sem Stripe-Signature header')
        return jsonify({'error': 'Missing signature'}), 400
    
    # Validar webhook
    event = verify_webhook(payload, signature)
    
    if 'error' in event:
        dbg('WEBHOOK', f"Erro ao verificar webhook: {event['error']}")
        return jsonify({'error': event['error']}), 400
    
    # Processar evento
    result = handle_webhook_event(event)
    
    if result.get('status') == 'error':
        dbg('WEBHOOK', f"Erro ao processar evento: {result.get('message')}")
        return jsonify({'error': result.get('message')}), 500
    
    dbg('WEBHOOK', f"Evento processado: {event.get('event_type')} [{event.get('event_id')}]")
    return jsonify({'status': 'success'}), 200


@app.server.route('/billing/health', methods=['GET'])
def webhook_health():
    """Health check para verificar se webhook está online."""
    from flask import jsonify
    return jsonify({'status': 'healthy', 'service': 'gvg_billing_webhook'}), 200
```

**Localização no código:**
```python
# Exemplo de onde adicionar:

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True
)

# <<<< ADICIONAR WEBHOOK AQUI >>>>
@app.server.route('/billing/webhook', methods=['POST'])
def stripe_webhook():
    # ... código acima

# Depois vem o resto do código (layout, callbacks, etc)
app.layout = html.Div([...])
```

---

## ✅ PASSO 2: Adicionar dcc.Location para Redirects

**Adicionar no layout principal:**

```python
# Procurar: app.layout = html.Div([
# Adicionar dcc.Location como PRIMEIRO elemento:

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),  # <<<< ADICIONAR ISSO
    dcc.Store(id='store-session', storage_type='session'),
    dcc.Store(id='store-results', storage_type='memory'),
    # ... resto dos stores e componentes
])
```

---

## ✅ PASSO 3: Criar Seção de Planos (UI)

**Adicionar nova página de planos (pode ser em qualquer lugar do layout):**

```python
# Exemplo de seção de planos
planos_section = html.Div([
    html.H2("📊 Escolha seu Plano", style={'textAlign': 'center', 'marginTop': '2rem'}),
    
    dbc.Row([
        # Plano FREE
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("FREE", className="text-center")),
                dbc.CardBody([
                    html.H3("R$ 0,00/mês", className="text-center text-muted"),
                    html.Hr(),
                    html.Ul([
                        html.Li("5 consultas/dia"),
                        html.Li("1 resumo/dia"),
                        html.Li("10 favoritos"),
                    ]),
                    html.P("Seu plano atual", className="text-center text-success", 
                           id='current-plan-free', style={'display': 'none'}),
                ]),
            ], className="h-100"),
        ], width=3),
        
        # Plano PLUS
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("PLUS", className="text-center text-primary")),
                dbc.CardBody([
                    html.H3("R$ 49,00/mês", className="text-center text-primary"),
                    html.Hr(),
                    html.Ul([
                        html.Li("50 consultas/dia"),
                        html.Li("10 resumos/dia"),
                        html.Li("100 favoritos"),
                    ]),
                    dbc.Button("Assinar PLUS", id='btn-upgrade-plus', 
                               color="primary", className="w-100"),
                ]),
            ], className="h-100 border-primary"),
        ], width=3),
        
        # Plano PRO
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("PRO", className="text-center text-warning")),
                dbc.CardBody([
                    html.H3("R$ 199,00/mês", className="text-center text-warning"),
                    html.Hr(),
                    html.Ul([
                        html.Li("200 consultas/dia"),
                        html.Li("50 resumos/dia"),
                        html.Li("500 favoritos"),
                    ]),
                    dbc.Button("Assinar PRO", id='btn-upgrade-pro', 
                               color="warning", className="w-100"),
                ]),
            ], className="h-100 border-warning"),
        ], width=3),
        
        # Plano CORP
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("CORP", className="text-center text-danger")),
                dbc.CardBody([
                    html.H3("R$ 999,00/mês", className="text-center text-danger"),
                    html.Hr(),
                    html.Ul([
                        html.Li("1000 consultas/dia"),
                        html.Li("200 resumos/dia"),
                        html.Li("2000 favoritos"),
                    ]),
                    dbc.Button("Assinar CORP", id='btn-upgrade-corp', 
                               color="danger", className="w-100"),
                ]),
            ], className="h-100 border-danger"),
        ], width=3),
    ], className="g-4"),
    
    # Mensagens de erro/sucesso
    html.Div(id='billing-message', style={'marginTop': '2rem'}),
    
], style={'padding': '2rem'})

# Adicionar ao layout principal onde quiser mostrar os planos
```

---

## ✅ PASSO 4: Callbacks para Upgrade

**Adicionar callbacks para redirecionar ao Stripe:**

```python
# Callback para PLUS
@app.callback(
    Output('url', 'href'),
    Output('billing-message', 'children'),
    Input('btn-upgrade-plus', 'n_clicks'),
    State('store-session', 'data'),
    prevent_initial_call=True
)
def upgrade_plus(n, session):
    if not n or not session:
        return dash.no_update, dash.no_update
    
    from gvg_billing import create_checkout_session
    
    user_id = session.get('user_id')
    email = session.get('email', 'teste@govgo.com.br')
    name = session.get('name', 'Usuário')
    
    if not user_id:
        return dash.no_update, dbc.Alert("Erro: Usuário não identificado", color="danger")
    
    result = create_checkout_session(user_id, 'PLUS', email, name)
    
    if 'error' in result:
        return dash.no_update, dbc.Alert(f"Erro: {result['error']}", color="danger")
    
    # Redireciona para o Stripe
    return result['checkout_url'], dash.no_update


# Callback para PRO
@app.callback(
    Output('url', 'href', allow_duplicate=True),
    Output('billing-message', 'children', allow_duplicate=True),
    Input('btn-upgrade-pro', 'n_clicks'),
    State('store-session', 'data'),
    prevent_initial_call=True
)
def upgrade_pro(n, session):
    if not n or not session:
        return dash.no_update, dash.no_update
    
    from gvg_billing import create_checkout_session
    
    user_id = session.get('user_id')
    email = session.get('email', 'teste@govgo.com.br')
    name = session.get('name', 'Usuário')
    
    if not user_id:
        return dash.no_update, dbc.Alert("Erro: Usuário não identificado", color="danger")
    
    result = create_checkout_session(user_id, 'PRO', email, name)
    
    if 'error' in result:
        return dash.no_update, dbc.Alert(f"Erro: {result['error']}", color="danger")
    
    return result['checkout_url'], dash.no_update


# Callback para CORP
@app.callback(
    Output('url', 'href', allow_duplicate=True),
    Output('billing-message', 'children', allow_duplicate=True),
    Input('btn-upgrade-corp', 'n_clicks'),
    State('store-session', 'data'),
    prevent_initial_call=True
)
def upgrade_corp(n, session):
    if not n or not session:
        return dash.no_update, dash.no_update
    
    from gvg_billing import create_checkout_session
    
    user_id = session.get('user_id')
    email = session.get('email', 'teste@govgo.com.br')
    name = session.get('name', 'Usuário')
    
    if not user_id:
        return dash.no_update, dbc.Alert("Erro: Usuário não identificado", color="danger")
    
    result = create_checkout_session(user_id, 'CORP', email, name)
    
    if 'error' in result:
        return dash.no_update, dbc.Alert(f"Erro: {result['error']}", color="danger")
    
    return result['checkout_url'], dash.no_update
```

---

## ✅ PASSO 5: Páginas de Retorno (Success/Cancel)

**Adicionar callback para mostrar páginas após retorno do Stripe:**

```python
@app.callback(
    Output('page-content', 'children'),  # Assumindo que você tem um div com id='page-content'
    Input('url', 'pathname'),
    Input('url', 'search'),  # Para pegar ?session_id=...
)
def display_page(pathname, search):
    if pathname == '/checkout/success':
        return html.Div([
            html.Div([
                html.I(className="fas fa-check-circle fa-5x text-success"),
                html.H2("✅ Pagamento Confirmado!", className="mt-4"),
                html.P("Seu plano será ativado em instantes.", className="lead"),
                html.P("Você receberá um email de confirmação do Stripe.", className="text-muted"),
                dbc.Button("Voltar ao Painel", href="/", color="primary", className="mt-3"),
            ], style={'textAlign': 'center', 'padding': '4rem'})
        ])
    
    elif pathname == '/checkout/cancel':
        return html.Div([
            html.Div([
                html.I(className="fas fa-times-circle fa-5x text-warning"),
                html.H2("❌ Pagamento Cancelado", className="mt-4"),
                html.P("Você pode tentar novamente quando quiser.", className="lead"),
                dbc.Button("Ver Planos Novamente", href="/pricing", color="warning", className="mt-3"),
            ], style={'textAlign': 'center', 'padding': '4rem'})
        ])
    
    # ... resto das suas páginas
    return html.Div("Página não encontrada")
```

---

## 🧪 COMO TESTAR

### 1. Iniciar o App
```powershell
cd "c:\Users\Haroldo Duraes\Desktop\Scripts\GovGo\v1\search\gvg_browser"
python GvG_Search_Browser.py
```

### 2. Verificar Webhook Health
Abrir navegador: `http://localhost:8060/billing/health`

**Deve retornar:**
```json
{"status": "healthy", "service": "gvg_billing_webhook"}
```

### 3. Testar Checkout via Python
```python
from gvg_billing import create_checkout_session

result = create_checkout_session(
    user_id='test_123',
    plan_code='PLUS',
    email='teste@govgo.com.br',
    name='Teste'
)

print(result['checkout_url'])
# Copiar URL e abrir no navegador
```

### 4. Configurar Stripe CLI (para webhooks locais)
```powershell
stripe listen --forward-to localhost:8060/billing/webhook
```

Copiar o `whsec_...` gerado e adicionar no `.env`:
```bash
STRIPE_WEBHOOK_SECRET=whsec_abc123...
```

### 5. Pagar com Cartão de Teste
- Cartão: `4242 4242 4242 4242`
- Data: qualquer futura
- CVC: qualquer 3 dígitos

### 6. Verificar Webhook Recebido
No terminal do Stripe CLI, deve aparecer:
```
[200] POST http://localhost:8060/billing/webhook [evt_...]
```

No console do Dash:
```
INFO:WEBHOOK:Evento processado: checkout.session.completed
```

---

## 📝 RESUMO DAS MUDANÇAS

### Arquivos Modificados:
1. ✅ `gvg_billing.py` - Já configurado com Stripe
2. ⏳ `GvG_Search_Browser.py` - Adicionar:
   - Rota webhook (`@app.server.route`)
   - `dcc.Location` component
   - UI de planos (cards)
   - Callbacks de upgrade
   - Páginas success/cancel

### Arquivos Deletados:
- ✅ `gvg_billing_webhook.py` - Não é mais necessário

### Configuração:
- ✅ `.env` - Já tem Price IDs e Secret Key
- ⏳ Supabase - Executar migration SQL (adicionar colunas gateway_*)

---

## 🚀 PRÓXIMO PASSO

Você quer que eu:
1. **Mostre o código exato de onde adicionar cada trecho no GSB** (preciso ver o arquivo completo)
2. **Ou você prefere adicionar manualmente** seguindo este guia?

Me avise qual opção prefere!
