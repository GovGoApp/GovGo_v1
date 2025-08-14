"""
PG_V2.py - Avaliação de Modelos de Classificação com Comparação em Nível 2
---------------------------------------------------------------------------
Esta versão implementa uma avaliação modificada que:
1. Compara apenas os códigos até o nível NV2 (ignorando CODNV3)
2. Usa um sistema binário de 3 bits (máximo 7) para pontuação
3. Implementa o conceito de CODCAT2 = concatenação de CODNV0 + CODNV1 + CODNV2

As métricas foram recalibradas para este novo modelo de comparação reduzida.
"""

import os
import pandas as pd
import numpy as np
import glob
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import re

# Inicializar console para output formatado
console = Console()

# Constantes de caminho
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CLASSY\\CLASSY_ITENS\\OUTPUT_ITENS\\"
SAMPLES_FILE = BASE_PATH + "SAMPLES\\SAMPLES_P176.xlsx"
OUTPUTS_DIR = BASE_PATH + "ESTUDOS\\P176\\"
RESULTADOS_DIR = BASE_PATH + "ESTUDOS\\P176\\RESULTADOS_NV2\\"  # Novo diretório para resultados NV2

# Constantes de pesos
WS = 0.5  # Peso para pontuação de semelhança
WP = 0.5  # Peso para pontuação de posição

# Pesos por posição de score
WSS = [10, 5, 3, 2, 1]  # Pesos para SCORE_1, SCORE_2, ..., SCORE_5

# MODIFICAÇÃO: Pontuação máxima de semelhança para normalização
# Agora usa 7 (máximo binário 111 = decimal 7) em vez de 15
PSM = 7 * sum(WSS)  # 7 (match perfeito NV2) * soma dos pesos = 7 * 21 = 147

# Pesos por posição (para PP)
PESOS_POSICAO = [1.0, 0.75, 0.5, 0.4, 0.3]  # Para posições 1, 2, 3, 4 e 5

def extrair_codigos(codigo_completo):
    """
    Extrai os códigos dos níveis de um código completo.
    Formato: {M/S}{0000}{00000}{00000}
    MODIFICAÇÃO: Retorna apenas os primeiros 3 níveis (ignorando CODNV3)
    
    Args:
        codigo_completo: Código completo no formato especificado
        
    Returns:
        Lista com os códigos dos níveis extraídos [CODNV0, CODNV1, CODNV2]
    """
    if not isinstance(codigo_completo, str) or len(codigo_completo) < 10:
        return None
    
    try:
        codnv0 = codigo_completo[0]  # M ou S
        codnv1 = codigo_completo[1:5]  # 4 dígitos
        codnv2 = codigo_completo[5:10]  # 5 dígitos
        
        return [codnv0, codnv1, codnv2]
    except:
        return None

def extrair_codigo_de_top(top_value):
    """
    Extrai o código do valor do campo TOP_N.
    MODIFICAÇÃO: Agora suporta diferentes formatos de código (NV1, NV2, NV3)
    Formatos típicos: 
    - "M00700704000227 - Nome da categoria" (15 caracteres, NV3)
    - "M0070070400 - Nome da categoria" (10 caracteres, NV2)
    - "M0070 - Nome da categoria" (5 caracteres, NV1)
    
    Args:
        top_value: Valor do campo TOP_N
        
    Returns:
        Código extraído ou None se não for possível extrair
    """
    if not isinstance(top_value, str):
        return None
    
    # Primeiro tentar padrão mais comum: letra seguida de 14 dígitos no início (NV3)
    match = re.match(r'^([MS]\d{14})\s*-', top_value)
    if match:
        return match.group(1)
    
    # Tentar padrão NV2: letra seguida de 9 dígitos
    match = re.match(r'^([MS]\d{9})\s*-', top_value)
    if match:
        return match.group(1)
        
    # Tentar padrão NV1: letra seguida de 4 dígitos
    match = re.match(r'^([MS]\d{4})\s*-', top_value)
    if match:
        return match.group(1)
    
    # Padrão genérico: qualquer código alfanumérico seguido de hífen
    match = re.match(r'^([MS][0-9A-Z]+)\s*-', top_value)
    if match:
        return match.group(1)
        
    console.print(f"[yellow]Aviso: Formato de código não reconhecido: '{top_value}'[/yellow]")
    return None

