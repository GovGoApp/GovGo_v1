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

# Configurações do Filtro de Relevância - Sistema de 3 Níveis
RELEVANCE_FILTER_LEVEL = 1             # Nível de filtro: 1=sem filtro, 2=flexível, 3=restritivo
DEBUG_RELEVANCE_FILTER = False         # Flag para debug do filtro de relevância
USE_PARTIAL_DESCRIPTION = True         # Flag para descrição parcial (até "::") ou completa

# IDs dos Assistants para cada nível de relevância
RELEVANCE_ASSISTANT_FLEXIBLE = "asst_tfD5oQxSgoGhtqdKQHK9UwRi"      # Nível 2 - Flexível
RELEVANCE_ASSISTANT_RESTRICTIVE = "asst_XmsefQEKbuVWu51uNST7kpYT"    # Nível 3 - Restritivo

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
    # Verificar se o filtro está ativado (nível > 1)
    if RELEVANCE_FILTER_LEVEL == 1 or not RELEVANCE_FILTER_AVAILABLE:
        return results, {
            'filter_applied': False,
            'reason': 'Filtro de relevância desativado (nível 1)' if RELEVANCE_FILTER_LEVEL == 1 else 'OpenAI não disponível',
            'original_count': len(results),
            'filtered_count': len(results),
            'level': RELEVANCE_FILTER_LEVEL
        }
    
    if not results:
        return results, {
            'filter_applied': False,
            'reason': 'Nenhum resultado para filtrar',
            'original_count': 0,
            'filtered_count': 0
        }
    
    try:
        # Obter ID do assistant conforme nível atual
        assistant_id = get_current_assistant_id()
        if not assistant_id:
            return results, {
                'filter_applied': False,
                'reason': 'Assistant ID não definido para este nível',
                'original_count': len(results),
                'filtered_count': len(results),
                'level': RELEVANCE_FILTER_LEVEL
            }
        
        # Preparar entrada SIMPLIFICADA para o Assistant
        input_data = prepare_relevance_filter_input(results, query, search_metadata)
        
        if DEBUG_RELEVANCE_FILTER:
            level_names = {2: "Flexível", 3: "Restritivo"}
            print(f"🔍 FILTRO DE RELEVÂNCIA - Nível {RELEVANCE_FILTER_LEVEL} ({level_names.get(RELEVANCE_FILTER_LEVEL, 'Desconhecido')})")
            print(f"📝 Query: {query}")
            print(f"📊 Enviando para Assistant: {len(input_data['results'])} resultados")
            print(f"📋 Formato: Posições + Descrições ({'Parciais' if USE_PARTIAL_DESCRIPTION else 'Completas'})")
            print(f"🎯 Assistant ID: {assistant_id}")
            
            # Mostrar exemplo dos primeiros 3 resultados
            print("📋 Exemplo de dados enviados:")
            for i, result in enumerate(input_data['results'][:3], 1):
                desc_preview = result['description'][:100] + "..." if len(result['description']) > 100 else result['description']
                print(f"   {result['position']}. {desc_preview}")
            if len(input_data['results']) > 3:
                print(f"   ... e mais {len(input_data['results']) - 3} resultados")
        
        # Chamar Assistant de Relevância
        thread = get_relevance_thread()
        if not thread:
            return results, {
                'filter_applied': False,
                'reason': 'Thread de relevância não disponível',
                'original_count': len(results),
                'filtered_count': len(results),
                'level': RELEVANCE_FILTER_LEVEL
            }
            
        response = call_openai_assistant(
            assistant_id=assistant_id,
            thread_id=thread.id,
            message_content=json.dumps(input_data, ensure_ascii=False, indent=2),
            max_wait_time=60  # Mais tempo para processamento
        )
        
        # Processar resposta do Assistant
        filtered_results = process_relevance_filter_response(response, results)
        
        filter_info = {
            'filter_applied': True,
            'original_count': len(results),
            'filtered_count': len(filtered_results),
            'reduction_percentage': round((1 - len(filtered_results) / len(results)) * 100, 1) if results else 0,
            'level': RELEVANCE_FILTER_LEVEL,
            'assistant_id': assistant_id
        }
        
        if DEBUG_RELEVANCE_FILTER:
            print(f"✅ FILTRO DE RELEVÂNCIA - Processado:")
            print(f"📥 Resposta recebida: {response[:200]}..." if len(response) > 200 else f"📥 Resposta: {response}")
            print(f"📊 Original: {filter_info['original_count']} → Filtrado: {filter_info['filtered_count']} (-{filter_info['reduction_percentage']}%)")
            if filtered_results != results:
                print(f"🎯 Posições mantidas: {[r.get('rank', 0) for r in filtered_results[:10]]}")
        
        return filtered_results, filter_info
        
    except Exception as e:
        print(f"❌ Erro no Filtro de Relevância: {str(e)}")
        # Em caso de erro, retornar resultados originais
        return results, {
            'filter_applied': False,
            'reason': f'Erro no processamento: {str(e)}',
            'original_count': len(results),
            'filtered_count': len(results)
        }

