"""
gvg_search_utils_v3.py
Módulo utilitário INTELIGENTE para funções de busca com separação automática de consultas
- Herda TODAS as funcionalidades do gvg_search_utils_v2
- Adiciona processamento inteligente de consultas com OpenAI Assistant
- Separação automática entre termos de busca e condicionantes SQL
- Integração transparente com sistema existente v9
- Preserva compatibilidade total com código legado
"""

# Importar TUDO do módulo v2 para manter compatibilidade
from gvg_search_utils_v2 import *
import json
import time
import gvg_pre_processing_v3 as preprocessor
from openai import OpenAI

# Configurações específicas para v3
ENABLE_INTELLIGENT_PROCESSING = True  # Flag para ativar/desativar processamento inteligente
DEBUG_INTELLIGENT_QUERIES = False     # Flag para debug das consultas processadas

# Configurações do Filtro de Relevância
ENABLE_RELEVANCE_FILTER = False        # Flag para ativar/desativar filtro de relevância
RELEVANCE_FILTER_ASSISTANT_ID = "asst_XmsefQEKbuVWu51uNST7kpYT"  # ID do Assistant
DEBUG_RELEVANCE_FILTER = False         # Flag para debug do filtro de relevância
TRUNCATE_DESCRIPTIONS_AT_SEPARATOR = True  # Flag para truncar descrições no primeiro " :: "

# Cliente OpenAI global
try:
    openai_client = OpenAI(api_key="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")
    # Thread será criada quando necessário
    relevance_thread = None
    RELEVANCE_FILTER_AVAILABLE = True
except Exception as e:
    print(f"⚠️ OpenAI não configurado para Filtro de Relevância: {e}")
    openai_client = None
    relevance_thread = None
    RELEVANCE_FILTER_AVAILABLE = False

# ====================================================================================
# FUNÇÕES GENÉRICAS PARA INTERAÇÃO COM OPENAI ASSISTANT
# ====================================================================================

def call_openai_assistant(assistant_id, thread_id, message_content, max_wait_time=30):
    """
    Função genérica para chamar um Assistant da OpenAI
    
    Args:
        assistant_id (str): ID do Assistant
        thread_id (str): ID do Thread
        message_content (str): Conteúdo da mensagem
        max_wait_time (int): Tempo máximo de espera em segundos
        
    Returns:
        str: Resposta do Assistant ou None se erro
    """
    if not openai_client:
        raise Exception("Cliente OpenAI não disponível")
    
    try:
        # Enviar mensagem para o thread
        openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_content
        )
        
        # Executar Assistant
        run = openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Aguardar conclusão
        response_content = poll_assistant_run(thread_id, run.id, max_wait_time)
        return response_content
        
    except Exception as e:
        raise Exception(f"Erro ao chamar Assistant {assistant_id}: {str(e)}")

def poll_assistant_run(thread_id, run_id, max_wait_time=10):
    """
    Aguarda a conclusão de um run do Assistant e retorna a resposta
    
    Args:
        thread_id (str): ID do Thread
        run_id (str): ID do Run
        max_wait_time (int): Tempo máximo de espera em segundos (reduzido para 10s)
        
    Returns:
        str: Conteúdo da resposta do Assistant
    """
    if not openai_client:
        raise Exception("Cliente OpenAI não disponível")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        
        if run.status == 'completed':
            # Buscar última mensagem do assistant
            messages = openai_client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=1
            )
            
            if messages.data and messages.data[0].role == 'assistant':
                content = messages.data[0].content[0].text.value
                return content
                
        elif run.status in ['failed', 'cancelled', 'expired']:
            raise Exception(f"Run falhou com status: {run.status}")
            
        time.sleep(1)
    
    raise Exception("Timeout aguardando resposta do Assistant")

def get_relevance_thread():
    """
    Retorna a thread do filtro de relevância, criando-a se necessário
    
    Returns:
        thread: Thread do OpenAI Assistant ou None se não disponível
    """
    global relevance_thread
    
    if not RELEVANCE_FILTER_AVAILABLE or not openai_client:
        return None
        
    if relevance_thread is None:
        try:
            relevance_thread = openai_client.beta.threads.create()
        except Exception as e:
            print(f"❌ Erro ao criar thread de relevância: {e}")
            return None
            
    return relevance_thread

# ====================================================================================
# FUNÇÕES DO FILTRO DE RELEVÂNCIA
# ====================================================================================