def extrair_codcat2(codigo_completo):
    """
    Extrai o CODCAT2 que é a concatenação de CODNV0+CODNV1+CODNV2 
    (primeiros 10 caracteres)
    MODIFICAÇÃO: Agora lida com códigos de diferentes tamanhos
    
    Args:
        codigo_completo: Código completo 
        
    Returns:
        CODCAT2: Primeiros 10 caracteres do código ou código parcial se menor
    """
    if not isinstance(codigo_completo, str):
        return None
    
    # Código já é NV2 ou menor (até 10 caracteres)
    if len(codigo_completo) <= 10:
        return codigo_completo
        
    # Código é maior que NV2, truncar para 10 caracteres
    return codigo_completo[:10]  # Primeiros 10 caracteres

def calcular_pss(codigo_correto, codigo_score):
    """
    Calcula a pontuação por semelhança por score (pss).
    MODIFICAÇÃO: Agora usa apenas 3 níveis e suporta códigos de diferentes tamanhos
    
    Args:
        codigo_correto: Código da resposta correta
        codigo_score: Código da previsão
        
    Returns:
        Pontuação binária por nível e valor decimal (máximo 7)
    """
    # Extrair apenas os 10 primeiros caracteres (CODCAT2) para ambos códigos
    codigo_correto_nv2 = extrair_codcat2(codigo_correto)
    codigo_score_nv2 = extrair_codcat2(codigo_score)
    
    if codigo_correto_nv2 is None or codigo_score_nv2 is None:
        return [0, 0, 0], 0
    
    # Verificar se conseguimos extrair os códigos individuais
    niveis_correto = extrair_codigos(codigo_correto_nv2)
    niveis_score = extrair_codigos(codigo_score_nv2)
    
    if niveis_correto is None or niveis_score is None:
        # Se não conseguimos extrair os códigos completos, podemos tentar comparação parcial
        binario = [0, 0, 0]  # Começa com zeros
        
        # Se o código score começa com o mesmo caractere (CODNV0), marca o primeiro bit
        if len(codigo_correto_nv2) > 0 and len(codigo_score_nv2) > 0:
            if codigo_correto_nv2[0] == codigo_score_nv2[0]:
                binario[0] = 1
                
                # Se temos pelo menos 5 caracteres (NV1 completo) e eles são iguais
                if len(codigo_correto_nv2) >= 5 and len(codigo_score_nv2) >= 5:
                    if codigo_correto_nv2[:5] == codigo_score_nv2[:5]:
                        binario[1] = 1
                        
                        # Se temos 10 caracteres (NV2 completo) e eles são iguais
                        if len(codigo_correto_nv2) >= 10 and len(codigo_score_nv2) >= 10:
                            if codigo_correto_nv2[:10] == codigo_score_nv2[:10]:
                                binario[2] = 1
                                
        # Converter binário para decimal (base 2)
        decimal = int(''.join(map(str, binario)), 2)
        return binario, decimal
    
    # Se temos códigos completos, usamos a lógica original
    binario = []
    for i in range(3):  # Apenas 3 níveis para NV2
        if i < len(niveis_correto) and i < len(niveis_score):
            binario.append(1 if niveis_correto[i] == niveis_score[i] else 0)
        else:
            binario.append(0)
    
    # Converter binário para decimal (base 2)
    decimal = int(''.join(map(str, binario)), 2)
    
    return binario, decimal

