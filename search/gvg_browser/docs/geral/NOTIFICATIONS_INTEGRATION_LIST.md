# Lista de Notificações para Integração no GSB

## 📋 Resumo Executivo
Esta lista identifica **32 pontos críticos** onde notificações Toast devem ser integradas no GovGo Search Browser (GSB) para melhorar significativamente a experiência do usuário com feedback visual imediato.

## 🎯 Categorização por Prioridade

### 🔴 PRIORIDADE ALTA (Implementação Imediata)

#### 1. **BUSCA E PESQUISA** (Callback: `run_search`)
- **Linha ~3149**: Função principal de busca
  - ✅ **SUCESSO**: "Busca concluída: X resultados encontrados"
    - Quando: `len(results) > 0` ao final da busca
    - Tipo: `NOTIF_SUCCESS`
  - ℹ️ **INFO**: "Nenhum resultado encontrado. Tente termos diferentes."
    - Quando: `len(results) == 0` após busca bem-sucedida
    - Tipo: `NOTIF_INFO`
  - ℹ️ **INFO**: "Busca limitada: Usando apenas filtros SQL"
    - Quando: `filter_route == 'sql-only'`
    - Tipo: `NOTIF_INFO`
  - ❌ **ERROR**: "Erro ao executar busca. Tente novamente."
    - Quando: Exception no bloco try/except da busca
    - Tipo: `NOTIF_ERROR`

#### 2. **LIMITES DE USO** (Callback: `run_search`, linha ~3240)
- ❌ **ERROR**: "Limite diário de consultas atingido. Faça upgrade do plano."
  - Quando: `LimitExceeded` exception em `ensure_capacity(uid, 'consultas')`
  - Tipo: `NOTIF_ERROR`
  - **CRÍTICO**: Usuário está bloqueado e precisa saber imediatamente

#### 3. **RESUMOS DE DOCUMENTOS** (Callback: `load_resumo_for_cards`, linha ~5410)
- ❌ **ERROR**: "Limite diário de resumos atingido. Faça upgrade do plano."
  - Quando: `LimitExceeded` exception em `ensure_capacity(uid, 'resumos')`
  - Tipo: `NOTIF_ERROR`
  - **CRÍTICO**: Bloqueio de funcionalidade paga
- ✅ **SUCCESS**: "Resumo gerado com sucesso!"
  - Quando: Resumo completado e salvo no cache
  - Tipo: `NOTIF_SUCCESS`
- ❌ **ERROR**: "Erro ao gerar resumo. Tente novamente."
  - Quando: Exception durante processamento do documento
  - Tipo: `NOTIF_ERROR`

#### 4. **EXPORTAÇÕES** (Callback: `export_files`, linha ~6927)
- ✅ **SUCCESS**: "Arquivo JSON exportado com sucesso!"
  - Quando: `btn_id == 'export-json'` e exportação bem-sucedida
  - Tipo: `NOTIF_SUCCESS`
- ✅ **SUCCESS**: "Planilha Excel exportada com sucesso!"
  - Quando: `btn_id == 'export-xlsx'` e exportação bem-sucedida
  - Tipo: `NOTIF_SUCCESS`
- ✅ **SUCCESS**: "Arquivo CSV exportado com sucesso!"
  - Quando: `btn_id == 'export-csv'` e exportação bem-sucedida
  - Tipo: `NOTIF_SUCCESS`
- ✅ **SUCCESS**: "Relatório PDF exportado com sucesso!"
  - Quando: `btn_id == 'export-pdf'` e exportação bem-sucedida
  - Tipo: `NOTIF_SUCCESS`
- ✅ **SUCCESS**: "Arquivo HTML exportado com sucesso!"
  - Quando: `btn_id == 'export-html'` e exportação bem-sucedida
  - Tipo: `NOTIF_SUCCESS`
- ❌ **ERROR**: "Erro ao exportar arquivo. Verifique os dados."
  - Quando: Exception no bloco try/except
  - Tipo: `NOTIF_ERROR`

---

### 🟡 PRIORIDADE MÉDIA (Implementação na Sequência)

#### 5. **BOLETINS - SALVAR** (Callback: `save_boletim`, linha ~1648)
- ✅ **SUCCESS**: "Boletim criado com sucesso!"
  - Quando: `boletim_id` retornado e `boletim_id is not None`
  - Tipo: `NOTIF_SUCCESS`
- ⚠️ **WARNING**: "Boletim já existe para esta consulta."
  - Quando: Query duplicada detectada no loop de verificação
  - Tipo: `NOTIF_WARNING`
- ❌ **ERROR**: "Erro ao salvar boletim. Tente novamente."
  - Quando: `not boletim_id` (id vazio após create_user_boletim)
  - Tipo: `NOTIF_ERROR`

#### 6. **BOLETINS - DELETAR** (Callback: `delete_boletim`, linha ~1769)
- ℹ️ **INFO**: "Boletim removido com sucesso."
  - Quando: `deactivate_user_boletim(bid)` bem-sucedido
  - Tipo: `NOTIF_INFO`
