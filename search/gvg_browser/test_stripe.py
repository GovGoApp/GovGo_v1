"""
Script de teste para verificar integração Stripe
"""
from gvg_billing import create_checkout_session, PLAN_PRICE_MAP

print("=" * 60)
print("🧪 TESTE: INTEGRAÇÃO STRIPE")
print("=" * 60)

# Verificar Price IDs carregados
print("\n1️⃣ Verificando PLAN_PRICE_MAP:")
print(f"   PLUS: {PLAN_PRICE_MAP.get('PLUS', 'NÃO CONFIGURADO')}")
print(f"   PRO: {PLAN_PRICE_MAP.get('PRO', 'NÃO CONFIGURADO')}")
print(f"   CORP: {PLAN_PRICE_MAP.get('CORP', 'NÃO CONFIGURADO')}")

if not all(PLAN_PRICE_MAP.values()):
    print("\n❌ ERRO: Price IDs não configurados no .env!")
    exit(1)

print("\n✅ Price IDs carregados do .env")

# Testar criação de Checkout Session
print("\n2️⃣ Testando create_checkout_session()...")

result = create_checkout_session(
    user_id='test_haroldo_001',
    plan_code='PLUS',
    email='hdaduraes@gmail.com',
    name='Haroldo Durães'
)

if 'error' in result:
    print(f"\n❌ ERRO ao criar checkout: {result['error']}")
    exit(1)

if 'checkout_url' in result and 'session_id' in result:
    print("\n✅ SUCESSO! Checkout Session criada!")
    print(f"\n📋 Detalhes:")
    print(f"   Session ID: {result['session_id']}")
    print(f"   Checkout URL: {result['checkout_url']}")
    
    print("\n" + "=" * 60)
    print("🎉 BACKEND STRIPE 100% FUNCIONAL!")
    print("=" * 60)
    
    print("\n📌 PRÓXIMO PASSO:")
    print("   1. Copie a URL acima")
    print("   2. Cole no navegador")
    print("   3. Pague com cartão teste: 4242 4242 4242 4242")
    print("\n" + "=" * 60)
else:
    print(f"\n❌ ERRO: Resposta inesperada: {result}")
    exit(1)