def calcular_ps(codigo_correto, codigo_scores):
    """
    Calcula a pontuação de semelhança (PS) normalizada.
    MODIFICAÇÃO: Usa nova escala baseada em 3 níveis (máximo 7)
    
    Args:
        codigo_correto: Código da resposta correta
        codigo_scores: Lista de códigos dos scores [CS1, CS2, ..., CS5]
        
    Returns:
        PS normalizado (0 a 1) e detalhes do cálculo
    """
    pss_resultados = []
    ps_soma = 0
    
    for i, cs in enumerate(codigo_scores):
        if cs:
            binario, decimal = calcular_pss(codigo_correto, cs)
            pss_valor = decimal
            ps_contrib = WSS[i] * pss_valor
            ps_soma += ps_contrib
            
            pss_resultados.append({
                'posicao': i+1,
                'codigo': cs,
                'binario': binario,
                'decimal': decimal,
                'peso': WSS[i],
                'contribuicao': ps_contrib
            })
        else:
            pss_resultados.append({
                'posicao': i+1,
                'codigo': None,
                'binario': [0, 0, 0],  # Agora apenas 3 bits
                'decimal': 0,
                'peso': WSS[i],
                'contribuicao': 0
            })
    
    # Normalizar PS (dividir pela pontuação máxima possível)
    ps_normalizado = ps_soma / PSM
    
    return ps_normalizado, pss_resultados, ps_soma

def calcular_pp(codigo_correto, codigo_scores):
    """
    Calcula a pontuação de posição (PP).
    MODIFICAÇÃO: Compara CODCAT2 com melhor robustez para diferentes formatos
    
    Args:
        codigo_correto: Código da resposta correta
        codigo_scores: Lista de códigos dos scores [CS1, CS2, ..., CS5]
        
    Returns:
        PP (0 a 1) e posição encontrada
    """
    codigo_correto_nv2 = extrair_codcat2(codigo_correto)
    
    if codigo_correto_nv2 is None:
        return 0, 0
        
    for i, cs in enumerate(codigo_scores):
        if cs is None:
            continue
            
        codigo_score_nv2 = extrair_codcat2(cs)
        
        if codigo_score_nv2 is None:
            continue
        
        # Comparar na maior profundidade disponível entre os dois códigos
        min_len = min(len(codigo_correto_nv2), len(codigo_score_nv2))
        
        # Para NV2 consideramos correto se os primeiros 10 caracteres são iguais (ou todos se menor)
        if min_len >= 10:  # Ambos têm pelo menos tamanho NV2 completo
            if codigo_correto_nv2[:10] == codigo_score_nv2[:10]:
                return PESOS_POSICAO[i], i+1
        elif min_len > 0:  # Comparação parcial
            if codigo_correto_nv2[:min_len] == codigo_score_nv2[:min_len]:
                return PESOS_POSICAO[i], i+1
    
    return 0, 0  # Não encontrado

def calcular_pg(ps, pp):
    """
    Calcula a pontuação geral (PG).
    
    Args:
        ps: Pontuação de semelhança normalizada
        pp: Pontuação de posição
        
    Returns:
        PG (0 a 1)
    """
    return WS * ps + WP * pp

def extrair_codigos_de_output(row):
    """
    Extrai os códigos dos campos TOP_N de uma linha do DataFrame de output.
    
    Args:
        row: Linha do DataFrame
        
    Returns:
        Lista de códigos [CS1, CS2, ..., CS5]
    """
    codigos = []
    for i in range(1, 6):
        codigo = extrair_codigo_de_top(row.get(f'TOP_{i}'))
        codigos.append(codigo)
    
    return codigos

