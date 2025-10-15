"""
Teste Backend Stripe Elements (Payment Element)

Fluxo testado (sem UI):
1) create_subscription_elements(user_id, plan_code, email, name)
   - Retorna client_secret, subscription_id, customer_id, amount, currency
2) apply_subscription_result(user_id, plan_code, customer_id, subscription_id, ...)
   - Faz UPSERT do plano em user_settings e grava histórico em user_payment
3) get_user_settings(user_id)
   - Verifica se o plano foi atualizado

Pré-requisitos:
- .env com STRIPE_SECRET_KEY e STRIPE_PUBLISHABLE_KEY válidos (modo test)
- Tabela system_plans com plano escolhido e stripe_price_id preenchido
- Variável PASS_USER_UID (UUID de um usuário válido em auth.users) para evitar FK error

Como rodar:
  python test_elements_backend.py

Obs: Este teste NÃO confirma pagamento no Stripe; ele simula a aplicação do resultado
via apply_subscription_result. Use-o para validar o backend e a persistência na DB.
"""
import os
import sys
from dotenv import load_dotenv

# Garantir que possamos importar módulos do gvg_browser
HERE = os.path.dirname(__file__)
GVG_BROWSER_ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
if GVG_BROWSER_ROOT not in sys.path:
    sys.path.insert(0, GVG_BROWSER_ROOT)

# Carregar .env desta pasta (ou do workspace root se desejar)
ENV_CANDIDATES = [
    os.path.join(GVG_BROWSER_ROOT, '.env'),
    os.path.join(os.path.dirname(GVG_BROWSER_ROOT), '.env'),
]
for p in ENV_CANDIDATES:
    if os.path.exists(p):
        load_dotenv(p)
        break
else:
    load_dotenv()  # genérico

print("="*70)
print("🧪 TESTE BACKEND STRIPE ELEMENTS")
print("="*70)

# Ler insumos do ambiente
USER_ID = os.getenv('PASS_USER_UID') or os.getenv('TEST_USER_UID') or ''
USER_EMAIL = os.getenv('PASS_USER_EMAIL') or os.getenv('TEST_USER_EMAIL') or ''
USER_NAME = os.getenv('PASS_USER_NAME') or os.getenv('TEST_USER_NAME') or 'Tester'
PLAN_CODE = (os.getenv('TEST_PLAN_CODE') or 'PLUS').upper()

if not USER_ID:
    print("⚠️  PASS_USER_UID/TEST_USER_UID não encontrado no .env.")
    print("   Defina um UUID válido de um usuário presente em auth.users.")

try:
    from gvg_billing import (
        create_subscription_elements,
        apply_subscription_result,
        get_user_settings,
    )
except Exception as e:
    print(f"❌ Erro ao importar gvg_billing: {e}")
    sys.exit(1)

print("\n1) Criando assinatura (incomplete) para montar Payment Element...")
result = create_subscription_elements(
    user_id=USER_ID,
    plan_code=PLAN_CODE,
    email=USER_EMAIL or 'tester@example.com',
    name=USER_NAME,
)
if result.get('error'):
    print(f"❌ create_subscription_elements falhou: {result['error']}")
    sys.exit(2)

client_secret = result.get('client_secret')
subscription_id = result.get('subscription_id')
customer_id = result.get('customer_id')
payment_amount = result.get('amount')
currency = result.get('currency')

print("✅ Subscription criada (incomplete)")
print(f"   subscription_id: {subscription_id}")
print(f"   customer_id:     {customer_id}")
print(f"   client_secret:   {str(client_secret)[:18]}...")
print(f"   amount/currency: {payment_amount} {currency}")

print("\n2) Aplicando resultado (simulado) com apply_subscription_result...")
apply = apply_subscription_result(
    user_id=USER_ID,
    plan_code=PLAN_CODE,
    customer_id=customer_id,
    subscription_id=subscription_id,
    payment_intent_id=None,  # opcional neste teste
    amount_paid=payment_amount,
    currency=currency or 'BRL',
)
if apply.get('error'):
    print(f"❌ apply_subscription_result falhou: {apply['error']}")
    sys.exit(3)
print("✅ Aplicado com sucesso (UPSERT do plano e histórico gravado)")

print("\n3) Conferindo plano do usuário...")
try:
    settings = get_user_settings(USER_ID)
    print(f"✅ user_settings: plan_code={settings.get('plan_code')}")
    if settings.get('plan_code') != PLAN_CODE:
        print("⚠️  Aviso: plan_code não refletiu atualização esperada.")
except Exception as e:
    print(f"⚠️  Não foi possível ler get_user_settings: {e}")

print("\nConcluído.\n")
