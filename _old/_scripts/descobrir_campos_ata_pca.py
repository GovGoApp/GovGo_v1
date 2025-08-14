#!/usr/bin/env python3
"""
GovGo V1 - Descobridor de Campos ATA e PCA
==========================================
Script para descobrir os campos específicos das APIs de ATA e PCA do PNCP
e auxiliar no refinamento da estrutura das tabelas
"""

import requests
import pandas as pd
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta

console = Console()

class CamposDiscoverer:
    """Descobridor de campos das APIs ATA e PCA"""
    
    def __init__(self):
        self.base_url = "https://pncp.gov.br/api/consulta/v1"
        
    def descobrir_campos_atas(self):
        """Descobre campos da API de ATAs"""
        console.print(Panel("🔍 Descobrindo campos da API de ATAs", style="blue"))
        
        # Usar datas recentes para tentar encontrar dados
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=30)
        
        url_atas = f"{self.base_url}/atas"
        params = {
            "dataInicial": data_inicio.strftime("%Y%m%d"),
            "dataFinal": data_fim.strftime("%Y%m%d"),
            "pagina": 1,
            "tamanhoPagina": 10
        }
        
        try:
            console.print(f"📡 Consultando: {url_atas}")
            console.print(f"📅 Período: {params['dataInicial']} a {params['dataFinal']}")
            
            response = requests.get(url_atas, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                console.print(f"✅ Status: {response.status_code}")
                console.print(f"📊 Resposta: {len(str(data))} caracteres")
                
                if "data" in data and data["data"]:
                    df_atas = pd.json_normalize(data["data"])
                    console.print(f"🎯 Encontrados {len(df_atas)} registros de ATAs")
                    
                    # Criar tabela com os campos
                    table = Table(title="📋 Campos encontrados em ATAs")
                    table.add_column("Campo", style="cyan")
                    table.add_column("Tipo", style="magenta")
                    table.add_column("Exemplo", style="green")
                    
                    for col in sorted(df_atas.columns):
                        primeiro_valor = df_atas[col].dropna().iloc[0] if not df_atas[col].dropna().empty else "N/A"
                        tipo_valor = type(primeiro_valor).__name__
                        exemplo = str(primeiro_valor)[:50] + "..." if len(str(primeiro_valor)) > 50 else str(primeiro_valor)
                        table.add_row(col, tipo_valor, exemplo)
                    
                    console.print(table)
                    
                    # Salvar campos em arquivo JSON
                    campos_atas = {
                        "descoberta_em": datetime.now().isoformat(),
                        "total_registros": len(df_atas),
                        "campos": {}
                    }
                    
                    for col in df_atas.columns:
                        campos_atas["campos"][col] = {
                            "tipo": str(df_atas[col].dtype),
                            "exemplo": str(df_atas[col].dropna().iloc[0]) if not df_atas[col].dropna().empty else None,
                            "valores_unicos": int(df_atas[col].nunique()) if df_atas[col].nunique() < 100 else "muitos"
                        }
                    
                    with open("campos_atas_descobertos.json", "w", encoding="utf-8") as f:
                        json.dump(campos_atas, f, indent=2, ensure_ascii=False)
                    
                    console.print("💾 Campos salvos em: campos_atas_descobertos.json")
                    return True
                    
                else:
                    console.print("⚠️ Nenhum dado de ATA encontrado no período")
                    return False
            else:
                console.print(f"❌ Erro na API: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            console.print(f"❌ Erro ao consultar ATAs: {e}")
            return False
    
    def descobrir_campos_pcas(self):
        """Descobre campos da API de PCAs"""
        console.print(Panel("🔍 Descobrindo campos da API de PCAs", style="green"))
        
        url_pca = f"{self.base_url}/pca"
        
        # Tentar diferentes anos
        anos = [2024, 2025, 2023]
        
        for ano in anos:
            params = {
                "ano": str(ano),
                "pagina": 1,
                "tamanhoPagina": 10
            }
            
            try:
                console.print(f"📡 Consultando: {url_pca} (ano {ano})")
                
                response = requests.get(url_pca, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    console.print(f"✅ Status: {response.status_code}")
                    
                    if "data" in data and data["data"]:
                        df_pca = pd.json_normalize(data["data"])
                        console.print(f"🎯 Encontrados {len(df_pca)} registros de PCA em {ano}")
                        
                        # Criar tabela com os campos
                        table = Table(title=f"📋 Campos encontrados em PCAs ({ano})")
                        table.add_column("Campo", style="cyan")
                        table.add_column("Tipo", style="magenta")
                        table.add_column("Exemplo", style="green")
                        
                        for col in sorted(df_pca.columns):
                            primeiro_valor = df_pca[col].dropna().iloc[0] if not df_pca[col].dropna().empty else "N/A"
                            tipo_valor = type(primeiro_valor).__name__
                            exemplo = str(primeiro_valor)[:50] + "..." if len(str(primeiro_valor)) > 50 else str(primeiro_valor)
                            table.add_row(col, tipo_valor, exemplo)
                        
                        console.print(table)
                        
                        # Salvar campos em arquivo JSON
                        campos_pca = {
                            "descoberta_em": datetime.now().isoformat(),
                            "ano_consultado": ano,
                            "total_registros": len(df_pca),
                            "campos": {}
                        }
                        
                        for col in df_pca.columns:
                            campos_pca["campos"][col] = {
                                "tipo": str(df_pca[col].dtype),
                                "exemplo": str(df_pca[col].dropna().iloc[0]) if not df_pca[col].dropna().empty else None,
                                "valores_unicos": int(df_pca[col].nunique()) if df_pca[col].nunique() < 100 else "muitos"
                            }
                        
                        with open(f"campos_pca_descobertos_{ano}.json", "w", encoding="utf-8") as f:
                            json.dump(campos_pca, f, indent=2, ensure_ascii=False)
                        
                        console.print(f"💾 Campos salvos em: campos_pca_descobertos_{ano}.json")
                        return True
                        
                    else:
                        console.print(f"⚠️ Nenhum dado de PCA encontrado em {ano}")
                        continue
                else:
                    console.print(f"❌ Erro na API para {ano}: {response.status_code}")
                    continue
                    
            except Exception as e:
                console.print(f"❌ Erro ao consultar PCAs em {ano}: {e}")
                continue
        
        console.print("❌ Não foi possível encontrar dados de PCA em nenhum ano testado")
        return False
    
    def gerar_sql_refinado(self):
        """Gera SQL refinado baseado nos campos descobertos"""
        console.print(Panel("🛠️ Gerando SQL refinado baseado nos campos descobertos", style="yellow"))
        
        # Verificar se os arquivos de descoberta existem
        import os
        
        arquivos_descoberta = []
        if os.path.exists("campos_atas_descobertos.json"):
            arquivos_descoberta.append("campos_atas_descobertos.json")
        
        for ano in [2024, 2025, 2023]:
            if os.path.exists(f"campos_pca_descobertos_{ano}.json"):
                arquivos_descoberta.append(f"campos_pca_descobertos_{ano}.json")
        
        if not arquivos_descoberta:
            console.print("⚠️ Nenhum arquivo de descoberta encontrado. Execute primeiro a descoberta de campos.")
            return
        
        sql_refinado = "-- SQL REFINADO baseado na descoberta de campos reais\\n\\n"
        
        for arquivo in arquivos_descoberta:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            
            tipo_tabela = "atas" if "atas" in arquivo else "pcas"
            sql_refinado += f"-- Campos descobertos para {tipo_tabela.upper()}\\n"
            sql_refinado += f"-- Baseado em: {arquivo}\\n"
            sql_refinado += f"-- Total de registros analisados: {dados['total_registros']}\\n\\n"
            
            for campo, info in dados["campos"].items():
                tipo_sql = self._mapear_tipo_sql(info["tipo"])
                comentario = f" -- Exemplo: {info['exemplo']}" if info["exemplo"] else ""
                sql_refinado += f"    {campo.replace('.', '_')} {tipo_sql},{comentario}\\n"
            
            sql_refinado += "\\n"
        
        # Salvar SQL refinado
        with open("sql_tabelas_refinado.sql", "w", encoding="utf-8") as f:
            f.write(sql_refinado)
        
        console.print("💾 SQL refinado salvo em: sql_tabelas_refinado.sql")
    
    def _mapear_tipo_sql(self, tipo_python):
        """Mapeia tipos Python para tipos SQL"""
        mapeamento = {
            "object": "TEXT",
            "int64": "INTEGER",
            "float64": "DECIMAL(15,2)",
            "bool": "BOOLEAN",
            "datetime64[ns]": "TIMESTAMPTZ"
        }
        return mapeamento.get(tipo_python, "TEXT")

def main():
    """Função principal"""
    console.print(Panel.fit(
        "[bold blue]GovGo V1 - Descobridor de Campos ATA/PCA[/bold blue]\\n"
        "Este script consulta as APIs do PNCP para descobrir\\n"
        "os campos reais de ATAs e PCAs e refinar a estrutura\\n"
        "das tabelas no banco de dados.",
        title="🔍 Campo Discoverer"
    ))
    
    discoverer = CamposDiscoverer()
    
    # Descobrir campos
    console.print("\\n🚀 Iniciando descoberta de campos...")
    
    # ATAs
    sucesso_atas = discoverer.descobrir_campos_atas()
    
    console.print("\\n" + "="*50 + "\\n")
    
    # PCAs
    sucesso_pcas = discoverer.descobrir_campos_pcas()
    
    console.print("\\n" + "="*50 + "\\n")
    
    # Gerar SQL refinado se houver algum sucesso
    if sucesso_atas or sucesso_pcas:
        discoverer.gerar_sql_refinado()
        console.print("\\n✅ [bold green]Descoberta concluída![/bold green]")
        console.print("🔧 Use os arquivos JSON e SQL gerados para refinar as tabelas ATAs e PCAs")
    else:
        console.print("\\n⚠️ [bold yellow]Nenhum campo foi descoberto.[/bold yellow]")
        console.print("🔧 As tabelas ATAs e PCAs foram criadas com estrutura baseada no Manual PNCP")

if __name__ == "__main__":
    main()
