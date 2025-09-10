"""
Autenticação Supabase para o GSB (Dash).
- Usa supabase-py v2 (supabase).
- Lê SUPABASE_URL e SUPABASE_ANON_KEY do .env (raiz do projeto ou pasta gvg_browser).
- Fornece funções: init_client, sign_in, sign_up_with_metadata, verify_otp, reset_password, sign_out, get_user_from_token.
- Tokens devem ser mantidos em cookies HttpOnly pela camada Flask (não em Stores do Dash).
"""
from __future__ import annotations

import os
from typing import Optional, Tuple, Dict, Any
import datetime as _dt
import traceback as _tb

from dotenv import load_dotenv

try:
    from supabase import create_client
except Exception:  # pacote pode não estar instalado ainda
    create_client = None  # type: ignore

# Carregar .env de forma defensiva
for candidate in (
    os.path.join(os.path.dirname(__file__), ".env"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
):
    if os.path.exists(candidate):
        load_dotenv(candidate, override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

_client: Optional[Any] = None

from gvg_debug import debug_log as dbg
def _dbg(tag: str, msg: str, extra: Optional[Dict[str, Any]] = None):
    try:
        payload = f"[gvg_auth.{tag}] {msg}"
        if extra:
            payload += f" | extra={extra}"
        dbg('AUTH', payload)
    except Exception:
        pass

def init_client() -> Optional[Any]:
    global _client
    if _client is not None:
        _dbg('init_client', 'Returning cached client')
        return _client
    if not create_client:
        _dbg('init_client', 'create_client not available (supabase not installed?)')
        return None
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        _dbg('init_client', 'Missing SUPABASE_URL or SUPABASE_ANON_KEY', {
            'has_url': bool(SUPABASE_URL),
            'has_key': bool(SUPABASE_ANON_KEY),
        })
        return None
    try:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        _dbg('init_client', 'Client created successfully')
        return _client
    except Exception as e:
        _dbg('init_client', f'Exception creating client: {type(e).__name__}: {e}')
        return None


def sign_in(email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Login com email/senha. Retorna (ok, session_dict, error_msg).
    session_dict: {'user': {uid,email,name,phone}, 'access_token', 'refresh_token'}
    """
    client = init_client()
    if not client:
        return False, None, "Cliente Supabase não inicializado"
    try:
        _dbg('sign_in', 'Attempting sign_in_with_password', {'email': email})
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        session = getattr(res, "session", None)
        user = getattr(res, "user", None)
        if session and user:
            user_info = {
                "uid": user.id,
                "email": user.email,
                "name": (user.user_metadata or {}).get("full_name") or (user.user_metadata or {}).get("name") or user.email,
                "phone": (user.user_metadata or {}).get("phone"),
            }
            out = {
                'user': user_info,
                'access_token': session.access_token,
                'refresh_token': session.refresh_token,
            }
            _dbg('sign_in', 'Login success', {'uid': user_info['uid']})
            return True, out, ""
        # Sem sessão/usuário: logar estrutura retornada
        try:
            _dbg('sign_in', 'No session/user returned', {
                'has_session': bool(session),
                'has_user': bool(user),
                'res_attrs': list(getattr(res, '__dict__', {}).keys()) if res else None,
            })
        except Exception:
            pass
        return False, None, "Credenciais inválidas ou e‑mail não confirmado"
    except Exception as e:
        _dbg('sign_in', f'Exception during sign_in: {type(e).__name__}: {e}')
        _dbg('sign_in', 'Traceback:\n' + _tb.format_exc())
        msg = f"{type(e).__name__}: {e}"
        # Tornar mensagem amigável para UI em casos comuns
        if 'Invalid login credentials' in str(e):
            msg = 'E-mail ou senha inválidos.'
        return False, None, msg


def sign_up_with_metadata(email: str, password: str, full_name: str, phone: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Cadastro com envio de OTP por e‑mail. Retorna (ok, error_msg)."""
    client = init_client()
    if not client:
        return False, "Cliente Supabase não inicializado"
    try:
        _dbg('sign_up', 'Attempting sign_up', {'email': email, 'has_phone': bool(phone)})
        res = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name, "phone": phone}}
        })
        # Se email confirm required via OTP, Supabase envia código automaticamente.
        u = getattr(res, "user", None)
        s = getattr(res, "session", None)
        try:
            _dbg('sign_up', 'Raw response', {
                'has_user': bool(u), 'has_session': bool(s),
                'user_id': getattr(u, 'id', None),
                'email_confirmed': getattr(u, 'email_confirmed_at', None) is not None,
            })
        except Exception:
            pass
        if u is not None:
            _dbg('sign_up', 'Sign up OK; OTP should be sent', {'uid': getattr(u, 'id', None)})
            return True, None
        _dbg('sign_up', 'Sign up failed (no user returned)')
        return False, "Falha ao cadastrar"
    except Exception as e:
        _dbg('sign_up', f'Exception during sign_up: {type(e).__name__}: {e}')
        _dbg('sign_up', 'Traceback:\n' + _tb.format_exc())
        return False, f"{type(e).__name__}: {e}"


