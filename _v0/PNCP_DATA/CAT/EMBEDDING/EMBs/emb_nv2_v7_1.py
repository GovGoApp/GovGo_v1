#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EmbedForge Ollama - Specialized version for Ollama-based embeddings using unified CAT

This script is an adaptation of emb_nv2_v7_1.py but uses the EmbedForge framework
with a unified CAT approach instead of separate CATMAT and CATSER models.

Features:
- Uses Ollama for embeddings generation
- Thread-safe Ollama access with locks 
- Uses unified CAT catalog
- Efficient batch processing with ThreadPoolExecutor
- Caching of embeddings
- Checkpoints for resumable processing
"""

import os
import json
import time
import pickle
import threading
import concurrent.futures
from datetime import datetime
import numpy as np
import pandas as pd
import requests
import ollama
import logging

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Configure logging to avoid messages interrupting progress bars
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ===============================================================================
# CONFIGURATIONS AND PATHS (from emb_forge_v0.py)
# ===============================================================================
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CAT_PATH = os.path.join(BASE_PATH, "CAT\\")
NOVA_CAT_PATH = os.path.join(CAT_PATH, "NOVA\\")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS\\")
CLASS_PATH = os.path.join(BASE_PATH, "CLASSIFICAÇÃO\\")
EMBEDDING_PATH = os.path.join(BASE_PATH, "EMBEDDING\\")
ITEMS_EMBED_PATH = os.path.join(EMBEDDING_PATH, "items\\")

INPUT_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES.xlsx")
INPUT_SHEET = "OBJETOS"
GABARITO_FILE = os.path.join(CLASS_PATH, "TESTE_SIMPLES_GABARITO_NOVA.xlsx")
GABARITO_SHEET = "GABARITO"

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M')
OUTPUT_FILE = os.path.join(REPORTS_PATH, f"TESTE_SIMPLES_ITENS_{TIMESTAMP}.xlsx")
CHECKPOINT_FILE = os.path.join(REPORTS_PATH, f"CHECKPOINT_TESTE_SIMPLES_ITENS_{TIMESTAMP}.pkl")

# Define the Ollama model to use
OLLAMA_MODEL = "llama3.2"  # Use LLaMa 3.2 as default

BATCH_SIZE = 20000
TOP_N = 5
MAX_WORKERS = min(32, os.cpu_count() * 4)

# Create directories if they don't exist
for d in [EMBEDDING_PATH, ITEMS_EMBED_PATH]:
    if not os.path.exists(d):
        os.makedirs(d)

# Locks for concurrent access
checkpoint_lock = threading.Lock()
embedding_lock = threading.Lock()
ollama_lock = threading.RLock()  # Global lock for Ollama access

# Initialize console for display
console = Console()
console.print(f"[bold blue]Using Ollama model: {OLLAMA_MODEL}")
console.print(f"CPU cores: {os.cpu_count()}, Workers: {MAX_WORKERS}")

# ===============================================================================
# UTILITY FUNCTIONS
# ===============================================================================
def provider_progress(provider_name, total):
    """Creates a standardized progress bar for all providers."""
    return Progress(
        SpinnerColumn(), 
        TextColumn(f"[bold cyan]({provider_name})..."),
        BarColumn(), 
        TaskProgressColumn(), 
        TimeElapsedColumn(),
        transient=False
    )

def save_embeddings(embeddings, filepath):
    """Saves embeddings to a pickle file with thread safety."""
    with embedding_lock:
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            console.print(f"[green]Embeddings saved[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Error saving embeddings: {str(e)}[/bold red]")
            return False

def load_embeddings(filepath):
    """Loads embeddings from a pickle file if it exists."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
            console.print(f"[green]Embeddings loaded[/green]")
            return embeddings
        except Exception as e:
            console.print(f"[bold red]Error loading embeddings: {str(e)}[/bold red]")
    return None

