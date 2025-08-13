"""
UPDATE_STATS.py - Atualização de Arquivos e Estatísticas de Modelos
------------------------------------------------------------------
Este script reorganiza os arquivos de resultados existentes e reconstrói
a tabela de estatísticas consolidadas com todos os parâmetros dos modelos.
"""

import os
import re
import pandas as pd
import glob
import shutil
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from datetime import datetime

# Inicializar console para output formatado
console = Console()

# Constantes de caminho
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CLASSY\\CLASSY_ITENS\\OUTPUT_ITENS\\"
OUTPUTS_DIR = BASE_PATH + "ESTUDOS\\P176\\"
RESULTADOS_DIR = BASE_PATH + "ESTUDOS\\P176\\RESULTADOS\\"
BACKUP_DIR = BASE_PATH + "ESTUDOS\\P176\\BACKUP_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "\\"

def extrair_parametros_do_nome(nome_arquivo):
    """
    Extrai os parâmetros de configuração do nome do arquivo.
    Formato esperado: OUTPUT_ITEM_176_D{WD}_H{WH}_{flags}.xlsx
    
    Args:
        nome_arquivo: Nome do arquivo
        
    Returns:
        Dicionário com os parâmetros extraídos
    """
    try:
        # Remover extensão e prefixo
        nome_base = os.path.splitext(nome_arquivo)[0]
        
        # Extrair parâmetros usando regex
        # Padrões possíveis:
        # OUTPUT_ITEM_176_D10_H0_OC_IT.xlsx
        # OUTPUT_ITEM_176_D7_H3_10_10_10.xlsx
        # OUTPUT_ITEM_176_D5_H5_MS_IT.xlsx
        
        # Extrair WD e WH
        wd_match = re.search(r'D(\d+)', nome_base)
        wh_match = re.search(r'H(\d+)', nome_base)
        
        if wd_match and wh_match:
            wd = int(wd_match.group(1)) / 10.0
            wh = int(wh_match.group(1)) / 10.0
            
            # Verificar se há NNN personalizado (10_10_10)
            nnn_match = re.search(r'(\d+_\d+_\d+)(?:_|$)', nome_base)
            if nnn_match:
                nnn = nnn_match.group(1).replace('_', ',')
            else:
                nnn = "5,5,5"  # Valor padrão
                
            # Verificar flags MS, OC, IT
            ms_flag = 1 if "_MS_" in nome_base or "_MS" in nome_base.split("_")[-1] else 0
            oc_flag = 1 if "_OC_" in nome_base or "_OC" in nome_base.split("_")[-1] else 0
            it_flag = 1  # Sempre 1 para esses arquivos
            
            # Criar um identificador legível para o modelo
            modelo = f"H{int(wh*10)}_D{int(wd*10)}"
            
            # Adicionar sufixos para filtros especiais
            if not ms_flag and oc_flag:
                modelo += "_OC_IT"
            elif ms_flag and not oc_flag:
                modelo += "_MS_IT"
            elif not ms_flag and not oc_flag:
                modelo += "_IT"
            elif ms_flag and oc_flag:
                modelo += "_MS_OC_IT"
                
            # Adicionar sufixo para NNN não padrão
            if nnn != "5,5,5":
                modelo += f"_{nnn.replace(',', '_')}"
            
            return {
                'modelo': modelo,
                'wh': wh,
                'wd': wd,
                'nnn': nnn,
                'ms': ms_flag,
                'oc': oc_flag,
                'it': it_flag,
                'arquivo_original': nome_arquivo,
                'arquivo_padronizado': f"OUTPUT_ITEM_176_H{int(wh*10)}_D{int(wd*10)}_{nnn.replace(',', '_')}_{ms_flag}_{oc_flag}_{it_flag}.xlsx"
            }
        
        return {
            'modelo': 'DESCONHECIDO',
            'wh': None,
            'wd': None,
            'nnn': None,
            'ms': None,
            'oc': None,
            'it': None,
            'arquivo_original': nome_arquivo,
            'arquivo_padronizado': nome_arquivo
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
            'arquivo_original': nome_arquivo,
            'arquivo_padronizado': nome_arquivo
        }

