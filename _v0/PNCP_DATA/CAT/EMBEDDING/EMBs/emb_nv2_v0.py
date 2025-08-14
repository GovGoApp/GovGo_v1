import os
import json
import logging
import numpy as np
import pandas as pd
import openai

# Configure logging for the module
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Define OpenAI API key (assumed to be set as an environment variable for security)
openai.api_key = os.getenv("OPENAI_API_KEY")  # Ensure the API key is set in your environment

def load_data(excel_path, catmat_path, catser_path):
    """Load input Excel and catalog JSON files."""
    try:
        df_items = pd.read_excel(excel_path, sheet_name="OBJETOS")
        logger.info(f"Loaded {len(df_items)} items from Excel.")
    except Exception as e:
        logger.error(f"Error loading Excel file: {e}")
        raise
    
    # Load catalogs
    try:
        with open(catmat_path, 'r', encoding='utf-8') as f:
            catmat = json.load(f)
        with open(catser_path, 'r', encoding='utf-8') as f:
            catser = json.load(f)
        logger.info(f"Loaded {len(catmat)} CATMAT groups and {len(catser)} CATSER groups.")
    except Exception as e:
        logger.error(f"Error loading catalog files: {e}")
        raise
    
    return df_items, catmat, catser

def prepare_catalog_entries(catmat, catser):
    """
    Prepare combined text entries for each class in CATMAT and CATSER.
    Returns two lists: catmat_texts, catser_texts and corresponding metadata lists.
    """
    catmat_texts = []
    catmat_meta = []  # Will hold tuples (catalog, group_code, group_name, class_code, class_name)
    for group in catmat:
        grp_code = group.get('codGrupo')
        grp_name = group.get('Grupo')
        for cls in group.get('Classes', []):
            class_code = cls.get('codClasse')
            class_name = cls.get('Classe')
            # Combine group and class names for embedding text (materials)
            combined_text = f"{grp_name} - {class_name}"
            catmat_texts.append(combined_text)
            catmat_meta.append(("CATMAT", grp_code, grp_name, class_code, class_name))
    logger.info(f"Prepared {len(catmat_texts)} CATMAT category texts for embedding.")
    
    catser_texts = []
    catser_meta = []
    for group in catser:
        grp_code = group.get('codGrupo')
        grp_name = group.get('Grupo')
        for cls in group.get('Classes', []):
            class_code = cls.get('codClasse')
            class_name = cls.get('Classe')
            # Combine group and class names for embedding text (services)
            combined_text = f"{grp_name} - {class_name}"
            catser_texts.append(combined_text)
            catser_meta.append(("CATSER", grp_code, grp_name, class_code, class_name))
    logger.info(f"Prepared {len(catser_texts)} CATSER category texts for embedding.")
    return catmat_texts, catmat_meta, catser_texts, catser_meta

def get_embeddings(texts, model="text-embedding-ada-002", batch_size=100):
    """
    Generate embeddings for a list of texts using OpenAI API, handling batching and rate limits.
    Returns a list of embedding vectors (as numpy arrays).
    """
    embeddings = []
    # Process in batches to avoid hitting token or request limits
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        try:
            logger.info(f"Embedding batch {i//batch_size + 1} of {int(np.ceil(len(texts)/batch_size))}, size {len(batch)}")
            response = openai.Embedding.create(model=model, input=batch)
        except openai.error.RateLimitError as e:
            logger.warning("Rate limit hit. Waiting 5 seconds and retrying...")
            import time
            time.sleep(5)
            try:
                response = openai.Embedding.create(model=model, input=batch)
            except Exception as e2:
                logger.error(f"Failed to retrieve embeddings after retry: {e2}")
                raise
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        # Extract embeddings from response
        batch_embeddings = [np.array(item["embedding"], dtype=float) for item in response['data']]
        embeddings.extend(batch_embeddings)
    return embeddings

