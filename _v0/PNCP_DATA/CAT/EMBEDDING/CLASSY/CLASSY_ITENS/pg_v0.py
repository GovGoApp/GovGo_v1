"""
PG_V0.py - Avaliação de Modelos de Classificação 
-------------------------------------------------
Este código compara resultados de diferentes modelos de classificação contra uma amostra de respostas corretas.
Calcula métricas de qualidade considerando:
- Semelhança entre códigos previstos e códigos corretos por nível (PS)
- Posição em que o código correto foi encontrado nas previsões (PP)
- Pontuação geral combinando semelhança e posição (PG)

As métricas são calculadas para cada item da amostra e para cada modelo, permitindo uma 
comparação detalhada de desempenho entre diferentes configurações.
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
RESULTADOS_DIR = BASE_PATH + "ESTUDOS\\P176\\RESULTADOS\\"

# Constantes de pesos
WS = 0.5  # Peso para pontuação de semelhança
WP = 0.5  # Peso para pontuação de posição

# Pesos por posição de score
WSS = [10, 5, 3, 2, 1]  # Pesos para SCORE_1, SCORE_2, ..., SCORE_5

# Pontuação máxima de semelhança para normalização
PSM = 15 * sum(WSS)  # 15 (match perfeito) * soma dos pesos = 15 * 21 = 315

# Pesos por posição (para PP)
PESOS_POSICAO = [1.0, 0.75, 0.5, 0.4, 0.3]  # Para posições 1, 2, 3, 4 e 5

def extrair_codigos(codigo_completo):
    """
    Extrai os códigos dos níveis de um código completo.
    Formato: {M/S}{0000}{00000}{00000}
    
    Args:
        codigo_completo: Código completo no formato especificado
        
    Returns:
        Lista com os códigos dos níveis extraídos
    """
    if not isinstance(codigo_completo, str) or len(codigo_completo) < 15:
        return None
    
    try:
        codnv0 = codigo_completo[0]  # M ou S
        codnv1 = codigo_completo[1:5]  # 4 dígitos
        codnv2 = codigo_completo[5:10]  # 5 dígitos
        codnv3 = codigo_completo[10:15]  # 5 dígitos
        
        return [codnv0, codnv1, codnv2, codnv3]
    except:
        return None

def calcular_pss(codigo_correto, codigo_score):
    """
    Calcula a pontuação por semelhança por score (pss).
    
    Args:
        codigo_correto: Código da resposta correta
        codigo_score: Código da previsão
        
    Returns:
        Pontuação binária por nível e valor decimal
    """
    niveis_correto = extrair_codigos(codigo_correto)
    niveis_score = extrair_codigos(codigo_score)
    
    if niveis_correto is None or niveis_score is None:
        return [0, 0, 0, 0], 0
    
    binario = []
    for i in range(4):
        if i < len(niveis_correto) and i < len(niveis_score):
            binario.append(1 if niveis_correto[i] == niveis_score[i] else 0)
        else:
            binario.append(0)
    
    # Converter binário para decimal (base 2)
    decimal = int(''.join(map(str, binario)), 2)
    
    return binario, decimal

def extrair_codigo_de_top(top_value):
    """
    Extrai o código do valor do campo TOP_N.
    Formato típico: "M00700704000227 - Nome da categoria"
    
    Args:
        top_value: Valor do campo TOP_N
        
    Returns:
        Código extraído
    """
    if not isinstance(top_value, str):
        return None
    
    # Tenta extrair o código (padrão: letra seguida de 14 dígitos no início)
    match = re.match(r'^([MS]\d{14})', top_value)
    if match:
        return match.group(1)
    
    return None

def calcular_ps(codigo_correto, codigo_scores):
    """
    Calcula a pontuação de semelhança (PS) normalizada.
    
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
                'binario': [0, 0, 0, 0],
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
    
    Args:
        codigo_correto: Código da resposta correta
        codigo_scores: Lista de códigos dos scores [CS1, CS2, ..., CS5]
        
    Returns:
        PP (0 a 1) e posição encontrada
    """
    for i, cs in enumerate(codigo_scores):
        if cs == codigo_correto:
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

def processar_output(output_file, samples_df):
    """
    Processa um arquivo de output para calcular métricas em relação às amostras.
    
    Args:
        output_file: Caminho do arquivo de output
        samples_df: DataFrame com as amostras de referência
        
    Returns:
        DataFrame com os resultados calculados
    """
    console.print(f"[bold cyan]Processando arquivo: {os.path.basename(output_file)}[/bold cyan]")
    
    try:
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
            
            # Calcular PS
            ps, pss_detalhes, ps_soma = calcular_ps(codigo_correto, codigos_scores)
            
            # Calcular PP
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
        
        # Calcular estatísticas agregadas para este output
        stats = {
            'arquivo': os.path.basename(output_file),
            'total_itens': len(resultados_df),
            'ps_media': resultados_df['PS'].mean(),
            'pp_media': resultados_df['PP'].mean(),
            'pg_media': resultados_df['PG'].mean(),
            'acertos_top1': len(resultados_df[resultados_df['posicao_encontrada'] == 1]),
            'acertos_top5': len(resultados_df[resultados_df['posicao_encontrada'] > 0])
        }
        
        console.print(f"[green]Estatísticas para {os.path.basename(output_file)}:[/green]")
        console.print(f"  Total de itens analisados: {stats['total_itens']}")
        console.print(f"  PS média: {stats['ps_media']:.4f}")
        console.print(f"  PP média: {stats['pp_media']:.4f}")
        console.print(f"  PG média: {stats['pg_media']:.4f}")
        console.print(f"  Acertos no TOP 1: {stats['acertos_top1']} ({stats['acertos_top1']/stats['total_itens']*100:.2f}%)")
        console.print(f"  Acertos no TOP 5: {stats['acertos_top5']} ({stats['acertos_top5']/stats['total_itens']*100:.2f}%)")
        
        return resultados_df, stats
    
    except Exception as e:
        console.print(f"[bold red]Erro ao processar {os.path.basename(output_file)}: {str(e)}[/bold red]")
        return None, None

def main():
    """
    Função principal que coordena o processamento de todos os arquivos de output.
    Agora verifica quais arquivos já foram processados para evitar retrabalho.
    """
    console.print("[bold magenta]===== INICIANDO AVALIAÇÃO DE MODELOS =====[/bold magenta]")
    
    # Verificar se o diretório de resultados existe, senão criar
    if not os.path.exists(RESULTADOS_DIR):
        os.makedirs(RESULTADOS_DIR)
        console.print(f"[yellow]Diretório de resultados criado: {RESULTADOS_DIR}[/yellow]")
    
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
        existing_results = glob.glob(os.path.join(RESULTADOS_DIR, "RESULTADOS_*.xlsx"))
        processed_files = set()
        
        for result_file in existing_results:
            # Extrair nome do arquivo original a partir do nome do resultado
            base_name = os.path.basename(result_file).replace("RESULTADOS_", "", 1)
            processed_files.add(base_name)
        
        console.print(f"[cyan]Encontrados {len(processed_files)} arquivos já processados[/cyan]")
        
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
                        'arquivo': os.path.basename(result_file).replace("RESULTADOS_", "", 1),
                        'total_itens': len(result_df),
                        'ps_media': result_df['PS'].mean(),
                        'pp_media': result_df['PP'].mean(),
                        'pg_media': result_df['PG'].mean(),
                        'acertos_top1': len(result_df[result_df['posicao_encontrada'] == 1]),
                        'acertos_top5': len(result_df[result_df['posicao_encontrada'] > 0])
                    }
                    todas_stats.append(stats)
                except Exception as e:
                    console.print(f"[red]Erro ao processar estatísticas de {result_file}: {str(e)}[/red]")
            
            # Gerar relatório consolidado
            if todas_stats:
                stats_df = pd.DataFrame(todas_stats)
                stats_file = os.path.join(RESULTADOS_DIR, "RESUMO_ESTATISTICAS.xlsx")
                stats_df.to_excel(stats_file, index=False)
                console.print(f"[bold green]Resumo de estatísticas atualizado: {stats_file}[/bold green]")
                
                # Mostrar ranking
                console.print("\n[bold cyan]Ranking dos modelos por PG média:[/bold cyan]")
                ranked_stats = stats_df.sort_values(by='pg_media', ascending=False)
                for i, (_, row) in enumerate(ranked_stats.iterrows(), 1):
                    console.print(f"  {i}. {row['arquivo']} - PG: {row['pg_media']:.4f}, Acertos TOP1: {row['acertos_top1']}/{row['total_itens']}")
            
            return
        
        # Lista para armazenar estatísticas dos novos arquivos processados
        novas_stats = []
        
        # Processar cada novo arquivo de output
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=False
        ) as progress:
            task = progress.add_task("[blue]Processando novos arquivos...", total=len(files_to_process))
            
            for output_file in files_to_process:
                # Processar o arquivo
                resultados_df, stats = processar_output(output_file, samples_df)
                
                if resultados_df is not None and len(resultados_df) > 0:
                    # Nome do arquivo de resultado
                    base_name = os.path.basename(output_file)
                    result_file = os.path.join(RESULTADOS_DIR, f"RESULTADOS_{base_name}")
                    
                    # Salvar resultados
                    resultados_df.to_excel(result_file, index=False)
                    console.print(f"[green]Resultados salvos em: {result_file}[/green]")
                    
                    # Adicionar estatísticas à lista
                    if stats:
                        novas_stats.append(stats)
                
                # Atualizar barra de progresso
                progress.update(task, advance=1)
        
        # Gerar ou atualizar as estatísticas consolidadas
        if novas_stats or existing_results:
            # Carregar estatísticas antigas se existirem
            stats_file = os.path.join(RESULTADOS_DIR, "RESUMO_ESTATISTICAS.xlsx")
            todas_stats = []
            
            if os.path.exists(stats_file):
                try:
                    old_stats_df = pd.read_excel(stats_file)
                    todas_stats = old_stats_df.to_dict('records')
                    console.print(f"[cyan]Carregadas {len(todas_stats)} estatísticas existentes[/cyan]")
                except Exception as e:
                    console.print(f"[yellow]Não foi possível carregar estatísticas existentes: {str(e)}[/yellow]")
            
            # Adicionar novas estatísticas
            todas_stats.extend(novas_stats)
            
            # Se não temos estatísticas antigas nem novas, carregar de todos os resultados
            if not todas_stats:
                console.print("[yellow]Reconstruindo estatísticas a partir dos resultados...[/yellow]")
                all_results = glob.glob(os.path.join(RESULTADOS_DIR, "RESULTADOS_*.xlsx"))
                
                for result_file in all_results:
                    try:
                        result_df = pd.read_excel(result_file)
                        stats = {
                            'arquivo': os.path.basename(result_file).replace("RESULTADOS_", "", 1),
                            'total_itens': len(result_df),
                            'ps_media': result_df['PS'].mean(),
                            'pp_media': result_df['PP'].mean(),
                            'pg_media': result_df['PG'].mean(),
                            'acertos_top1': len(result_df[result_df['posicao_encontrada'] == 1]),
                            'acertos_top5': len(result_df[result_df['posicao_encontrada'] > 0])
                        }
                        todas_stats.append(stats)
                    except Exception as e:
                        console.print(f"[red]Erro ao processar estatísticas de {result_file}: {str(e)}[/red]")
            
            # Criar DataFrame com todas as estatísticas e salvar
            if todas_stats:
                stats_df = pd.DataFrame(todas_stats)
                stats_df.to_excel(stats_file, index=False)
                console.print(f"[bold green]Resumo de estatísticas atualizado em: {stats_file}[/bold green]")
                
                # Mostrar ranking dos modelos pelo PG médio
                console.print("\n[bold cyan]Ranking dos modelos por PG média:[/bold cyan]")
                ranked_stats = stats_df.sort_values(by='pg_media', ascending=False)
                for i, (_, row) in enumerate(ranked_stats.iterrows(), 1):
                    console.print(f"  {i}. {row['arquivo']} - PG: {row['pg_media']:.4f}, Acertos TOP1: {row['acertos_top1']}/{row['total_itens']}")
        
        console.print("[bold green]Processamento concluído com sucesso![/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]Erro durante o processamento: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()