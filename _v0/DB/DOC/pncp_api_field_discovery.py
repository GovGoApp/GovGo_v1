#!/usr/bin/env python3
"""
Script para descobrir os campos reais retornados pela API do PNCP
Baseado no Manual de Integração PNCP v2.2.1
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class PNCPFieldDiscovery:
    def __init__(self, base_url: str = "https://pncp.gov.br/api/consulta/v1"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'PNCP-Field-Discovery/1.0'
        })
        
    def safe_request(self, url: str, params: Dict = None, timeout: int = 30) -> Optional[Dict]:
        """Faz requisição segura com tratamento de erros"""
        try:
            print(f"🔍 Testando: {url}")
            response = self.session.get(url, params=params, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Sucesso: {response.status_code}")
                return data
            else:
                print(f"❌ Erro: {response.status_code} - {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Erro JSON: {str(e)}")
            return None
    
    def extract_fields_from_response(self, data: Any, prefix: str = "") -> Dict[str, str]:
        """Extrai campos e tipos de uma resposta JSON"""
        fields = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                field_name = f"{prefix}_{key}" if prefix else key
                
                if isinstance(value, dict):
                    # Recursivo para objetos aninhados
                    nested_fields = self.extract_fields_from_response(value, field_name)
                    fields.update(nested_fields)
                elif isinstance(value, list):
                    if value and isinstance(value[0], dict):
                        # Para listas de objetos, analisa o primeiro item
                        nested_fields = self.extract_fields_from_response(value[0], field_name)
                        fields.update(nested_fields)
                    else:
                        fields[field_name] = f"Lista de {type(value[0]).__name__ if value else 'unknown'}"
                else:
                    # Determina o tipo do campo
                    if isinstance(value, str):
                        if self.is_date_string(value):
                            fields[field_name] = "DATE"
                        elif self.is_datetime_string(value):
                            fields[field_name] = "DATETIME"
                        else:
                            max_len = len(str(value))
                            fields[field_name] = f"TEXT({max_len})"
                    elif isinstance(value, (int, float)):
                        fields[field_name] = "REAL" if isinstance(value, float) else "INTEGER"
                    elif isinstance(value, bool):
                        fields[field_name] = "BOOLEAN"
                    else:
                        fields[field_name] = "TEXT"
        
        elif isinstance(data, list) and data:
            # Se é uma lista, analisa o primeiro item
            return self.extract_fields_from_response(data[0], prefix)
        
        return fields
    
    def is_date_string(self, value: str) -> bool:
        """Verifica se string é uma data"""
        date_patterns = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f'
        ]
        
        for pattern in date_patterns:
            try:
                datetime.strptime(value, pattern)
                return True
            except ValueError:
                continue
        return False
    
    def is_datetime_string(self, value: str) -> bool:
        """Verifica se string é datetime"""
        return 'T' in value and ':' in value
    
    def test_compras_orgao_sequencial(self) -> Dict[str, Dict]:
        """Testa endpoint de compras por órgão, ano e sequencial (consulta)"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: COMPRAS POR ÓRGÃO/ANO/SEQUENCIAL (CONSULTA)")
        print("="*60)
        results = {}
        cnpj = '10000000000003'
        ano = '2021'
        sequencial = '1'
        url = f"{self.base_url}/orgaos/{cnpj}/compras/{ano}/{sequencial}"
        data = self.safe_request(url)
        if data:
            fields = self.extract_fields_from_response(data)
            results['compras_orgao_ano_sequencial_consulta'] = fields
            print(f"📊 Campos encontrados: {len(fields)}")
        else:
            print("❌ Nenhum dado retornado para compras.")
        return results
    
    def test_contratos_orgao_sequencial(self) -> Dict[str, Dict]:
        """Testa endpoint de contratos por órgão, ano e sequencial"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: CONTRATOS POR ÓRGÃO/ANO/SEQUENCIAL")
        print("="*60)
        results = {}
        # Exemplo do manual
        cnpj = '10000000000003'
        ano = '2021'
        sequencial = '1'
        url = f"{self.base_url}/orgaos/{cnpj}/contratos/{ano}/{sequencial}"
        data = self.safe_request(url)
        if data:
            fields = self.extract_fields_from_response(data)
            results['contratos_orgao_ano_sequencial'] = fields
            print(f"📊 Campos encontrados: {len(fields)}")
        else:
            print("❌ Nenhum dado retornado para contratos.")
        return results
    
    def test_atas_endpoints(self) -> Dict[str, Dict]:
        """Testa endpoints de atas de registro de preços"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: ATAS DE REGISTRO DE PREÇOS")
        print("="*60)
        
        results = {}
        
        # URLs baseadas no manual - seção 6.6
        endpoints = [
            {
                'name': 'atas_basico',
                'url': f"{self.base_url}/atas",
                'params': {
                    'dataPublicacaoDe': '2024-01-01',
                    'dataPublicacaoAte': '2024-01-31',
                    'pagina': 1,
                    'tamanhoPagina': 5
                }
            },
            {
                'name': 'atas_por_orgao',
                'url': f"{self.base_url}/atas",
                'params': {
                    'cnpjOrgao': '00394460000141',
                    'dataPublicacaoDe': '2024-01-01',
                    'dataPublicacaoAte': '2024-01-31',
                    'pagina': 1,
                    'tamanhoPagina': 5
                }
            }
        ]
        
        for endpoint in endpoints:
            data = self.safe_request(endpoint['url'], endpoint['params'])
            if data:
                fields = self.extract_fields_from_response(data)
                results[endpoint['name']] = fields
                print(f"📊 Campos encontrados: {len(fields)}")
                
            time.sleep(1)
        
        return results
    
    def test_pca_endpoints(self) -> Dict[str, Dict]:
        """Testa endpoints de PCA (Planos de Contratações Anuais)"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: PCA (PLANOS DE CONTRATAÇÕES)")
        print("="*60)
        
        results = {}
        
        # URLs baseadas no manual - seção 6.7
        endpoints = [
            {
                'name': 'pca_consolidado_orgao',
                'url': f"{self.base_url}/orgaos/00394460000141/pca/2024/consolidado",
                'params': None
            },
            {
                'name': 'pca_unidades_orgao',
                'url': f"{self.base_url}/orgaos/00394460000141/pca/2024/consolidado/unidades",
                'params': {
                    'pagina': 1,
                    'tamanhoPagina': 5
                }
            },
            {
                'name': 'pca_valores_categoria',
                'url': f"{self.base_url}/orgaos/00394460000141/pca/2024/valorcategoriaitem",
                'params': None
            }
        ]
        
        for endpoint in endpoints:
            data = self.safe_request(endpoint['url'], endpoint['params'])
            if data:
                fields = self.extract_fields_from_response(data)
                results[endpoint['name']] = fields
                print(f"📊 Campos encontrados: {len(fields)}")
                
            time.sleep(1)
        
        return results
    
    def test_item_endpoints(self) -> Dict[str, Dict]:
        """Testa endpoints de itens"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: ITENS")
        print("="*60)
        
        results = {}
        
        # Primeiro, vamos tentar obter alguns IDs de exemplo
        contratacao_exemplo = self.safe_request(
            f"{self.base_url}/contratacoes",
            {
                'dataPublicacaoDe': '2024-01-01',
                'dataPublicacaoAte': '2024-01-31',
                'pagina': 1,
                'tamanhoPagina': 1
            }
        )
        
        if contratacao_exemplo and 'data' in contratacao_exemplo and contratacao_exemplo['data']:
            primeiro_item = contratacao_exemplo['data'][0]
            numero_controle = primeiro_item.get('numeroControlePNCP')
            
            if numero_controle:
                print(f"🔍 Usando numeroControlePNCP exemplo: {numero_controle}")
                
                endpoints = [
                    {
                        'name': 'itens_contratacao',
                        'url': f"{self.base_url}/contratacoes/{numero_controle}/itens",
                        'params': {
                            'pagina': 1,
                            'tamanhoPagina': 5
                        }
                    },
                    {
                        'name': 'resultados_itens',
                        'url': f"{self.base_url}/contratacoes/{numero_controle}/resultados",
                        'params': {
                            'pagina': 1,
                            'tamanhoPagina': 5
                        }
                    }
                ]
                
                for endpoint in endpoints:
                    data = self.safe_request(endpoint['url'], endpoint['params'])
                    if data:
                        fields = self.extract_fields_from_response(data)
                        results[endpoint['name']] = fields
                        print(f"📊 Campos encontrados: {len(fields)}")
                        
                    time.sleep(1)
        
        return results
    
    def generate_sql_from_fields(self, table_name: str, fields: Dict[str, str]) -> str:
        """Gera SQL CREATE TABLE baseado nos campos descobertos"""
        sql = f"CREATE TABLE {table_name} (\n"
        sql += "    ID INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        
        for field_name, field_type in fields.items():
            # Sanitiza nome do campo
            clean_field_name = field_name.replace('.', '_').replace('-', '_')
            
            # Mapeia tipos
            if field_type.startswith('TEXT'):
                sql_type = field_type
            elif field_type == 'INTEGER':
                sql_type = 'INTEGER'
            elif field_type == 'REAL':
                sql_type = 'REAL'
            elif field_type == 'BOOLEAN':
                sql_type = 'BOOLEAN'
            elif field_type in ['DATE', 'DATETIME']:
                sql_type = 'TEXT'  # SQLite não tem tipo DATE nativo
            else:
                sql_type = 'TEXT'
            
            sql += f"    {clean_field_name} {sql_type},\n"
        
        sql = sql.rstrip(',\n') + "\n);"
        return sql
    
    def run_discovery(self) -> Dict[str, Any]:
        """Executa descoberta completa de campos"""
        print("🚀 INICIANDO DESCOBERTA DE CAMPOS DA API PNCP")
        print("="*60)
        all_results = {}
        try:
            all_results['compras_orgao_ano_sequencial'] = self.test_compras_orgao_sequencial()
            all_results['contratos_orgao_ano_sequencial'] = self.test_contratos_orgao_sequencial()
            all_results['atas'] = self.test_atas_endpoints()
            all_results['pca'] = self.test_pca_endpoints()
            all_results['itens'] = self.test_item_endpoints()
        except Exception as e:
            print(f"❌ Erro durante descoberta: {str(e)}")
        return all_results
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Salva resultados em arquivo"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"pncp_fields_discovery_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultados salvos em: {filename}")
    
    def generate_sql_schemas(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Gera esquemas SQL para todas as tabelas descobertas"""
        schemas = {}
        
        for category, endpoints in results.items():
            for endpoint_name, fields in endpoints.items():
                if fields:  # Se tem campos
                    table_name = f"{category}_{endpoint_name}"
                    schemas[table_name] = self.generate_sql_from_fields(table_name, fields)
        
        return schemas

def main():
    """Função principal"""
    print("🔍 PNCP API FIELD DISCOVERY")
    print("="*60)
    
    # Cria descobridor
    discoverer = PNCPFieldDiscovery()
    
    # Executa descoberta
    results = discoverer.run_discovery()
    
    # Salva resultados
    discoverer.save_results(results)
    
    # Gera schemas SQL
    schemas = discoverer.generate_sql_schemas(results)
    
    # Salva schemas
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    schema_filename = f"pncp_schemas_{timestamp}.sql"
    
    with open(schema_filename, 'w', encoding='utf-8') as f:
        f.write("-- ESQUEMAS SQL GERADOS AUTOMATICAMENTE\n")
        f.write(f"-- Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- Fonte: API PNCP\n\n")
        
        for table_name, schema in schemas.items():
            f.write(f"-- Tabela: {table_name}\n")
            f.write(f"{schema}\n\n")
    
    print(f"📄 Esquemas SQL salvos em: {schema_filename}")
    
    # Relatório final
    print("\n" + "="*60)
    print("📊 RELATÓRIO FINAL")
    print("="*60)
    
    total_endpoints = 0
    total_fields = 0
    
    for category, endpoints in results.items():
        print(f"\n📂 {category.upper()}:")
        for endpoint_name, fields in endpoints.items():
            field_count = len(fields) if fields else 0
            status = "✅" if fields else "❌"
            print(f"  {status} {endpoint_name}: {field_count} campos")
            total_fields += field_count
            total_endpoints += 1
    
    print(f"\n📈 TOTAL: {total_endpoints} endpoints testados, {total_fields} campos descobertos")
    print("="*60)

if __name__ == "__main__":
    main()
