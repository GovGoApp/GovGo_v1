"""
gvg_pre_processing_v3.py
Módulo de pré-processamento inteligente para consultas de busca GvG
- Análise de linguagem natural usando OpenAI Assistant
- Separação entre termos de busca e condicionantes SQL
- Integração com sistema de busca semântica, palavra-chave e híbrida
- Validação e formatação de condições SQL dinâmicas
"""

import os
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv

# Cliente OpenAI
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configurações do Assistant
ASSISTANT_ID = "asst_argxuo1SK6KE3HS5RGo4VRBV"  # Assistant criado com SUPABASE_SEARCH_v0.txt
MODEL_ID = "gpt-4o"
MAX_RETRIES = 3
CURRENT_YEAR = datetime.now().year

# Criar thread global para o Assistant
thread = client.beta.threads.create()

class SearchQueryProcessor:
    """
    Processador inteligente de consultas de busca que separa termos de busca 
    de condicionantes SQL usando OpenAI Assistant especializado.
    """
    
    def __init__(self):
        self.assistant_id = ASSISTANT_ID
        self.thread = thread
        
    def process_query(self, user_query: str, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
        """
        Processa uma consulta de usuário separando termos de busca de condicionantes SQL.
        
        Args:
            user_query (str): Consulta do usuário em linguagem natural
            max_retries (int): Número máximo de tentativas em caso de erro
            
        Returns:
            Dict[str, Any]: Dicionário com search_terms, sql_conditions, explanation e requires_join_embeddings
        """
        if not user_query or not user_query.strip():
            return self._get_empty_result("Consulta vazia fornecida")
        
        # Limpar e preparar consulta
        cleaned_query = self._clean_query(user_query)
        
        for attempt in range(max_retries):
            try:
                # Chamar OpenAI Assistant
                response = self._call_openai_assistant(cleaned_query)
                
                # Validar e processar resposta
                result = self._validate_and_process_response(response, cleaned_query)
                
                if result:
                    return result
                    
            except Exception as e:
                print(f"Tentativa {attempt + 1} falhou: {e}")
                if attempt == max_retries - 1:
                    return self._get_fallback_result(cleaned_query, str(e))
        
        return self._get_fallback_result(cleaned_query, "Máximo de tentativas excedido")

    def _clean_query(self, query: str) -> str:
        """Limpa e normaliza a consulta do usuário"""
        # Remover caracteres especiais excessivos
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Normalizar separadores de negação
        query = re.sub(r'\s*[-–—]+\s*', ' -- ', query)
        
        # Remover caracteres especiais problemáticos
        query = re.sub(r'[^\w\sáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ\-\$\%\(\)\[\]\/\.]', ' ', query)
        
        return query.strip()

    def _call_openai_assistant(self, query: str) -> str:
        """Chama o Assistant da OpenAI para processar a consulta"""
        # Enviar mensagem para o thread
        client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=f'Analise esta consulta e retorne JSON: "{query}"'
        )
        
        # Executar Assistant
        run = client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant_id
        )
        
        # Aguardar conclusão
        response_content = self._poll_run(run.id)
        return response_content

    def _poll_run(self, run_id: str) -> str:
        """Aguarda a conclusão do run e retorna a resposta"""
        max_wait_time = 30  # 30 segundos máximo
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            run = client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run_id
            )
            
            if run.status == 'completed':
                # Buscar última mensagem do assistant
                messages = client.beta.threads.messages.list(
                    thread_id=self.thread.id,
                    limit=1
                )
                
                if messages.data and messages.data[0].role == 'assistant':
                    content = messages.data[0].content[0].text.value
                    return content
                    
            elif run.status in ['failed', 'cancelled', 'expired']:
                raise Exception(f"Run falhou com status: {run.status}")
                
            time.sleep(1)
        
        raise Exception("Timeout aguardando resposta do Assistant")

    def _validate_and_process_response(self, response: str, original_query: str) -> Optional[Dict[str, Any]]:
        """Valida e processa a resposta do Assistant"""
        try:
            # Extrair JSON da resposta (pode vir com markdown)
            json_content = self._extract_json_from_response(response)
            data = json.loads(json_content)
            
            # Validar campos obrigatórios
            required_fields = ['search_terms', 'sql_conditions', 'explanation', 'requires_join_embeddings']
            if not all(field in data for field in required_fields):
                raise ValueError(f"Campos obrigatórios ausentes: {required_fields}")
            
            # Processar e validar cada campo
            result = {
                'search_terms': self._process_search_terms(data['search_terms']),
                'sql_conditions': self._process_sql_conditions(data['sql_conditions']),
                'explanation': str(data['explanation']).strip(),
                'requires_join_embeddings': bool(data['requires_join_embeddings']),
                'original_query': original_query,
                'processing_success': True
            }
            
            # Validar que pelo menos search_terms não está vazio
            if not result['search_terms'].strip():
                result['search_terms'] = original_query
                result['explanation'] += " (Termos de busca preservados do original)"
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
            return None
        except Exception as e:
            print(f"Erro ao validar resposta: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> str:
        """Extrai JSON da resposta do Assistant (remove markdown se presente)"""
        # Tentar extrair JSON do conteúdo (pode vir com markdown)
        if "```json" in response:
            json_content = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_content = response.split("```")[1].split("```")[0].strip()
        else:
            json_content = response.strip()
            
        return json_content

    def _process_search_terms(self, search_terms: Any) -> str:
        """Processa e valida os termos de busca"""
        if isinstance(search_terms, list):
            return ' '.join(str(term) for term in search_terms).strip()
        return str(search_terms).strip()

    def _process_sql_conditions(self, sql_conditions: Any) -> List[str]:
        """Processa e valida as condições SQL"""
        if not sql_conditions:
            return []
        
        if isinstance(sql_conditions, str):
            sql_conditions = [sql_conditions]
        
        validated_conditions = []
        for condition in sql_conditions:
            condition_str = str(condition).strip()
            if condition_str and self._validate_sql_condition(condition_str):
                validated_conditions.append(condition_str)
        
        return validated_conditions

    def _validate_sql_condition(self, condition: str) -> bool:
        """Valida se uma condição SQL é segura e bem formada"""
        # Lista de padrões perigosos
        dangerous_patterns = [
            r';\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)',
            r'--[^-]',  # Comentários SQL (exceto negação --)
            r'/\*.*\*/',  # Comentários de bloco
            r'EXEC\s*\(',
            r'xp_',
            r'sp_',
        ]
        
        condition_upper = condition.upper()
        
        # Verificar padrões perigosos
        for pattern in dangerous_patterns:
            if re.search(pattern, condition_upper, re.IGNORECASE):
                print(f"Condição SQL rejeitada por segurança: {condition}")
                return False
        
        # Verificar se contém prefixo de tabela válido (c. ou e.)
        if not re.search(r'\b[ce]\.\w+', condition):
            print(f"Condição SQL rejeitada - sem prefixo de tabela válido: {condition}")
            return False
        
        return True

    def _get_empty_result(self, reason: str) -> Dict[str, Any]:
        """Retorna resultado vazio com explicação"""
        return {
            'search_terms': '',
            'sql_conditions': [],
            'explanation': f"Consulta não processada: {reason}",
            'requires_join_embeddings': False,
            'original_query': '',
            'processing_success': False
        }

    def _get_fallback_result(self, query: str, error: str) -> Dict[str, Any]:
        """Retorna resultado de fallback quando o processamento falha"""
        return {
            'search_terms': query,
            'sql_conditions': [],
            'explanation': f"Processamento inteligente falhou ({error}). Usando consulta original como termos de busca.",
            'requires_join_embeddings': False,
            'original_query': query,
            'processing_success': False
        }

    def get_enhanced_query_info(self, processed_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera informações básicas sobre a consulta processada.
        
        Args:
            processed_query (Dict): Resultado do process_query
            
        Returns:
            Dict: Informações básicas sobre a consulta (sem recomendações)
        """
        info = {
            'has_negation': '--' in processed_query['search_terms'],
            'has_conditions': len(processed_query['sql_conditions']) > 0,
            'condition_count': len(processed_query['sql_conditions']),
            'requires_embeddings_join': processed_query['requires_join_embeddings'],
            'condition_types': self._analyze_condition_types(processed_query['sql_conditions'])
        }
        
        return info

    def _analyze_condition_types(self, conditions: List[str]) -> Dict[str, int]:
        """Analisa os tipos de condições presentes na consulta"""
        types = {
            'temporal': 0,
            'geographic': 0,
            'financial': 0,
            'administrative': 0,
            'modalidade': 0,
            'categorization': 0
        }
        
        for condition in conditions:
            condition_lower = condition.lower()
            
            # Temporal
            if any(field in condition_lower for field in ['data', 'ano', 'quarter', 'month']):
                types['temporal'] += 1
            
            # Geográfica
            if any(field in condition_lower for field in ['ufsigla', 'municipio', 'unidadeorgao']):
                types['geographic'] += 1
            
            # Financeira
            if any(field in condition_lower for field in ['valor', 'between', '>', '<']):
                types['financial'] += 1
            
            # Administrativa
            if any(field in condition_lower for field in ['poderid', 'esferaid', 'orgao']):
                types['administrative'] += 1
            
            # Modalidade
            if any(field in condition_lower for field in ['modalidade', 'disputa']):
                types['modalidade'] += 1
            
            # Categorização
            if any(field in condition_lower for field in ['confidence', 'categories']):
                types['categorization'] += 1
        
        return types

    def format_for_display(self, processed_query: Dict[str, Any]) -> str:
        """Formata o resultado processado para exibição amigável"""
        lines = []
        lines.append("🔍 CONSULTA PROCESSADA:")
        lines.append(f"   Original: {processed_query['original_query']}")
        lines.append(f"   Termos: {processed_query['search_terms']}")
        
        if processed_query['sql_conditions']:
            lines.append("📋 CONDIÇÕES SQL:")
            for i, condition in enumerate(processed_query['sql_conditions'], 1):
                lines.append(f"   {i}. {condition}")
        
        lines.append(f"💡 {processed_query['explanation']}")
        
        if processed_query['requires_join_embeddings']:
            lines.append("⚠️  Requer JOIN com tabela embeddings")
        
        return '\n'.join(lines)


# Instância global do processador
query_processor = SearchQueryProcessor()

def process_search_query(user_query: str) -> Dict[str, Any]:
    """
    Função principal para processar consultas de busca.
    Interface simplificada para o módulo gvg_search_utils_v3.
    
    Args:
        user_query (str): Consulta do usuário
        
    Returns:
        Dict[str, Any]: Consulta processada com termos de busca e condições SQL
    """
    return query_processor.process_query(user_query)

def enhance_sql_query(base_query: str, sql_conditions: List[str], requires_join_embeddings: bool) -> str:
    """
    Adiciona condições SQL dinâmicas à consulta base.
    
    Args:
        base_query (str): Consulta SQL base
        sql_conditions (List[str]): Lista de condições para adicionar
        requires_join_embeddings (bool): Se requer JOIN com embeddings
        
    Returns:
        str: Consulta SQL modificada
    """
    if not sql_conditions:
        return base_query
    
    # Encontrar onde inserir as condições (após WHERE existente)
    where_pattern = r'WHERE\s+'
    where_match = re.search(where_pattern, base_query, re.IGNORECASE)
    
    if where_match:
        # Adicionar condições após WHERE existente
        conditions_sql = '\n        AND ' + '\n        AND '.join(sql_conditions)
        
        # Inserir após a primeira condição WHERE
        insert_pos = base_query.find('\n', where_match.end())
        if insert_pos == -1:
            insert_pos = len(base_query)
        
        enhanced_query = base_query[:insert_pos] + conditions_sql + base_query[insert_pos:]
    else:
        # Adicionar WHERE se não existir
        conditions_sql = '\n        WHERE ' + '\n        AND '.join(sql_conditions)
        
        # Procurar por ORDER BY para inserir antes
        order_by_match = re.search(r'\s+ORDER\s+BY', base_query, re.IGNORECASE)
        if order_by_match:
            enhanced_query = base_query[:order_by_match.start()] + conditions_sql + base_query[order_by_match.start():]
        else:
            enhanced_query = base_query + conditions_sql
    
    return enhanced_query

def test_query_processor():
    """Função de teste para validar o processador de consultas"""
    test_queries = [
        "material escolar -- uniformes no ES acima de 500 mil",
        "equipamentos médicos nordeste 2024 bem categorizados",
        "serviços de limpeza federal entre 100 mil e 1 milhão",
        "notebooks para educação",
        "pregão eletrônico medicamentos"
    ]
    
    print("🧪 TESTANDO PROCESSADOR DE CONSULTAS\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"--- TESTE {i} ---")
        result = process_search_query(query)
        print(query_processor.format_for_display(result))
        
        info = query_processor.get_enhanced_query_info(result)
        print(f"Tipos de condição: {info['condition_types']}")
        print()

if __name__ == "__main__":
    # Executar testes se o módulo for chamado diretamente
    test_query_processor()
