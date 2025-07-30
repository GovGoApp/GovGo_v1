#!/usr/bin/env python3
"""
GovGo V1 - Executar Migração Completa
=====================================
Script master para executar toda a sequência de migração
FASE 2 + FASE 3 completas

SEQUÊNCIA DE EXECUÇÃO:
01. Configurar base Supabase
02. Descobrir campos API
03. Migrar dados locais
04. Coletar dados via API  
05. Reconciliar dados
06. Gerar relatório final
"""

import os
import sys
import subprocess
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
import time

console = Console()

class MigrationMaster:
    """Controlador master da migração GovGo V0 → V1"""
    
    def __init__(self):
        self.scripts_dir = os.path.dirname(__file__)
        self.scripts = [
            {
                "numero": "01",
                "nome": "setup_database.py",
                "titulo": "Configurar Base Supabase",
                "descricao": "Criar todas as tabelas no Supabase",
                "fase": "FASE 2"
            },
            {
                "numero": "02", 
                "nome": "descobrir_campos_ata_pca.py",
                "titulo": "Descobrir Campos API",
                "descricao": "Mapear campos das ATAs e PCAs",
                "fase": "FASE 2"
            },
            {
                "numero": "03",
                "nome": "migrate_from_local.py", 
                "titulo": "Migrar Dados Locais",
                "descricao": "Migrar SQLite V0 → Supabase V1",
                "fase": "FASE 3"
            },
            {
                "numero": "04",
                "nome": "collect_from_api.py",
                "titulo": "Coletar Dados via API",
                "descricao": "Buscar dados faltantes na API PNCP",
                "fase": "FASE 3"
            },
            {
                "numero": "05",
                "nome": "reconcile_data.py",
                "titulo": "Reconciliar Dados", 
                "descricao": "Unificar e resolver conflitos",
                "fase": "FASE 3"
            },
            {
                "numero": "06",
                "nome": "migration_report.py",
                "titulo": "Relatório Final",
                "descricao": "Validar e reportar migração",
                "fase": "FASE 3"
            }
        ]
        self.resultados = {}
        
    def mostrar_introducao(self):
        """Mostra introdução do processo"""
        console.print(Panel.fit(
            "[bold blue]GovGo V1 - Migração Completa V0 → V1[/bold blue]\n"
            "\n"
            "[yellow]FASE 2 - Estrutura do Banco:[/yellow]\n"
            "• 01. Configurar base Supabase (7 tabelas)\n"
            "• 02. Descobrir campos API (ATAs e PCAs)\n"
            "\n"
            "[green]FASE 3 - Migração Híbrida:[/green]\n"
            "• 03. Migrar dados locais (SQLite → Supabase)\n"
            "• 04. Coletar dados via API (dados faltantes)\n"
            "• 05. Reconciliar dados (resolver conflitos)\n"
            "• 06. Relatório final (validação completa)\n"
            "\n"
            "[cyan]Tempo estimado: 15-30 minutos[/cyan]",
            title="🚀 Master Migration Script"
        ))
        
        # Tabela dos scripts
        table = Table(title="Scripts da Migração")
        table.add_column("Nº", style="cyan", width=4)
        table.add_column("Script", style="blue", width=25)
        table.add_column("Fase", style="yellow", width=8)
        table.add_column("Descrição", style="green")
        
        for script in self.scripts:
            table.add_row(
                script["numero"],
                script["nome"],
                script["fase"], 
                script["descricao"]
            )
        
        console.print(table)
        
        console.print("\n⚠️ [yellow]ATENÇÃO:[/yellow]")
        console.print("• Certifique-se de que as credenciais do Supabase estão configuradas")
        console.print("• O banco SQLite V0 deve estar acessível")
        console.print("• A conexão com a internet é necessária para a API PNCP")
        
        resposta = console.input("\n🚀 Deseja continuar com a migração completa? [s/N]: ")
        return resposta.lower() in ['s', 'sim', 'y', 'yes']
    
    def executar_script(self, script_info):
        """Executa um script individual"""
        script_path = os.path.join(self.scripts_dir, f"{script_info['numero']}_{script_info['nome']}")
        
        if not os.path.exists(script_path):
            console.print(f"❌ Script não encontrado: {script_path}")
            return False
        
        console.print(f"\n🔄 Executando: {script_info['titulo']}")
        console.print(f"📄 Script: {script_info['numero']}_{script_info['nome']}")
        
        inicio = datetime.now()
        
        try:
            # Executar o script
            resultado = subprocess.run(
                [sys.executable, script_path],
                cwd=self.scripts_dir,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutos timeout
            )
            
            fim = datetime.now()
            duracao = (fim - inicio).total_seconds()
            
            # Processar resultado
            if resultado.returncode == 0:
                console.print(f"✅ {script_info['titulo']} concluído ({duracao:.1f}s)")
                status = "SUCESSO"
            else:
                console.print(f"❌ {script_info['titulo']} falhou ({duracao:.1f}s)")
                console.print(f"Erro: {resultado.stderr}")
                status = "FALHA"
            
            # Armazenar resultado
            self.resultados[script_info['numero']] = {
                "script": script_info['nome'],
                "titulo": script_info['titulo'],
                "status": status,
                "duracao": duracao,
                "stdout": resultado.stdout,
                "stderr": resultado.stderr,
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat()
            }
            
            return status == "SUCESSO"
            
        except subprocess.TimeoutExpired:
            console.print(f"⏱️ {script_info['titulo']} excedeu tempo limite (30min)")
            self.resultados[script_info['numero']] = {
                "script": script_info['nome'],
                "titulo": script_info['titulo'],
                "status": "TIMEOUT",
                "duracao": 1800,
                "erro": "Timeout de 30 minutos excedido"
            }
            return False
            
        except Exception as e:
            console.print(f"💥 Erro inesperado ao executar {script_info['titulo']}: {e}")
            self.resultados[script_info['numero']] = {
                "script": script_info['nome'],
                "titulo": script_info['titulo'],
                "status": "ERRO",
                "erro": str(e)
            }
            return False
    
    def executar_migracao_completa(self):
        """Executa toda a sequência de migração"""
        if not self.mostrar_introducao():
            console.print("❌ Migração cancelada pelo usuário")
            return False
        
        console.print("\n" + "="*60)
        console.print("🚀 INICIANDO MIGRAÇÃO COMPLETA")
        console.print("="*60)
        
        inicio_total = datetime.now()
        
        # Executar scripts em sequência
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Executando migração...", total=len(self.scripts))
            
            for i, script in enumerate(self.scripts):
                progress.update(task, description=f"[{script['fase']}] {script['titulo']}")
                
                sucesso = self.executar_script(script)
                
                if not sucesso:
                    console.print(f"\n❌ [bold red]MIGRAÇÃO INTERROMPIDA![/bold red]")
                    console.print(f"Falha no script: {script['titulo']}")
                    
                    # Perguntar se quer continuar
                    continuar = console.input("\n🤔 Deseja continuar mesmo assim? [s/N]: ")
                    if not continuar.lower() in ['s', 'sim', 'y', 'yes']:
                        console.print("🛑 Migração interrompida pelo usuário")
                        return False
                
                progress.advance(task)
                
                # Pausa entre scripts (exceto o último)
                if i < len(self.scripts) - 1:
                    time.sleep(2)
        
        fim_total = datetime.now()
        duracao_total = (fim_total - inicio_total).total_seconds()
        
        # Mostrar resultado final
        self.mostrar_resultado_final(duracao_total)
        
        # Salvar log completo
        self.salvar_log_execucao(inicio_total, fim_total)
        
        return True
    
    def mostrar_resultado_final(self, duracao_total):
        """Mostra resultado final da migração"""
        console.print("\n" + "="*60)
        console.print("📊 RESULTADO FINAL DA MIGRAÇÃO")
        console.print("="*60)
        
        # Contar sucessos e falhas
        sucessos = sum(1 for r in self.resultados.values() if r["status"] == "SUCESSO")
        falhas = sum(1 for r in self.resultados.values() if r["status"] in ["FALHA", "ERRO", "TIMEOUT"])
        
        # Status geral
        if falhas == 0:
            status_geral = "✅ SUCESSO COMPLETO"
            cor = "bold green"
        elif sucessos >= 4:  # Pelo menos migração básica funcionou
            status_geral = "🟡 SUCESSO PARCIAL"
            cor = "bold yellow"
        else:
            status_geral = "❌ FALHA CRÍTICA"
            cor = "bold red"
        
        console.print(f"[{cor}]{status_geral}[/{cor}]")
        console.print(f"Tempo total: {duracao_total/60:.1f} minutos")
        console.print(f"Scripts executados: {len(self.resultados)}/{len(self.scripts)}")
        console.print(f"Sucessos: {sucessos} | Falhas: {falhas}")
        
        # Tabela detalhada
        table = Table(title="Detalhes da Execução")
        table.add_column("Script", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Tempo", style="blue")
        table.add_column("Observações", style="green")
        
        for script in self.scripts:
            resultado = self.resultados.get(script["numero"], {"status": "NÃO EXECUTADO", "duracao": 0})
            
            if resultado["status"] == "SUCESSO":
                emoji = "✅"
                cor_status = "green"
            elif resultado["status"] in ["FALHA", "ERRO"]:
                emoji = "❌"
                cor_status = "red"
            elif resultado["status"] == "TIMEOUT":
                emoji = "⏱️"
                cor_status = "yellow"
            else:
                emoji = "⏸️"
                cor_status = "gray"
            
            observacao = ""
            if "erro" in resultado:
                observacao = resultado["erro"][:50] + "..." if len(resultado["erro"]) > 50 else resultado["erro"]
            
            table.add_row(
                f"{script['numero']}. {script['titulo']}",
                f"[{cor_status}]{emoji} {resultado['status']}[/{cor_status}]",
                f"{resultado.get('duracao', 0):.1f}s",
                observacao
            )
        
        console.print(table)
        
        # Próximos passos
        console.print("\n🎯 [bold blue]PRÓXIMOS PASSOS:[/bold blue]")
        
        if falhas == 0:
            console.print("🎉 Migração 100% concluída!")
            console.print("📊 Verifique o relatório final: relatorio_migracao_completo.json")
            console.print("🚀 O sistema V1 está pronto para uso!")
        elif sucessos >= 3:
            console.print("⚠️ Migração parcialmente concluída")
            console.print("🔧 Revise os scripts que falharam")
            console.print("📊 Verifique os relatórios gerados")
        else:
            console.print("❌ Migração com problemas críticos")
            console.print("🔧 Revise a configuração do Supabase")
            console.print("📞 Verifique conectividade e credenciais")
        
        console.print("\n💾 Log completo salvo em: migracao_completa_log.json")
    
    def salvar_log_execucao(self, inicio, fim):
        """Salva log completo da execução"""
        import json
        
        log = {
            "migracao_info": {
                "data_inicio": inicio.isoformat(),
                "data_fim": fim.isoformat(),
                "duracao_total_segundos": (fim - inicio).total_seconds(),
                "versao_origem": "V0 (SQLite)",
                "versao_destino": "V1 (Supabase)"
            },
            "scripts_executados": self.resultados,
            "estatisticas": {
                "total_scripts": len(self.scripts),
                "scripts_executados": len(self.resultados),
                "sucessos": sum(1 for r in self.resultados.values() if r["status"] == "SUCESSO"),
                "falhas": sum(1 for r in self.resultados.values() if r["status"] in ["FALHA", "ERRO", "TIMEOUT"])
            }
        }
        
        with open("migracao_completa_log.json", "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        
        console.print("💾 Log salvo: migracao_completa_log.json")

def main():
    """Função principal"""
    master = MigrationMaster()
    
    console.print(Panel.fit(
        "[bold blue]GovGo V1 - Master Migration Script[/bold blue]\n"
        "Script controlador para migração completa V0 → V1",
        title="🎯 Migration Master"
    ))
    
    if master.executar_migracao_completa():
        console.print("\n🏁 [bold green]MIGRAÇÃO MASTER CONCLUÍDA![/bold green]")
    else:
        console.print("\n🛑 [bold red]MIGRAÇÃO MASTER INTERROMPIDA[/bold red]")
        exit(1)

if __name__ == "__main__":
    main()
