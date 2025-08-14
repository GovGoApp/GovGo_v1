#!/usr/bin/env python3
"""
URLs dos endpoints PNCP baseadas no Manual de Integração v2.2.1
Seções específicas do manual referenciadas
"""

# =============================================================================
# ENDPOINTS IDENTIFICADOS NO MANUAL PNCP v2.2.1
# =============================================================================

PNCP_ENDPOINTS = {
    
    # CONTRATAÇÕES (Seção 6.3)
    'contratacoes': {
        'base_url': '/contratacoes',
        'exemplos': [
            # Consultar contratações com filtros básicos
            {
                'url': '/contratacoes',
                'params': {
                    'dataPublicacaoDe': '2024-01-01',
                    'dataPublicacaoAte': '2024-01-31',
                    'cnpjOrgao': '00394460000141',
                    'pagina': 1,
                    'tamanhoPagina': 10
                }
            },
            # Consultar contratação específica
            {
                'url': '/contratacoes/{numeroControlePNCP}',
                'exemplo': '/contratacoes/00394460000141-2024-1'
            },
            # Consultar itens de contratação
            {
                'url': '/contratacoes/{numeroControlePNCP}/itens',
                'exemplo': '/contratacoes/00394460000141-2024-1/itens'
            },
            # Consultar resultados de contratação
            {
                'url': '/contratacoes/{numeroControlePNCP}/resultados',
                'exemplo': '/contratacoes/00394460000141-2024-1/resultados'
            }
        ]
    },
    
    # CONTRATOS (Seção 6.4)
    'contratos': {
        'base_url': '/contratos',
        'exemplos': [
            # Consultar contratos
            {
                'url': '/contratos',
                'params': {
                    'dataPublicacaoDe': '2024-01-01',
                    'dataPublicacaoAte': '2024-01-31',
                    'cnpjOrgao': '00394460000141',
                    'pagina': 1,
                    'tamanhoPagina': 10
                }
            },
            # Consultar contrato específico
            {
                'url': '/contratos/{numeroControlePNCP}',
                'exemplo': '/contratos/00394460000141-2024-1'
            },
            # Consultar itens de contrato
            {
                'url': '/contratos/{numeroControlePNCP}/itens',
                'exemplo': '/contratos/00394460000141-2024-1/itens'
            }
        ]
    },
    
    # ATAS DE REGISTRO DE PREÇOS (Seção 6.5)
    'atas': {
        'base_url': '/atas',
        'exemplos': [
            # Consultar atas
            {
                'url': '/atas',
                'params': {
                    'dataPublicacaoDe': '2024-01-01',
                    'dataPublicacaoAte': '2024-01-31',
                    'cnpjOrgao': '00394460000141',
                    'pagina': 1,
                    'tamanhoPagina': 10
                }
            },
            # Consultar ata específica
            {
                'url': '/atas/{numeroControlePNCP}',
                'exemplo': '/atas/00394460000141-2024-1'
            },
            # Consultar itens de ata
            {
                'url': '/atas/{numeroControlePNCP}/itens',
                'exemplo': '/atas/00394460000141-2024-1/itens'
            }
        ]
    },
    
    # PCA - PLANOS DE CONTRATAÇÕES ANUAIS (Seção 6.7)
    'pca': {
        'base_url': '/orgaos/{cnpj}/pca',
        'exemplos': [
            # Consultar plano consolidado por órgão e ano
            {
                'url': '/orgaos/{cnpj}/pca/{ano}/consolidado',
                'exemplo': '/orgaos/00394460000141/pca/2024/consolidado'
            },
            # Consultar planos das unidades
            {
                'url': '/orgaos/{cnpj}/pca/{ano}/consolidado/unidades',
                'exemplo': '/orgaos/00394460000141/pca/2024/consolidado/unidades',
                'params': {
                    'pagina': 1,
                    'tamanhoPagina': 10
                }
            },
            # Consultar valores por categoria
            {
                'url': '/orgaos/{cnpj}/pca/{ano}/valorcategoriaitem',
                'exemplo': '/orgaos/00394460000141/pca/2024/valorcategoriaitem'
            },
            # Consultar plano específico de uma unidade
            {
                'url': '/orgaos/{cnpj}/pca/{ano}/{sequencial}/consolidado',
                'exemplo': '/orgaos/00394460000141/pca/2024/1/consolidado'
            },
            # Consultar itens do plano de uma unidade
            {
                'url': '/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens',
                'exemplo': '/orgaos/00394460000141/pca/2024/1/itens',
                'params': {
                    'categoria': 1,
                    'pagina': 1,
                    'tamanhoPagina': 10
                }
            }
        ]
    },
    
    # ÓRGÃOS E UNIDADES (Seção 6.2)
    'orgaos': {
        'base_url': '/orgaos',
        'exemplos': [
            # Consultar órgão por CNPJ
            {
                'url': '/orgaos/{cnpj}',
                'exemplo': '/orgaos/00394460000141'
            },
            # Consultar unidades de um órgão
            {
                'url': '/orgaos/{cnpj}/unidades',
                'exemplo': '/orgaos/00394460000141/unidades'
            },
            # Consultar unidade específica
            {
                'url': '/orgaos/{cnpj}/unidades/{codigoUnidade}',
                'exemplo': '/orgaos/00394460000141/unidades/12345'
            }
        ]
    }
}