def apply_relevance_filter(results, query, search_metadata=None):
    """
    Aplica filtro de relevância usando OpenAI Assistant nos resultados de busca
    
    Args:
        results (list): Lista de resultados da busca
        query (str): Query original da busca
        search_metadata (dict): Metadados da busca (opcional)
        
    Returns:
        tuple: (filtered_results, filter_info) - resultados filtrados e informações do filtro
    """
    if not ENABLE_RELEVANCE_FILTER or not RELEVANCE_FILTER_AVAILABLE:
        # Retornar resultados originais se filtro desabilitado
        return results, {
            'filter_applied': False,
            'reason': 'Filtro de relevância desabilitado ou não disponível',
            'original_count': len(results),
            'filtered_count': len(results)
        }
    
    if not results:
        return results, {
            'filter_applied': False,
            'reason': 'Nenhum resultado para filtrar',
            'original_count': 0,
            'filtered_count': 0
        }
    
    try:
        # Preparar JSON de entrada para o Assistant
        input_json = prepare_relevance_filter_input(results, query, search_metadata)
        
        if DEBUG_RELEVANCE_FILTER:
            print("🔍 FILTRO DE RELEVÂNCIA - Input JSON:")
            print(f"Query: {query}")
            print(f"Total resultados: {len(results)}")
        
        # Chamar Assistant de Relevância
        thread = get_relevance_thread()
        if not thread:
            return results, {
                'filter_applied': False,
                'reason': 'Thread de relevância não disponível',
                'original_count': len(results),
                'filtered_count': len(results)
            }
            
        response = call_openai_assistant(
            assistant_id=RELEVANCE_FILTER_ASSISTANT_ID,
            thread_id=thread.id,
            message_content=json.dumps(input_json, ensure_ascii=False, indent=2),
            max_wait_time=20  # Reduzido para 20s devido ao formato otimizado
        )
        
        # Processar resposta do Assistant
        filtered_results = process_relevance_filter_response(response, results)
        
        filter_info = {
            'filter_applied': True,
            'original_count': len(results),
            'filtered_count': len(filtered_results),
            'reduction_percentage': round((1 - len(filtered_results) / len(results)) * 100, 1) if results else 0
        }
        
        if DEBUG_RELEVANCE_FILTER:
            print(f"✅ FILTRO DE RELEVÂNCIA - Processado:")
            print(f"Original: {filter_info['original_count']} → Filtrado: {filter_info['filtered_count']} (-{filter_info['reduction_percentage']}%)")
        
        return filtered_results, filter_info
        
    except Exception as e:
        
        # Em caso de erro, retornar resultados originais
        return results, {
            'filter_applied': False,
            'reason': f'Erro no processamento: {str(e)}',
            'original_count': len(results),
            'filtered_count': len(results)
        }

def prepare_relevance_filter_input(results, query, search_metadata=None):
    """
    Prepara o JSON simplificado de entrada para o Assistant de Relevância (v2)
    Envia apenas query e descrições para reduzir tamanho da mensagem
    
    Args:
        results (list): Resultados da busca
        query (str): Query original
        search_metadata (dict): Metadados da busca (não usado na v2)
        
    Returns:
        dict: JSON simplificado para o Assistant
    """
    # Extrair apenas descrições e posições para formato simplificado
    descriptions = []
    for i, result in enumerate(results, 1):
        details = result.get('details', {})
        description = details.get('descricaocompleta', '')
        
        # Aplicar truncamento se flag estiver ativada
        if TRUNCATE_DESCRIPTIONS_AT_SEPARATOR and ' :: ' in description:
            description = description.split(' :: ')[0].strip()
        
        descriptions.append({
            'rank': i,  # Posição sequencial 1, 2, 3...
            'description': description
        })
    
    return {
        'query': query,
        'descriptions': descriptions
    }

def process_relevance_filter_response(response, original_results):
    """
    Processa a resposta simplificada do Assistant de Relevância (v2)
    Recebe lista de posições e retorna apenas os resultados nessas posições
    
    Args:
        response (str): Resposta do Assistant (lista de posições)
        original_results (list): Resultados originais da busca
        
    Returns:
        list: Resultados filtrados mantendo formato original
    """
    try:
        # Extrair lista de posições da resposta
        positions_json = extract_json_from_assistant_response(response)
        relevant_positions = json.loads(positions_json)
        
        # Validar que é uma lista
        if not isinstance(relevant_positions, list):
            raise ValueError("Resposta do Assistant deve ser uma lista de posições")
        
        # Filtrar resultados baseado nas posições (convertendo para índice 0-based)
        filtered_results = []
        for position in relevant_positions:
            if isinstance(position, int) and 1 <= position <= len(original_results):
                # position é 1-based, converter para 0-based
                result_index = position - 1
                filtered_results.append(original_results[result_index])
        
        if DEBUG_RELEVANCE_FILTER:
            print(f"🔍 Posições relevantes recebidas: {relevant_positions}")
            print(f"🔍 Resultados filtrados: {len(filtered_results)} de {len(original_results)}")
        
        return filtered_results
        
    except Exception as e:
        print(f"Erro ao processar resposta do Filtro de Relevância: {e}")
        print(f"Resposta recebida: {response[:200]}...")
        # Em caso de erro, retornar resultados originais
        return original_results