def prepare_relevance_filter_input(results, query, search_metadata=None):
    """
    Prepara entrada SIMPLIFICADA para o Assistant de Relevância
    
    Envia apenas:
    - Posição/ranking do resultado  
    - Descrição (parcial até "::" ou completa conforme flag)
    
    Args:
        results (list): Resultados da busca
        query (str): Query original
        search_metadata (dict): Metadados da busca
        
    Returns:
        dict: Entrada simplificada para o Assistant
    """
    # Lista simplificada para o Assistant
    simplified_results = []
    
    for result in results:
        rank = result.get('rank', 0)
        details = result.get('details', {})
        full_description = details.get('descricaocompleta', '')
        
        # Aplicar flag de descrição parcial/completa
        if USE_PARTIAL_DESCRIPTION and '::' in full_description:
            description = full_description.split('::')[0].strip()
        else:
            description = full_description
        
        # Entrada simplificada: apenas ranking e descrição
        simplified_results.append({
            'position': rank,
            'description': description
        })
    
    # Metadados mínimos
    if not search_metadata:
        search_metadata = {'search_type': 'Desconhecido'}
    
    return {
        'query': query,
        'search_type': search_metadata.get('search_type', 'Desconhecido'),
        'results': simplified_results
    }

def process_relevance_filter_response(response, original_results):
    """
    Processa resposta SIMPLIFICADA do Assistant de Relevância
    
    Espera receber apenas uma lista de posições/rankings dos resultados relevantes.
    Filtra os resultados originais usando essas posições.
    
    Args:
        response (str): Lista de posições relevantes do Assistant
        original_results (list): Resultados originais da busca
        
    Returns:
        list: Resultados filtrados mantendo formato original
    """
    try:
        # Extrair conteúdo da resposta (pode vir com markdown)
        response_content = extract_json_from_assistant_response(response)
        
        # Tentar interpretar como lista de posições
        try:
            # Se vier como JSON array: [1, 3, 5, 7]
            relevant_positions = json.loads(response_content)
        except:
            try:
                # Se vier como lista de números separados: "1,3,5,7" ou "1 3 5 7"
                response_clean = response_content.replace('[', '').replace(']', '').replace(',', ' ')
                relevant_positions = [int(x.strip()) for x in response_clean.split() if x.strip().isdigit()]
            except:
                # Se falhar, assumir que todos são relevantes
                print(f"⚠️ Formato inesperado na resposta do Assistant: {response_content[:100]}...")
                return original_results
        
        if not relevant_positions:
            print("⚠️ Nenhuma posição relevante retornada pelo Assistant")
            return []
        
        # Filtrar resultados originais pelas posições relevantes
        filtered_results = []
        for result in original_results:
            result_position = result.get('rank', 0)
            if result_position in relevant_positions:
                filtered_results.append(result)
        
        # Reordenar conforme ordem retornada pelo Assistant
        position_order = {pos: idx for idx, pos in enumerate(relevant_positions)}
        filtered_results.sort(key=lambda x: position_order.get(x.get('rank', 0), 999))
        
        # Atualizar rankings sequenciais
        for i, result in enumerate(filtered_results, 1):
            result['rank'] = i
        
        return filtered_results
        
    except Exception as e:
        print(f"❌ Erro ao processar resposta do Filtro de Relevância: {e}")
        # Em caso de erro, retornar resultados originais
        return original_results

def extract_json_from_assistant_response(response):
    """
    Extrai JSON da resposta do Assistant (remove markdown se presente)
    
    Args:
        response (str): Resposta do Assistant
        
    Returns:
        str: JSON extraído
    """
    # Tentar extrair JSON do conteúdo (pode vir com markdown)
    if "```json" in response:
        json_content = response.split("```json")[1].split("```")[0].strip()
    elif "```" in response:
        json_content = response.split("```")[1].split("```")[0].strip()
    else:
        json_content = response.strip()
    
    return json_content

