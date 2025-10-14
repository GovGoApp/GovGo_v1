"""Camada Billing com Stripe

Consolida:
- Leitura de planos (system_plans)
- Leitura/atualização de user_settings
- Snapshot simples de uso atual (eventos hoje + favoritos)
- Integração Stripe (Checkout Session, Subscription, Webhook)

Integração completa com Stripe para pagamentos recorrentes.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import datetime as _dt
import os
import csv

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()  # Carrega .env do diretório atual

# Stripe
import stripe

from gvg_database import db_fetch_all, db_fetch_one, db_execute  # type: ignore
from gvg_debug import debug_log as dbg  # type: ignore

# =============================
# Configuração Stripe
# =============================
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Cache de planos do CSV (carregado uma vez)
_PLANS_FALLBACK_CACHE = None

# Cache de planos do banco (carregado uma vez no início)
_SYSTEM_PLANS_CACHE = None

def _load_plans_fallback() -> Dict[str, Dict[str, Any]]:
	"""Carrega planos do CSV de fallback e retorna dict indexado por code."""
	global _PLANS_FALLBACK_CACHE
	if _PLANS_FALLBACK_CACHE is not None:
		return _PLANS_FALLBACK_CACHE
	
	plans = {}
	try:
		csv_path = os.path.join(os.path.dirname(__file__), 'docs', 'system_plans_fallback.csv')
		with open(csv_path, 'r', encoding='utf-8') as f:
			reader = csv.DictReader(f)
			for row in reader:
				code = row['code'].upper()
				plans[code] = {
					'limit_consultas_per_day': int(row['limit_consultas_per_day']),
					'limit_resumos_per_day': int(row['limit_resumos_per_day']),
					'limit_boletim_per_day': int(row['limit_boletim_per_day']),
					'limit_favoritos_capacity': int(row['limit_favoritos_capacity']),
				}
		_PLANS_FALLBACK_CACHE = plans
		return plans
	except Exception as e:
		dbg('BILLING', f"Erro ao carregar plans fallback CSV: {e}")
		# Fallback hardcoded se CSV falhar
		return {
			'FREE': {'limit_consultas_per_day': 5, 'limit_resumos_per_day': 1, 'limit_boletim_per_day': 1, 'limit_favoritos_capacity': 10},
			'PLUS': {'limit_consultas_per_day': 20, 'limit_resumos_per_day': 20, 'limit_boletim_per_day': 5, 'limit_favoritos_capacity': 200},
			'PRO': {'limit_consultas_per_day': 100, 'limit_resumos_per_day': 100, 'limit_boletim_per_day': 10, 'limit_favoritos_capacity': 2000},
			'CORP': {'limit_consultas_per_day': 1000, 'limit_resumos_per_day': 1000, 'limit_boletim_per_day': 100, 'limit_favoritos_capacity': 20000},
		}


# =============================
# Planos / User Settings
# =============================
# Ajustado para o schema atual: coluna price_month_brl (numeric) e não existe billing_period / price_cents.
# Expomos price_cents (inteiro) e billing_period fixo ('month') para compatibilidade com a UI existente.
PLAN_COLUMNS = (
	"id, code, name, (price_month_brl * 100)::int AS price_cents, 'month' AS billing_period, "
	"limit_consultas_per_day, limit_resumos_per_day, limit_boletim_per_day, limit_favoritos_capacity"
)


def get_system_plans() -> List[Dict[str, Any]]:
	"""
	Retorna todos os planos ativos com TODOS os campos (incluindo Stripe IDs).
	Usa cache para evitar SQL repetido.
	"""
	global _SYSTEM_PLANS_CACHE
	
	# Se já carregou, retorna cache
	if _SYSTEM_PLANS_CACHE is not None:
		return _SYSTEM_PLANS_CACHE
	
	# Buscar TODOS os campos do banco
	sql = """
		SELECT 
			id, code, name, price_month_brl, 
			limit_consultas_per_day, limit_resumos_per_day, 
			limit_boletim_per_day, limit_favoritos_capacity,
			stripe_product_id, stripe_price_id,
			active, created_at
		FROM public.system_plans 
		WHERE active = true 
		ORDER BY price_month_brl ASC, id ASC
	"""
	rows = db_fetch_all(sql, as_dict=True, ctx="BILLING.get_system_plans")
	
	out: List[Dict[str, Any]] = []
	for r in rows:
		if isinstance(r, dict):
			plan = r.copy()
		else:
			# Fallback se não retornar dict
			plan = {
				'id': r[0], 'code': r[1], 'name': r[2], 'price_month_brl': r[3],
				'limit_consultas_per_day': r[4], 'limit_resumos_per_day': r[5],
				'limit_boletim_per_day': r[6], 'limit_favoritos_capacity': r[7],
				'stripe_product_id': r[8], 'stripe_price_id': r[9],
				'active': r[10], 'created_at': r[11]
			}
		
		# Adicionar price_cents (calculado a partir de price_month_brl)
		# Para compatibilidade com código existente do GSB
		price_brl = plan.get('price_month_brl', 0)
		if price_brl is not None:
			try:
				plan['price_cents'] = int(float(price_brl) * 100)
			except (ValueError, TypeError):
				plan['price_cents'] = 0
		else:
			plan['price_cents'] = 0
		
		out.append(plan)
	
	# Guardar em cache
	_SYSTEM_PLANS_CACHE = out
	dbg('BILLING', f"Planos carregados e cacheados: {len(out)} planos")
	return out


def _get_plan_by_code(plan_code: str) -> Dict[str, Any] | None:
	"""
	Busca plano no cache por código.
	Retorna dict completo com todos os campos ou None.
	"""
	plans = get_system_plans()  # Usa cache
	for plan in plans:
		if plan.get('code') == plan_code:
			return plan
	return None


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
	dbg('BILLING', f"get_user_settings: user_id={user_id} row={row}")
	
	if not row:
		dbg('BILLING', f"get_user_settings: row vazio, retornando FREE fallback")
		return _fallback_free()
	
	result = {
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
	dbg('BILLING', f"get_user_settings: retornando result={result}")
	return result


def _fallback_free() -> Dict[str, Any]:
	# Buscar limites FREE do CSV
	plans_fallback = _load_plans_fallback()
	free_limits = plans_fallback.get('FREE', {
		'limit_consultas_per_day': 5,
		'limit_resumos_per_day': 1,
		'limit_boletim_per_day': 1,
		'limit_favoritos_capacity': 10,
	})
	return {
		'user_id': '',
		'plan_code': 'FREE',
		'plan_name': 'Free',
		'limits': {
			'consultas': free_limits.get('limit_consultas_per_day', 5),
			'resumos': free_limits.get('limit_resumos_per_day', 1),
			'boletim_run': free_limits.get('limit_boletim_per_day', 1),
			'favoritos': free_limits.get('limit_favoritos_capacity', 10),
		}
	}


# =============================
# Stripe Checkout
# =============================
def create_checkout_session(user_id: str, plan_code: str, email: str, name: str = None) -> Dict[str, Any]:
	"""
	Cria uma Checkout Session do Stripe para assinatura.
	
	Args:
		user_id: ID do usuário no sistema
		plan_code: Código do plano (PLUS, PRO, CORP)
		email: Email do usuário
		name: Nome do usuário (opcional)
	
	Returns:
		{'checkout_url': str, 'session_id': str} ou {'error': str}
	"""
	if not all([user_id, plan_code, email]):
		return {'error': 'Parâmetros obrigatórios faltando'}
	
	# Buscar plano do cache (não faz SQL)
	plan = _get_plan_by_code(plan_code)
	if not plan:
		return {'error': 'Plano inexistente ou inativo'}
	
	# Verificar se tem Price ID configurado
	price_id = plan.get('stripe_price_id')
	if not price_id:
		return {'error': f'Price ID não configurado para plano {plan_code}'}
	
	base_url = os.getenv('BASE_URL', 'http://localhost:8050')
	
	try:
		# Criar Checkout Session
		session = stripe.checkout.Session.create(
			payment_method_types=['card'],
			mode='subscription',
			customer_email=email,
			client_reference_id=user_id,  # Para identificar usuário no webhook
			line_items=[{
				'price': price_id,
				'quantity': 1,
			}],
			success_url=f'{base_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}',
			cancel_url=f'{base_url}/checkout/cancel',
			metadata={
				'user_id': user_id,
				'plan_code': plan_code,
			}
		)
		
		dbg('BILLING', f"Checkout Session criada: {session.id} para user_id={user_id} plan={plan_code}")
		
		return {
			'checkout_url': session.url,
			'session_id': session.id
		}
	
	except stripe.error.StripeError as e:
		dbg('BILLING', f"Erro ao criar Checkout Session: {e}")
		return {'error': f'Erro Stripe: {str(e)}'}


# =============================
# Webhook Stripe
# =============================
def verify_webhook(payload: bytes, signature: str) -> Dict[str, Any]:
	"""
	Verifica assinatura do webhook Stripe e retorna evento.
	
	Args:
		payload: Corpo da requisição (bytes)
		signature: Header Stripe-Signature
	
	Returns:
		{'event_type': str, 'event_id': str, 'data': dict} ou {'error': str}
	"""
	webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
	if not webhook_secret:
		return {'error': 'STRIPE_WEBHOOK_SECRET não configurado'}
	
	try:
		event = stripe.Webhook.construct_event(
			payload=payload,
			sig_header=signature,
			secret=webhook_secret
		)
		
		return {
			'event_type': event['type'],
			'event_id': event['id'],
			'data': event['data']['object']
		}
	
	except ValueError:
		return {'error': 'Payload inválido'}
	except stripe.error.SignatureVerificationError:
		return {'error': 'Assinatura inválida'}


def handle_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Processa evento do webhook Stripe.
	
	Args:
		event: Evento retornado por verify_webhook()
	
	Returns:
		{'status': 'success'} ou {'status': 'error', 'message': str}
	"""
	event_type = event.get('event_type')
	data = event.get('data', {})
	
	dbg('BILLING', f"Processando webhook: {event_type}")
	
	# checkout.session.completed: Pagamento confirmado
	if event_type == 'checkout.session.completed':
		user_id = data.get('client_reference_id') or data.get('metadata', {}).get('user_id')
		plan_code = data.get('metadata', {}).get('plan_code')
		customer_id = data.get('customer')
		subscription_id = data.get('subscription')
		
		if not all([user_id, plan_code, customer_id, subscription_id]):
			return {'status': 'error', 'message': 'Dados incompletos no evento'}
		
		# Atualizar plano do usuário
		result = upgrade_plan(user_id, plan_code, customer_id, subscription_id)
		if 'error' in result:
			return {'status': 'error', 'message': result['error']}
		
		dbg('BILLING', f"Upgrade concluído: user_id={user_id} plan={plan_code}")
		return {'status': 'success'}
	
	# customer.subscription.deleted: Assinatura cancelada
	elif event_type == 'customer.subscription.deleted':
		subscription_id = data.get('id')
		
		if subscription_id:
			# Reverter para plano FREE
			sql = """
			UPDATE public.user_settings 
			SET plan_id = (SELECT id FROM public.system_plans WHERE code = 'FREE' LIMIT 1),
				gateway_subscription_id = NULL
			WHERE gateway_subscription_id = %s
			"""
			db_execute(sql, (subscription_id,), ctx="BILLING.cancel_subscription")
			dbg('BILLING', f"Assinatura cancelada: {subscription_id}")
		
		return {'status': 'success'}
	
	# Outros eventos (ignorar por enquanto)
	else:
		dbg('BILLING', f"Evento não processado: {event_type}")
		return {'status': 'success'}