def verify_otp(email: str, token: str, type_: str = "signup") -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Confirma código OTP. type_: 'signup' ou 'email_change'.
    Retorna (ok, session_dict, error)
    """
    client = init_client()
    if not client:
        return False, None, "Cliente Supabase não inicializado"
    try:
        _dbg('verify_otp', 'Verifying OTP', {'email': email, 'type': type_})
        res = client.auth.verify_otp({"email": email, "token": token, "type": type_})
        session = getattr(res, "session", None)
        user = getattr(res, "user", None)
        if session and user:
            user_info = {
                "uid": user.id,
                "email": user.email,
                "name": (user.user_metadata or {}).get("full_name") or user.email,
                "phone": (user.user_metadata or {}).get("phone"),
            }
            out = {
                'user': user_info,
                'access_token': session.access_token,
                'refresh_token': session.refresh_token,
            }
            _dbg('verify_otp', 'OTP verified successfully', {'uid': user_info['uid']})
            return True, out, ""
        _dbg('verify_otp', 'Verification failed (no session/user)')
        return False, None, "Código inválido"
    except Exception as e:
        _dbg('verify_otp', f'Exception during verify_otp: {type(e).__name__}: {e}')
        _dbg('verify_otp', 'Traceback:\n' + _tb.format_exc())
        return False, None, f"{type(e).__name__}: {e}"


def reset_password(email: str) -> Tuple[bool, Optional[str]]:
    client = init_client()
    if not client:
        return False, "Cliente Supabase não inicializado"
    try:
        _dbg('reset_password', 'Requesting reset email', {'email': email})
        client.auth.reset_password_email(email)
        return True, None
    except Exception as e:
        _dbg('reset_password', f'Exception during reset_password: {type(e).__name__}: {e}')
        _dbg('reset_password', 'Traceback:\n' + _tb.format_exc())
        return False, f"{type(e).__name__}: {e}"


def sign_out(refresh_token: Optional[str]) -> bool:
    client = init_client()
    if not client:
        return False
    try:
        _dbg('sign_out', 'Signing out', {'has_refresh_token': bool(refresh_token)})
        if refresh_token:
            client.auth.sign_out(refresh_token)
        else:
            client.auth.sign_out()
        return True
    except Exception as e:
        _dbg('sign_out', f'Exception during sign_out: {type(e).__name__}: {e}')
        return False


def get_user_from_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Valida token e retorna dados básicos do usuário (uid, email, nome, phone)."""
    client = init_client()
    if not client:
        return None
    try:
        _dbg('get_user_from_token', 'Fetching user from token', {'token_len': len(access_token or '')})
        user = client.auth.get_user(access_token)
        if not user:
            _dbg('get_user_from_token', 'No user returned for token')
            return None
        u = getattr(user, "user", None) or user
        out = {
            "uid": u.id,
            "email": u.email,
            "name": (u.user_metadata or {}).get("full_name") or u.email,
            "phone": (u.user_metadata or {}).get("phone"),
        }
        _dbg('get_user_from_token', 'User resolved from token', {'uid': out['uid']})
        return out
    except Exception as e:
        _dbg('get_user_from_token', f'Exception during get_user_from_token: {type(e).__name__}: {e}')
        _dbg('get_user_from_token', 'Traceback:\n' + _tb.format_exc())
        return None


def resend_otp(email: str, type_: str = 'signup') -> Tuple[bool, Optional[str]]:
    """Reenvia um novo código OTP para o e-mail informado (tipos: 'signup', 'email_change')."""
    client = init_client()
    if not client:
        return False, "Cliente Supabase não inicializado"
    try:
        _dbg('resend_otp', 'Requesting resend', {'email': email, 'type': type_})
        # Supabase GoTrue v2: resend aceita dict com { email, type }
        client.auth.resend({"email": email, "type": type_})
        return True, None
    except Exception as e:
        _dbg('resend_otp', f'Exception during resend_otp: {type(e).__name__}: {e}')
        _dbg('resend_otp', 'Traceback:\n' + _tb.format_exc())
        return False, f"{type(e).__name__}: {e}"