# ====================================================================================
# FUNÇÕES DE CONTROLE DO FILTRO DE RELEVÂNCIA (Sistema de 3 Níveis)
# ====================================================================================

def toggle_relevance_filter_debug(enable=True):
    """
    Ativa ou desativa o debug do filtro de relevância
    
    Args:
        enable (bool): True para ativar, False para desativar
    """
    global DEBUG_RELEVANCE_FILTER
    DEBUG_RELEVANCE_FILTER = enable

def toggle_partial_description(enable=True):
    """
    Ativa ou desativa descrição parcial (até "::") para o filtro de relevância
    
    Args:
        enable (bool): True para parcial (até "::"), False para completa
    """
    global USE_PARTIAL_DESCRIPTION
    USE_PARTIAL_DESCRIPTION = enable

def toggle_relevance_filter(enable=True):
    """
    Função de compatibilidade para ativar/desativar filtro de relevância
    Se enable=True, mantém o nível atual (ou define nível 2 se estiver em 1)
    Se enable=False, define nível 1 (sem filtro)
    
    Args:
        enable (bool): True para ativar, False para desativar
    """
    global RELEVANCE_FILTER_LEVEL
    if enable:
        if RELEVANCE_FILTER_LEVEL == 1:
            RELEVANCE_FILTER_LEVEL = 2  # Ativar com nível flexível por padrão
    else:
        RELEVANCE_FILTER_LEVEL = 1  # Desativar (sem filtro)

# ====================================================================================
# FUNÇÕES DO SISTEMA DE 3 NÍVEIS DE RELEVÂNCIA
# ====================================================================================

def set_relevance_filter_level(level):
    """
    Define o nível do filtro de relevância.
    
    Args:
        level (int): Nível do filtro (1=sem filtro, 2=flexível, 3=restritivo)
    """
    global RELEVANCE_FILTER_LEVEL
    if level in [1, 2, 3]:
        RELEVANCE_FILTER_LEVEL = level
        if DEBUG_RELEVANCE_FILTER:
            level_names = {1: "Sem filtro", 2: "Flexível", 3: "Restritivo"}
            print(f"🎯 Filtro de Relevância: {level_names[level]} (nível {level})")
    else:
        raise ValueError("Nível deve ser 1, 2 ou 3")

def get_relevance_filter_status():
    """
    Retorna o status atual do filtro de relevância.
    
    Returns:
        dict: Status das configurações do filtro
    """
    level_names = {1: "Sem filtro", 2: "Flexível", 3: "Restritivo"}
    assistant_ids = {
        1: None,
        2: RELEVANCE_ASSISTANT_FLEXIBLE,
        3: RELEVANCE_ASSISTANT_RESTRICTIVE
    }
    
    return {
        'relevance_filter_level': RELEVANCE_FILTER_LEVEL,
        'level_name': level_names.get(RELEVANCE_FILTER_LEVEL, "Desconhecido"),
        'assistant_id': assistant_ids.get(RELEVANCE_FILTER_LEVEL),
        'relevance_filter_available': RELEVANCE_FILTER_AVAILABLE,
        'debug_enabled': DEBUG_RELEVANCE_FILTER,
        'use_partial_description': USE_PARTIAL_DESCRIPTION,
        'description_mode': 'Parcial (até "::")' if USE_PARTIAL_DESCRIPTION else 'Completa'
    }

def get_current_assistant_id():
    """
    Retorna o ID do assistant conforme o nível atual de relevância.
    
    Returns:
        str or None: ID do assistant ou None se sem filtro
    """
    if RELEVANCE_FILTER_LEVEL == 2:
        return RELEVANCE_ASSISTANT_FLEXIBLE
    elif RELEVANCE_FILTER_LEVEL == 3:
        return RELEVANCE_ASSISTANT_RESTRICTIVE
    else:
        return None

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
        
        # Aplicar filtro de relevância se ativo (nível > 1)
        if RELEVANCE_FILTER_LEVEL > 1:
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
            
            # Aplicar filtro de relevância se habilitado (nível > 1)
            if RELEVANCE_FILTER_LEVEL > 1:
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
        if RELEVANCE_FILTER_LEVEL > 1:
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
        if RELEVANCE_FILTER_LEVEL > 1:
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
            if RELEVANCE_FILTER_LEVEL > 1:
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
        if RELEVANCE_FILTER_LEVEL > 1:
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
        if RELEVANCE_FILTER_LEVEL > 1:
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
            if RELEVANCE_FILTER_LEVEL > 1:
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
        if RELEVANCE_FILTER_LEVEL > 1:
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