# =============================
# Cancelamento de Assinatura
# =============================
def cancel_subscription(user_id: str) -> Dict[str, Any]:
	"""
	Cancela assinatura Stripe do usuário.
	
	Args:
		user_id: ID do usuário
	
	Returns:
		{'status': 'success', 'ends_at': timestamp} ou {'error': str}
	"""
	settings = get_user_settings(user_id)
	subscription_id = settings.get('gateway_subscription_id')
	
	if not subscription_id:
		return {'error': 'Usuário não possui assinatura ativa'}
	
	try:
		# Cancelar no Stripe (cancela ao final do período pago)
		subscription = stripe.Subscription.modify(
			subscription_id,
			cancel_at_period_end=True
		)
		
		ends_at = subscription.current_period_end
		dbg('BILLING', f"Assinatura cancelada: user_id={user_id} ends_at={ends_at}")
		
		return {
			'status': 'success',
			'ends_at': ends_at
		}
	
	except stripe.error.StripeError as e:
		dbg('BILLING', f"Erro ao cancelar assinatura: {e}")
		return {'error': f'Erro Stripe: {str(e)}'}


# =============================
# Snapshot de Uso
# =============================
def _count_event_today(user_id: str, event_type: str) -> int:
	sql = """
	SELECT COUNT(*) FROM public.user_usage_events
	 WHERE user_id = %s AND event_type = %s AND created_at_date = current_date
	"""
	row = db_fetch_one(sql, (user_id, event_type), ctx="BILLING.count_event")
	if not row:
		return 0
	if isinstance(row, dict):
		return int(list(row.values())[0])
	return int(row[0])