def extract_json_from_assistant_response(response):
    """
    Extrai JSON da resposta do Assistant (remove markdown se presente)
    Otimizada para resposta simplificada v2 (lista de posições)
    
    Args:
        response (str): Resposta do Assistant
        
    Returns:
        str: JSON extraído
    """
    # Limpar resposta
    response = response.strip()
    
    # Tentar extrair JSON do conteúdo (pode vir com markdown)
    if "```json" in response:
        json_content = response.split("```json")[1].split("```")[0].strip()
    elif "```" in response:
        json_content = response.split("```")[1].split("```")[0].strip()
    else:
        json_content = response
    
    # Para v2, esperamos uma lista simples como [1, 3, 5]
    # Se não começar com [, pode ser uma resposta sem formatação
    if not json_content.startswith('['):
        # Tentar encontrar lista na resposta
        import re
        list_match = re.search(r'\[[\d\s,]*\]', json_content)
        if list_match:
            json_content = list_match.group()
        else:
            # Se não encontrou lista, retornar lista vazia
            json_content = "[]"
    
    return json_content

# ====================================================================================
# FUNÇÕES DE CONTROLE DO FILTRO DE RELEVÂNCIA
# ====================================================================================

def toggle_relevance_filter(enable=True):
    """
    Ativa ou desativa o filtro de relevância globalmente
    
    Args:
        enable (bool): True para ativar, False para desativar
    """
    global ENABLE_RELEVANCE_FILTER
    ENABLE_RELEVANCE_FILTER = enable

def toggle_relevance_filter_debug(enable=True):
    """
    Ativa ou desativa o debug do filtro de relevância
    
    Args:
        enable (bool): True para ativar, False para desativar
    """
    global DEBUG_RELEVANCE_FILTER
    DEBUG_RELEVANCE_FILTER = enable

def toggle_description_truncation(enable=True):
    """
    Ativa ou desativa o truncamento de descrições no primeiro " :: "
    
    Args:
        enable (bool): True para truncar, False para enviar descrição completa
    """
    global TRUNCATE_DESCRIPTIONS_AT_SEPARATOR
    TRUNCATE_DESCRIPTIONS_AT_SEPARATOR = enable

def get_relevance_filter_status():
    """
    Retorna o status atual do filtro de relevância
    
    Returns:
        dict: Status das configurações do filtro
    """
    return {
        'relevance_filter_enabled': ENABLE_RELEVANCE_FILTER,
        'relevance_filter_available': RELEVANCE_FILTER_AVAILABLE,
        'debug_enabled': DEBUG_RELEVANCE_FILTER,
        'truncate_descriptions': TRUNCATE_DESCRIPTIONS_AT_SEPARATOR,
        'assistant_id': RELEVANCE_FILTER_ASSISTANT_ID if RELEVANCE_FILTER_AVAILABLE else None
    }

# ====================================================================================
# FUNÇÕES INTELIGENTES ATUALIZADAS COM FILTRO DE RELEVÂNCIA
# ====================================================================================