- ❌ **ERROR**: "Erro ao remover boletim. Tente novamente."
  - Quando: Exception durante deactivate_user_boletim
  - Tipo: `NOTIF_ERROR`

#### 7. **AUTENTICAÇÃO - LOGIN** (Callback: `do_login`, linha ~2224)
- ✅ **SUCCESS**: "Login realizado com sucesso!"
  - Quando: `ok == True` e sessão criada
  - Tipo: `NOTIF_SUCCESS`
- ⚠️ **WARNING**: "E-mail não confirmado. Verifique o código enviado."
  - Quando: `'Email not confirmed' in err`
  - Tipo: `NOTIF_WARNING`
- ❌ **ERROR**: "Falha no login. Verifique suas credenciais."
  - Quando: `not ok or not session`
  - Tipo: `NOTIF_ERROR`

#### 8. **AUTENTICAÇÃO - CADASTRO** (Callback: `do_signup`, linha ~2278)
- ✅ **SUCCESS**: "Cadastro realizado! Verifique seu e-mail."
  - Quando: `ok == True` após sign_up_with_metadata
  - Tipo: `NOTIF_SUCCESS`
- ❌ **ERROR**: "Erro ao cadastrar. Verifique os dados."
  - Quando: `not ok`
  - Tipo: `NOTIF_ERROR`
- ⚠️ **WARNING**: "Aceite os Termos de Contratação para continuar."
  - Quando: `'ok' not in terms`
  - Tipo: `NOTIF_WARNING`

#### 9. **AUTENTICAÇÃO - CONFIRMAÇÃO OTP** (Callback: `do_confirm`, linha ~2326)
- ✅ **SUCCESS**: "E-mail confirmado com sucesso!"
  - Quando: `ok == True` e sessão criada
  - Tipo: `NOTIF_SUCCESS`
- ❌ **ERROR**: "Código inválido ou expirado."
  - Quando: `not ok or not session`
  - Tipo: `NOTIF_ERROR`

#### 10. **AUTENTICAÇÃO - RECUPERAÇÃO DE SENHA** (Callback: `do_forgot`, linha ~2372)
- ℹ️ **INFO**: "E-mail de recuperação enviado!"
  - Quando: `ok == True` após reset_password
  - Tipo: `NOTIF_INFO`
- ❌ **ERROR**: "Erro ao enviar e-mail de recuperação."
  - Quando: `not ok`
  - Tipo: `NOTIF_ERROR`

#### 11. **AUTENTICAÇÃO - REENVIO OTP** (Callback: `do_resend_otp`, linha ~2393)
- ℹ️ **INFO**: "Novo código enviado para seu e-mail!"
  - Quando: `ok == True` após resend_otp
  - Tipo: `NOTIF_INFO`
- ❌ **ERROR**: "Erro ao reenviar código. Tente novamente."
  - Quando: `not ok`
  - Tipo: `NOTIF_ERROR`

#### 12. **LOGOUT** (Callback: `do_logout`, linha ~2550)
- ℹ️ **INFO**: "Você saiu da sua conta."
  - Quando: Logout bem-sucedido
  - Tipo: `NOTIF_INFO`

---

### 🟢 PRIORIDADE BAIXA (Melhorias de UX)

#### 13. **CARREGAMENTO DE ITENS** (Callback: `load_itens_for_cards`, linha ~5027)
- ✅ **SUCCESS**: "Itens carregados com sucesso!"
  - Quando: Itens carregados e processados
  - Tipo: `NOTIF_SUCCESS`
- ❌ **ERROR**: "Erro ao carregar itens do processo."
  - Quando: Exception durante fetch
  - Tipo: `NOTIF_ERROR`

#### 14. **CARREGAMENTO DE DOCUMENTOS** (Callback: `load_docs_for_cards`, linha ~5136)
- ✅ **SUCCESS**: "Documentos carregados com sucesso!"
  - Quando: Documentos carregados e processados
  - Tipo: `NOTIF_SUCCESS`
- ❌ **ERROR**: "Erro ao carregar documentos do processo."
  - Quando: Exception durante fetch
  - Tipo: `NOTIF_ERROR`

#### 15. **ABERTURA DE ABA FAVORITA** (Callback: `open_pncp_tab_from_favorite`, linha ~3830)
- ℹ️ **INFO**: "Abrindo processo: [PNCP_ID]"
  - Quando: Nova aba criada a partir de favorito
  - Tipo: `NOTIF_INFO`

#### 16. **HISTÓRICO DE BUSCAS**
- ℹ️ **INFO**: "Busca adicionada ao histórico."
  - Quando: Busca salva no histórico com sucesso
  - Tipo: `NOTIF_INFO`