# =============================================================================
# PARÂMETROS COMUNS IDENTIFICADOS NO MANUAL
# =============================================================================

PARAMETROS_COMUNS = {
    'filtros_data': {
        'dataPublicacaoDe': 'YYYY-MM-DD',
        'dataPublicacaoAte': 'YYYY-MM-DD',
        'dataAberturaDe': 'YYYY-MM-DD',
        'dataAberturaAte': 'YYYY-MM-DD'
    },
    'filtros_orgao': {
        'cnpjOrgao': 'string (14 dígitos)',
        'codigoUnidade': 'string',
        'municipio': 'string',
        'uf': 'string (2 letras)'
    },
    'filtros_modalidade': {
        'modalidadeId': 'integer',
        'modoDisputaId': 'integer'
    },
    'filtros_valores': {
        'valorDe': 'decimal',
        'valorAte': 'decimal'
    },
    'paginacao': {
        'pagina': 'integer (default: 1)',
        'tamanhoPagina': 'integer (default: 10, max: 500)'
    },
    'pca_especificos': {
        'cnpj': 'string (14 dígitos)',
        'ano': 'integer (YYYY)',
        'sequencial': 'integer',
        'categoria': 'integer'
    }
}

# =============================================================================
# CNPJS DE EXEMPLO ENCONTRADOS NO MANUAL
# =============================================================================

CNPJS_TESTE = [
    '00394460000141',  # Exemplo principal usado no manual
    '10000000000003',  # Exemplo usado em alguns endpoints
    '00000000000000'   # Exemplo genérico
]

# =============================================================================
# FUNÇÃO PARA GERAR URLS DE TESTE
# =============================================================================

def generate_test_urls(base_url: str = "https://pncp.gov.br/api/pncp/v1") -> list:
    """Gera lista de URLs para testar baseadas no manual"""
    
    urls_teste = []
    
    for categoria, config in PNCP_ENDPOINTS.items():
        for exemplo in config['exemplos']:
            # URL base
            url = exemplo.get('url', exemplo.get('exemplo', ''))
            
            if '{cnpj}' in url:
                # Substitui CNPJ por exemplo
                url = url.replace('{cnpj}', CNPJS_TESTE[0])
            
            if '{numeroControlePNCP}' in url:
                # Para estes, precisamos primeiro obter IDs reais
                continue
            
            if '{ano}' in url:
                url = url.replace('{ano}', '2024')
            
            if '{sequencial}' in url:
                url = url.replace('{sequencial}', '1')
            
            if '{codigoUnidade}' in url:
                url = url.replace('{codigoUnidade}', '12345')
            
            # Monta URL completa
            full_url = base_url + url
            
            # Adiciona parâmetros se especificados
            params = exemplo.get('params', {})
            
            urls_teste.append({
                'categoria': categoria,
                'url': full_url,
                'params': params,
                'description': f"{categoria} - {url}"
            })
    
    return urls_teste

if __name__ == "__main__":
    # Gera URLs de teste
    urls = generate_test_urls()
    
    print("URLs DE TESTE GERADAS BASEADAS NO MANUAL PNCP:")
    print("="*60)
    
    for i, url_config in enumerate(urls, 1):
        print(f"\n{i}. {url_config['description']}")
        print(f"   URL: {url_config['url']}")
        if url_config['params']:
            print(f"   Params: {url_config['params']}")
    
    print(f"\n\nTotal de URLs: {len(urls)}")
