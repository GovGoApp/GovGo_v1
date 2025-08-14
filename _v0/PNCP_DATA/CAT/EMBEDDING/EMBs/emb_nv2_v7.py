### EMB_NV2_v7 (EMBEDDING NIVEL 2 V7) – Versão com Ollama ###

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
import time
import ollama  # Biblioteca para acessar modelos locais via Ollama

# Instância do console para exibição formatada
console = Console()

# Definir caminhos e arquivos
PATH = "C:\\Users\\Haroldo Duraes\\"
BASE_PATH = PATH + "Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = BASE_PATH + "CAT\\"
CLASS_PATH = BASE_PATH + "CLASSIFICAÇÃO\\"
EMBEDDING_PATH = BASE_PATH + "EMBEDDING\\"
ITEMS_EMBED_PATH = EMBEDDING_PATH + "ITENS\\"

# Definir o modelo a ser utilizado com Ollama
OLLAMA_MODEL = "mxbai-embed-large"  # Este é o modelo baixado com: ollama pull mxbai-embed-large

console.print(f"[bold blue]Usando modelo Ollama: {OLLAMA_MODEL}")

EXCEL_FILE = CLASS_PATH + "TESTE_SIMPLES.xlsx"
CATMAT_FILE = CAT_PATH + "CATMAT_nv2.json"
CATSER_FILE = CAT_PATH + "CATSER_nv2.json"
SHEET = "OBJETOS"

# Nome do arquivo de saída com timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = CLASS_PATH + f"CLASSIFICACAO_{OLLAMA_MODEL}_{TIMESTAMP}.xlsx"
CHECKPOINT_FILE = CLASS_PATH + f"CHECKPOINT_EMB_{TIMESTAMP}.pkl"
BATCH_SIZE = 20000  # Tamanho do batch para processamento

# Caminhos para armazenamento de embeddings
CATMAT_EMBED_FILE = EMBEDDING_PATH + f"catmat_embeddings_{OLLAMA_MODEL.replace('-', '_')}.pkl"
CATSER_EMBED_FILE = EMBEDDING_PATH + f"catser_embeddings_{OLLAMA_MODEL.replace('-', '_')}.pkl"

SAVE_ITEM_EMBEDDINGS = False

# Criar diretórios se não existirem
for directory in [EMBEDDING_PATH, ITEMS_EMBED_PATH]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Constantes para controle de execução
MAX_WORKERS = min(32, os.cpu_count() * 4)
console.print("CPU: " + str(os.cpu_count()))
console.print("WORKERS = " + str(MAX_WORKERS))

# Locks para acessos concorrentes
results_lock = threading.Lock()
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()


def save_embeddings(embeddings, filepath):
    """Salva embeddings em arquivo pickle."""
    with embedding_lock:
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            console.print(f"[green]Embeddings salvos em {filepath}[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar embeddings: {str(e)}[/bold red]")
            return False