def intelligent_semantic_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, 
                               filter_expired=DEFAULT_FILTER_EXPIRED, use_negation=DEFAULT_USE_NEGATION,
                               enable_intelligent=ENABLE_INTELLIGENT_PROCESSING):
    """
    Busca semântica INTELIGENTE com separação automática de consultas.
    
    Args:
        query_text (str): Texto da consulta
        limit (int): Limite de resultados
        min_results (int): Mínimo de resultados
        filter_expired (bool): Filtrar contratações encerradas
        use_negation (bool): Usar negation embeddings
        enable_intelligent (bool): Ativar processamento inteligente
    
    Returns:
        tuple: (results, confidence) com resultados e nível de confiança
    """
    if not enable_intelligent:
        # Fallback para versão v2 original
        results, confidence = semantic_search(query_text, limit, min_results, filter_expired, use_negation)
        
        # Aplicar filtro de relevância se ativo
        if ENABLE_RELEVANCE_FILTER:
            search_metadata = {
                'search_type': 'Semântica',
                'search_approach': 'Direta',
                'sort_mode': 'Similaridade'
            }
            results, filter_info = apply_relevance_filter(results, query_text, search_metadata)
        
        return results, confidence
    
    try:
        # Processar consulta inteligentemente
        processed = preprocessor.process_search_query(query_text)
        
        if DEBUG_INTELLIGENT_QUERIES:
            print("🤖 PROCESSAMENTO INTELIGENTE:")
            print(preprocessor.query_processor.format_for_display(processed))
            print()
        
        # Usar apenas os termos de busca para a busca semântica
        search_terms = processed['search_terms']
        sql_conditions = processed['sql_conditions']
        requires_join = processed['requires_join_embeddings']
        
        # Executar busca semântica com termos limpos
        connection = create_connection()
        cursor = connection.cursor()
        
        try:
            # Escolher tipo de embedding baseado na configuração
            if use_negation:
                query_embedding = get_negation_embedding(search_terms)
            else:
                query_embedding = get_embedding(search_terms)
                
            query_embedding_list = query_embedding.tolist()
            
            # Construir consulta base
            base_query = """
            SELECT 
                c.numeroControlePNCP,
                c.anoCompra,
                c.descricaoCompleta,
                c.valorTotalHomologado,
                c.valorTotalEstimado,
                c.dataAberturaProposta,
                c.dataEncerramentoProposta,
                c.dataInclusao,
                c.linkSistemaOrigem,
                c.modalidadeId,
                c.modalidadeNome,
                c.modaDisputaId,
                c.modaDisputaNome,
                c.usuarioNome,
                c.orgaoEntidade_poderId,
                c.orgaoEntidade_esferaId,
                c.unidadeOrgao_ufSigla,
                c.unidadeOrgao_municipioNome,
                c.unidadeOrgao_nomeUnidade,
                c.orgaoEntidade_razaosocial,
                1 - (e.embedding_vector <=> %s::vector) AS similarity
            FROM 
                contratacoes c
            JOIN 
                contratacoes_embeddings e ON c.numeroControlePNCP = e.numeroControlePNCP
            WHERE 
                e.embedding_vector IS NOT NULL
            """

            # Adicionar filtro de expiração se ativo
            if filter_expired:
                base_query += " AND c.dataEncerramentoProposta >= CURRENT_DATE"

            # Adicionar condições SQL dinâmicas se existirem
            if sql_conditions:
                enhanced_query = preprocessor.enhance_sql_query(base_query, sql_conditions, requires_join)
            else:
                enhanced_query = base_query

            enhanced_query += """
            ORDER BY 
                similarity DESC
            LIMIT %s
            """

            cursor.execute(enhanced_query, (query_embedding_list, limit))
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            
            formatted_results = []
            for i, row in enumerate(results):
                result_dict = dict(zip(column_names, row))
                
                # Formatar datas para string
                if 'datainclusao' in result_dict:
                    result_dict['datainclusao'] = format_date(result_dict['datainclusao'])
                if 'dataaberturaproposta' in result_dict:
                    result_dict['dataaberturaproposta'] = format_date(result_dict['dataaberturaproposta'])
                if 'dataencerramentoproposta' in result_dict:
                    result_dict['dataencerramentoproposta'] = format_date(result_dict['dataencerramentoproposta'])
                
                # Adicionar informações do processamento inteligente
                result_dict['intelligent_processing'] = {
                    'original_query': processed['original_query'],
                    'processed_terms': processed['search_terms'],
                    'applied_conditions': len(sql_conditions),
                    'explanation': processed['explanation']
                }
                
                formatted_results.append({
                    "rank": i + 1,
                    "id": result_dict["numerocontrolepncp"],
                    "similarity": float(result_dict["similarity"]),
                    "details": result_dict
                })
            
            # Aplicar filtro de relevância se habilitado
            if ENABLE_RELEVANCE_FILTER:
                search_metadata = {
                    'search_type': 'Semântica (Inteligente)',
                    'search_approach': 'Direta',
                    'sort_mode': 'Similaridade'
                }
                filtered_results, filter_info = apply_relevance_filter(formatted_results, query_text, search_metadata)
            else:
                filtered_results = formatted_results
            
            confidence = calculate_confidence([r["similarity"] for r in filtered_results])
            return filtered_results, confidence
        
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e:
        print(f"Erro no processamento inteligente: {e}")
        print("Revertendo para busca semântica tradicional...")
        # Fallback para versão v2 em caso de erro
        results, confidence = semantic_search(query_text, limit, min_results, filter_expired, use_negation)
        
        # Aplicar filtro de relevância se ativo mesmo no fallback
        if ENABLE_RELEVANCE_FILTER:
            search_metadata = {
                'search_type': 'Semântica (Fallback)',
                'search_approach': 'Direta',
                'sort_mode': 'Similaridade'
            }
            results, filter_info = apply_relevance_filter(results, query_text, search_metadata)
        
        return results, confidence