def extrair_parametros_do_nome(nome_arquivo):
    """
    Extrai os parâmetros de configuração do nome do arquivo.
    MODIFICAÇÃO: Suporta ambos formatos de nomenclatura
    Formatos esperados: 
    - OUTPUT_ITEM_XXX_HY_DZ_N1_N2_N3_MS_OC_IT.xlsx
    - OUTPUT_ITEM_XXX_HY_DZ_N1_N2_N3_MS_OC_IT_AAAAMMDD_HHMM_vXX.xlsx
    
    Args:
        nome_arquivo: Nome do arquivo
        
    Returns:
        Dicionário com os parâmetros extraídos
    """
    try:
        # Remover extensão e prefixo
        nome_base = os.path.splitext(nome_arquivo)[0]
        
        # Extrair parâmetros usando regex
        # Padrão mais flexível para capturar ambos formatos
        pattern = r'H(\d+)_D(\d+)_(\d+(?:_\d+)*)_(\d)_(\d)_(\d)'
        match = re.search(pattern, nome_base)
        
        if match:
            wh = int(match.group(1)) / 10  # Converter H5 para 0.5
            wd = int(match.group(2)) / 10  # Converter D5 para 0.5
            
            # Tratar a parte NNN (pode ser 5_5_5 ou 10_10_10)
            nnn_str = match.group(3)
            nnn = nnn_str.replace('_', ',')
            
            ms = match.group(4) == '1'  # Converter para boolean
            oc = match.group(5) == '1'  # Converter para boolean
            it = match.group(6) == '1'  # Converter para boolean
            
            # Criar um identificador legível para o modelo
            nnn_display = nnn
                
            modelo = f"H{int(wh*10)}_D{int(wd*10)}"
            
            # Adicionar sufixos para filtros especiais
            if not ms and oc:
                modelo += "_OC_IT"
            elif ms and not oc:
                modelo += "_MS_IT"
            elif not ms and not oc:
                modelo += "_IT"
            
            # Adicionar sufixo para NNN não padrão
            modelo += f"_{nnn_display}"
            
            # Verificar se o nome contém data/hora/versão
            date_pattern = r'(\d{8})_(\d{4})_v(\d{2})'
            date_match = re.search(date_pattern, nome_base)
            if date_match:
                data = date_match.group(1)
                hora = date_match.group(2)
                versao = date_match.group(3)
                modelo += f"_{data}_{hora}_v{versao}"
            
            return {
                'modelo': modelo,
                'wh': wh,
                'wd': wd,
                'nnn': nnn_display,
                'ms': int(ms),
                'oc': int(oc),
                'it': int(it),
                'arquivo': nome_arquivo
            }
        
        return {
            'modelo': 'DESCONHECIDO',
            'wh': None,
            'wd': None,
            'nnn': None,
            'ms': None,
            'oc': None,
            'it': None,
            'arquivo': nome_arquivo
        }
    except Exception as e:
        console.print(f"[red]Erro ao extrair parâmetros do nome {nome_arquivo}: {str(e)}[/red]")
        return {
            'modelo': 'ERRO',
            'wh': None,
            'wd': None,
            'nnn': None,
            'ms': None,
            'oc': None,
            'it': None,
            'arquivo': nome_arquivo
        }

