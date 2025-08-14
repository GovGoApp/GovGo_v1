import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn

# Criar uma instância de console para exibição formatada
console = Console()

# Configuração da OpenAI
client = OpenAI(api_key="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")

# Definir caminhos e arquivos
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
REPORTS_PATH = BASE_PATH + "REPORTS\\"
EXCEL_FILE = REPORTS_PATH + "TESTE_SIMPLES.xlsx"
CATMAT_FILE = CAT_PATH + "CATMAT_nv2.json"
CATSER_FILE = CAT_PATH + "CATSER_nv2.json"
SHEET = "OBJETOS"

# Nome do arquivo de saída com timestamp
OUTPUT_FILE = REPORTS_PATH + f"CLASSIFICACAO_EMB_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

def load_data():
    """Carregar dados do Excel e arquivos de catálogo."""
    console.print("[bold magenta]Carregando dados...[/bold magenta]")
    
    try:
        df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
        console.print(f"[green]Carregados {len(df_items)} itens do Excel.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
        raise
    
    # Carregar catálogos
    try:
        with open(CATMAT_FILE, 'r', encoding='utf-8') as f:
            catmat = json.load(f)
        with open(CATSER_FILE, 'r', encoding='utf-8') as f:
            catser = json.load(f)
        console.print(f"[green]Carregados {len(catmat)} grupos CATMAT e {len(catser)} grupos CATSER.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivos de catálogo: {str(e)}[/bold red]")
        raise
    
    return df_items, catmat, catser

def prepare_catalog_entries(catmat, catser):
    """Preparar entradas de catálogo combinadas para embedding."""
    console.print("[bold magenta]Preparando textos de catálogo...[/bold magenta]")
    
    catmat_texts = []
    catmat_meta = []  # Vai armazenar tuplas (catalog, group_code, group_name, class_code, class_name)
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Processando CATMAT..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(catmat))
        
        for group in catmat:
            grp_code = group.get('codGrupo')
            grp_name = group.get('Grupo')
            for cls in group.get('Classes', []):
                class_code = cls.get('codClasse')
                class_name = cls.get('Classe')
                # Combinar nomes de grupo e classe para texto de embedding (materiais)
                combined_text = f"{grp_name} - {class_name}"
                catmat_texts.append(combined_text)
                catmat_meta.append(("MATERIAL", grp_code, grp_name, class_code, class_name))
            progress.update(task, advance=1)
    
    catser_texts = []
    catser_meta = []
    
    with Progress(
        SpinnerColumn(), 
        TextColumn("[bold cyan]Processando CATSER..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(catser))
        
        for group in catser:
            grp_code = group.get('codGrupo')
            grp_name = group.get('Grupo')
            for cls in group.get('Classes', []):
                class_code = cls.get('codClasse')
                class_name = cls.get('Classe')
                # Combinar nomes de grupo e classe para texto de embedding (serviços)
                combined_text = f"{grp_name} - {class_name}"
                catser_texts.append(combined_text)
                catser_meta.append(("SERVIÇO", grp_code, grp_name, class_code, class_name))
            progress.update(task, advance=1)
    
    console.print(f"[green]Preparados {len(catmat_texts)} textos de categoria CATMAT para embedding.[/green]")
    console.print(f"[green]Preparados {len(catser_texts)} textos de categoria CATSER para embedding.[/green]")
    
    return catmat_texts, catmat_meta, catser_texts, catser_meta

# 1. Modifique a função get_embeddings para aceitar um parâmetro que desativa a barra de progresso
def get_embeddings(texts, model="text-embedding-ada-002", batch_size=100, show_progress=True):
    """Gerar embeddings para uma lista de textos usando a API da OpenAI."""
    embeddings = []
    
    # Processar em lotes para evitar limites de token ou requisição
    total_batches = int(np.ceil(len(texts) / batch_size))
    
    # Determinar como processar - com ou sem barra de progresso
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("", total=total_batches)
            
            # Loop de processamento com progresso visível
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_embeddings = process_batch(batch, model)
                embeddings.extend(batch_embeddings)
                progress.update(task, advance=1)
    else:
        # Loop de processamento sem progresso visível
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = process_batch(batch, model)
            embeddings.extend(batch_embeddings)
    
    return embeddings

# Função auxiliar para processar um lote (extraída do código original para evitar duplicação)
def process_batch(batch, model):
    """Processa um lote de textos para embeddings, com tentativas em caso de erro."""
    try:
        response = client.embeddings.create(
            model=model, 
            input=batch
        )
        return [np.array(item.embedding, dtype=float) for item in response.data]
    except Exception as e:
        if "rate limit" in str(e).lower():
            console.print("[yellow]Limite de taxa atingido. Aguardando 5 segundos...[/yellow]")
            import time
            time.sleep(5)
            try:
                response = client.embeddings.create(
                    model=model, 
                    input=batch
                )
                return [np.array(item.embedding, dtype=float) for item in response.data]
            except Exception as e2:
                console.print(f"[bold red]Falha na segunda tentativa: {str(e2)}[/bold red]")
                raise
        else:
            console.print(f"[bold red]Erro na API OpenAI: {str(e)}[/bold red]")
            raise

def classify_items(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, top_n=5):
    """Classificar cada item utilizando os embeddings dos catálogos."""
    results = []
    
    # Pré-computar matrizes numpy para cálculo de similaridade mais rápido
    catmat_matrix = np.vstack(catmat_embeddings)  # shape: (M, D)
    catser_matrix = np.vstack(catser_embeddings)  # shape: (S, D)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Classificando itens..."),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[bold yellow]{task.fields[status]}"),
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task("", total=len(df_items), status="Iniciando...")
        
        for idx, row in df_items.iterrows():
            item_id = row.get("id") or row.get("id_pncp")  # lidar com variações no nome da coluna
            description = str(row.get("objetoCompra") or "")
            
            progress.update(task, status=f"Item {idx+1}/{len(df_items)}: {item_id}")
            
            if not description or description.lower() in ["nan", "none"]:
                console.print(f"[yellow]Item {item_id} tem descrição vazia. Pulando.[/yellow]")
                continue
            
            # Obter embedding para a descrição do item
            try:
                item_emb = get_embeddings([description], show_progress=False)[0]
            except Exception as e:
                console.print(f"[bold red]Falha no embedding para item {item_id}: {str(e)}[/bold red]")
                continue
            
            # Calcular similaridade com CATMAT e CATSER
            catmat_scores = catmat_matrix.dot(item_emb)   # numpy dot: (M, D) · (D,) -> (M,)
            catser_scores = catser_matrix.dot(item_emb)   # (S,)
            
            # Identificar melhor correspondência em cada catálogo
            best_mat_idx = int(np.argmax(catmat_scores))
            best_ser_idx = int(np.argmax(catser_scores))
            best_mat_score = float(catmat_scores[best_mat_idx])
            best_ser_score = float(catser_scores[best_ser_idx])
            
            # Determinar tipo pela maior similaridade
            if best_mat_score >= best_ser_score:
                tipo = "Material"
                best_idx = best_mat_idx
                best_meta = catmat_meta[best_idx]
                # Obter top N categorias de material
                top_indices = np.argsort(catmat_scores)[-top_n:][::-1]
                top_matches = [(catmat_meta[i], float(catmat_scores[i])) for i in top_indices]
            else:
                tipo = "Serviço"
                best_idx = best_ser_idx
                best_meta = catser_meta[best_idx]
                # Obter top N categorias de serviço
                top_indices = np.argsort(catser_scores)[-top_n:][::-1]
                top_matches = [(catser_meta[i], float(catser_scores[i])) for i in top_indices]
            
            # Formatar a melhor categoria
            catalog_label, grp_code, grp_name, class_code, class_name = best_meta
            best_category_str = f"{catalog_label}; {grp_code}-{grp_name}; {class_code}-{class_name}"
            
            # Formatar lista top N como strings com scores
            top_list_str = []
            for meta, score in top_matches:
                cat_label, g_code, g_name, c_code, c_name = meta
                cat_str = f"{cat_label}; {g_code}-{g_name}; {c_code}-{c_name} (score={score:.3f})"
                top_list_str.append(cat_str)
            
            # Garantir que a coluna scoreCategoria exista no resultado
            results.append({
                "id": item_id,
                "objetoCompra": description,
                "tipoDetectado": tipo,
                "categoriaMelhor": best_category_str,
                "scoreCategoria": float(best_mat_score if tipo == "Material" else best_ser_score),  # Garantir que este campo exista
                "categoriasTopN": top_list_str
            })
            
            progress.update(task, advance=1)
    
    # Converter resultados para DataFrame
    df_results = pd.DataFrame(results)
    return df_results

# Função principal
def main():
    start_time = time.time()
    
    try:
        # Carregar dados
        df_items, catmat, catser = load_data()
        
        # Preparar textos de catálogo para embeddings
        catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)
        
        # Incorporar categorias de catálogo
        console.print("[bold magenta]Gerando embeddings para categorias do catálogo...[/bold magenta]")
        catmat_embeddings = get_embeddings(catmat_texts)
        catser_embeddings = get_embeddings(catser_texts)
        console.print("[green]Embeddings de categorias gerados com sucesso.[/green]")
        
        # Classificar cada item do Excel
        console.print("[bold magenta]Classificando itens...[/bold magenta]")
        df_output = classify_items(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, top_n=5)
        
        # Salvar ou exibir a saída
        console.print("[bold magenta]Salvando resultados...[/bold magenta]")
        
        # Mover a coluna scoreCategoria para antes de categoriasTopN para melhor visualização
        # Verificar se a coluna existe antes de tentar removê-la
        cols = df_output.columns.tolist()
        if "scoreCategoria" in cols:
            cols.remove("scoreCategoria")
            cols.insert(cols.index("categoriasTopN"), "scoreCategoria")
            df_output = df_output[cols]
        
        # Salvar em Excel
        df_output.to_excel(OUTPUT_FILE, index=False)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Classificação concluída em {total_time:.2f} segundos![/green]")
        console.print(f"[bold green]Resultados salvos em: {OUTPUT_FILE}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

# Executar o código principal
if __name__ == "__main__":
    import time
    main()