def intelligent_keyword_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, 
                              filter_expired=DEFAULT_FILTER_EXPIRED,
                              enable_intelligent=ENABLE_INTELLIGENT_PROCESSING):
    """
    Busca por palavras-chave INTELIGENTE com separação automática de consultas.
    
    Args:
        query_text (str): Texto da consulta
        limit (int): Limite de resultados
        min_results (int): Mínimo de resultados
        filter_expired (bool): Filtrar contratações encerradas
        enable_intelligent (bool): Ativar processamento inteligente
    
    Returns:
        tuple: (results, confidence) com resultados e nível de confiança
    """
    if not enable_intelligent:
        # Fallback para versão v2 original
        results, confidence = keyword_search(query_text, limit, min_results, filter_expired)
        
        # Aplicar filtro de relevância se ativo
        if ENABLE_RELEVANCE_FILTER:
            search_metadata = {
                'search_type': 'Palavras-chave',
                'search_approach': 'Direta',
                'sort_mode': 'Relevância'
            }
            results, filter_info = apply_relevance_filter(results, query_text, search_metadata)
        
        return results, confidence
    
    try:
        # Processar consulta inteligentemente
        processed = preprocessor.process_search_query(query_text)
        
        if DEBUG_INTELLIGENT_QUERIES:
            print("🤖 PROCESSAMENTO INTELIGENTE:")
            print(preprocessor.query_processor.format_for_display(processed))
            print()
        
        # Usar apenas os termos de busca para a busca por palavras-chave
        search_terms = processed['search_terms']
        sql_conditions = processed['sql_conditions']
        requires_join = processed['requires_join_embeddings']
        
        # Executar busca por palavras-chave com termos limpos
        connection = create_connection()
        cursor = connection.cursor()
        
        try:
            tsquery = " & ".join(search_terms.split())
            tsquery_prefix = ":* & ".join(search_terms.split()) + ":*"
            
            # Construir consulta base
            base_query = """
            SELECT 
                c.numeroControlePNCP,
                c.anoCompra,
                c.descricaoCompleta,
                c.valorTotalHomologado,
                c.valorTotalEstimado,
                c.dataAberturaProposta,
                c.dataEncerramentoProposta,
                c.dataInclusao,
                c.linkSistemaOrigem,
                c.modalidadeId,
                c.modalidadeNome,
                c.modaDisputaId,
                c.modaDisputaNome,
                c.usuarioNome,
                c.orgaoEntidade_poderId,
                c.orgaoEntidade_esferaId,
                c.unidadeOrgao_ufSigla,
                c.unidadeOrgao_municipioNome,
                c.unidadeOrgao_nomeUnidade,
                c.orgaoEntidade_razaosocial,
                ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) AS rank,
                ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) AS rank_prefix
            FROM 
                contratacoes c
            WHERE 
                (to_tsvector('portuguese', c.descricaoCompleta) @@ to_tsquery('portuguese', %s)
                OR to_tsvector('portuguese', c.descricaoCompleta) @@ to_tsquery('portuguese', %s))
            """

            # Adicionar filtro de expiração se ativo
            if filter_expired:
                base_query += " AND c.dataEncerramentoProposta >= CURRENT_DATE"

            # Adicionar condições SQL dinâmicas se existirem
            if sql_conditions:
                enhanced_query = preprocessor.enhance_sql_query(base_query, sql_conditions, requires_join)
            else:
                enhanced_query = base_query

            enhanced_query += """
            ORDER BY 
                (ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) * 0.7 + 
                ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)) * 0.3) DESC
            LIMIT %s
            """
            
            cursor.execute(enhanced_query, (
                tsquery, tsquery_prefix, tsquery, tsquery_prefix, 
                tsquery, tsquery_prefix, limit
            ))
            
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            
            formatted_results = []
            for i, row in enumerate(results):
                result_dict = dict(zip(column_names, row))
                score = float(result_dict["rank"]) * 0.7 + float(result_dict["rank_prefix"]) * 0.3
                max_possible_score = len(search_terms.split()) * 0.1
                normalized_score = min(score / max_possible_score, 1.0)
                
                # Formatar datas para string
                if 'datainclusao' in result_dict:
                    result_dict['datainclusao'] = format_date(result_dict['datainclusao'])
                if 'dataaberturaproposta' in result_dict:
                    result_dict['dataaberturaproposta'] = format_date(result_dict['dataaberturaproposta'])
                if 'dataencerramentoproposta' in result_dict:
                    result_dict['dataencerramentoproposta'] = format_date(result_dict['dataencerramentoproposta'])
                
                # Adicionar informações do processamento inteligente
                result_dict['intelligent_processing'] = {
                    'original_query': processed['original_query'],
                    'processed_terms': processed['search_terms'],
                    'applied_conditions': len(sql_conditions),
                    'explanation': processed['explanation']
                }
                
                formatted_results.append({
                    "rank": i + 1,
                    "id": result_dict["numerocontrolepncp"],
                    "similarity": normalized_score,
                    "details": result_dict
                })
            
            # Aplicar filtro de relevância se habilitado
            if ENABLE_RELEVANCE_FILTER:
                search_metadata = {
                    'search_type': 'Palavras-chave (Inteligente)',
                    'search_approach': 'Direta',
                    'sort_mode': 'Relevância'
                }
                filtered_results, filter_info = apply_relevance_filter(formatted_results, query_text, search_metadata)
            else:
                filtered_results = formatted_results
            
            confidence = calculate_confidence([r["similarity"] for r in filtered_results])
            return filtered_results, confidence
        
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e:
        print(f"Erro no processamento inteligente: {e}")
        print("Revertendo para busca por palavras-chave tradicional...")
        # Fallback para versão v2 em caso de erro
        results, confidence = keyword_search(query_text, limit, min_results, filter_expired)
        
        # Aplicar filtro de relevância se ativo mesmo no fallback
        if ENABLE_RELEVANCE_FILTER:
            search_metadata = {
                'search_type': 'Palavras-chave (Fallback)',
                'search_approach': 'Direta',
                'sort_mode': 'Relevância'
            }
            results, filter_info = apply_relevance_filter(results, query_text, search_metadata)
        
        return results, confidence