def load_checkpoint():
    """Loads checkpoint if it exists."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            console.print(f"[bold red]Error loading checkpoint: {str(e)}[/bold red]")
    return None

def save_checkpoint(last_processed, output_file):
    """Saves checkpoint for later resuming."""
    with checkpoint_lock:
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'last_processed': last_processed,
            'output_file': output_file
        }
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(checkpoint, f)
        console.print(f"[green]Checkpoint saved: {CHECKPOINT_FILE}[/green]")

def load_data():
    """Loads data from Excel and the unified catalog."""
    console.print("[bold magenta]Loading data and unified catalog...[/bold magenta]")
    checkpoint = load_checkpoint()
    
    if checkpoint:
        console.print("[bold yellow]Checkpoint found. Continuing from last processing...[/bold yellow]")
        last_processed = checkpoint['last_processed']
        try:
            skiprows = list(range(1, last_processed + 1))
            df_items = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET, skiprows=skiprows)
        except Exception as e:
            console.print(f"[bold red]Error loading Excel: {str(e)}[/bold red]")
            raise e
    else:
        try:
            df_items = pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)
        except Exception as e:
            console.print(f"[bold red]Error loading Excel: {str(e)}[/bold red]")
            raise e
            
    # Load the unified catalog from Excel
    try:
        catalog_file = os.path.join(NOVA_CAT_PATH, "NOVA CAT.xlsx")
        cat_df = pd.read_excel(catalog_file, sheet_name="CAT")
        cat = cat_df.to_dict(orient="records")
        console.print(f"[green]Loaded {len(cat)} catalog entries from unified CAT.[/green]")
    except Exception as e:
        console.print(f"[bold red]Error loading unified catalog: {str(e)}[/bold red]")
        raise e
        
    # Load existing results if available from checkpoint
    existing_results = pd.DataFrame()
    if checkpoint and 'output_file' in checkpoint:
        try:
            existing_results = pd.read_excel(checkpoint['output_file'])
            console.print(f"[green]Loaded {len(existing_results)} previous results.[/green]")
        except Exception as e:
            console.print(f"[bold red]Error loading previous results: {str(e)}[/bold red]")
            
    return df_items, cat, existing_results, checkpoint

def prepare_catalog_entries(cat):
    """Prepares catalog entries for embedding."""
    console.print("[bold magenta]Preparing unified catalog texts...[/bold magenta]")
    cat_texts = []
    cat_meta = []
    
    for entry in cat:
        # Uses CODCAT and NOMCAT columns from Excel
        codcat = entry.get('CODCAT', '')
        nomcat = entry.get('NOMCAT', '')
        # Forms embedding text by concatenating the fields with a space
        combined_text = f"{codcat} {nomcat}"
        cat_texts.append(combined_text)
        cat_meta.append((codcat, nomcat))
        
    console.print(f"[magenta]Prepared {len(cat_texts)} unified catalog texts.[/magenta]")
    return cat_texts, cat_meta

# ===============================================================================
# OLLAMA EMBEDDINGS IMPLEMENTATION
# ===============================================================================
def get_embeddings_ollama(texts):
    """Generates embeddings for a batch of texts using Ollama."""
    embeddings = []
    expected_dim = 4096  # Default dimension for llama3.2
    
    # Function to extract embedding from Ollama response
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
    
    # Test and store the actual dimension if this is the first use
    with ollama_lock:
        if not hasattr(get_embeddings_ollama, "_dim"):
            try:
                console.print("[bold yellow]Testing connection with Ollama...[/bold yellow]")
                test_response = ollama.embed(model=OLLAMA_MODEL, input="Connection test")
                test_emb = extract_embedding(test_response)
                actual_dim = test_emb.shape[0]
                get_embeddings_ollama._dim = actual_dim
                console.print(f"[green]Connection established! (embedding dimension: {actual_dim})[/green]")
            except Exception as e:
                console.print(f"[bold red]Error testing Ollama model {OLLAMA_MODEL}: {str(e)}[/bold red]")
                console.print("[bold yellow]TROUBLESHOOTING INSTRUCTIONS FOR OLLAMA:[/bold yellow]")
                console.print("1. Check if the Ollama server is running")
                console.print("2. Make sure the model has been downloaded: ollama pull llama3.2")
                console.print("3. Test manually in the terminal: ollama embed -m llama3.2 \"test\"")
                raise
    
    # Get the embedding dimension for this model
    actual_dim = getattr(get_embeddings_ollama, "_dim", expected_dim)
    
    # Process each text in the batch
    for text in texts:
        if not text or text.isspace():
            embeddings.append(np.zeros(actual_dim))
            continue
        
        # Use lock to ensure thread safety
        with ollama_lock:
            try:
                response = ollama.embed(model=OLLAMA_MODEL, input=text)
                emb = extract_embedding(response)
                embeddings.append(emb)
            except Exception as e:
                console.print(f"[bold red]Error embedding text with Ollama: {str(e)}[/bold red]")
                embeddings.append(np.zeros(actual_dim))
    
    return embeddings

# ===============================================================================
# MAIN CLASSIFICATION FUNCTIONS
# ===============================================================================
def classify_items_batched(df_items, cat_embeds, cat_meta, last_processed=0):
    """Classifies items in batches with parallel processing."""
    # Precompute numpy matrices for faster similarity calculation
    cat_matrix = np.vstack(cat_embeds)
    
    # Convert catalog embeddings to unit vectors for cosine similarity
    cat_norm = np.linalg.norm(cat_matrix, axis=1, keepdims=True)
    cat_matrix = cat_matrix / np.where(cat_norm != 0, cat_norm, 1)
    
    # Initialize accumulated results
    all_results = pd.DataFrame()
    total_items = len(df_items)
    
    # Process in batches to save incremental results
    for batch_start in range(0, total_items, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_items)
        df_batch = df_items.iloc[batch_start:batch_end]
        
        console.print(f"[bold magenta]Processing batch {batch_start//BATCH_SIZE + 1}/{(total_items-1)//BATCH_SIZE + 1} "
                      f"(items {batch_start+1}-{batch_end}/{total_items})[/bold magenta]")
        
        # Extract item descriptions
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
        
        # Generate embeddings for items
        console.print("[bold cyan]Getting embeddings for the batch...[/bold cyan]")
        
        try:
            valid_indices = [i for i, desc in enumerate(descriptions) if desc]
            valid_descriptions = [descriptions[i] for i in valid_indices]
            
            if valid_descriptions:
                with provider_progress("Ollama", 1) as progress:
                    task = progress.add_task("", total=1)
                    item_embeddings = get_embeddings_ollama(valid_descriptions)
                    progress.update(task, advance=1)
                    
                # Map embeddings back to original indices
                all_item_embeddings = [None] * len(descriptions)
                for i, emb in zip(valid_indices, item_embeddings):
                    all_item_embeddings[i] = emb
                    
                # Save embeddings summary (optional)
                embeddings_file = os.path.join(ITEMS_EMBED_PATH, f"batch_{batch_start}_{batch_end}_{OLLAMA_MODEL.replace('-', '_')}_{TIMESTAMP}.pkl")
                save_embeddings({"model": OLLAMA_MODEL, "embeddings": item_embeddings}, embeddings_file)
            else:
                all_item_embeddings = []
                
        except Exception as e:
            console.print(f"[bold red]Error generating batch embeddings: {str(e)}[/bold red]")
            continue
        
        # Prepare arguments for parallel classification
        console.print("[bold cyan]Classifying with parallel processing...[/bold cyan]")
        
        classification_args = []
        for i, (idx, item_id, description) in enumerate(zip(indices, item_ids, descriptions)):
            if i < len(all_item_embeddings) and all_item_embeddings[i] is not None:
                item_emb = all_item_embeddings[i]
                classification_args.append((idx, item_id, description, item_emb, cat_matrix, cat_meta, TOP_N))
            else:
                classification_args.append((idx, item_id, description, None, None, None, TOP_N))
        
        # Use ThreadPoolExecutor for parallel classification
        batch_results = []
        with Progress(
            SpinnerColumn(), 
            TextColumn("[bold cyan]Classifying items..."),
            BarColumn(), 
            TaskProgressColumn(), 
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("", total=len(classification_args))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(classify_item, args) for args in classification_args]
                
                for future in futures:
                    try:
                        idx, item_id, result = future.result()
                        batch_results.append(result)
                        progress.update(task, advance=1)
                    except Exception as e:
                        console.print(f"[bold red]Error in classification future: {str(e)}[/bold red]")
                        progress.update(task, advance=1)
        
        # Convert batch results to DataFrame
        df_batch_results = pd.DataFrame(batch_results)
        
        # Process top-N categories for better display
        if 'topCategories' in df_batch_results.columns:
            df_batch_results['topCategories'] = df_batch_results['topCategories'].apply(
                lambda x: '\n'.join(x) if isinstance(x, list) else str(x))
        
        # Remove embedding vectors before saving to Excel (too large)
        if 'embedding' in df_batch_results.columns:
            df_batch_results = df_batch_results.drop(columns=['embedding'])
        
        # Add to accumulated results
        all_results = pd.concat([all_results, df_batch_results], ignore_index=True)
        
        # Save incremental results
        temp_output = OUTPUT_FILE.replace('.xlsx', f'_incremental.xlsx')
        try:
            all_results.to_excel(temp_output, index=False)
            console.print(f"[green]Saved incrementally: {temp_output} "
                         f"({len(all_results)} items processed)[/green]")
            
            # Update checkpoint for recovery
            save_checkpoint(
                last_processed + batch_end,
                temp_output
            )
        except Exception as e:
            console.print(f"[bold red]Error saving incremental results: {str(e)}[/bold red]")
    
    # Organize columns for better display
    cols = all_results.columns.tolist()
    if "score" in cols and "topCategories" in cols:
        all_results = all_results[["id", "objetoCompra", "category", "score", "topCategories"] + 
                                  [c for c in cols if c not in ["id", "objetoCompra", "category", "score", "topCategories"]]]
    
    # Save final version
    try:
        all_results.to_excel(OUTPUT_FILE, index=False)
        console.print(f"[bold green]Final results saved to: {OUTPUT_FILE}[/bold green]")
        
        # Clean up temporary files after success
        if os.path.exists(temp_output):
            os.remove(temp_output)
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    except Exception as e:
        console.print(f"[bold red]Error saving final results: {str(e)}[/bold red]")
    
    return all_results

def classify_item(args):
    """Classifies a single item using cosine similarity."""
    idx, item_id, description, item_emb, cat_matrix, cat_meta, top_n = args
    
    # If no embedding, return unclassified
    if item_emb is None:
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "category": "Not classified",
            "score": 0.0,
            "topCategories": [],
            "embedding": None
        }
    
    try:
        # Normalize item embedding for cosine similarity
        item_emb_norm = item_emb / np.linalg.norm(item_emb)
        
        # Calculate similarity with all catalog entries
        scores = cat_matrix.dot(item_emb_norm)
        
        # Get top N matches
        top_indices = np.argsort(scores)[-top_n:][::-1]
        top_scores = scores[top_indices]
        top_categories = [cat_meta[i] for i in top_indices]
        
        # Format the top categories with scores
        top_categories_str = []
        for (codcat, nomcat), score in zip(top_categories, top_scores):
            cat_str = f"{codcat}: {nomcat} (score={score:.3f})"
            top_categories_str.append(cat_str)
        
        # Get the best match
        best_idx = top_indices[0]
        best_score = float(scores[best_idx])
        best_cat = cat_meta[best_idx]
        
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "category": f"{best_cat[0]}: {best_cat[1]}",
            "score": best_score,
            "topCategories": top_categories_str,
            "embedding": item_emb.tolist()  # Convert to list for serialization
        }
    except Exception as e:
        console.print(f"[bold red]Error in classification: {str(e)}[/bold red]")
        return idx, item_id, {
            "id": item_id,
            "objetoCompra": description,
            "category": f"Error: {str(e)}",
            "score": 0.0,
            "topCategories": [],
            "embedding": None
        }

# ===============================================================================
# MAIN FUNCTION
# ===============================================================================
def main():
    start_time = time.time()
    
    try:
        # Load data and check for checkpoint
        df_items, cat, existing_results, checkpoint = load_data()
        last_processed = checkpoint['last_processed'] if checkpoint else 0
        
        # Prepare catalog texts for embeddings
        cat_texts, cat_meta = prepare_catalog_entries(cat)
        
        # Check for existing catalog embeddings
        console.print("[bold magenta]Checking for existing catalog embeddings...[/bold magenta]")
        
        # Define the path for catalog embeddings cache
        model_safe_name = OLLAMA_MODEL.replace("/", "_").replace("-", "_").replace(".", "_").lower()
        cat_embed_file = os.path.join(EMBEDDING_PATH, f"cat_unified_{model_safe_name}.pkl")
        
        cat_embeds = load_embeddings(cat_embed_file)
        if cat_embeds is None or len(cat_embeds) != len(cat_texts):
            console.print(f"[yellow]Catalog embeddings not found or outdated. Generating new ones with {OLLAMA_MODEL}...[/yellow]")
            with provider_progress("Ollama", 1) as progress:
                task = progress.add_task("", total=1)
                cat_embeds = get_embeddings_ollama(cat_texts)
                progress.update(task, advance=1)
            save_embeddings(cat_embeds, cat_embed_file)
        
        console.print("[green]Catalog embeddings ready.[/green]")
        
        # Classify items in batches with parallel processing
        console.print("[bold magenta]Starting classification in batches with parallel processing...[/bold magenta]")
        results = classify_items_batched(
            df_items, 
            cat_embeds, 
            cat_meta,
            last_processed
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Classification completed in {total_time/60:.2f} minutes![/green]")
        console.print(f"[green]({total_time:.2f} seconds total, {total_time/len(df_items):.4f} seconds per item)[/green]")
        console.print(f"[cyan]Embeddings saved to:")
        console.print(f"- Catalog: {cat_embed_file}")
        console.print(f"- Items: {ITEMS_EMBED_PATH}[/cyan]")
        console.print(f"[bold blue]Model used: {OLLAMA_MODEL} via Ollama")
        
    except Exception as e:
        console.print(f"[bold red]Pipeline failed: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()