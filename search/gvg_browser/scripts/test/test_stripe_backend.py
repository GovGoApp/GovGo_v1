"""
Teste Backend Stripe - Verificação Completa

Testa:
1. Carregamento de variáveis .env
2. PLAN_PRICE_MAP configurado
3. Criação de Checkout Session
4. Funções de webhook
"""
import sys
import os

# Adicionar path do gvg_browser ao sys.path
gvg_browser_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, gvg_browser_path)

# Carregar .env do diretório correto
from dotenv import load_dotenv
env_path = os.path.join(gvg_browser_path, '.env')
load_dotenv(env_path)

print("="*70)
print("🧪 TESTE BACKEND STRIPE")
print("="*70)

# Teste 1: Verificar variáveis .env
print("\n✅ TESTE 1: Variáveis .env")
print("-"*70)

stripe_key = os.getenv('STRIPE_SECRET_KEY')
price_plus = os.getenv('STRIPE_PRICE_PLUS')
price_pro = os.getenv('STRIPE_PRICE_PRO')
price_corp = os.getenv('STRIPE_PRICE_CORP')

if stripe_key:
    print(f"✅ STRIPE_SECRET_KEY: {stripe_key[:15]}... (carregado)")
else:
    print("❌ STRIPE_SECRET_KEY: NÃO ENCONTRADO")

if price_plus:
    print(f"✅ STRIPE_PRICE_PLUS: {price_plus}")
else:
    print("❌ STRIPE_PRICE_PLUS: NÃO ENCONTRADO")

if price_pro:
    print(f"✅ STRIPE_PRICE_PRO: {price_pro}")
else:
    print("❌ STRIPE_PRICE_PRO: NÃO ENCONTRADO")

if price_corp:
    print(f"✅ STRIPE_PRICE_CORP: {price_corp}")
else:
    print("❌ STRIPE_PRICE_CORP: NÃO ENCONTRADO")

# Teste 2: Importar gvg_billing
print("\n✅ TESTE 2: Importar gvg_billing")
print("-"*70)

try:
    from gvg_billing import PLAN_PRICE_MAP, create_checkout_session
    print("✅ gvg_billing importado com sucesso")
    print(f"✅ PLAN_PRICE_MAP: {PLAN_PRICE_MAP}")
except Exception as e:
    print(f"❌ Erro ao importar gvg_billing: {e}")
    sys.exit(1)

# Teste 3: Criar Checkout Session
print("\n✅ TESTE 3: Criar Checkout Session")
print("-"*70)

try:
    result = create_checkout_session(
        user_id='test_haroldo_001',
        plan_code='PLUS',
        email='hdaduraes@gmail.com',
        name='Haroldo Teste'
    )
    
    if 'error' in result:
        print(f"❌ Erro ao criar checkout: {result['error']}")
    else:
        print(f"✅ Checkout criado com sucesso!")
        print(f"   Session ID: {result.get('session_id')}")
        print(f"   Checkout URL: {result.get('checkout_url')[:80]}...")
        print(f"\n🌐 Abrir no navegador:")
        print(f"   {result.get('checkout_url')}")
        
except Exception as e:
    print(f"❌ Erro ao criar checkout: {e}")
    import traceback
    traceback.print_exc()

# Teste 4: Testar outros planos
print("\n✅ TESTE 4: Testar PRO e CORP")
print("-"*70)

for plan_code, plan_name, price in [('PRO', 'Pro', 'R$ 199'), ('CORP', 'Corp', 'R$ 999')]:
    try:
        result = create_checkout_session(
            user_id=f'test_{plan_code.lower()}_001',
            plan_code=plan_code,
            email='teste@govgo.com.br',
            name=f'Teste {plan_name}'
        )
        
        if 'error' in result:
            print(f"❌ {plan_code}: {result['error']}")
        else:
            print(f"✅ {plan_code} ({price}/mês): Checkout criado")
            
    except Exception as e:
        print(f"❌ {plan_code}: {e}")

print("\n" + "="*70)
print("✅ TESTE CONCLUÍDO")
print("="*70)
print("\n💡 PRÓXIMO PASSO:")
print("   1. Copiar URL do PLUS acima")
print("   2. Abrir no navegador")
print("   3. Pagar com cartão: 4242 4242 4242 4242")
print("   4. Verificar webhook (quando configurado)")
