-- Governança GovGo — Sommelier snapshots
-- Data: 2025-11-24
-- Objetivo: permitir caching completo de Contratos/Editais por CNPJ.

BEGIN;

ALTER TABLE sommelier.prompt
    ADD COLUMN IF NOT EXISTS contratos JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS editais   JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN sommelier.prompt.contratos IS
    'Snapshot dos contratos exibidos no Sommelier (lista JSON pronta para a aba).';

COMMENT ON COLUMN sommelier.prompt.editais IS
    'Snapshot dos editais exibidos no Sommelier (lista JSON pronta para a aba).';

COMMIT;