def processar_output(output_file, samples_df):
    """
    Processa um arquivo de output para calcular métricas em relação às amostras.
    MODIFICAÇÃO: Usa o novo sistema de pontuação baseado em NV2 (3 níveis)
    """
    console.print(f"[bold cyan]Processando arquivo: {os.path.basename(output_file)}[/bold cyan]")
    
    try:
        # Extrair parâmetros do nome do arquivo
        parametros = extrair_parametros_do_nome(os.path.basename(output_file))
        
        # Carregar output
        output_df = pd.read_excel(output_file)
        
        # Criar uma lista para armazenar os resultados processados
        resultados = []
        
        # Filtrar itens que estão no sample
        for _, sample in samples_df.iterrows():
            id_item = sample['ID_ITEM_CONTRATACAO']
            
            # Encontrar o item correspondente no output
            item_match = output_df[output_df['ID_ITEM_CONTRATACAO'] == id_item]
            
            if len(item_match) == 0:
                console.print(f"[yellow]Item {id_item} não encontrado no output[/yellow]")
                continue
            
            item_row = item_match.iloc[0]
            
            # Extrair o código correto e códigos dos scores
            codigo_correto = sample['COD CORRETO']
            codigos_scores = extrair_codigos_de_output(item_row)
            
            # MODIFICAÇÃO: Extrair CODCAT2 (10 primeiros caracteres)
            codigo_correto_nv2 = extrair_codcat2(codigo_correto)
            
            # Calcular PS com o novo sistema
            ps, pss_detalhes, ps_soma = calcular_ps(codigo_correto, codigos_scores)
            
            # Calcular PP com o novo sistema
            pp, posicao_encontrada = calcular_pp(codigo_correto, codigos_scores)
            
            # Calcular PG
            pg = calcular_pg(ps, pp)
            
            # Criar dicionário para armazenar os resultados
            resultado = {
                'numeroControlePNCP': item_row.get('numeroControlePNCP'),
                'numeroItem': item_row.get('numeroItem'),
                'ID_ITEM_CONTRATACAO': id_item,
                'descrição': item_row.get('descrição'),
                'item_type': item_row.get('item_type'),
                'RESPOSTA CORRETA': sample.get('RESPOSTA CORRETA'),
                'COD CORRETO': codigo_correto,
                'CODCAT2': codigo_correto_nv2,  # Novo campo CODCAT2
                'TOP_1': item_row.get('TOP_1'),
                'TOP_2': item_row.get('TOP_2'),
                'TOP_3': item_row.get('TOP_3'),
                'TOP_4': item_row.get('TOP_4'),
                'TOP_5': item_row.get('TOP_5'),
                'SCORE_1': item_row.get('SCORE_1'),
                'SCORE_2': item_row.get('SCORE_2'),
                'SCORE_3': item_row.get('SCORE_3'),
                'SCORE_4': item_row.get('SCORE_4'),
                'SCORE_5': item_row.get('SCORE_5'),
                'CONFIDENCE': item_row.get('CONFIDENCE'),
                'PS': ps,
                'PP': pp,
                'PG': pg,
                'posicao_encontrada': posicao_encontrada
            }
            
            # Adicionar detalhes de PSS para cada score
            for i, pss in enumerate(pss_detalhes):
                resultado[f'PSS{i+1}_bin'] = ''.join(map(str, pss['binario']))
                resultado[f'PSS{i+1}_dec'] = pss['decimal']
                resultado[f'PSS{i+1}_contrib'] = pss['contribuicao']
            
            resultado['PS_soma'] = ps_soma
            
            resultados.append(resultado)
        
        # Criar DataFrame com todos os resultados
        resultados_df = pd.DataFrame(resultados)
        
        # Adicionar parâmetros às estatísticas
        stats = {
            'arquivo': os.path.basename(output_file),
            'modelo': parametros['modelo'],
            'wh': parametros['wh'],
            'wd': parametros['wd'],
            'nnn': parametros['nnn'],
            'ms': parametros['ms'],
            'oc': parametros['oc'],
            'it': parametros['it'],
            'total_itens': len(resultados_df),
            'ps_media': resultados_df['PS'].mean(),
            'pp_media': resultados_df['PP'].mean(),
            'pg_media': resultados_df['PG'].mean(),
            'A_top1': len(resultados_df[resultados_df['posicao_encontrada'] == 1]),
            'A_top5': len(resultados_df[resultados_df['posicao_encontrada'] > 0]),
            'A_top1_pct': len(resultados_df[resultados_df['posicao_encontrada'] == 1])/len(resultados_df)*100,
            'A_top5_pct': len(resultados_df[resultados_df['posicao_encontrada'] > 0])/len(resultados_df)*100,
            'C>50': len(resultados_df[resultados_df['CONFIDENCE'] > 50])/len(resultados_df)*100,
            'C<50': len(resultados_df[resultados_df['CONFIDENCE'] <= 50])/len(resultados_df)*100,
            'S>70': len(resultados_df[resultados_df['SCORE_1'] > 0.7])/len(resultados_df)*100,
            'S<70': len(resultados_df[resultados_df['SCORE_1'] <= 0.7])/len(resultados_df)*100
        }
        
        # Exibir estatísticas com informações do modelo
        console.print(f"[green]Estatísticas para {parametros['modelo']} ({os.path.basename(output_file)}):[/green]")
        console.print(f"  Configuração: WH={parametros['wh']}, WD={parametros['wd']}, NNN={parametros['nnn']}, MS={parametros['ms']}, OC={parametros['oc']}, IT={parametros['it']},")
        console.print(f"  Total de itens analisados: {stats['total_itens']}")
        console.print(f"  PS média (NV2): {stats['ps_media']:.4f}")
        console.print(f"  PP média (NV2): {stats['pp_media']:.4f}")
        console.print(f"  PG média (NV2): {stats['pg_media']:.4f}")
        console.print(f"  Acertos no TOP 1 (NV2): {stats['A_top1']} ({stats['A_top1_pct']:.2f}%)")
        console.print(f"  Acertos no TOP 5 (NV2): {stats['A_top5']} ({stats['A_top5_pct']:.2f}%)")
        console.print(f"  CONFIDENCE >50: {stats['C>50']:.2f}%")
        console.print(f"  SCORE_1 >0.7: {stats['S>70']:.2f}%")
        
        return resultados_df, stats
    
    except Exception as e:
        console.print(f"[bold red]Erro ao processar {os.path.basename(output_file)}: {str(e)}[/bold red]")
        return None, None