def intelligent_hybrid_search(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, 
                             semantic_weight=SEMANTIC_WEIGHT, filter_expired=DEFAULT_FILTER_EXPIRED, 
                             use_negation=DEFAULT_USE_NEGATION, enable_intelligent=ENABLE_INTELLIGENT_PROCESSING):
    """
    Busca híbrida INTELIGENTE com separação automática de consultas.
    
    Args:
        query_text (str): Texto da consulta
        limit (int): Limite de resultados
        min_results (int): Mínimo de resultados
        semantic_weight (float): Peso da busca semântica
        filter_expired (bool): Filtrar contratações encerradas
        use_negation (bool): Usar negation embeddings
        enable_intelligent (bool): Ativar processamento inteligente
    
    Returns:
        tuple: (results, confidence) com resultados e nível de confiança
    """
    if not enable_intelligent:
        # Fallback para versão v2 original
        results, confidence = hybrid_search(query_text, limit, min_results, semantic_weight, filter_expired, use_negation)
        
        # Aplicar filtro de relevância se ativo
        if ENABLE_RELEVANCE_FILTER:
            search_metadata = {
                'search_type': 'Híbrida',
                'search_approach': 'Direta',
                'sort_mode': 'Híbrida'
            }
            results, filter_info = apply_relevance_filter(results, query_text, search_metadata)
        
        return results, confidence
    
    try:
        # Processar consulta inteligentemente
        processed = preprocessor.process_search_query(query_text)
        
        if DEBUG_INTELLIGENT_QUERIES:
            print("🤖 PROCESSAMENTO INTELIGENTE:")
            print(preprocessor.query_processor.format_for_display(processed))
            print()
        
        # Usar apenas os termos de busca para a busca híbrida
        search_terms = processed['search_terms']
        sql_conditions = processed['sql_conditions']
        requires_join = processed['requires_join_embeddings']
        
        # Executar busca híbrida com termos limpos
        connection = create_connection()
        cursor = connection.cursor()
        
        try:
            # Escolher tipo de embedding baseado na configuração
            if use_negation:
                query_embedding = get_negation_embedding(search_terms)
            else:
                query_embedding = get_embedding(search_terms)
                
            query_embedding_list = query_embedding.tolist()
            
            tsquery = " & ".join(search_terms.split())
            tsquery_prefix = ":* & ".join(search_terms.split()) + ":*"
            
            # Construir consulta base
            base_query = """
            SELECT 
                c.numeroControlePNCP,
                c.anoCompra,
                c.descricaoCompleta,
                c.valorTotalHomologado,
                c.valorTotalEstimado,
                c.dataAberturaProposta,
                c.dataEncerramentoProposta,
                c.dataInclusao,
                c.linkSistemaOrigem,
                c.modalidadeId,
                c.modalidadeNome,
                c.modaDisputaId,
                c.modaDisputaNome,
                c.usuarioNome,
                c.orgaoEntidade_poderId,
                c.orgaoEntidade_esferaId,
                c.unidadeOrgao_ufSigla,
                c.unidadeOrgao_municipioNome,
                c.unidadeOrgao_nomeUnidade,
                c.orgaoEntidade_razaosocial,
                (1 - (e.embedding_vector <=> %s::vector)) AS semantic_score,
                COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) AS keyword_score,
                COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) AS keyword_prefix_score,
                (
                    %s * (1 - (e.embedding_vector <=> %s::vector)) + 
                    (1 - %s) * (
                        LEAST(
                            (0.7 * COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0) + 
                            0.3 * COALESCE(ts_rank(to_tsvector('portuguese', c.descricaoCompleta), to_tsquery('portuguese', %s)), 0)) 
                            / (%s), 1.0
                        )
                    )
                ) AS combined_score
            FROM 
                contratacoes c
            JOIN 
                contratacoes_embeddings e ON c.numeroControlePNCP = e.numeroControlePNCP
            WHERE 
                e.embedding_vector IS NOT NULL
            """

            # Adicionar filtro de expiração se ativo
            if filter_expired:
                base_query += " AND c.dataEncerramentoProposta >= CURRENT_DATE"

            # Adicionar condições SQL dinâmicas se existirem
            if sql_conditions:
                enhanced_query = preprocessor.enhance_sql_query(base_query, sql_conditions, requires_join)
            else:
                enhanced_query = base_query

            enhanced_query += """
            ORDER BY 
                combined_score DESC
            LIMIT %s
            """

            max_possible_keyword_score = len(search_terms.split()) * 0.1
            
            cursor.execute(enhanced_query, (
                query_embedding_list, tsquery, tsquery_prefix,
                semantic_weight, query_embedding_list, semantic_weight,
                tsquery, tsquery_prefix, max_possible_keyword_score, limit
            ))
            
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            
            formatted_results = []
            for i, row in enumerate(results):
                result_dict = dict(zip(column_names, row))
                
                # Formatar datas para string
                if 'datainclusao' in result_dict:
                    result_dict['datainclusao'] = format_date(result_dict['datainclusao'])
                if 'dataaberturaproposta' in result_dict:
                    result_dict['dataaberturaproposta'] = format_date(result_dict['dataaberturaproposta'])
                if 'dataencerramentoproposta' in result_dict:
                    result_dict['dataencerramentoproposta'] = format_date(result_dict['dataencerramentoproposta'])
                
                # Adicionar informações do processamento inteligente
                result_dict['intelligent_processing'] = {
                    'original_query': processed['original_query'],
                    'processed_terms': processed['search_terms'],
                    'applied_conditions': len(sql_conditions),
                    'explanation': processed['explanation']
                }
                
                formatted_results.append({
                    "rank": i + 1,
                    "id": result_dict["numerocontrolepncp"],
                    "similarity": float(result_dict["combined_score"]),
                    "semantic_score": float(result_dict["semantic_score"]),
                    "keyword_score": float(result_dict["keyword_score"]) if result_dict["keyword_score"] else 0,
                    "details": result_dict
                })
            
            # Aplicar filtro de relevância se habilitado
            if ENABLE_RELEVANCE_FILTER:
                search_metadata = {
                    'search_type': 'Híbrida (Inteligente)',
                    'search_approach': 'Direta',
                    'sort_mode': 'Híbrida'
                }
                filtered_results, filter_info = apply_relevance_filter(formatted_results, query_text, search_metadata)
            else:
                filtered_results = formatted_results
            
            confidence = calculate_confidence([r["similarity"] for r in filtered_results])
            return filtered_results, confidence
        
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e:
        print(f"Erro no processamento inteligente: {e}")
        print("Revertendo para busca híbrida tradicional...")
        # Fallback para versão v2 em caso de erro
        results, confidence = hybrid_search(query_text, limit, min_results, semantic_weight, filter_expired, use_negation)
        
        # Aplicar filtro de relevância se ativo mesmo no fallback
        if ENABLE_RELEVANCE_FILTER:
            search_metadata = {
                'search_type': 'Híbrida (Fallback)',
                'search_approach': 'Direta',
                'sort_mode': 'Híbrida'
            }
            results, filter_info = apply_relevance_filter(results, query_text, search_metadata)
        
        return results, confidence

