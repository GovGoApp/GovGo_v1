"""
gvg_pre_processing.py
Módulo para pré-processamento de texto configurável
- Normalização e limpeza de texto com opções granulares
- Remoção de caracteres especiais, acentos e stopwords
- Lemmatização e transformações de case
- Gestão de modelos de embedding por índice
- Geração automática de nomes de arquivo para embeddings
- Parsing de configurações de pré-processamento
"""

import re
import unidecode
import nltk
import os
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Garantir que os recursos NLTK necessários estão disponíveis
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Mapeamento de modelos para índices
EMBEDDING_MODELS = {
    0: "text-embedding-3-large",
    1: "text-embedding-3-small",
    2: "text-embedding-ada-002"
}

# Mapeamento reverso de nomes de modelos para índices
EMBEDDING_MODELS_REVERSE = {v: k for k, v in EMBEDDING_MODELS.items()}

def clean_illegal_chars(text):
    """
    Remove caracteres ilegais de controle (0x00-0x1F) de uma string.
    
    Args:
        text: String ou qualquer outro tipo de dado
        
    Returns:
        str: String limpa ou o valor original se não for string
    """
    if isinstance(text, str):
        return re.sub(r'[\x00-\x1F]+', ' ', text)
    return text

def gvg_create_embedding_filename(base_path, model_index, preproc_options):
    """
    Cria o nome do arquivo de embeddings a partir do índice do modelo e opções de pré-processamento.
    
    Args:
        base_path (str): Caminho base onde o arquivo será salvo
        model_index (int): Índice do modelo (0, 1, 2)
        preproc_options (dict): Dicionário com opções de pré-processamento
        
    Returns:
        str: Nome completo do arquivo de embeddings
    """
    # Verificar se o modelo existe
    if model_index not in EMBEDDING_MODELS:
        raise ValueError(f"Índice de modelo inválido: {model_index}. Use 0, 1 ou 2.")
    
    # Criar código para as opções de pré-processamento
    preproc_code = (
        f"{'A' if preproc_options['remove_accents'] else 'a'}"
        f"{'X' if preproc_options['remove_special_chars'] else 'x'}"
        f"{'S' if preproc_options['keep_separators'] else 's'}"
        f"{'C' if preproc_options['case'] == 'upper' else 'c' if preproc_options['case'] == 'lower' else 'o'}"
        f"{'W' if preproc_options['remove_stopwords'] else 'w'}"
        f"{'L' if preproc_options['lemmatize'] else 'l'}"
    )
    
    
    # Construir o nome do arquivo usando o índice do modelo (0, 1, 2) em vez do nome
    return os.path.join(base_path, f"GvG_embeddings_{model_index}_{preproc_code}.pkl")

def gvg_parse_embedding_filename(filename):
    """
    Analisa um nome de arquivo de embeddings para extrair o modelo e as opções de pré-processamento.
    
    Args:
        filename (str): Nome do arquivo de embeddings
        
    Returns:
        tuple: (model_name, model_index, preproc_options)
    """
    # Extrair o nome base do arquivo (sem caminho)
    basename = os.path.basename(filename)
    
    # Verificar se o formato do nome é válido
    parts = basename.split('_')
    if len(parts) < 3 or not basename.endswith('.pkl'):
        raise ValueError(f"Formato de nome de arquivo inválido: {basename}")
    
    # Extrair o índice do modelo e o código de pré-processamento
    try:
        model_index = int(parts[-2])  # Agora extraímos o índice diretamente
        if model_index not in EMBEDDING_MODELS:
            raise ValueError(f"Índice de modelo inválido: {model_index}")
    except ValueError:
        raise ValueError(f"Índice de modelo não é um número válido: {parts[-2]}")
    
    preproc_code = parts[-1].replace('.pkl', '')
    
    # Obter o nome do modelo a partir do índice
    model_name = EMBEDDING_MODELS[model_index]
    
    # Verificar se o código de pré-processamento tem o formato correto
    if len(preproc_code) != 6:
        raise ValueError(f"Código de pré-processamento inválido: {preproc_code}")
    
    # Extrair as opções de pré-processamento
    preproc_options = {
        "remove_accents": preproc_code[0] == 'A',
        "remove_special_chars": preproc_code[1] == 'X',
        "keep_separators": preproc_code[2] == 'S',
        "case": "upper" if preproc_code[3] == 'C' else "lower" if preproc_code[3] == 'c' else "original",
        "remove_stopwords": preproc_code[4] == 'W',
        "lemmatize": preproc_code[5] == 'L'
    }
    
    return (model_name, model_index, preproc_options)

