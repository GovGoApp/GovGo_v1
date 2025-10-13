"""
Teste do Webhook Stripe no GSB

Testa:
1. Health check endpoint
2. Webhook endpoint (sem processar eventos reais)
"""
import requests
import time

BASE_URL = "http://localhost:8060"

print("="*70)
print("🧪 TESTE WEBHOOK STRIPE NO GSB")
print("="*70)
print("\n⚠️  IMPORTANTE: O GvG_Search_Browser.py DEVE ESTAR RODANDO!")
print("   Execute em outro terminal: python GvG_Search_Browser.py\n")

input("Pressione ENTER quando o GSB estiver rodando...")

# Teste 1: Health Check
print("\n✅ TESTE 1: Health Check")
print("-"*70)

try:
    response = requests.get(f"{BASE_URL}/billing/health", timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Health check respondeu: {data}")
        print(f"   Status: {data.get('status')}")
        print(f"   Service: {data.get('service')}")
    else:
        print(f"❌ Health check falhou: {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print(f"❌ Não conseguiu conectar em {BASE_URL}")
    print("   Certifique-se que o GSB está rodando!")
    exit(1)
    
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)

# Teste 2: Webhook endpoint existe
print("\n✅ TESTE 2: Webhook Endpoint")
print("-"*70)

try:
    # Tentar POST sem assinatura (deve retornar erro 400)
    response = requests.post(
        f"{BASE_URL}/billing/webhook",
        data=b'{"test": "data"}',
        headers={'Content-Type': 'application/json'},
        timeout=5
    )
    
    if response.status_code == 400:
        data = response.json()
        if 'Missing signature' in data.get('error', ''):
            print(f"✅ Webhook endpoint funcionando corretamente")
            print(f"   Rejeitou requisição sem assinatura (esperado)")
        else:
            print(f"⚠️  Webhook respondeu 400 mas com erro inesperado: {data}")
    else:
        print(f"⚠️  Webhook respondeu com código inesperado: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"❌ Erro ao testar webhook: {e}")

print("\n" + "="*70)
print("✅ TESTE CONCLUÍDO")
print("="*70)
print("\n💡 PRÓXIMO PASSO:")
print("   1. Configurar Stripe CLI:")
print("      stripe listen --forward-to localhost:8060/billing/webhook")
print("   2. Copiar whsec_... para .env como STRIPE_WEBHOOK_SECRET")
print("   3. Testar pagamento real")
