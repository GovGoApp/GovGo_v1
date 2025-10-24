"""Camada Billing com mock local e integrações Stripe

Consolida:
- Leitura de planos (system_plans)
- Leitura/atualização de user_settings
- Snapshot simples de uso atual (eventos hoje + favoritos)
- Fluxo de checkout mock (gateway fictício local)
- Integração Stripe: Embedded Checkout/Popup, Webhook e helpers

Observações:
- Mantemos o mock para compatibilidade local.
- Quando variáveis STRIPE_* estiverem definidas, as funções Stripe funcionam.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import uuid
import datetime as _dt
import os
import csv
import json

# Stripe (opcional). Se ausente, as funções retornarão erro amigável
try:
	from dotenv import load_dotenv  # type: ignore
except Exception:
	load_dotenv = None  # type: ignore
try:
	import stripe  # type: ignore
	try:
		# Exceções específicas
		from stripe.error import StripeError, SignatureVerificationError  # type: ignore
	except Exception:  # fallback
		class StripeError(Exception):
			pass
		class SignatureVerificationError(Exception):
			pass
	STRIPE_AVAILABLE = True
except Exception:
	stripe = None  # type: ignore
	class StripeError(Exception):
		pass
	class SignatureVerificationError(Exception):
		pass
	STRIPE_AVAILABLE = False

if load_dotenv:
	try:
		load_dotenv()
	except Exception:
		pass
if STRIPE_AVAILABLE:
	try:
		stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
	except Exception:
		pass

from gvg_database import db_fetch_all, db_fetch_one, db_execute  # type: ignore
from gvg_debug import debug_log as dbg  # type: ignore

# Cache de planos do CSV (carregado uma vez)
_PLANS_FALLBACK_CACHE = None

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
		dbg('BILL', f"Erro ao carregar plans fallback CSV: {e}")
		# Fallback hardcoded se CSV falhar
		return {
			'FREE': {'limit_consultas_per_day': 5, 'limit_resumos_per_day': 1, 'limit_boletim_per_day': 1, 'limit_favoritos_capacity': 10},
			'PLUS': {'limit_consultas_per_day': 20, 'limit_resumos_per_day': 20, 'limit_boletim_per_day': 5, 'limit_favoritos_capacity': 200},
			'PRO': {'limit_consultas_per_day': 100, 'limit_resumos_per_day': 100, 'limit_boletim_per_day': 10, 'limit_favoritos_capacity': 2000},
			'CORP': {'limit_consultas_per_day': 1000, 'limit_resumos_per_day': 1000, 'limit_boletim_per_day': 100, 'limit_favoritos_capacity': 20000},
		}


# =============================
# Modelos e Gateway Mock
# =============================
@dataclass
class SystemPlan:
	id: int
	code: str
	name: str
	price_cents: int
	billing_period: str
	limit_consultas_per_day: int
	limit_resumos_per_day: int
	limit_boletim_per_day: int
	limit_favoritos_capacity: int


class MockBillingGateway:
	"""Gateway fictício de checkout (não persiste)."""

	def create_session(self, plan_code: str, user_id: str) -> Dict[str, Any]:
		session_id = str(uuid.uuid4())
		dbg('BILL', f"mock_session plan={plan_code} uid={user_id} sid={session_id}")
		return {
			'session_id': session_id,
			'plan_code': plan_code,
			'user_id': user_id,
			'checkout_url': f"/checkout?session={session_id}",  # placeholder interno
			'created_at': _dt.datetime.utcnow().isoformat(),
		}

	def finalize(self, session_id: str) -> bool:
		# Mock sempre sucesso
		dbg('BILL', f"mock_finalize sid={session_id}")
		return True


_GATEWAY_SINGLETON: Optional[MockBillingGateway] = None


def get_gateway() -> MockBillingGateway:
	global _GATEWAY_SINGLETON
	if _GATEWAY_SINGLETON is None:
		_GATEWAY_SINGLETON = MockBillingGateway()
	return _GATEWAY_SINGLETON


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
	# ORDER BY no valor original para preservar precisão
	sql = f"SELECT {PLAN_COLUMNS} FROM public.system_plans WHERE active = true ORDER BY price_month_brl ASC, id ASC"
	rows = db_fetch_all(sql, ctx="BILLING.get_system_plans")
	out: List[Dict[str, Any]] = []
	for r in rows:
		# rows pode ser list[tuple]; converter se necessário
		if isinstance(r, dict):
			out.append(r)  # já dict
		else:
			out.append({
				'id': r[0], 'code': r[1], 'name': r[2], 'price_cents': r[3], 'billing_period': r[4],
				'limit_consultas_per_day': r[5], 'limit_resumos_per_day': r[6], 'limit_boletim_per_day': r[7], 'limit_favoritos_capacity': r[8]
			})
	return out


def get_user_settings(user_id: str) -> Dict[str, Any]:
	if not user_id:
		return _fallback_free()
	# Buscar settings + IDs do gateway
	sql = f"""
	SELECT us.user_id,
	       sp.code AS plan_code,
	       sp.name AS plan_name,
	       sp.limit_consultas_per_day,
	       sp.limit_resumos_per_day,
	       sp.limit_boletim_per_day,
	       sp.limit_favoritos_capacity,
	       us.gateway_customer_id,
	       us.gateway_subscription_id
	  FROM public.user_settings us
	  JOIN public.system_plans sp ON sp.id = us.plan_id
	 WHERE us.user_id = %s
	"""
	row = db_fetch_one(sql, (user_id,), as_dict=True, ctx="BILLING.get_user_settings")
	dbg('BILL', f"get_user_settings: user_id={user_id} row={row}")
	if not row:
		# Se não existir, garantir criação automática com plano FREE
		try:
			_created = ensure_user_settings(user_id)
			dbg('BILL', f"get_user_settings: ensure_user_settings created={_created}")
		except Exception as e:
			dbg('BILL', f"get_user_settings: erro ensure_user_settings e={e}")
		# Tentar novamente
		row = db_fetch_one(sql, (user_id,), as_dict=True, ctx="BILLING.get_user_settings.retry")
		if not row:
			dbg('BILL', f"get_user_settings: row ainda vazio, retornando FREE fallback")
			return _fallback_free()
	result = {
		'user_id': user_id,
		'plan_code': row['plan_code'],
		'plan_name': row['plan_name'],
		'limits': {
			'consultas': row['limit_consultas_per_day'],
			'resumos': row['limit_resumos_per_day'],
			'boletim_run': row['limit_boletim_per_day'],
			'favoritos': row['limit_favoritos_capacity'],
		},
		'gateway_customer_id': row.get('gateway_customer_id'),
		'gateway_subscription_id': row.get('gateway_subscription_id'),
	}
	dbg('BILL', f"get_user_settings: retornando result={result}")
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
# Checkout Mock
# =============================
def start_checkout(plan_code: str, user_id: str) -> Dict[str, Any]:
	if not plan_code or not user_id:
		return {'error': 'Parâmetros inválidos'}
	# Validar plano
	sql = "SELECT id FROM public.system_plans WHERE code = %s AND active = true"
	row = db_fetch_one(sql, (plan_code,), ctx="BILLING.start_checkout")
	if not row:
		return {'error': 'Plano inexistente ou inativo'}
	gw = get_gateway()
	session = gw.create_session(plan_code, user_id)
	return session


def finalize_upgrade_mock(user_id: str, plan_code: str) -> Dict[str, Any]:
	if not user_id or not plan_code:
		return {'error': 'Parâmetros inválidos'}
	# Obter id do plano
	row = db_fetch_one("SELECT id FROM public.system_plans WHERE code = %s AND active = true", (plan_code,), ctx="BILLING.finalize_upgrade")
	if not row:
		return {'error': 'Plano inválido'}
	plan_id = row[0] if not isinstance(row, dict) else row['id']
	# Atualiza user_settings (precisa existir registro)
	affected = db_execute("UPDATE public.user_settings SET plan_id = %s WHERE user_id = %s", (plan_id, user_id), ctx="BILLING.upd_plan")
	if affected == 0:
		# tentativa de insert se não existir
		db_execute("INSERT INTO public.user_settings (user_id, plan_id) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET plan_id = EXCLUDED.plan_id", (user_id, plan_id), ctx="BILLING.ins_plan")
	dbg('BILL', f"upgrade_mock uid={user_id} plan={plan_code}")
	return get_user_settings(user_id)


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
	'get_system_plans', 'get_user_settings', 'start_checkout', 'finalize_upgrade_mock', 'get_usage_snapshot', 'get_gateway'
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

def _get_free_plan_id_default() -> int:
	"""Obtém o id do plano FREE; se não achar, retorna 1 como fallback."""
	row = db_fetch_one("SELECT id FROM public.system_plans WHERE UPPER(code)='FREE' LIMIT 1", ctx="BILLING.free_plan")
	if not row:
		return 1
	return row[0] if not isinstance(row, dict) else int(row.get('id', 1))


def ensure_user_settings(user_id: str) -> bool:
	"""Garante que exista uma linha em user_settings para o usuário (plano FREE).
	Retorna True se inseriu, False se já existia ou nada foi feito.
	"""
	if not user_id:
		return False
	free_id = _get_free_plan_id_default()
	sql = (
		"INSERT INTO public.user_settings (user_id, plan_id, plan_status, plan_started_at) "
		"VALUES (%s, %s, 'active', now()) "
		"ON CONFLICT (user_id) DO NOTHING"
	)
	affected = 0
	try:
		affected = db_execute(sql, (user_id, free_id), ctx="BILLING.ensure_user_settings")
		try:
			dbg('BILL', f"ensure_user_settings uid={user_id} affected={affected}")
		except Exception:
			pass
	except Exception as e:
		try:
			dbg('BILL', f"ensure_user_settings erro: {e}")
		except Exception:
			pass
	return affected > 0


def upgrade_plan(user_id: str, target_plan_code: str, gateway_customer_id: Optional[str] = None, gateway_subscription_id: Optional[str] = None) -> Dict[str, Any]:
	pid = _plan_code_to_id(target_plan_code)
	if not user_id or pid is None:
		return {'error': 'Plano inválido'}
	# Tentar UPDATE direto
	sql_upd = (
		"UPDATE public.user_settings "
		"SET plan_id = %s, next_plan_id = NULL, plan_status='active', "
		"plan_started_at = COALESCE(plan_started_at, now()), "
		"gateway_customer_id = COALESCE(%s, gateway_customer_id), "
		"gateway_subscription_id = COALESCE(%s, gateway_subscription_id) "
		"WHERE user_id = %s"
	)
	affected = db_execute(sql_upd, (pid, gateway_customer_id, gateway_subscription_id, user_id), ctx="BILLING.upgrade_plan.upd")
	if affected == 0:
		# Upsert se não existir
		sql_ins = (
			"INSERT INTO public.user_settings (user_id, plan_id, next_plan_id, plan_status, plan_started_at, gateway_customer_id, gateway_subscription_id) "
			"VALUES (%s, %s, NULL, 'active', now(), %s, %s) "
			"ON CONFLICT (user_id) DO UPDATE SET "
			"plan_id = EXCLUDED.plan_id, next_plan_id = EXCLUDED.next_plan_id, plan_status = EXCLUDED.plan_status, "
			"plan_started_at = COALESCE(user_settings.plan_started_at, EXCLUDED.plan_started_at), "
			"gateway_customer_id = COALESCE(EXCLUDED.gateway_customer_id, user_settings.gateway_customer_id), "
			"gateway_subscription_id = COALESCE(EXCLUDED.gateway_subscription_id, user_settings.gateway_subscription_id)"
		)
		db_execute(sql_ins, (user_id, pid, gateway_customer_id, gateway_subscription_id), ctx="BILLING.upgrade_plan.ins")
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

# =============================
# Helpers Stripe / Plan lookup
# =============================
def _get_plan_by_code(plan_code: str) -> Optional[Dict[str, Any]]:
	if not plan_code:
		return None
	sql = (
		"SELECT id, code, name, price_month_brl, stripe_product_id, stripe_price_id, active "
		"FROM public.system_plans WHERE active = true AND UPPER(code) = UPPER(%s) LIMIT 1"
	)
	row = db_fetch_one(sql, (plan_code,), as_dict=True, ctx="BILLING._get_plan_by_code")
	return row if row else None


# =============================
# Stripe Checkout (popup) - legado
# =============================
def create_checkout_session(user_id: str, plan_code: str, email: str, name: Optional[str] = None) -> Dict[str, Any]:
	"""Cria sessão do Stripe Checkout (popup) para assinatura recorrente."""
	if not STRIPE_AVAILABLE:
		return {'error': 'Stripe não disponível neste ambiente'}
	if not all([user_id, plan_code, email]):
		return {'error': 'Parâmetros obrigatórios faltando'}
	plan = _get_plan_by_code(plan_code)
	if not plan:
		return {'error': 'Plano inexistente ou inativo'}
	price_id = plan.get('stripe_price_id')
	if not price_id:
		return {'error': f'Price ID não configurado para plano {plan_code}'}
	base_url = os.getenv('BASE_URL', 'http://localhost:8060')
	try:
		session = stripe.checkout.Session.create(
			payment_method_types=['card'],
			mode='subscription',
			customer_email=email,
			client_reference_id=user_id,
			line_items=[{'price': price_id, 'quantity': 1}],
			success_url=f'{base_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}',
			cancel_url=f'{base_url}/checkout/cancel',
			metadata={'user_id': user_id, 'plan_code': plan_code}
		)
		try:
			dbg('BILL', f"[create_checkout_session] sid={getattr(session,'id',None)} user={user_id} plan={plan_code}")
		except Exception:
			pass
		return {'checkout_url': getattr(session,'url',None), 'session_id': getattr(session,'id',None)}
	except StripeError as e:
		try:
			dbg('BILL', f"[create_checkout_session] StripeError: {e}")
		except Exception:
			pass
		return {'error': f'Erro Stripe: {str(e)}'}


# =============================
# Stripe Checkout Embedded (ui_mode='embedded')
# =============================
def create_checkout_embedded_session(user_id: str, plan_code: str, email: str, name: Optional[str] = None) -> Dict[str, Any]:
	"""Cria sessão Embedded Checkout e retorna client_secret para montar no modal."""
	try:
		dbg('BILL', f"[create_checkout_embedded_session] start uid={user_id} plan={plan_code}")
	except Exception:
		pass
	if not STRIPE_AVAILABLE:
		return {'error': 'Stripe não disponível neste ambiente'}
	if not all([user_id, plan_code, email]):
		return {'error': 'Parâmetros obrigatórios faltando'}
	plan = _get_plan_by_code(plan_code)
	if not plan:
		return {'error': 'Plano inexistente ou inativo'}
	price_id = plan.get('stripe_price_id')
	if not price_id:
		return {'error': f'Price ID não configurado para plano {plan_code}'}
	try:
		session = stripe.checkout.Session.create(
			ui_mode='embedded',
			mode='subscription',
			customer_email=email,
			client_reference_id=user_id,
			line_items=[{'price': price_id, 'quantity': 1}],
			metadata={'user_id': user_id, 'plan_code': plan_code},
			# Embedded exige return_url OU desativar redirect automático
			redirect_on_completion='never'
		)
		has_secret = bool(getattr(session, 'client_secret', None))
		try:
			dbg('BILL', f"[create_checkout_embedded_session] sid={getattr(session,'id',None)} has_client_secret={has_secret}")
		except Exception:
			pass
		return {
			'checkout_session_id': getattr(session,'id',None),
			'client_secret': getattr(session, 'client_secret', None),
			'plan_code': plan_code
		}
	except StripeError as e:
		try:
			dbg('BILL', f"[create_checkout_embedded_session] StripeError: {e}")
		except Exception:
			pass
		return {'error': f'Erro Stripe: {str(e)}'}


# =============================
# Stripe Elements (legado) – stub para compat
# =============================
def create_subscription_elements(user_id: str, plan_code: str, email: str, name: Optional[str] = None) -> Dict[str, Any]:
	"""Stub: manter compat do endpoint legado; preferir Embedded Checkout."""
	return {'error': 'Fluxo Elements desativado. Use Embedded Checkout.'}


def apply_subscription_result(user_id: str, plan_code: str, customer_id: str, subscription_id: str,
							  payment_intent_id: Optional[str], amount_paid: Optional[float], currency: str = 'BRL') -> Dict[str, Any]:
	"""Aplica resultado de cobrança (compatibilidade com Elements)."""
	if not all([user_id, plan_code, customer_id, subscription_id]):
		return {'error': 'Dados insuficientes'}
	updated = upgrade_plan(user_id, plan_code,)
	if isinstance(updated, dict) and updated.get('error'):
		return {'error': updated.get('error')}
	try:
		amount_val = float(amount_paid) if amount_paid is not None else 0.0
		currency_val = (currency or 'BRL').upper()
		plan = _get_plan_by_code(plan_code) or {}
		plan_id = plan.get('id')
		sql_history = (
			"INSERT INTO public.user_payment (user_id, plan_id, stripe_customer_id, stripe_subscription_id, "
			"stripe_payment_intent_id, amount_paid, currency, status, event_type, metadata) "
			"VALUES (%s, %s, %s, %s, %s, %s, %s, 'succeeded', 'upgrade', %s)"
		)
		metadata = {'source': 'elements_apply'}
		db_execute(sql_history, (
			user_id, plan_id, customer_id, subscription_id,
			payment_intent_id, amount_val, currency_val, json.dumps(metadata)
		), ctx="BILLING.save_payment_apply")
	except Exception as e:
		try:
			dbg('BILL', f"[apply_subscription_result] erro histórico: {e}")
		except Exception:
			pass
	return {'status': 'success'}


# =============================
# Webhook Stripe
# =============================
def verify_webhook(payload: bytes, signature: str) -> Dict[str, Any]:
	webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
	try:
		dbg('BILL', f"[verify_webhook] signature_present={bool(signature)} secret_present={bool(webhook_secret)}")
	except Exception:
		pass
	if not STRIPE_AVAILABLE:
		return {'error': 'Stripe não disponível neste ambiente'}
	if not webhook_secret:
		return {'error': 'STRIPE_WEBHOOK_SECRET não configurado'}
	try:
		event = stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=webhook_secret)
		return {'event_type': event['type'], 'event_id': event['id'], 'data': event['data']['object']}
	except ValueError:
		return {'error': 'Payload inválido'}
	except SignatureVerificationError:
		return {'error': 'Assinatura inválida'}


def handle_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
	event_type = event.get('event_type')
	data = event.get('data', {})
	try:
		dbg('BILL', f"[handle_webhook_event] type={event_type}")
	except Exception:
		pass
	if event_type == 'checkout.session.completed':
		user_id = data.get('client_reference_id') or (data.get('metadata') or {}).get('user_id')
		plan_code = (data.get('metadata') or {}).get('plan_code')
		customer_id = data.get('customer')
		subscription_id = data.get('subscription')
		amount_total = (data.get('amount_total') or 0) / 100
		currency = (data.get('currency') or 'brl').upper()
		payment_intent = data.get('payment_intent')
		try:
			dbg('BILL', f"[webhook.completed] uid={user_id} plan={plan_code} cust={customer_id} sub={subscription_id} amount={amount_total} {currency}")
		except Exception:
			pass
		if not all([user_id, plan_code, customer_id, subscription_id]):
			return {'status': 'error', 'message': 'Dados incompletos no evento'}
		plan = _get_plan_by_code(plan_code)
		if not plan:
			return {'status': 'error', 'message': f'Plano {plan_code} não encontrado'}
		plan_id = plan.get('id')
		# Persistir plano e IDs do gateway no user_settings (upsert)
		result = upgrade_plan(user_id, plan_code, customer_id, subscription_id)
		try:
			dbg('BILL', f"[webhook.completed] upgrade_plan applied uid={user_id} plan={plan_code} cust={customer_id} sub={subscription_id}")
		except Exception:
			pass
		if 'error' in result:
			return {'status': 'error', 'message': result['error']}
		try:
			sql_history = (
				"INSERT INTO public.user_payment (user_id, plan_id, stripe_customer_id, stripe_subscription_id, "
				"stripe_payment_intent_id, amount_paid, currency, status, event_type, metadata) "
				"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
			)
			metadata = {
				'event_id': event.get('event_id'),
				'event_type': event_type,
				'plan_code': plan_code,
				'checkout_session_id': data.get('id')
			}
			db_execute(sql_history, (
				user_id, plan_id, customer_id, subscription_id,
				payment_intent, amount_total, currency, 'succeeded', 'upgrade', json.dumps(metadata)
			), ctx="BILLING.save_payment_history")
			try:
				dbg('BILL', f"[webhook.completed] histórico salvo: uid={user_id} plan={plan_code} amount={amount_total}")
			except Exception:
				pass
		except Exception as e:
			try:
				dbg('BILL', f"[webhook.completed] erro salvar histórico: {e}")
			except Exception:
				pass
		return {'status': 'success'}
	elif event_type == 'customer.subscription.deleted':
		subscription_id = data.get('id')
		if subscription_id:
			sql = (
				"UPDATE public.user_settings SET plan_id = (SELECT id FROM public.system_plans WHERE code = 'FREE' LIMIT 1), "
				"gateway_subscription_id = NULL WHERE gateway_subscription_id = %s"
			)
			db_execute(sql, (subscription_id,), ctx="BILLING.cancel_subscription")
			try:
				dbg('BILL', f"[webhook.canceled] assinatura cancelada sub={subscription_id}")
			except Exception:
				pass
		return {'status': 'success'}
	else:
		try:
			dbg('BILL', f"[handle_webhook_event] ignorado type={event_type}")
		except Exception:
			pass
		return {'status': 'success'}


# =============================
# Cancelamento de Assinatura
# =============================
def cancel_subscription(user_id: str) -> Dict[str, Any]:
	if not STRIPE_AVAILABLE:
		return {'error': 'Stripe não disponível neste ambiente'}
	settings = get_user_settings(user_id)
	subscription_id = settings.get('gateway_subscription_id')
	if not subscription_id:
		return {'error': 'Usuário não possui assinatura ativa'}
	try:
		subscription = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
		ends_at = getattr(subscription, 'current_period_end', None)
		try:
			dbg('BILL', f"[cancel_subscription] uid={user_id} sub={subscription_id} ends_at={ends_at}")
		except Exception:
			pass
		return {'status': 'success', 'ends_at': ends_at}
	except StripeError as e:
		try:
			dbg('BILL', f"[cancel_subscription] StripeError: {e}")
		except Exception:
			pass
		return {'error': f'Erro Stripe: {str(e)}'}


# Exportar símbolos Stripe para quem importa deste módulo
__all__ += ['create_checkout_session', 'create_checkout_embedded_session', 'create_subscription_elements', 'apply_subscription_result', 'verify_webhook', 'handle_webhook_event', 'cancel_subscription']