def toggle_intelligent_processing(enable: bool = True):
    """
    Ativa ou desativa o processamento inteligente globalmente.
    
    Args:
        enable (bool): True para ativar, False para desativar
    """
    global ENABLE_INTELLIGENT_PROCESSING
    ENABLE_INTELLIGENT_PROCESSING = enable

def toggle_intelligent_debug(enable: bool = True):
    """
    Ativa ou desativa o debug das consultas inteligentes.
    
    Args:
        enable (bool): True para ativar, False para desativar
    """
    global DEBUG_INTELLIGENT_QUERIES
    DEBUG_INTELLIGENT_QUERIES = enable

def get_intelligent_status():
    """
    Retorna o status atual do processamento inteligente.
    
    Returns:
        dict: Status das configurações inteligentes
    """
    return {
        'intelligent_processing_enabled': ENABLE_INTELLIGENT_PROCESSING,
        'debug_enabled': DEBUG_INTELLIGENT_QUERIES,
        'preprocessor_available': True,
        'assistant_id': preprocessor.ASSISTANT_ID
    }

# Funções de compatibilidade que redirecionam para as versões inteligentes
# Estas funções mantêm a mesma assinatura das v2, mas usam processamento inteligente por padrão

def semantic_search_v3(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, 
                       filter_expired=DEFAULT_FILTER_EXPIRED, use_negation=DEFAULT_USE_NEGATION):
    """Wrapper para busca semântica inteligente mantendo compatibilidade v2"""
    return intelligent_semantic_search(query_text, limit, min_results, filter_expired, use_negation, True)