def main():
    """
    Função principal que coordena o processamento de todos os arquivos de output.
    MODIFICAÇÃO: Usa o novo diretório para resultados NV2 e exibe claramente que está usando o novo sistema
    """
    console.print("[bold magenta]===== INICIANDO AVALIAÇÃO DE MODELOS (VERSÃO NV2) =====[/bold magenta]")
    console.print("[bold yellow]ATENÇÃO: Esta versão avalia apenas os níveis 0, 1 e 2 (ignorando NV3)[/bold yellow]")
    
    # Verificar se o diretório de resultados existe, senão criar
    if not os.path.exists(RESULTADOS_DIR):
        os.makedirs(RESULTADOS_DIR)
        console.print(f"[yellow]Diretório de resultados NV2 criado: {RESULTADOS_DIR}[/yellow]")
    
    try:
        # Carregar arquivo de amostras
        console.print("[cyan]Carregando arquivo de amostras...[/cyan]")
        samples_df = pd.read_excel(SAMPLES_FILE, sheet_name="SAMPLES")
        console.print(f"[green]Amostras carregadas: {len(samples_df)} itens[/green]")
        
        # Listar todos os arquivos de output disponíveis
        available_outputs = glob.glob(os.path.join(OUTPUTS_DIR, "*.xlsx"))
        console.print(f"[cyan]Encontrados {len(available_outputs)} arquivos de output disponíveis[/cyan]")
        
        if not available_outputs:
            console.print("[bold red]Nenhum arquivo de output encontrado![/bold red]")
            return
        
        # Listar arquivos já processados (resultados existentes)
        existing_results = glob.glob(os.path.join(RESULTADOS_DIR, "RESULTADOS_NV2_*.xlsx"))
        processed_files = set()
        
        for result_file in existing_results:
            # Extrair nome do arquivo original a partir do nome do resultado
            base_name = os.path.basename(result_file).replace("RESULTADOS_NV2_", "", 1)
            processed_files.add(base_name)
        
        console.print(f"[cyan]Encontrados {len(processed_files)} arquivos já processados com sistema NV2[/cyan]")
        
        # Identificar quais arquivos precisam ser processados
        files_to_process = []
        for output_file in available_outputs:
            base_name = os.path.basename(output_file)
            if base_name not in processed_files:
                files_to_process.append(output_file)
        
        console.print(f"[cyan]Arquivos novos a processar: {len(files_to_process)}[/cyan]")
        
        if not files_to_process:
            console.print("[yellow]Todos os arquivos já estão processados. Nada a fazer.[/yellow]")
            
            # Mesmo assim vamos gerar o resumo estatístico com todos os resultados
            todas_stats = []
            for result_file in existing_results:
                try:
                    result_df = pd.read_excel(result_file)
                    stats = {
                        'arquivo': os.path.basename(result_file).replace("RESULTADOS_NV2_", "", 1),
                        'total_itens': len(result_df),
                        'ps_media': result_df['PS'].mean(),
                        'pp_media': result_df['PP'].mean(),
                        'pg_media': result_df['PG'].mean(),
                        'A_top1': len(result_df[result_df['posicao_encontrada'] == 1]),
                        'A_top5': len(result_df[result_df['posicao_encontrada'] > 0])
                    }
                    todas_stats.append(stats)
                except Exception as e:
                    console.print(f"[red]Erro ao processar estatísticas de {result_file}: {str(e)}[/red]")
            
            # Gerar relatório consolidado
            if todas_stats:
                stats_df = pd.DataFrame(todas_stats)
                stats_file = os.path.join(RESULTADOS_DIR, "RESUMO_ESTATISTICAS_NV2.xlsx")
                stats_df.to_excel(stats_file, index=False)
                console.print(f"[bold green]Resumo de estatísticas NV2 atualizado: {stats_file}[/bold green]")
                
                # Mostrar ranking
                console.print("\n[bold cyan]Ranking dos modelos por PG média (sistema NV2):[/bold cyan]")
                ranked_stats = stats_df.sort_values(by='pg_media', ascending=False)
                for i, (_, row) in enumerate(ranked_stats.iterrows(), 1):
                    console.print(f"  {i}. {row['arquivo']} - PG: {row['pg_media']:.4f}, Acertos TOP1: {row['A_top1']}/{row['total_itens']}")
            
            return
        
        # Lista para armazenar estatísticas dos novos arquivos processados
        novas_stats = []
        
        # Verificar se existem resultados já processados para reutilizar
        reused_results = {}
        for result_file in existing_results:
            try:
                base_name = os.path.basename(result_file).replace("RESULTADOS_NV2_", "", 1)
                if base_name in [os.path.basename(f) for f in files_to_process]:
                    # Carregar resultados existentes para este arquivo
                    result_df = pd.read_excel(result_file)
                    reused_results[base_name] = result_df
                    console.print(f"[yellow]Reutilizando resultados existentes para {base_name}[/yellow]")
            except Exception as e:
                console.print(f"[red]Erro ao carregar resultados existentes: {str(e)}[/red]")

        # Processar cada novo arquivo de output
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=False
        ) as progress:
            task = progress.add_task("[blue]Processando novos arquivos com sistema NV2...", total=len(files_to_process))
            
            for output_file in files_to_process:
                base_name = os.path.basename(output_file)
                
                # Se já temos resultados processados, apenas reutilizá-los
                if base_name in reused_results:
                    resultados_df = reused_results[base_name]
                    console.print(f"[cyan]Reutilizando resultados para {base_name}[/cyan]")
                else:
                    # Processar o arquivo normalmente
                    resultados_df, stats = processar_output(output_file, samples_df)
                
                if resultados_df is not None and len(resultados_df) > 0:
                    # Nome do arquivo de resultado
                    base_name = os.path.basename(output_file)
                    result_file = os.path.join(RESULTADOS_DIR, f"RESULTADOS_NV2_{base_name}")
                    
                    # Salvar resultados
                    resultados_df.to_excel(result_file, index=False)
                    console.print(f"[green]Resultados NV2 salvos em: {result_file}[/green]")
                    
                    # Adicionar estatísticas à lista
                    if stats:
                        novas_stats.append(stats)
                
                # Atualizar barra de progresso
                progress.update(task, advance=1)
        
        # Gerar ou atualizar as estatísticas consolidadas
        if novas_stats or existing_results:
            # Carregar estatísticas antigas se existirem
            stats_file = os.path.join(RESULTADOS_DIR, "RESUMO_ESTATISTICAS_NV2.xlsx")
            todas_stats = []
            
            if os.path.exists(stats_file):
                try:
                    old_stats_df = pd.read_excel(stats_file)
                    todas_stats = old_stats_df.to_dict('records')
                    console.print(f"[cyan]Carregadas {len(todas_stats)} estatísticas NV2 existentes[/cyan]")
                except Exception as e:
                    console.print(f"[yellow]Não foi possível carregar estatísticas existentes: {str(e)}[/yellow]")
            
            # Adicionar novas estatísticas
            todas_stats.extend(novas_stats)
            
            # Se não temos estatísticas antigas nem novas, carregar de todos os resultados
            if not todas_stats:
                console.print("[yellow]Reconstruindo estatísticas NV2 a partir dos resultados...[/yellow]")
                all_results = glob.glob(os.path.join(RESULTADOS_DIR, "RESULTADOS_NV2_*.xlsx"))
                
                for result_file in all_results:
                    try:
                        result_df = pd.read_excel(result_file)
                        stats = {
                            'arquivo': os.path.basename(result_file).replace("RESULTADOS_NV2_", "", 1),
                            'total_itens': len(result_df),
                            'ps_media': result_df['PS'].mean(),
                            'pp_media': result_df['PP'].mean(),
                            'pg_media': result_df['PG'].mean(),
                            'A_top1': len(result_df[result_df['posicao_encontrada'] == 1]),
                            'A_top5': len(result_df[result_df['posicao_encontrada'] > 0])
                        }
                        todas_stats.append(stats)
                    except Exception as e:
                        console.print(f"[red]Erro ao processar estatísticas de {result_file}: {str(e)}[/red]")
            
            # Criar DataFrame com todas as estatísticas e salvar
            if todas_stats:
                stats_df = pd.DataFrame(todas_stats)
                stats_df.to_excel(stats_file, index=False)
                console.print(f"[bold green]Resumo de estatísticas NV2 atualizado em: {stats_file}[/bold green]")
                
                # Mostrar ranking dos modelos pelo PG médio
                console.print("\n[bold cyan]Ranking dos modelos por PG média (sistema NV2):[/bold cyan]")
                ranked_stats = stats_df.sort_values(by='pg_media', ascending=False)
                
                # Cabeçalho da tabela
                console.print("[bold]Pos | Modelo      | WH  | WD  | NNN       | MS | OC | PG    | TOP 1 | Score>0.7 | Conf>50[/bold]")
                console.print("=" * 80)
                
                for i, (_, row) in enumerate(ranked_stats.iterrows(), 1):
                    # Garantir que modelo seja string
                    modelo = str(row['modelo']) if pd.notna(row['modelo']) else "DESCONHECIDO"
                    pg = row['pg_media']
                    acertos_pct = row['A_top1_pct'] if 'A_top1_pct' in row and pd.notna(row['A_top1_pct']) else 0
                    
                    wh = row['wh'] if pd.notna(row['wh']) else "-"
                    wd = row['wd'] if pd.notna(row['wd']) else "-"
                    nnn = str(row['nnn']) if pd.notna(row['nnn']) else "-"  # Garantir que nnn seja string
                    ms = row['ms'] if pd.notna(row['ms']) else "-"
                    oc = row['oc'] if pd.notna(row['oc']) else "-"
                    
                    # Garantir que as métricas existam e sejam numéricas
                    score_gt70 = row['score1_gt70'] if 'score1_gt70' in row and pd.notna(row['score1_gt70']) else 0
                    conf_gt50 = row['confidence_gt50'] if 'confidence_gt50' in row and pd.notna(row['confidence_gt50']) else 0
                    
                    # Usar formatação segura
                    console.print(f"{i:2d} | {modelo:12} | {wh:3} | {wd:3} | {nnn:9} | {ms:2} | {oc:2} | {pg:.4f} | {acertos_pct:5.1f}% | {score_gt70:6.1f}% | {conf_gt50:6.1f}%")
        
        console.print("[bold green]Processamento NV2 concluído com sucesso![/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]Erro durante o processamento: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()