#### 17. **RESET DE SENHA - CONFIRMAÇÃO** (Callback: `confirm_password_reset`, linha ~2495)
- ✅ **SUCCESS**: "Senha alterada com sucesso!"
  - Quando: Senha atualizada com sucesso
  - Tipo: `NOTIF_SUCCESS`
- ❌ **ERROR**: "Erro ao alterar senha. Tente novamente."
  - Quando: Falha na atualização
  - Tipo: `NOTIF_ERROR`
- ⚠️ **WARNING**: "As senhas não coincidem."
  - Quando: Validação de senhas falha
  - Tipo: `NOTIF_WARNING`

---

## 📊 Estatísticas

| Categoria | Quantidade | Prioridade |
|-----------|-----------|-----------|
| **Busca e Pesquisa** | 4 | 🔴 Alta |
| **Limites de Uso** | 2 | 🔴 Alta |
| **Resumos** | 3 | 🔴 Alta |
| **Exportações** | 6 | 🔴 Alta |
| **Boletins** | 4 | 🟡 Média |
| **Autenticação** | 10 | 🟡 Média |
| **Carregamentos** | 2 | 🟢 Baixa |
| **Outras UX** | 1 | 🟢 Baixa |
| **TOTAL** | **32** | - |

---

## 🎨 Padrão de Implementação

### Template Base para Cada Callback

```python
# 1. Adicionar ao callback signature:
Output('store-notifications', 'data', allow_duplicate=True),
State('store-notifications', 'data'),

# 2. Adicionar parâmetro:
def callback_name(..., notifications):

# 3. Inicializar lista:
updated_notifs = list(notifications or [])

# 4. Criar notificação:
notif = add_note(NOTIF_SUCCESS, "Mensagem de sucesso")
updated_notifs.append(notif)

# 5. Retornar:
return ..., updated_notifs
```

### Tipos de Notificação e Cores

| Tipo | Constante | Cor | Ícone | Uso |
|------|-----------|-----|-------|-----|
| ✅ Sucesso | `NOTIF_SUCCESS` | Verde #28a745 | `fa-check-circle` | Operações concluídas |
| ❌ Erro | `NOTIF_ERROR` | Vermelho #dc3545 | `fa-exclamation-circle` | Falhas e erros |
| ⚠️ Aviso | `NOTIF_WARNING` | Amarelo #ffc107 | `fa-exclamation-triangle` | Alertas e limitações |
| ℹ️ Info | `NOTIF_INFO` | Azul #17a2b8 | `fa-info-circle` | Informações gerais |

---

## 🚀 Próximos Passos

### Fase 1: Alta Prioridade (15 notificações)
1. 🔄 Favoritos (checar botão 'excluir')
2. 🔄 Busca e Pesquisa (4 notificações)
3. 🔄 Limites de Uso (2 notificações)
4. 🔄 Resumos (3 notificações)
5. 🔄 Exportações (6 notificações)

### Fase 2: Média Prioridade (14 notificações)
6. 🔄 Boletins (4 notificações)
7. 🔄 Autenticação (10 notificações)

### Fase 3: Baixa Prioridade (3 notificações)
8. 🔄 Carregamentos e outras UX (3 notificações)

---

## 📝 Observações Importantes

1. **Callbacks Críticos**: Busca, Limites e Exportações afetam diretamente a experiência principal do usuário
2. **Feedback de Bloqueio**: Notificações de limite são CRÍTICAS pois usuário está impedido de usar funcionalidade
3. **Confirmação de Ações**: Todas as operações de escrita (criar/deletar boletins, login/cadastro) devem ter feedback
4. **Erros Silenciosos**: Muitos try/except atualmente silenciam erros - notificações vão expor isso ao usuário
5. **Auto-dismiss**: Mantém 3 segundos para todas as notificações (já configurado no sistema)

---

## 🔧 Modificações Necessárias por Arquivo

### `GvG_Search_Browser.py`
- **~10 callbacks** precisam adicionar Output/State de notificações
- **~32 pontos** de inserção de `add_note()`
- Todos os callbacks de exportação, busca, autenticação, boletins

### Sem alterações necessárias:
- `gvg_notifications.py` (já completo)
- `gvg_styles.py` (já completo)
- `docs/README.md` (já documentado)

---

## ✅ Checklist de Implementação

Para cada notificação:
- [ ] Identificar linha exata no código
- [ ] Adicionar Output/State no @app.callback
- [ ] Adicionar parâmetro `notifications` na função
- [ ] Inicializar `updated_notifs = list(notifications or [])`
- [ ] Criar notificação com `add_note(tipo, texto)`
- [ ] Adicionar ao array: `updated_notifs.append(notif)`
- [ ] Retornar `updated_notifs` no return
- [ ] Testar funcionamento em desenvolvimento
- [ ] Validar auto-dismiss de 3 segundos
- [ ] Verificar responsividade (desktop/mobile)

---

**Documento criado em:** 2025-10-09  
**Versão:** 1.0  
**Sistema:** GovGo Search Browser (GSB) v1  
**Módulo:** Sistema de Notificações Toast