def keyword_search_v3(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, 
                      filter_expired=DEFAULT_FILTER_EXPIRED):
    """Wrapper para busca por palavras-chave inteligente mantendo compatibilidade v2"""
    return intelligent_keyword_search(query_text, limit, min_results, filter_expired, True)

def hybrid_search_v3(query_text, limit=MAX_RESULTS, min_results=MIN_RESULTS, 
                     semantic_weight=SEMANTIC_WEIGHT, filter_expired=DEFAULT_FILTER_EXPIRED, 
                     use_negation=DEFAULT_USE_NEGATION):
    """Wrapper para busca híbrida inteligente mantendo compatibilidade v2"""
    return intelligent_hybrid_search(query_text, limit, min_results, semantic_weight, filter_expired, use_negation, True)

# Função para testar as novas capacidades inteligentes
def test_intelligent_search():
    """Testa as funcionalidades de busca inteligente"""
    test_queries = [
        "material escolar -- uniformes no ES acima de 500 mil",
        "equipamentos médicos nordeste 2024 bem categorizados",
        "serviços de limpeza federal entre 100 mil e 1 milhão"
    ]
    
    print("🧪 TESTANDO BUSCA INTELIGENTE\n")
    
    # Ativar debug temporariamente
    toggle_intelligent_debug(True)
    
    for i, query in enumerate(test_queries, 1):
        print(f"=== TESTE {i}: {query} ===")
        
        try:
            # Testar busca semântica inteligente
            print("🔍 Busca Semântica Inteligente:")
            results, confidence = intelligent_semantic_search(query, limit=3)
            print(f"Resultados: {len(results)}, Confiança: {confidence:.2f}%")
            
            if results:
                print(f"Primeiro resultado: {results[0]['details']['descricaocompleta'][:100]}...")
                if 'intelligent_processing' in results[0]['details']:
                    print(f"Processamento: {results[0]['details']['intelligent_processing']['explanation']}")
            
            print()
            
        except Exception as e:
            print(f"Erro no teste {i}: {e}\n")
    
    # Desativar debug
    toggle_intelligent_debug(False)
    print("✅ Testes concluídos!")

if __name__ == "__main__":
    # Executar testes se o módulo for chamado diretamente
    test_intelligent_search()