def _count_favoritos(user_id: str) -> int:
	sql = "SELECT COUNT(*) FROM public.user_bookmarks WHERE user_id = %s AND active = true"
	row = db_fetch_one(sql, (user_id,), ctx="BILLING.count_fav")
	if not row:
		return 0
	if isinstance(row, dict):
		return int(list(row.values())[0])
	return int(row[0])


def get_usage_snapshot(user_id: str) -> Dict[str, Any]:
	settings = get_user_settings(user_id)
	usage = {
		'consultas': _count_event_today(user_id, 'query'),
		'resumos': _count_event_today(user_id, 'summary_success'),
		'boletim_run': _count_event_today(user_id, 'boletim_run'),
		'favoritos': _count_favoritos(user_id),
	}
	return {
		'user_id': user_id,
		'plan_code': settings['plan_code'],
		'limits': settings['limits'],
		'usage': usage,
		'generated_at': _dt.datetime.utcnow().isoformat(),
	}


__all__ = [
	'get_system_plans', 
	'get_user_settings', 
	'get_usage_snapshot',
	'create_checkout_session',
	'verify_webhook',
	'handle_webhook_event',
	'cancel_subscription',
]

# =============================
# Gerenciamento interno de plano (sem cobrança)
# =============================
def _plan_code_to_id(plan_code: str) -> Optional[int]:
	if not plan_code:
		return None
	row = db_fetch_one("SELECT id FROM public.system_plans WHERE code = %s AND active = true", (plan_code,), ctx="BILLING.plan_code_to_id")
	if not row:
		return None
	return row[0] if not isinstance(row, dict) else row.get('id')