def obter_estatisticas_resultado(result_file):
    """
    Extrai estatísticas de um arquivo de resultado.
    
    Args:
        result_file: Caminho do arquivo de resultado
        
    Returns:
        Dicionário com estatísticas extraídas
    """
    try:
        result_df = pd.read_excel(result_file)
        
        # Extrair parâmetros do nome do arquivo de resultado
        arquivo_origem = os.path.basename(result_file).replace("RESULTADOS_", "", 1)
        parametros = extrair_parametros_do_nome(arquivo_origem)
        
        # Calcular estatísticas
        total_itens = len(result_df)
        ps_media = result_df['PS'].mean() if 'PS' in result_df.columns else None
        pp_media = result_df['PP'].mean() if 'PP' in result_df.columns else None
        pg_media = result_df['PG'].mean() if 'PG' in result_df.columns else None
        
        acertos_top1 = len(result_df[result_df['posicao_encontrada'] == 1]) if 'posicao_encontrada' in result_df.columns else 0
        acertos_top5 = len(result_df[result_df['posicao_encontrada'] > 0]) if 'posicao_encontrada' in result_df.columns else 0
        
        # Calcular porcentagens para CONFIDENCE e SCORE_1
        confidence_gt50 = 0
        confidence_lt50 = 0
        score1_gt70 = 0
        score1_lt70 = 0
        
        if 'CONFIDENCE' in result_df.columns:
            confidence_gt50 = len(result_df[result_df['CONFIDENCE'] > 50]) / total_itens * 100
            confidence_lt50 = len(result_df[result_df['CONFIDENCE'] <= 50]) / total_itens * 100
        
        if 'SCORE_1' in result_df.columns:
            score1_gt70 = len(result_df[result_df['SCORE_1'] > 0.7]) / total_itens * 100
            score1_lt70 = len(result_df[result_df['SCORE_1'] <= 0.7]) / total_itens * 100
        
        stats = {
            'arquivo': arquivo_origem,
            'arquivo_padronizado': parametros['arquivo_padronizado'],
            'modelo': parametros['modelo'],
            'wh': parametros['wh'],
            'wd': parametros['wd'],
            'nnn': parametros['nnn'],
            'ms': parametros['ms'],
            'oc': parametros['oc'],
            'it': parametros['it'],
            'total_itens': total_itens,
            'ps_media': ps_media,
            'pp_media': pp_media,
            'pg_media': pg_media,
            'acertos_top1': acertos_top1,
            'acertos_top5': acertos_top5,
            'acertos_top1_pct': acertos_top1 / total_itens * 100 if total_itens > 0 else 0,
            'acertos_top5_pct': acertos_top5 / total_itens * 100 if total_itens > 0 else 0,
            'confidence_gt50': confidence_gt50,
            'confidence_lt50': confidence_lt50,
            'score1_gt70': score1_gt70,
            'score1_lt70': score1_lt70
        }
        
        return stats
    except Exception as e:
        console.print(f"[red]Erro ao processar estatísticas de {result_file}: {str(e)}[/red]")
        return None

