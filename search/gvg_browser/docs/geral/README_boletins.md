# Boletins (agendados)

- UI permite cadastrar/ativar/desativar boletins por usuário
- Persistência: agora em `public.user_schedule` (antes `user_boletins`)
- Resultados por execução são gravados em `public.user_boletim`
- Migração SQL: veja `db/migrations/2025-09-11_user_schedule_and_user_boletim.sql` (na raiz do projeto)
- Execução manual/cron: `python -m search.gvg_browser.scripts.run_scheduled_boletins`

Campos JSON de referência:
- `config_snapshot`: {"sort_mode": 1, "max_results": 30, "search_type": 1, "filter_expired": true, "relevance_level": 2, "search_approach": 3, "top_categories_count": 10}
- `schedule_detail`: {"slots": ["manha", "tarde", "noite"], "days": ["seg","ter",...]} (para SEMANAL)
- `channels`: ["email", "whatsapp"]
