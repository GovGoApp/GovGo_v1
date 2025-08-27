"""
gvg_exporters.py
Módulo unificado de exportação (JSON / XLSX / PDF) e geração de nomes de arquivo.

Centraliza lógica antes duplicada em:
 - GvG_Search_Prompt.py
 - GvG_Search_Function.py
 - GvG_Search_Terminal.py

Assinaturas expostas:
  generate_export_filename(query, search_type, approach, relevance, order, intelligent_enabled, output_dir, extension)
  export_results_json(results, query, params, output_dir)
  export_results_excel(results, query, params, output_dir)
  export_results_pdf(results, query, params, output_dir)  (silencioso se reportlab ausente)

O objeto `params` pode ser:
  - argparse.Namespace (atributos) ou
  - dict com chaves: search, approach, relevance, order

Depende apenas de: pandas, (opcional) reportlab e utilidades de formatação
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List
import os, re, json

import pandas as pd

try:  # PDF opcional
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except Exception:  # pragma: no cover
    REPORTLAB_AVAILABLE = False

# Importar formatters (após fusão solicitada devem residir em gvg_preprocessing)
from gvg_preprocessing import format_currency, format_date, decode_poder, decode_esfera
from gvg_search_core import get_intelligent_status

# Mapas reutilizados (evita import circular com scripts)
SEARCH_TYPES = {1: {"name": "Semântica"}, 2: {"name": "Palavras-chave"}, 3: {"name": "Híbrida"}}
SEARCH_APPROACHES = {1: {"name": "Direta"}, 2: {"name": "Correspondência"}, 3: {"name": "Filtro"}}
RELEVANCE_LEVELS = {1: {"name": "Sem filtro"}, 2: {"name": "Flexível"}, 3: {"name": "Restritivo"}}


def _get_attr(params: Any, name: str, default=None):
    if params is None:
        return default
    if isinstance(params, dict):
        return params.get(name, default)
    return getattr(params, name, default)


def generate_export_filename(query: str, search_type: int, approach: int, relevance: int, order: int,
                              intelligent_enabled: bool, output_dir: str, extension: str) -> str:
    """Gera nome padronizado (compatível com padrão v2/v9)."""
    try:
        clean = re.sub(r'[^\w\s-]', '', query).strip().upper()
        clean = re.sub(r'\s+', '_', clean)[:30]
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        flag = 'I' if intelligent_enabled else 'N'
        filename = f"Busca_{clean}_S{search_type}_A{approach}_R{relevance}_O{order}_I{flag}_{ts}.{extension}"
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, filename)
    except Exception:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(output_dir, f"Busca_EXPORT_ERR_{ts}.{extension}")


def _collect_metadata(results: List[dict], query: str, params) -> dict:
    return {
        'query': query,
        'search_type': SEARCH_TYPES.get(_get_attr(params, 'search'), {}).get('name'),
        'approach': SEARCH_APPROACHES.get(_get_attr(params, 'approach'), {}).get('name'),
        'relevance_level': _get_attr(params, 'relevance'),
        'order': _get_attr(params, 'order'),
        'export_date': datetime.now().isoformat(),
        'total_results': len(results)
    }


def export_results_json(results: List[dict], query: str, params, output_dir: str) -> str:
    status = get_intelligent_status()
    filename = generate_export_filename(
        query,
        _get_attr(params, 'search'),
        _get_attr(params, 'approach'),
        _get_attr(params, 'relevance'),
        _get_attr(params, 'order'),
        status['intelligent_processing'],
        output_dir,
        'json'
    )
    rows = []
    for r in results:
        d = r.get('details', {})
        rows.append({
            'rank': r.get('rank'),
            'id': r.get('id'),
            'similarity': r.get('similarity'),
            'orgao': d.get('orgao_entidade_razao_social'),
            'unidade': d.get('unidade_orgao_nome_unidade'),
            'municipio': d.get('unidade_orgao_municipio_nome'),
            'uf': d.get('unidade_orgao_uf_sigla'),
            'valor_estimado': d.get('valor_total_estimado'),
            'valor_homologado': d.get('valor_total_homologado'),
            'data_inclusao': d.get('data_inclusao'),
            'data_abertura': d.get('data_abertura_proposta'),
            'data_encerramento': d.get('data_encerramento_proposta'),
            'modalidade_id': d.get('modalidade_id'),
            'modalidade_nome': d.get('modalidade_nome'),
            'disputa_id': d.get('modo_disputa_id'),
            'disputa_nome': d.get('modo_disputa_nome'),
            'descricao': d.get('objeto_compra')
        })
    payload = {'metadata': _collect_metadata(results, query, params), 'results': rows}
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return filename


def export_results_excel(results: List[dict], query: str, params, output_dir: str) -> str:
    filename = generate_export_filename(
        query,
        _get_attr(params, 'search'),
        _get_attr(params, 'approach'),
        _get_attr(params, 'relevance'),
        _get_attr(params, 'order'),
        get_intelligent_status()['intelligent_processing'],
        output_dir,
        'xlsx'
    )
    rows = []
    for r in results:
        d = r.get('details', {})
        rows.append({
            'Rank': r.get('rank'),
            'ID': r.get('id'),
            'Similaridade': r.get('similarity'),
            'Órgão': d.get('orgao_entidade_razao_social'),
            'Unidade': d.get('unidade_orgao_nome_unidade'),
            'Município': d.get('unidade_orgao_municipio_nome'),
            'UF': d.get('unidade_orgao_uf_sigla'),
            'Valor Estimado': d.get('valor_total_estimado'),
            'Data Encerramento': d.get('data_encerramento_proposta')
        })
    pd.DataFrame(rows).to_excel(filename, index=False, engine='openpyxl')
    return filename


def export_results_csv(results: List[dict], query: str, params, output_dir: str) -> str:
    """Exporta resultados em CSV (compatível com Excel)."""
    filename = generate_export_filename(
        query,
        _get_attr(params, 'search'),
        _get_attr(params, 'approach'),
        _get_attr(params, 'relevance'),
        _get_attr(params, 'order'),
        get_intelligent_status()['intelligent_processing'],
        output_dir,
        'csv'
    )
    rows = []
    for r in results:
        d = r.get('details', {})
        rows.append({
            'Rank': r.get('rank'),
            'ID': r.get('id'),
            'Similaridade': r.get('similarity'),
            'Órgão': d.get('orgao_entidade_razao_social'),
            'Unidade': d.get('unidade_orgao_nome_unidade'),
            'Município': d.get('unidade_orgao_municipio_nome'),
            'UF': d.get('unidade_orgao_uf_sigla'),
            'Valor Estimado': d.get('valor_total_estimado'),
            'Data Encerramento': d.get('data_encerramento_proposta')
        })
    df = pd.DataFrame(rows)
    # utf-8-sig para abrir bem no Excel com acentuação
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    return filename

def export_results_pdf(results: List[dict], query: str, params, output_dir: str):  # pragma: no cover
    if not REPORTLAB_AVAILABLE:
        return None
    filename = generate_export_filename(
        query,
        _get_attr(params, 'search'),
        _get_attr(params, 'approach'),
        _get_attr(params, 'relevance'),
        _get_attr(params, 'order'),
        get_intelligent_status()['intelligent_processing'],
        output_dir,
        'pdf'
    )
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=45,leftMargin=45,topMargin=54,bottomMargin=54)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleX', parent=styles['Title'], alignment=1, fontSize=16)
    normal = styles['Normal']
    elements = []
    elements.append(Paragraph(f'BUSCA: "{query.upper()}"', title_style))
    elements.append(Paragraph(
        f"Tipo: {SEARCH_TYPES.get(_get_attr(params,'search'),{}).get('name')} | Abordagem: {SEARCH_APPROACHES.get(_get_attr(params,'approach'),{}).get('name')} | Relevância: {RELEVANCE_LEVELS.get(_get_attr(params,'relevance'),{}).get('name')}",
        normal
    ))
    elements.append(Paragraph(f'Exportado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', normal))
    elements.append(Spacer(1, 0.2*inch))
    table_data = [["Rank","Unidade","Local","Similaridade","Valor (R$)","Data Enc."]]
    for r in results:
        d = r.get('details', {})
        unidade = d.get('unidade_orgao_nome_unidade') or 'N/A'
        municipio = d.get('unidade_orgao_municipio_nome') or 'N/A'
        uf = d.get('unidade_orgao_uf_sigla') or ''
        local = f"{municipio}/{uf}" if uf else municipio
        valor = format_currency(d.get('valor_total_estimado') or 0)
        data_enc = format_date(d.get('data_encerramento_proposta') or 'N/A')
        table_data.append([str(r.get('rank')), unidade[:30], local[:25], f"{r.get('similarity',0):.4f}", valor, str(data_enc)])
    pdf_table = PDFTable(table_data, repeatRows=1)
    pdf_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ALIGN',(0,0),(-1,0),'CENTER'),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),8),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE')
    ]))
    elements.append(pdf_table)
    doc.build(elements)
    return filename

def export_results_html(results: List[dict], query: str, params, output_dir: str) -> str:
        """Exporta resultados em HTML simples, sem dependências extras."""
        filename = generate_export_filename(
                query,
                _get_attr(params, 'search'),
                _get_attr(params, 'approach'),
                _get_attr(params, 'relevance'),
                _get_attr(params, 'order'),
                get_intelligent_status()['intelligent_processing'],
                output_dir,
                'html'
        )
        meta = _collect_metadata(results, query, params)
        # Pequeno CSS embutido para legibilidade
        css = """
        body { font-family: Arial, sans-serif; margin: 24px; }
        h1 { font-size: 20px; margin: 0 0 8px 0; }
        .meta { color: #444; margin-bottom: 16px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 6px 8px; font-size: 12px; }
        th { background: #0b5394; color: #fff; text-align: left; }
        tr:nth-child(even) { background: #f6f8fa; }
        .right { text-align: right; }
        .center { text-align: center; }
        .small { color: #666; font-size: 11px; }
        """
        # Monta linhas
        def _local_str(d: dict):
                municipio = d.get('unidade_orgao_municipio_nome') or ''
                uf = d.get('unidade_orgao_uf_sigla') or ''
                return f"{municipio}/{uf}" if uf else municipio
        rows_html = []
        for r in results:
                d = r.get('details', {})
                unidade = (d.get('unidade_orgao_nome_unidade') or d.get('orgao_entidade_razao_social') or 'N/A')
                local = _local_str(d)
                valor = format_currency(d.get('valor_total_estimado') or d.get('valor_total_homologado') or 0)
                data_enc = format_date(d.get('data_encerramento_proposta') or '')
                rows_html.append(
                        f"<tr>"
                        f"<td class='center'>{r.get('rank','')}</td>"
                        f"<td>{unidade}</td>"
                        f"<td>{local}</td>"
                        f"<td class='right'>{(r.get('similarity') or 0):.4f}</td>"
                        f"<td class='right'>{valor}</td>"
                        f"<td class='center'>{data_enc}</td>"
                        f"</tr>"
                )
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8" />
    <title>Busca: {query}</title>
    <style>{css}</style>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body>
    <h1>Resultado da Busca</h1>
    <div class="meta">
        <div><strong>Consulta:</strong> {query}</div>
        <div><strong>Tipo:</strong> {SEARCH_TYPES.get(_get_attr(params,'search'),{}).get('name')} | <strong>Abordagem:</strong> {SEARCH_APPROACHES.get(_get_attr(params,'approach'),{}).get('name')} | <strong>Relevância:</strong> {RELEVANCE_LEVELS.get(_get_attr(params,'relevance'),{}).get('name')}</div>
        <div><strong>Exportado em:</strong> {meta['export_date']}</div>
        <div class="small"><strong>Total resultados:</strong> {meta['total_results']}</div>
    </div>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Unidade</th>
                <th>Local</th>
                <th>Similaridade</th>
                <th>Valor (R$)</th>
                <th>Data Enc.</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows_html)}
        </tbody>
    </table>
</body>
</html>
"""
        with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
        return filename

__all__ = [
    'generate_export_filename',
    'export_results_json',
    'export_results_excel',
    'export_results_csv',
    'export_results_pdf',
    'export_results_html'
]