def main():
    """
    Função principal que coordena a atualização dos arquivos e estatísticas.
    """
    console.print("[bold magenta]===== ATUALIZANDO ARQUIVOS E ESTATÍSTICAS =====[/bold magenta]")
    
    # Criar diretório de backup se não existir
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        console.print(f"[yellow]Diretório de backup criado: {BACKUP_DIR}[/yellow]")
    
    try:
        # Listar arquivos de resultados existentes
        existing_results = glob.glob(os.path.join(RESULTADOS_DIR, "RESULTADOS_*.xlsx"))
        console.print(f"[cyan]Encontrados {len(existing_results)} arquivos de resultado existentes[/cyan]")
        
        if not existing_results:
            console.print("[yellow]Nenhum arquivo de resultado encontrado para processar.[/yellow]")
            return
        
        # Coletar estatísticas de todos os arquivos de resultado
        todas_stats = []
        mapeamento_arquivos = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=False
        ) as progress:
            task = progress.add_task("[blue]Processando arquivos de resultado...", total=len(existing_results))
            
            for result_file in existing_results:
                stats = obter_estatisticas_resultado(result_file)
                if stats:
                    todas_stats.append(stats)
                    
                    # Guardar mapeamento entre nome original e nome padronizado
                    original = stats['arquivo']
                    padronizado = stats['arquivo_padronizado']
                    if original != padronizado:
                        mapeamento_arquivos[original] = padronizado
                
                progress.update(task, advance=1)
        
        # Remover duplicatas (alguns arquivos apareceram duplicados no ranking)
        unique_stats = []
        modelos_vistos = set()
        
        for stat in todas_stats:
            modelo_key = f"{stat['modelo']}_{stat['nnn']}_{stat['ms']}_{stat['oc']}_{stat['it']}"
            if modelo_key not in modelos_vistos:
                modelos_vistos.add(modelo_key)
                unique_stats.append(stat)
        
        console.print(f"[green]Coletadas estatísticas de {len(unique_stats)} modelos únicos[/green]")
        
        # Criar DataFrame com todas as estatísticas
        stats_df = pd.DataFrame(unique_stats)
        
        # Organizar colunas em ordem lógica
        ordered_columns = [
            'modelo', 'wh', 'wd', 'nnn', 'ms', 'oc', 'it',
            'pg_media', 'ps_media', 'pp_media', 
            'acertos_top1', 'acertos_top5', 'acertos_top1_pct', 'acertos_top5_pct',
            'confidence_gt50', 'confidence_lt50',
            'score1_gt70', 'score1_lt70', 
            'total_itens', 'arquivo', 'arquivo_padronizado'
        ]
        
        # Usar apenas as colunas que existem
        valid_columns = [col for col in ordered_columns if col in stats_df.columns]
        stats_df = stats_df[valid_columns]
        
        # Ordenar por PG média (decrescente)
        stats_df = stats_df.sort_values(by='pg_media', ascending=False)
        
        # Salvar resumo de estatísticas
        stats_file = os.path.join(RESULTADOS_DIR, "RESUMO_ESTATISTICAS_ATUALIZADO.xlsx")
        stats_df.to_excel(stats_file, index=False)
        console.print(f"[bold green]Resumo de estatísticas atualizado salvo em: {stats_file}[/bold green]")
        
        # Backup e atualização dos arquivos de output originais
        if mapeamento_arquivos:
            console.print(f"[cyan]Renomeando {len(mapeamento_arquivos)} arquivos para o formato padronizado...[/cyan]")
            
            # Verificar arquivos no diretório de outputs
            output_files = glob.glob(os.path.join(OUTPUTS_DIR, "*.xlsx"))
            
            for output_file in output_files:
                base_name = os.path.basename(output_file)
                if base_name in mapeamento_arquivos:
                    # Fazer backup do arquivo original
                    backup_file = os.path.join(BACKUP_DIR, base_name)
                    shutil.copy2(output_file, backup_file)
                    
                    # Criar novo nome padronizado
                    novo_nome = os.path.join(OUTPUTS_DIR, mapeamento_arquivos[base_name])
                    
                    # Renomear arquivo
                    os.rename(output_file, novo_nome)
                    console.print(f"[green]Arquivo renomeado: {base_name} -> {mapeamento_arquivos[base_name]}[/green]")
                    
                    # Também atualizar arquivo de resultados
                    result_file = os.path.join(RESULTADOS_DIR, f"RESULTADOS_{base_name}")
                    if os.path.exists(result_file):
                        # Fazer backup do arquivo de resultado
                        backup_result = os.path.join(BACKUP_DIR, f"RESULTADOS_{base_name}")
                        shutil.copy2(result_file, backup_result)
                        
                        # Renomear arquivo de resultado
                        novo_result = os.path.join(RESULTADOS_DIR, f"RESULTADOS_{mapeamento_arquivos[base_name]}")
                        os.rename(result_file, novo_result)
                        console.print(f"[green]Resultado renomeado: RESULTADOS_{base_name} -> RESULTADOS_{mapeamento_arquivos[base_name]}[/green]")
        
        # Exibir ranking atualizado
        console.print("\n[bold cyan]Ranking atualizado dos modelos por PG média:[/bold cyan]")
        console.print("[bold]Pos | Modelo      | WH  | WD  | NNN       | MS | OC | PG    | TOP 1 | Score>0.7 | Conf>50[/bold]")
        console.print("=" * 80)
        
        for i, (_, row) in enumerate(stats_df.iterrows(), 1):
            modelo = row['modelo']
            pg = row['pg_media']
            acertos_pct = row['acertos_top1_pct']
            
            wh = row['wh'] if pd.notna(row['wh']) else "-"
            wd = row['wd'] if pd.notna(row['wd']) else "-"
            nnn = row['nnn'] if pd.notna(row['nnn']) else "-"
            ms = row['ms'] if pd.notna(row['ms']) else "-"
            oc = row['oc'] if pd.notna(row['oc']) else "-"
            
            score_gt70 = row['score1_gt70'] if 'score1_gt70' in row and pd.notna(row['score1_gt70']) else 0
            conf_gt50 = row['confidence_gt50'] if 'confidence_gt50' in row and pd.notna(row['confidence_gt50']) else 0
            
            console.print(f"{i:2d} | {modelo:12s} | {wh:3} | {wd:3} | {nnn:9s} | {ms:2} | {oc:2} | {pg:.4f} | {acertos_pct:5.1f}% | {score_gt70:6.1f}% | {conf_gt50:6.1f}%")
        
        console.print("[bold green]Processamento concluído com sucesso![/bold green]")
        console.print(f"[bold yellow]Backup dos arquivos originais feito em: {BACKUP_DIR}[/bold yellow]")
    
    except Exception as e:
        console.print(f"[bold red]Erro durante o processamento: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()