#!/usr/bin/env python3
"""
Script para Descobrir Campos da API PNCP v2.2.1
Sistema corrigido baseado no manual oficial
"""

import requests
import json
import datetime
import time
from typing import Dict, List, Any, Optional

class PNCPFieldDiscoveryV2:
    def __init__(self, base_url: str = "https://pncp.gov.br/api/pncp/v1"):
        self.base_url = base_url
        self.discovered_fields = {}
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def safe_request(self, url: str, method: str = 'GET', params: Optional[Dict] = None) -> Dict:
        """Fazer requisição segura com tratamento de erros"""
        try:
            response = requests.request(method, url, headers=self.headers, params=params, timeout=30)
            
            print(f"🔍 Testando: {url}")
            
            if response.status_code == 200:
                print(f"✅ Sucesso: {response.status_code}")
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        fields = self.extract_fields_from_response(data)
                        print(f"📊 Campos encontrados: {len(fields)}")
                        return {"success": True, "data": data, "fields": fields}
                    elif isinstance(data, list) and len(data) > 0:
                        fields = self.extract_fields_from_response(data[0])
                        print(f"📊 Campos encontrados: {len(fields)}")
                        return {"success": True, "data": data, "fields": fields}
                    else:
                        return {"success": True, "data": data, "fields": []}
                except json.JSONDecodeError:
                    return {"success": False, "error": "JSON decode error"}
            else:
                error_msg = f"{response.status_code} - {response.text[:200]}"
                print(f"❌ Erro: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def extract_fields_from_response(self, data: Dict) -> List[Dict]:
        """Extrair campos de uma resposta JSON"""
        fields = []
        
        def extract_recursive(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_key = f"{prefix}.{key}" if prefix else key
                    field_type = type(value).__name__
                    
                    if isinstance(value, (dict, list)):
                        fields.append({
                            "name": current_key,
                            "type": field_type,
                            "sample": str(value)[:100] if isinstance(value, list) else "object"
                        })
                        extract_recursive(value, current_key)
                    else:
                        fields.append({
                            "name": current_key,
                            "type": field_type,
                            "sample": str(value)[:100] if value is not None else "null"
                        })
            elif isinstance(obj, list) and len(obj) > 0:
                extract_recursive(obj[0], prefix)
        
        extract_recursive(data)
        return fields
    
    def test_pca_endpoints(self) -> Dict:
        """Testar endpoints de PCA (Plano de Contratações)"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: PCA (PLANO DE CONTRATAÇÕES)")
        print("="*60)
        
        results = {}
        
        # Endpoints de PCA baseados no manual
        endpoints = [
            {
                "name": "pca_consolidado_orgao",
                "url": f"{self.base_url}/orgaos/00394460000141/pca/2024/consolidado",
                "description": "Plano de Contratações Consolidado do Órgão"
            },
            {
                "name": "pca_unidades_orgao",
                "url": f"{self.base_url}/orgaos/00394460000141/pca/2024/consolidado/unidades",
                "description": "Unidades do Plano de Contratações"
            },
            {
                "name": "pca_categoria_item",
                "url": f"{self.base_url}/orgaos/00394460000141/pca/2024/categoria/item",
                "description": "Categoria de Itens do PCA"
            },
            {
                "name": "pca_itens_unidade",
                "url": f"{self.base_url}/orgaos/00394460000141/pca/2024/unidades/1/itens",
                "description": "Itens do PCA por Unidade"
            }
        ]
        
        for endpoint in endpoints:
            result = self.safe_request(endpoint["url"])
            if result["success"]:
                results[endpoint["name"]] = result["fields"]
            time.sleep(1)
        
        return results
    
    def test_compras_endpoints(self) -> Dict:
        """Testar endpoints de compras (contratações)"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: COMPRAS/CONTRATAÇÕES")
        print("="*60)
        
        results = {}
        
        # Endpoints de compras baseados no manual
        endpoints = [
            {
                "name": "compra_orgao",
                "url": f"{self.base_url}/orgaos/00394460000141/compras/2024/1",
                "description": "Dados de uma Compra específica"
            },
            {
                "name": "compras_orgao_ano",
                "url": f"{self.base_url}/orgaos/00394460000141/compras/2024",
                "description": "Compras de um Órgão por Ano"
            },
            {
                "name": "compra_itens",
                "url": f"{self.base_url}/orgaos/00394460000141/compras/2024/1/itens",
                "description": "Itens de uma Compra"
            },
            {
                "name": "compra_item",
                "url": f"{self.base_url}/orgaos/00394460000141/compras/2024/1/itens/1",
                "description": "Item específico de uma Compra"
            },
            {
                "name": "compra_arquivos",
                "url": f"{self.base_url}/orgaos/00394460000141/compras/2024/1/arquivos",
                "description": "Arquivos de uma Compra"
            }
        ]
        
        for endpoint in endpoints:
            result = self.safe_request(endpoint["url"])
            if result["success"]:
                results[endpoint["name"]] = result["fields"]
            time.sleep(1)
        
        return results
    
    def test_atas_endpoints(self) -> Dict:
        """Testar endpoints de atas"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: ATAS DE REGISTRO DE PREÇOS")
        print("="*60)
        
        results = {}
        
        # Endpoints de atas baseados no manual
        endpoints = [
            {
                "name": "atas_compra",
                "url": f"{self.base_url}/orgaos/00394460000141/compras/2024/1/atas",
                "description": "Atas de uma Compra"
            },
            {
                "name": "ata_especifica",
                "url": f"{self.base_url}/orgaos/00394460000141/compras/2024/1/atas/1",
                "description": "Ata específica"
            },
            {
                "name": "ata_arquivos",
                "url": f"{self.base_url}/orgaos/00394460000141/compras/2024/1/atas/1/arquivos",
                "description": "Arquivos de uma Ata"
            }
        ]
        
        for endpoint in endpoints:
            result = self.safe_request(endpoint["url"])
            if result["success"]:
                results[endpoint["name"]] = result["fields"]
            time.sleep(1)
        
        return results
    
    def test_contratos_endpoints(self) -> Dict:
        """Testar endpoints de contratos"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: CONTRATOS")
        print("="*60)
        
        results = {}
        
        # Endpoints de contratos baseados no manual
        endpoints = [
            {
                "name": "contratos_orgao",
                "url": f"{self.base_url}/orgaos/00394460000141/contratos/2024",
                "description": "Contratos de um Órgão por Ano"
            },
            {
                "name": "contrato_especifico",
                "url": f"{self.base_url}/orgaos/00394460000141/contratos/2024/1",
                "description": "Contrato específico"
            },
            {
                "name": "contrato_arquivos",
                "url": f"{self.base_url}/orgaos/00394460000141/contratos/2024/1/arquivos",
                "description": "Arquivos de um Contrato"
            }
        ]
        
        for endpoint in endpoints:
            result = self.safe_request(endpoint["url"])
            if result["success"]:
                results[endpoint["name"]] = result["fields"]
            time.sleep(1)
        
        return results
    
    def test_orgaos_endpoints(self) -> Dict:
        """Testar endpoints de órgãos"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CAMPOS: ÓRGÃOS E UNIDADES")
        print("="*60)
        
        results = {}
        
        # Endpoints de órgãos baseados no manual
        endpoints = [
            {
                "name": "orgao_por_cnpj",
                "url": f"{self.base_url}/orgaos/00394460000141",
                "description": "Dados de um Órgão por CNPJ"
            },
            {
                "name": "unidades_orgao",
                "url": f"{self.base_url}/orgaos/00394460000141/unidades",
                "description": "Unidades de um Órgão"
            },
            {
                "name": "unidade_especifica",
                "url": f"{self.base_url}/orgaos/00394460000141/unidades/1",
                "description": "Unidade específica"
            }
        ]
        
        for endpoint in endpoints:
            result = self.safe_request(endpoint["url"])
            if result["success"]:
                results[endpoint["name"]] = result["fields"]
            time.sleep(1)
        
        return results
    
    def generate_sql_from_fields(self, table_name: str, fields: List[Dict]) -> str:
        """Gerar SQL CREATE TABLE a partir dos campos descobertos"""
        sql_lines = [f"CREATE TABLE IF NOT EXISTS {table_name} ("]
        
        for field in fields:
            field_name = field["name"].replace(".", "_")
            field_type = field["type"]
            
            if field_type == "str":
                sql_type = "TEXT"
            elif field_type == "int":
                sql_type = "INTEGER"
            elif field_type == "float":
                sql_type = "REAL"
            elif field_type == "bool":
                sql_type = "BOOLEAN"
            elif field_type == "list":
                sql_type = "TEXT"  # JSON
            elif field_type == "dict":
                sql_type = "TEXT"  # JSON
            else:
                sql_type = "TEXT"
            
            sql_lines.append(f"    {field_name} {sql_type},")
        
        # Remove última vírgula
        if sql_lines[-1].endswith(","):
            sql_lines[-1] = sql_lines[-1][:-1]
        
        sql_lines.append(");")
        return "\n".join(sql_lines)
    
    def save_results(self, all_results: Dict):
        """Salvar resultados em arquivos"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Salvar JSON
        json_filename = f"pncp_fields_discovery_v2_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        # Salvar SQL
        sql_filename = f"pncp_schemas_v2_{timestamp}.sql"
        with open(sql_filename, 'w', encoding='utf-8') as f:
            f.write(f"-- Esquemas SQL gerados automaticamente em {timestamp}\n")
            f.write(f"-- Baseado na API PNCP v2.2.1\n\n")
            
            for table_name, fields in all_results.items():
                if fields:
                    sql = self.generate_sql_from_fields(table_name, fields)
                    f.write(f"-- Tabela: {table_name}\n")
                    f.write(sql)
                    f.write("\n\n")
        
        print(f"💾 Resultados salvos em: {json_filename}")
        print(f"📄 Esquemas SQL salvos em: {sql_filename}")
    
    def run_discovery(self):
        """Executar descoberta completa de campos"""
        print("🔍 PNCP API FIELD DISCOVERY V2")
        print("="*60)
        print("🚀 INICIANDO DESCOBERTA DE CAMPOS DA API PNCP V2.2.1")
        print("="*60)
        
        all_results = {}
        
        # Testar todos os endpoints
        all_results.update(self.test_orgaos_endpoints())
        all_results.update(self.test_compras_endpoints())
        all_results.update(self.test_atas_endpoints())
        all_results.update(self.test_contratos_endpoints())
        all_results.update(self.test_pca_endpoints())
        
        # Salvar resultados
        self.save_results(all_results)
        
        # Relatório final
        print("\n" + "="*60)
        print("📊 RELATÓRIO FINAL")
        print("="*60)
        
        total_endpoints = 0
        total_fields = 0
        
        for category, fields in all_results.items():
            if fields:
                print(f"  ✅ {category}: {len(fields)} campos")
                total_endpoints += 1
                total_fields += len(fields)
            else:
                print(f"  ❌ {category}: sem dados")
        
        print(f"📈 TOTAL: {total_endpoints} endpoints testados, {total_fields} campos descobertos")
        print("="*60)

def main():
    """Função principal"""
    discovery = PNCPFieldDiscoveryV2()
    discovery.run_discovery()

if __name__ == "__main__":
    main()