# GvG_Pre-Processamento de Texto (PP)
def gvg_pre_processing(text, 
           remove_special_chars=True, 
           keep_separators=False, 
           remove_accents=True, 
           case="lower", 
           remove_stopwords=True, 
           lemmatize=True):
    """
    Normaliza e limpa o texto para processamento de acordo com as opções fornecidas.
    """
    # Converter para string se não for
    text = str(text)

    # Limpar caracteres ilegais
    text = clean_illegal_chars(text)

    # Remover acentos se configurado
    if remove_accents:
        text = unidecode.unidecode(text)
    
    # Aplicar transformação de caixa conforme configurado
    if case == 'lower':
        text = text.lower()
    elif case == 'upper':
        text = text.upper()
    # Se 'original', não faz nada
    
    # Remover caracteres especiais conforme configurado
    if remove_special_chars:
        if keep_separators:
            # Definir padrão regex baseado na configuração de caixa e manutenção de acentos
            if remove_accents:
                # Se acentos forem removidos, usar apenas letras ASCII
                if case == 'lower':
                    pattern = r'[^a-z0-9\s:;,.!?_\-]'
                elif case == 'upper':
                    pattern = r'[^A-Z0-9\s:;,.!?_\-]'
                else:  # original
                    pattern = r'[^a-zA-Z0-9\s:;,.!?_\-]'
            else:
                # Se acentos forem mantidos, incluir caracteres acentuados
                if case == 'lower':
                    pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ0-9\s:;,.!?_\-]'
                elif case == 'upper':
                    pattern = r'[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s:;,.!?_\-]'
                else:  # original
                    pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿA-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s:;,.!?_\-]'
            
            # Manter letras, números, espaços e separadores gráficos comuns
            text = re.sub(pattern, '', text)
        else:
            # Padrão para remover tudo exceto letras, números e espaços
            if remove_accents:
                # Se acentos forem removidos, usar apenas letras ASCII
                if case == 'lower':
                    pattern = r'[^a-z0-9\s]'
                elif case == 'upper':
                    pattern = r'[^A-Z0-9\s]'
                else:  # original
                    pattern = r'[^a-zA-Z0-9\s]'
            else:
                # Se acentos forem mantidos, incluir caracteres acentuados
                if case == 'lower':
                    pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ0-9\s]'
                elif case == 'upper':
                    pattern = r'[^A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s]'
                else:  # original
                    pattern = r'[^a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿA-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸ0-9\s]'
            
            # Remover tudo exceto letras, números e espaços
            text = re.sub(pattern, '', text)
    
    # Dividir o texto em palavras
    words = text.split()
    
    # Remover stopwords se configurado
    if remove_stopwords:
        sw = set(stopwords.words('portuguese'))
        # Considerar a caixa das stopwords
        if case == 'lower':
            words = [word for word in words if word.lower() not in sw]
        elif case == 'upper':
            words = [word for word in words if word.lower() not in sw]
        else:  # original
            words = [word for word in words if word.lower() not in sw]
    
    # Aplicar lematização se configurado
    if lemmatize:
        lemmatizer = WordNetLemmatizer()
        words = [lemmatizer.lemmatize(word) for word in words]
    
    return ' '.join(words)