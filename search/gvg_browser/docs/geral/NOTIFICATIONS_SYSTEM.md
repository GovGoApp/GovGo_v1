# Sistema de Notificações Toast - GSB

## Visão Geral

Sistema de notificações temporárias (Toast) para feedback visual ao usuário no GovGo Search Browser.

## Características

- **Duração**: Auto-dismiss em 3 segundos
- **Tipos**: 4 tipos com cores e ícones distintos
  - `success` (verde #28a745) - Operação bem-sucedida
  - `error` (vermelho #dc3545) - Erro ou falha
  - `warning` (amarelo #ffc107) - Aviso ou alerta
  - `info` (azul #17a2b8) - Informação geral

## Posicionamento

- **Desktop/Notebook**: Canto inferior direito da tela
- **Mobile (≤992px)**: Centro inferior da tela

## Arquitetura

### Módulo Principal: `gvg_notifications.py`

```python
from gvg_notifications import add_note, NOTIF_SUCCESS, NOTIF_ERROR, NOTIF_WARNING, NOTIF_INFO

# Adicionar notificação de sucesso
notif = add_note(NOTIF_SUCCESS, "Operação concluída com sucesso!")

# Adicionar notificação de erro
notif = add_note(NOTIF_ERROR, "Erro ao processar a solicitação")
```

### Estrutura de Notificação

```python
{
    'id': 'uuid-único',
    'tipo': 'success',  # success, error, warning, info
    'texto': 'Mensagem da notificação',
    'icon': 'fas fa-check-circle',  # ícone FontAwesome
    'color': '#28a745',  # cor da borda/ícone
    'timestamp': 1234567890.123,  # tempo de criação
}
```

### Store e Callbacks

**Store**: `store-notifications` (lista de notificações ativas)

**Callbacks**:
1. `render_notifications`: Renderiza notificações na UI
2. `auto_remove_notifications`: Remove notificações após 3s (triggered por `notifications-interval` a cada 500ms)

### Estilos (`gvg_styles.py`)

```python
# Container fixo
styles['toast_container'] = {
    'position': 'fixed',
    'bottom': '20px',
    'right': '20px',  # desktop
    'zIndex': 9999,
    ...
}

# Toast individual
styles['toast_item'] = {
    'backgroundColor': '#f8f9fa',  # cinza claro
    'border': '3px solid',  # cor dinâmica por tipo
    'borderRadius': '12px',
    'padding': '12px 16px',
    ...
}
```

### CSS de Animação

```css
/* Entrada (desliza da direita) */
@keyframes slideInRight {
    from { opacity: 0; transform: translateX(100%); }
    to { opacity: 1; transform: translateX(0); }
}

/* Saída (desvanece) */
@keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
}
```

## Uso nos Callbacks

### Exemplo: Toggle de Favoritos

```python
@app.callback(
    Output('store-favorites', 'data'),
    Output('store-notifications', 'data'),  # Adicionar output
    Input('bookmark-btn', 'n_clicks'),
    State('store-favorites', 'data'),
    State('store-notifications', 'data'),  # Adicionar state
)
def toggle_bookmark(n_clicks, favs, notifications):
    updated_favs = list(favs or [])
    updated_notifs = list(notifications or [])
    
    # Lógica de add/remove favorito
    if adicionar:
        # ... código de adição ...
        notif = add_note(NOTIF_SUCCESS, f"Favorito adicionado: {rotulo}")
        updated_notifs.append(notif)
    else:
        # ... código de remoção ...
        notif = add_note(NOTIF_INFO, f"Favorito removido: {pncp}")
        updated_notifs.append(notif)
    
    return updated_favs, updated_notifs
```

## Integração Atual

✅ **Favoritos** (add/remove) - Implementado como teste inicial

### Próximas Integrações (Sugeridas)

- Busca concluída (sucesso/erro)
- Resumo gerado (sucesso/erro)
- Boletim salvo/removido
- Limites atingidos (warning)
- Exportação concluída
- E-mail enviado
- Erros de autenticação

## Layout no App Principal

```python
# Em GvG_Search_Browser.py (layout)

# Store
dcc.Store(id='store-notifications', data=[]),

# Interval para auto-remoção
dcc.Interval(id='notifications-interval', interval=500, n_intervals=0, disabled=False),

# Container de notificações
html.Div(id='toast-container', style=styles['toast_container']),
```

## Boas Práticas

1. **Mensagens curtas**: Máximo 80-100 caracteres
2. **Tipo apropriado**: Usar o tipo correto conforme contexto
3. **Evitar spam**: Não adicionar múltiplas notificações idênticas em sequência
4. **Feedback imediato**: Adicionar notificação logo após a ação do usuário

## Testes

Para testar o sistema:
1. Adicionar um favorito → Notificação verde "Favorito adicionado"
2. Remover um favorito → Notificação azul "Favorito removido"
3. Aguardar 3 segundos → Notificação desaparece automaticamente

---

**Última atualização**: 2025-10-09
**Autor**: Sistema GSB
**Status**: ✅ Implementado e testado
