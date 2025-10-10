"""Camada Billing (Step3 Mock)

Consolida:
- Leitura de planos (system_plans)
- Leitura/atualização de user_settings
- Snapshot simples de uso atual (eventos hoje + favoritos)
- Fluxo de checkout mock (gateway fictício local)

Sem chamadas externas. Preparado para futura integração Pagar.me.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import uuid
import datetime as _dt
import os
import csv

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
		dbg('BILLING', f"Erro ao carregar plans fallback CSV: {e}")
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
		dbg('BILLING', f"mock_session plan={plan_code} uid={user_id} sid={session_id}")
		return {
			'session_id': session_id,
			'plan_code': plan_code,
			'user_id': user_id,
			'checkout_url': f"/checkout?session={session_id}",  # placeholder interno
			'created_at': _dt.datetime.utcnow().isoformat(),
		}

	def finalize(self, session_id: str) -> bool:
		# Mock sempre sucesso
		dbg('BILLING', f"mock_finalize sid={session_id}")
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
	sql = f"""
	SELECT us.user_id, sp.code AS plan_code, sp.name AS plan_name,
		   sp.limit_consultas_per_day, sp.limit_resumos_per_day, sp.limit_boletim_per_day, sp.limit_favoritos_capacity
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
	dbg('BILLING', f"upgrade_mock uid={user_id} plan={plan_code}")
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

def upgrade_plan(user_id: str, target_plan_code: str) -> Dict[str, Any]:
	pid = _plan_code_to_id(target_plan_code)
	if not user_id or pid is None:
		return {'error': 'Plano inválido'}
	# Aplica imediato (sem cobrança) e limpa next_plan_id
	# Removido updated_at (coluna não existe no schema atual user_settings)
	db_execute("UPDATE public.user_settings SET plan_id = %s, next_plan_id = NULL, plan_status='active', plan_started_at = COALESCE(plan_started_at, now()) WHERE user_id = %s", (pid, user_id), ctx="BILLING.upgrade_plan")
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