def classify_items(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, top_n=3):
    """
    Classify each item in df_items using the provided catalog embeddings.
    Returns a DataFrame with classification results.
    """
    results = []
    # Precompute numpy arrays for faster similarity calculation
    catmat_matrix = np.vstack(catmat_embeddings)  # shape: (M, D)
    catser_matrix = np.vstack(catser_embeddings)  # shape: (S, D)
    for idx, row in df_items.iterrows():
        item_id = row.get("id") or row.get("id_pncp")  # handle column name variations
        description = str(row.get("objetoCompra") or "")
        if not description or description.lower() in ["nan", "none"]:
            logger.warning(f"Item {item_id} has empty description. Skipping.")
            continue
        # Get embedding for the item description
        try:
            item_emb = get_embeddings([description])[0]
        except Exception as e:
            logger.error(f"Embedding failed for item {item_id}: {e}")
            continue
        
        # Compute cosine similarity with CATMAT and CATSER (dot product since vectors are unit-length)
        catmat_scores = catmat_matrix.dot(item_emb)   # numpy dot: (M, D) · (D,) -> (M,)
        catser_scores = catser_matrix.dot(item_emb)   # (S,)
        # Identify best match in each
        best_mat_idx = int(np.argmax(catmat_scores))
        best_ser_idx = int(np.argmax(catser_scores))
        best_mat_score = float(catmat_scores[best_mat_idx])
        best_ser_score = float(catser_scores[best_ser_idx])
        # Determine type by higher similarity
        if best_mat_score >= best_ser_score:
            tipo = "Material"
            best_idx = best_mat_idx
            best_meta = catmat_meta[best_idx]
            # Get top N material categories
            top_indices = np.argsort(catmat_scores)[-top_n:][::-1]
            top_matches = [(catmat_meta[i], float(catmat_scores[i])) for i in top_indices]
        else:
            tipo = "Serviço"
            best_idx = best_ser_idx
            best_meta = catser_meta[best_idx]
            # Get top N service categories
            top_indices = np.argsort(catser_scores)[-top_n:][::-1]
            top_matches = [(catser_meta[i], float(catser_scores[i])) for i in top_indices]
        # Format the best category as required: "CATMAT; CODGRUPO-GRUPO; CODCLASSE-CLASSE"
        catalog_label, grp_code, grp_name, class_code, class_name = best_meta
        best_category_str = f"{catalog_label}; {grp_code}-{grp_name}; {class_code}-{class_name}"
        # Format top N list as strings with scores (rounded for readability)
        top_list_str = []
        for meta, score in top_matches:
            cat_label, g_code, g_name, c_code, c_name = meta
            cat_str = f"{cat_label}; {g_code}-{g_name}; {c_code}-{c_name} (score={score:.3f})"
            top_list_str.append(cat_str)
        results.append({
            "id": item_id,
            "objetoCompra": description,
            "tipoDetectado": tipo,
            "categoriaMelhor": best_category_str,
            "categoriasTopN": top_list_str
        })
        logger.debug(f"Classified item {item_id} as {tipo}, best match: {best_category_str}")
    # Convert results to DataFrame
    df_results = pd.DataFrame(results)
    return df_results

# Main execution flow (could be under if __name__ == '__main__' guard in a script)
try:
    # File paths (adjust as needed)
    excel_file = "TESTE.xlsx"  # Example file name for the Excel input
    catmat_file = "CATMAT_nv2.json"
    catser_file = "CATSER_nv2.json"
    # Load data
    df_items, catmat, catser = load_data(excel_file, catmat_file, catser_file)
    # Prepare catalog texts for embeddings
    catmat_texts, catmat_meta, catser_texts, catser_meta = prepare_catalog_entries(catmat, catser)
    # Embed catalog categories (to build our reference vectors database)
    catmat_embeddings = get_embeddings(catmat_texts)
    catser_embeddings = get_embeddings(catser_texts)
    logger.info("Catalog categories embedded successfully.")
    # Classify each item from the Excel
    df_output = classify_items(df_items, catmat_embeddings, catmat_meta, catser_embeddings, catser_meta, top_n=5)
    # Save or display the output
    df_output.to_csv("classification_results.csv", index=False)
    logger.info(f"Classification completed. Results saved to classification_results.csv")
except Exception as e:
    logger.error(f"Pipeline failed: {e}")