def load_embeddings(filepath):
    """Carrega embeddings de arquivo pickle se existir."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings carregados de {filepath}[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar embeddings: {str(e)}[/bold red]")
    return None

def load_data():
    """Carrega dados do Excel e arquivos de catálogo."""
    console.print("[bold magenta]Carregando dados...[/bold magenta]")
    checkpoint = load_checkpoint()
    if checkpoint:
        console.print("[bold yellow]Checkpoint encontrado. Continuando do último processamento...[/bold yellow]")
        last_processed = checkpoint['last_processed']
        try:
            skiprows = list(range(1, last_processed + 1))
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET, skiprows=skiprows)
            console.print(f"[green]Carregados {len(df_items)} itens restantes do Excel (a partir da linha {last_processed+1}).[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    else:
        try:
            df_items = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)
            console.print(f"[green]Carregados {len(df_items)} itens do Excel.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    try:
        with open(CATMAT_FILE, 'r', encoding='utf-8') as f:
            catmat = json.load(f)
        with open(CATSER_FILE, 'r', encoding='utf-8') as f:
            catser = json.load(f)
        console.print(f"[green]Carregados {len(catmat)} grupos CATMAT e {len(catser)} grupos CATSER.[/green]")
    except Exception as e:
        console.print(f"[bold red]Erro ao carregar arquivos de catálogo: {str(e)}[/bold red]")
        raise
    if checkpoint and 'output_file' in checkpoint:
        try:
            existing_results = pd.read_excel(checkpoint['output_file'])
            console.print(f"[green]Carregados {len(existing_results)} resultados anteriores.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar resultados anteriores: {str(e)}[/bold red]")
            existing_results = pd.DataFrame()
    else:
        existing_results = pd.DataFrame()
    return df_items, catmat, catser, existing_results, checkpoint

def save_checkpoint(last_processed, output_file):
    """Salva checkpoint para retomar o processamento posteriormente."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file
        }
        check_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        checkpoint_file = CHECKPOINT_FILE.replace('.pkl', f'_{check_timestamp}.pkl')
        with open(checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[green]Checkpoint salvo em: {checkpoint_file}[/green]")

def load_checkpoint():
    """Carrega checkpoint se existir."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def prepare_catalog_entries(catmat, catser):
    """Prepara entradas de catálogo combinadas para embedding."""
    console.print("[bold magenta]Preparando textos de catálogo...[/bold magenta]")
    catmat_texts = []
    catmat_meta = []
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Processando CATMAT..."), 
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn()) as progress:
        task = progress.add_task("", total=len(catmat))
        for group in catmat:
            grp_code = group.get('codGrupo')
            grp_name = group.get('Grupo')
            for cls in group.get('Classes', []):
                class_code = cls.get('codClasse')
                class_name = cls.get('Classe')
                combined_text = f"{grp_name} - {class_name}"
                catmat_texts.append(combined_text)
                catmat_meta.append(("MATERIAL", grp_code, grp_name, class_code, class_name))
            progress.update(task, advance=1)
    catser_texts = []
    catser_meta = []
    with Progress(SpinnerColumn(), TextColumn("[bold cyan]Processando CATSER..."), 
                  BarColumn(), TaskProgressColumn(), TimeElapsedColumn()) as progress:
        task = progress.add_task("", total=len(catser))
        for group in catser:
            grp_code = group.get('codGrupo')
            grp_name = group.get('Grupo')
            for cls in group.get('Classes', []):
                class_code = cls.get('codClasse')
                class_name = cls.get('Classe')
                combined_text = f"{grp_name} - {class_name}"
                catser_texts.append(combined_text)
                catser_meta.append(("SERVIÇO", grp_code, grp_name, class_code, class_name))
            progress.update(task, advance=1)
    console.print(f"[green]Preparados {len(catmat_texts)} textos de categoria CATMAT para embedding.[/green]")
    console.print(f"[green]Preparados {len(catser_texts)} textos de categoria CATSER para embedding.[/green]")
    return catmat_texts, catmat_meta, catser_texts, catser_meta

def get_embeddings(texts, batch_size=32, show_progress=True):
    """Gera embeddings para uma lista de textos usando a função ollama.embed.
    
    Args:
        texts: Lista de textos para gerar embeddings
        batch_size: Tamanho do lote para processamento
        show_progress: Se deve mostrar barra de progresso
        
    Returns:
        Lista de arrays numpy com os embeddings
    """
    embeddings = []
    total_batches = int(np.ceil(len(texts) / batch_size))
    embedding_dim = 1024  # Dimensão padrão para mxbai-embed-large
    
    # Testar a conexão primeiro com um texto simples
    console.print("[bold yellow]Testando conexão com o modelo Ollama...[/bold yellow]")
    try:
        # Mostrar a versão da biblioteca Ollama para debug
        console.print(f"[cyan]Usando biblioteca Ollama versão: {ollama.__version__ if hasattr(ollama, '__version__') else 'desconhecida'}[/cyan]")
        
        test_text = "Teste de conexão"
        # Tentar obter um embedding de teste
        try:
            test_response = ollama.embed(model=OLLAMA_MODEL, input=test_text)
            console.print("[green]API usa parâmetro 'input'[/green]")
        except Exception:
            try:
                test_response = ollama.embed(OLLAMA_MODEL, test_text)
                console.print("[green]API usa parâmetros posicionais[/green]")
            except Exception:
                try:
                    test_response = ollama.embeddings(model=OLLAMA_MODEL, prompt=test_text)
                    console.print("[green]API usa método 'embeddings'[/green]")
                except Exception as e:
                    console.print(f"[bold red]Todas as tentativas falharam: {str(e)}[/bold red]")
                    raise
        
        # Tratamento específico do objeto EmbedResponse
        console.print(f"[cyan]Tipo da resposta: {type(test_response).__name__}[/cyan]")
        
        # Extrair o embedding da resposta
        if hasattr(test_response, "embedding"):
            test_emb = np.array(test_response.embedding)
        elif hasattr(test_response, "embeddings"):
            test_emb = np.array(test_response.embeddings[0])
        elif isinstance(test_response, dict):
            if "embedding" in test_response:
                test_emb = np.array(test_response["embedding"])
            elif "embeddings" in test_response:
                test_emb = np.array(test_response["embeddings"][0])
        else:
            # Tentativa final - converter diretamente para numpy
            test_emb = np.array(test_response)
            
        # Atualizar a dimensão esperada
        embedding_dim = test_emb.shape[0]
        console.print(f"[green]Conexão estabelecida! (dimensão do embedding: {embedding_dim})[/green]")
        
    except Exception as e:
        console.print(f"[bold red]Erro ao testar conexão: {str(e)}[/bold red]")
        console.print("\n[bold yellow]INSTRUÇÕES PARA RESOLVER PROBLEMAS COM OLLAMA:[/bold yellow]")
        console.print("1. Verifique se o servidor Ollama está em execução")
        console.print("2. Certifique-se que o modelo foi baixado: ollama pull mxbai-embed-large")
        console.print("3. Teste manualmente no terminal: ollama embed -m mxbai-embed-large \"teste\"")
        console.print("4. Verifique a documentação do Ollama para o formato correto dos comandos")
        raise
    
    # Função interna para converter resposta de embedding em array
    def extract_embedding(response):
        if hasattr(response, "embedding"):
            return np.array(response.embedding)
        elif hasattr(response, "embeddings"):
            return np.array(response.embeddings[0])
        elif isinstance(response, dict):
            if "embedding" in response:
                return np.array(response["embedding"])
            elif "embeddings" in response:
                return np.array(response["embeddings"][0])
        else:
            return np.array(response)
    
    # Processamento com barra de progresso
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Processando embeddings..."),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("", total=total_batches)
            
            # Processar em lotes
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                batch_embeddings = []
                
                # Processar cada texto no lote
                for text in batch:
                    # Garantir que o texto não está vazio
                    if not text or text.isspace():
                        batch_embeddings.append(np.zeros(embedding_dim))
                        continue
                        
                    # Obter embedding sem retry
                    try:
                        response = ollama.embed(model=OLLAMA_MODEL, input=text)
                        emb = extract_embedding(response)
                        batch_embeddings.append(emb)
                    except Exception as e:
                        console.print(f"[bold red]Erro ao processar texto: {str(e)}[/bold red]")
                        batch_embeddings.append(np.zeros(embedding_dim))
                    
                embeddings.extend(batch_embeddings)
                progress.update(task, advance=1)
    else:
        # Processamento sem barra de progresso
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = []
            
            for text in batch:
                if not text or text.isspace():
                    batch_embeddings.append(np.zeros(embedding_dim))
                    continue
                    
                try:
                    response = ollama.embed(model=OLLAMA_MODEL, input=text)
                    emb = extract_embedding(response)
                    batch_embeddings.append(emb)
                except Exception as e:
                    console.print(f"[bold red]Erro ao processar texto: {str(e)}[/bold red]")
                    batch_embeddings.append(np.zeros(embedding_dim))
                
            embeddings.extend(batch_embeddings)
    
    # Verificar se todos os embeddings são válidos
    zero_embeddings = sum(1 for e in embeddings if np.all(e == 0))
    if zero_embeddings > 0:
        console.print(f"[yellow]Aviso: {zero_embeddings} de {len(embeddings)} embeddings são vetores de zeros.[/yellow]")
    
    return embeddings

def classify_items_batched(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, 
                           existing_results=None, last_processed=0, top_n=5):
    """Classifica itens em batches com processamento paralelo."""
    catmat_matrix = np.vstack(catmat_embeddings)
    catser_matrix = np.vstack(catser_embeddings)
    all_results = existing_results if existing_results is not None else pd.DataFrame()
    total_items = len(df_items)
    for batch_start in range(0, total_items, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_items)
        df_batch = df_items.iloc[batch_start:batch_end]
        console.print(f"[bold magenta]Processando batch {batch_start//BATCH_SIZE + 1}/{total_items//BATCH_SIZE + 1} "
                      f"(itens {batch_start+1}-{batch_end}/{total_items})[/bold magenta]")
        descriptions = []
        item_ids = []
        indices = []
        for idx, row in df_batch.iterrows():
            item_id = row.get("id") or row.get("id_pncp")
            description = str(row.get("objetoCompra") or "")
            if not description or pd.isna(description) or description.lower() in ["nan", "none"]:
                descriptions.append("")
            else:
                descriptions.append(description)
            item_ids.append(item_id)
            indices.append(idx)
        console.print("[bold cyan]Obtendo embeddings para o batch...[/bold cyan]")
        try:
            valid_indices = [i for i, desc in enumerate(descriptions) if desc]
            valid_descriptions = [descriptions[i] for i in valid_indices]
            if valid_descriptions:
                item_embeddings = get_embeddings(valid_descriptions, batch_size=32, show_progress=True)
                all_item_embeddings = [None] * len(descriptions)
                for i, emb in zip(valid_indices, item_embeddings):
                    all_item_embeddings[i] = emb
                if SAVE_ITEM_EMBEDDINGS:
                    embeddings_summary = {
                        'batch': f"{batch_start}_{batch_end}",
                        'timestamp': TIMESTAMP,
                        'model': OLLAMA_MODEL,
                        'num_items': len(valid_indices),
                        'mean_vector': np.mean(item_embeddings, axis=0).tolist() if item_embeddings else None,
                        'std_vector': np.std(item_embeddings, axis=0).tolist() if item_embeddings else None
                    }
                    summary_file = f"{ITEMS_EMBED_PATH}SUMMARY_{batch_start}_{batch_end}_{OLLAMA_MODEL.replace('-', '_')}_{TIMESTAMP}.pkl"
                    save_embeddings(embeddings_summary, summary_file)
                    console.print(f"[green]Resumo de embeddings salvo em: {summary_file}[/green]")
            else:
                all_item_embeddings = []
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar embeddings do batch: {str(e)}[/bold red]")
            continue
        console.print("[bold cyan]Classificando itens com processamento paralelo...[/bold cyan]")
        classification_args = []
        for i, (idx, item_id, description) in enumerate(zip(indices, item_ids, descriptions)):
            if i < len(all_item_embeddings) and all_item_embeddings[i] is not None:
                item_emb = all_item_embeddings[i]
                classification_args.append((idx, item_id, description, item_emb, catmat_matrix, 
                                             catser_matrix, catmat_meta, catser_meta, top_n))
            else:
                classification_args.append((idx, item_id, description, None, None, None, None, None, top_n))
        batch_results = []
        with Progress(SpinnerColumn(), TextColumn("[bold cyan]Classificando items...[/bold cyan]"),
                      BarColumn(), TaskProgressColumn(), TimeElapsedColumn()) as progress:
            task_items = progress.add_task("", total=len(classification_args))
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(classify_item_local, args) for args in classification_args]
                for future in futures:
                    try:
                        idx, item_id, result = future.result()
                        batch_results.append(result)
                        progress.update(task_items, advance=1)
                    except Exception as e:
                        console.print(f"[bold red]Erro em future: {str(e)}[/bold red]")
                        progress.update(task_items, advance=1)
        df_batch_results = pd.DataFrame(batch_results)
        if 'categoriasTopN' in df_batch_results.columns:
            df_batch_results['categoriasTopN'] = df_batch_results['categoriasTopN'].apply(
                lambda x: '\n'.join(x) if isinstance(x, list) else str(x))
        if 'embedding' in df_batch_results.columns:
            df_batch_results = df_batch_results.drop(columns=['embedding'])
        all_results = pd.concat([all_results, df_batch_results], ignore_index=True)
        temp_output = OUTPUT_FILE.replace('.xlsx', f'_incremental.xlsx')
        try:
            all_results.to_excel(temp_output, index=False)
            console.print(f"[green]Salvo incrementalmente: {temp_output} ({len(all_results)} itens processados)[/green]")
            save_checkpoint(last_processed + batch_end, temp_output)
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar resultados incrementais: {str(e)}[/bold red]")
    cols = all_results.columns.tolist()
    if "scoreCategoria" in cols:
        cols.remove("scoreCategoria")
        cols.insert(cols.index("categoriasTopN") if "categoriasTopN" in cols else -1, "scoreCategoria")
        all_results = all_results[cols]
    try:
        all_results.to_excel(OUTPUT_FILE, index=False)
        console.print(f"[bold green]Resultados finais salvos em: {OUTPUT_FILE}[/bold green]")
        if os.path.exists(temp_output):
            os.remove(temp_output)
    except Exception as e:
        console.print(f"[bold red]Erro ao salvar resultados finais: {str(e)}[/bold red]")
    return all_results

def classify_item_local(args):
    """Realiza a classificação local com normalização dos vetores."""
    idx, item_id, description, item_emb, catmat_matrix, catser_matrix, catmat_meta, catser_meta, top_n = args
    if item_emb is None:
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Não classificado",
            "categoriaMelhor": "Descrição inválida",
            "scoreCategoria": 0.0,
            "categoriasTopN": [],
            "embedding": None
        }
    try:
        item_emb_norm = item_emb / np.linalg.norm(item_emb)
        catmat_scores = catmat_matrix.dot(item_emb_norm)
        catser_scores = catser_matrix.dot(item_emb_norm)
        best_mat_idx = int(np.argmax(catmat_scores))
        best_ser_idx = int(np.argmax(catser_scores))
        best_mat_score = float(catmat_scores[best_mat_idx])
        best_ser_score = float(catser_scores[best_ser_idx])
        if best_mat_score >= best_ser_score:
            tipo = "Material"
            best_meta = catmat_meta[best_mat_idx]
            top_indices = np.argsort(catmat_scores)[-top_n:][::-1]
            top_matches = [(catmat_meta[i], float(catmat_scores[i])) for i in top_indices]
        else:
            tipo = "Serviço"
            best_meta = catser_meta[best_ser_idx]
            top_indices = np.argsort(catser_scores)[-top_n:][::-1]
            top_matches = [(catser_meta[i], float(catser_scores[i])) for i in top_indices]
        catalog_label, grp_code, grp_name, class_code, class_name = best_meta
        best_category_str = f"{catalog_label}; {grp_code}-{grp_name}; {class_code}-{class_name}"
        top_list_str = []
        for meta, score in top_matches:
            cat_label, g_code, g_name, c_code, c_name = meta
            cat_str = f"{cat_label}; {g_code}-{g_name}; {c_code}-{c_name} (score={score:.3f})"
            top_list_str.append(cat_str)
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": tipo,
            "categoriaMelhor": best_category_str,
            "scoreCategoria": float(best_mat_score if tipo == "Material" else best_ser_score),
            "categoriasTopN": top_list_str,
            "embedding": item_emb.tolist()
        }
    except Exception as e:
        console.print(f"[bold red]Erro na classificação do item {item_id}: {str(e)}[/bold red]")
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": "Erro",
            "categoriaMelhor": f"Erro: {str(e)}",
            "scoreCategoria": 0.0,
            "categoriasTopN": [],
            "embedding": None
        }

def main():
    start_time = time.time()
    try:
        df_items, catmat, catser, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)
        print(catser_texts[:5])
        print(catmat_texts[:5])
        console.print("[bold magenta]Verificando embeddings de catálogo existentes...[/bold magenta]")
        catmat_embeddings = load_embeddings(CATMAT_EMBED_FILE)
        if catmat_embeddings is None or len(catmat_embeddings) != len(catmat_texts):
            console.print(f"[yellow]Embeddings de CATMAT não encontrados ou desatualizados. Gerando novos com {OLLAMA_MODEL}...[/yellow]")
            catmat_embeddings = get_embeddings(catmat_texts)
            save_embeddings(catmat_embeddings, CATMAT_EMBED_FILE)
        catser_embeddings = load_embeddings(CATSER_EMBED_FILE)
        if catser_embeddings is None or len(catser_embeddings) != len(catser_texts):
            console.print(f"[yellow]Embeddings de CATSER não encontrados ou desatualizados. Gerando novos com {OLLAMA_MODEL}...[/yellow]")
            catser_embeddings = get_embeddings(catser_texts)
            save_embeddings(catser_embeddings, CATSER_EMBED_FILE)
        console.print("[cyan]Normalizando vetores para cálculo de similaridade por cosseno...[/cyan]")
        catmat_embeddings = [emb / np.linalg.norm(emb) for emb in catmat_embeddings]
        catser_embeddings = [emb / np.linalg.norm(emb) for emb in catser_embeddings]
        console.print("[green]Embeddings de categorias preparados.[/green]")
        console.print("[bold magenta]Iniciando classificação em batches com processamento paralelo...[/bold magenta]")
        results = classify_items_batched(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, existing_results, last_processed)
        end_time = time.time()
        total_time = end_time - start_time
        console.print(f"[green]Classificação concluída em {total_time/60:.2f} minutos![/green]")
        console.print(f"[green]({total_time:.2f} segundos total, {total_time/len(df_items):.4f} segundos por item)[/green]")
        console.print(f"[cyan]Embeddings salvos em:")
        console.print(f"- Catálogos: {EMBEDDING_PATH}")
        console.print(f"- Itens: {ITEMS_EMBED_PATH}[/cyan]")
        console.print(f"[bold blue]Modelo utilizado: {OLLAMA_MODEL} via Ollama")
    except Exception as e:
        console.print(f"[bold red]Pipeline falhou: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()