def upgrade_plan(user_id: str, target_plan_code: str, 
				  gateway_customer_id: str = None, 
				  gateway_subscription_id: str = None) -> Dict[str, Any]:
	"""
	Atualiza plano do usuário (com ou sem IDs do Stripe).
	
	Args:
		user_id: ID do usuário
		target_plan_code: Código do plano (FREE, PLUS, PRO, CORP)
		gateway_customer_id: ID do Customer no Stripe (opcional)
		gateway_subscription_id: ID da Subscription no Stripe (opcional)
	
	Returns:
		Configurações atualizadas do usuário ou {'error': str}
	"""
	pid = _plan_code_to_id(target_plan_code)
	if not user_id or pid is None:
		return {'error': 'Plano inválido'}
	
	# Monta SQL com ou sem IDs Stripe
	if gateway_customer_id and gateway_subscription_id:
		sql = """
		UPDATE public.user_settings 
		SET plan_id = %s, 
			next_plan_id = NULL, 
			plan_status = 'active', 
			plan_started_at = COALESCE(plan_started_at, now()),
			gateway_customer_id = %s,
			gateway_subscription_id = %s
		WHERE user_id = %s
		"""
		params = (pid, gateway_customer_id, gateway_subscription_id, user_id)
	else:
		sql = """
		UPDATE public.user_settings 
		SET plan_id = %s, 
			next_plan_id = NULL, 
			plan_status = 'active', 
			plan_started_at = COALESCE(plan_started_at, now())
		WHERE user_id = %s
		"""
		params = (pid, user_id)
	
	db_execute(sql, params, ctx="BILLING.upgrade_plan")
	return get_user_settings(user_id)

def schedule_downgrade(user_id: str, target_plan_code: str) -> Dict[str, Any]:
	pid = _plan_code_to_id(target_plan_code)
	if not user_id or pid is None:
		return {'error': 'Plano inválido'}
	db_execute("UPDATE public.user_settings SET next_plan_id = %s WHERE user_id = %s", (pid, user_id), ctx="BILLING.schedule_downgrade")
	return get_user_settings(user_id)

def cancel_scheduled_downgrade(user_id: str) -> Dict[str, Any]:
	if not user_id:
		return {'error': 'Usuário inválido'}
	db_execute("UPDATE public.user_settings SET next_plan_id = NULL WHERE user_id = %s", (user_id,), ctx="BILLING.cancel_sched")
	return get_user_settings(user_id)

def apply_scheduled_plan_changes(user_id: str) -> Dict[str, Any]:
	# Aplica next_plan_id se existir (simula renovação)
	row = db_fetch_one("SELECT next_plan_id FROM public.user_settings WHERE user_id = %s", (user_id,), ctx="BILLING.apply_sched")
	if not row:
		return {'error': 'Usuário sem settings'}
	next_pid = row[0] if not isinstance(row, dict) else row.get('next_plan_id')
	if not next_pid:
		return {'status': 'nothing_to_apply'}
	db_execute("UPDATE public.user_settings SET plan_id = next_plan_id, next_plan_id = NULL WHERE user_id = %s", (user_id,), ctx="BILLING.apply_sched_upd")
	return get_user_settings(user_id)

def get_plan_map() -> Dict[str, int]:
	rows = db_fetch_all("SELECT code, id FROM public.system_plans WHERE active = true", ctx="BILLING.plan_map")
	out = {}
	for r in rows:
		code = r[0] if not isinstance(r, dict) else r.get('code')
		pid = r[1] if not isinstance(r, dict) else r.get('id')
		if code and pid:
			out[str(code).upper()] = int(pid)
	return out

__all__ += ['upgrade_plan', 'schedule_downgrade', 'cancel_scheduled_downgrade', 'apply_scheduled_plan_changes', 'get_plan_map']

