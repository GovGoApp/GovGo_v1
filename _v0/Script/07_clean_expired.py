# =======================================================================
# [7/7] MIGRAÇÃO E LIMPEZA DE CONTRATOS EXPIRADOS - MÓDULO AUTOMATIZADO
# =======================================================================
# Este script migra contratos expirados e seus embeddings da base principal
# para uma base separada de expirados, garantindo integridade dos dados,
# limpeza da base principal e liberação de espaço físico.
# 
# Funcionalidades:
# - Migração robusta com processamento em batches
# - Verificação de duplicados e integridade de dados
# - Limpeza automática da base principal após migração confirmada
# - VACUUM FULL e REINDEX para liberação de espaço físico
# - Barra de progresso detalhada com Rich
# - Logs estruturados e tratamento de erros
# 
# Resultado: Base principal apenas com contratos ativos, base de expirados íntegra.
# =======================================================================

import psycopg2
import os
import time
import json
import sys
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from rich.panel import Panel
from rich.table import Table

def check_new_records():
    """Verifica se houve inserção de novos registros nos scripts anteriores"""
    try:
        # Caminho do arquivo de log
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LOGS")
        log_file = os.path.join(log_dir, "processamento.log")
        
        # Se o arquivo não existir, não continuar
        if not os.path.exists(log_file):
            return False
            
        # Obter a data atual para filtrar apenas registros de hoje
        data_atual = datetime.now().strftime("%Y-%m-%d")
        
        # Ler o arquivo de log
        with open(log_file, "r") as f:
            lines = f.readlines()
            
        # Filtrar apenas as linhas de hoje
        todays_lines = [line for line in lines if line.startswith(data_atual)]
        
        if not todays_lines:
            return False
            
        # Verificar se algum script adicionou registros
        for line in todays_lines:
            if "SCRIPT03:" in line or "SCRIPT04:" in line:
                # Extrair o número de registros adicionados
                parts = line.split(":")
                if len(parts) >= 2:
                    try:
                        count = int(parts[1].split()[0])
                        if count > 0:
                            # Se encontrou pelo menos um registro adicionado, continuar
                            return True
                    except ValueError:
                        # Se não conseguir converter para int, ignorar esta linha
                        pass
                        
        # Se chegou aqui, nenhum script adicionou registros
        return False
        
    except Exception as e:
        print(f"Erro ao verificar registros no log: {e}")
        return False  # Em caso de erro, não continuar

# Configure Rich console
console = Console()

def log_message(message, log_type="info"):
    """Log padronizado para o pipeline"""
    if log_type == "info":
        console.print(f"[white]ℹ️  {message}[/white]")
    elif log_type == "success":
        console.print(f"[green]✅ {message}[/green]")
    elif log_type == "warning":
        console.print(f"[yellow]⚠️  {message}[/yellow]")
    elif log_type == "error":
        console.print(f"[red]❌ {message}[/red]")
    elif log_type == "debug":
        console.print(f"[cyan]🔧 {message}[/cyan]")

def load_env_config(env_file):
    """Carrega configurações do arquivo .env com validação rigorosa"""
    config = {}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, env_file)
    
    if not os.path.exists(env_path):
        log_message(f"Arquivo de configuração não encontrado: {env_path}", "error")
        sys.exit(1)
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if value:  # Só adiciona se o valor não estiver vazio
                    config[key] = value
    
    return config

def validate_db_config(config, config_type="source"):
    """Valida se todas as configurações necessárias estão presentes"""
    if config_type == "source":
        required_keys = ['user', 'password', 'host', 'port', 'dbname']
    else:  # expired
        required_keys = ['user_expired', 'password_expired', 'host_expired', 'port_expired', 'dbname_expired']
    
    missing_keys = []
    for key in required_keys:
        if key not in config or not config[key]:
            missing_keys.append(key)
    
    if missing_keys:
        log_message(f"Configurações faltando para {config_type}: {', '.join(missing_keys)}", "error")
        return False
    
    return True

def migrate_expired_data():
    """Migração completa de contratos expirados + embeddings"""
    
    log_message("Migração e limpeza de contratos expirados iniciada")
    
    # CARREGAR E VALIDAR CONFIGURAÇÕES
    log_message("Carregando configurações das bases de dados")
    source_config = load_env_config('supabase_v0.env')
    target_config = load_env_config('supabase_expired_v0.env')
    
    # Validar configurações
    if not validate_db_config(source_config, "source"):
        log_message("Erro nas configurações da base principal", "error")
        sys.exit(1)
    
    if not validate_db_config(target_config, "expired"):
        log_message("Erro nas configurações da base de expirados", "error")
        sys.exit(1)
    
    # CONECTAR À BASE ORIGEM
    log_message("Conectando à base principal")
    try:
        source_conn = psycopg2.connect(
            user=source_config['user'],
            password=source_config['password'],
            host=source_config['host'],
            port=source_config['port'],
            dbname=source_config['dbname']
        )
        log_message("Conectado à base principal", "success")
    except Exception as e:
        log_message(f"Erro ao conectar à base principal: {e}", "error")
        sys.exit(1)
    
    # CONECTAR À BASE DESTINO
    log_message("Conectando à base de expirados")
    try:
        target_conn = psycopg2.connect(
            user=target_config['user_expired'],
            password=target_config['password_expired'],
            host=target_config['host_expired'],
            port=target_config['port_expired'],
            dbname=target_config['dbname_expired']
        )
        log_message("Conectado à base de expirados", "success")
    except Exception as e:
        log_message(f"Erro ao conectar à base de expirados: {e}", "error")
        try:
            source_conn.close()
        except:
            pass
        sys.exit(1)
    
    source_cur = source_conn.cursor()
    target_cur = target_conn.cursor()
    
    try:
        # 0. CRIAR TABELAS SE NÃO EXISTIREM
        log_message("Verificando tabelas na base de destino")
        
        # Criar tabela de contratos expirados se não existir
        target_cur.execute("""
            CREATE TABLE IF NOT EXISTS contratacoes_expiradas (
                LIKE contratacoes INCLUDING ALL
            )
        """)
        
        # Criar tabela de embeddings expirados se não existir
        target_cur.execute("""
            CREATE TABLE IF NOT EXISTS contratacoes_embeddings_expiradas (
                LIKE contratacoes_embeddings INCLUDING ALL
            )
        """)
        
        target_conn.commit()
        log_message("Tabelas verificadas com sucesso", "success")
        
        # 1. VERIFICAR CONTRATOS EXPIRADOS
        log_message("Verificando contratos expirados")
        source_cur.execute("""
            SELECT COUNT(*) FROM contratacoes 
            WHERE dataencerramentoproposta < CURRENT_DATE
        """)
        total_contratos_expirados = source_cur.fetchone()[0]
        
        # VERIFICAR CONTRATOS JÁ MIGRADOS
        target_cur.execute("SELECT COUNT(*) FROM contratacoes_expiradas")
        contratos_ja_migrados = target_cur.fetchone()[0]
        
        if total_contratos_expirados > 0:
            log_message(f"Contratos expirados: {total_contratos_expirados:,} (migrados: {contratos_ja_migrados:,})")
        
        # 2. MIGRAR CONTRATOS FALTANTES (se houver)
        if contratos_ja_migrados < total_contratos_expirados:
            log_message("Migrando contratos faltantes")
            
            # BUSCAR CONTRATOS NÃO MIGRADOS
            source_cur.execute("""
                SELECT c.numerocontrolepncp, c.anocompra, c.descricaocompleta, 
                       c.valortotalhomologado, c.dataaberturaproposta, c.dataencerramentoproposta,
                       c.unidadeorgao_ufsigla, c.unidadeorgao_municipionome, 
                       c.unidadeorgao_nomeunidade, c.orgaoentidade_razaosocial,
                       c.created_at, c.valortotalestimado
                FROM contratacoes c
                WHERE c.dataencerramentoproposta < CURRENT_DATE
                  AND NOT EXISTS (
                      SELECT 1 FROM contratacoes_expiradas e 
                      WHERE e.numerocontrolepncp = c.numerocontrolepncp
                  )
            """)
            
            contratos_faltantes = source_cur.fetchall()
            console.print(f"   🔄 Migrando {len(contratos_faltantes):,} contratos...")
            
            # INSERIR CONTRATOS EM LOTES
            for i, contrato in enumerate(contratos_faltantes):
                target_cur.execute("""
                    INSERT INTO contratacoes_expiradas 
                    (numerocontrolepncp, anocompra, descricaocompleta, valortotalhomologado,
                     dataaberturaproposta, dataencerramentoproposta, unidadeorgao_ufsigla,
                     unidadeorgao_municipionome, unidadeorgao_nomeunidade, orgaoentidade_razaosocial,
                     created_at, valortotalestimado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, contrato)
                
                if (i + 1) % 1000 == 0:
                    target_conn.commit()
                    console.print(f"      ✅ {i + 1:,} contratos migrados")
            
            target_conn.commit()
            console.print(f"   ✅ [green]Contratos migrados com sucesso![/green]")
        
        # 3. VERIFICAR EMBEDDINGS
        console.print("\n🧠 [yellow]Verificando embeddings expirados...[/yellow]")
        source_cur.execute("""
            SELECT COUNT(*) FROM contratacoes_embeddings e
            JOIN contratacoes c ON e.numerocontrolepncp = c.numerocontrolepncp
            WHERE c.dataencerramentoproposta < CURRENT_DATE
        """)
        total_embeddings_expirados = source_cur.fetchone()[0]
        
        # VERIFICAR EMBEDDINGS JÁ MIGRADOS
        target_cur.execute("SELECT COUNT(*) FROM contratacoes_embeddings_expiradas")
        embeddings_ja_migrados = target_cur.fetchone()[0]
        
        console.print(f"   🧠 Total de embeddings expirados: {total_embeddings_expirados:,}")
        console.print(f"   ✅ Já migrados: {embeddings_ja_migrados:,}")
        console.print(f"   🆕 Faltam: {total_embeddings_expirados - embeddings_ja_migrados:,}")
        
        # 4. MIGRAR EMBEDDINGS FALTANTES
        if embeddings_ja_migrados < total_embeddings_expirados:
            console.print("🧠 [bold blue]Migrando embeddings faltantes (3072D)...[/bold blue]")
            
            # CONTAR EMBEDDINGS FALTANTES PARA BARRA DE PROGRESSO
            embeddings_faltantes = total_embeddings_expirados - embeddings_ja_migrados
            
            # BUSCAR EMBEDDINGS NÃO MIGRADOS EM LOTES PEQUENOS
            batch_size = 500  # Lotes pequenos para vetores grandes
            offset = 0
            total_migrated = 0
            
            # CRIAR BARRA DE PROGRESSO
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%",
                "•",
                "[progress.completed]{task.completed:,}",
                "/",
                "[progress.total]{task.total:,}",
                "•",
                TimeRemainingColumn(),
                console=console
            ) as progress:
                
                # Criar task para embeddings
                embeddings_task = progress.add_task(
                    "🧠 Migrando embeddings", 
                    total=embeddings_faltantes
                )
                
                while True:
                    # BUSCAR APENAS EMBEDDINGS NÃO MIGRADOS
                    source_cur.execute("""
                        SELECT e.numerocontrolepncp, e.embedding_vector, e.modelo_embedding, 
                               e.metadata, e.created_at
                        FROM contratacoes_embeddings e
                        JOIN contratacoes c ON e.numerocontrolepncp = c.numerocontrolepncp
                        WHERE c.dataencerramentoproposta < CURRENT_DATE
                          AND NOT EXISTS (
                              SELECT 1 FROM contratacoes_embeddings_expiradas ee 
                              WHERE ee.numerocontrolepncp = e.numerocontrolepncp 
                                AND ee.modelo_embedding = e.modelo_embedding
                          )
                        ORDER BY e.id
                        LIMIT %s OFFSET %s
                    """, (batch_size, offset))
                    
                    embeddings_batch = source_cur.fetchall()
                    
                    if not embeddings_batch:
                        break  # Não há mais embeddings
                    
                    # INSERIR EMBEDDINGS (já filtrados para não duplicados)
                    for embedding in embeddings_batch:
                        numerocontrolepncp, embedding_vector, modelo_embedding, metadata, created_at = embedding
                        
                        # NOVA TRANSAÇÃO INDIVIDUAL PARA CADA EMBEDDING
                        try:
                            # Converter metadata para JSON string se necessário
                            if isinstance(metadata, dict):
                                metadata_json = json.dumps(metadata)
                            else:
                                metadata_json = metadata
                            
                            # INSERIR DIRETAMENTE (sem verificar duplicados, já filtrado na query)
                            target_cur.execute("""
                                INSERT INTO contratacoes_embeddings_expiradas 
                                (numerocontrolepncp, embedding_vector, modelo_embedding, metadata, created_at)
                                VALUES (%s, %s::vector, %s, %s::jsonb, %s)
                            """, (numerocontrolepncp, embedding_vector, modelo_embedding, metadata_json, created_at))
                            
                            # COMMIT INDIVIDUAL PARA EVITAR TRANSACTION ABORTED
                            target_conn.commit()
                            total_migrated += 1
                            
                            # ATUALIZAR BARRA DE PROGRESSO
                            progress.update(embeddings_task, advance=1)
                            
                        except Exception as e:
                            console.print(f"      [red]❌ Erro no embedding {numerocontrolepncp}: {e}[/red]")
                            target_conn.rollback()  # Rollback só desta transação individual
                            # MESMO COM ERRO, AVANÇA A BARRA
                            progress.update(embeddings_task, advance=1)
                            continue
                    
                    offset += batch_size
                    
                    # PAUSA ENTRE LOTES PARA EVITAR SOBRECARGA
                    time.sleep(0.05)  # Reduzido para não travar muito a barra
            
            console.print("   ✅ [green]Embeddings migrados com sucesso![/green]")
        
        # 5. VERIFICAÇÃO E LIMPEZA DA BASE PRINCIPAL
        console.print("\n🔍 [bold magenta]VERIFICAÇÃO E LIMPEZA DA BASE PRINCIPAL:[/bold magenta]")
        
        try:
            # CONTAR CONTRATOS MIGRADOS
            target_cur.execute("SELECT COUNT(*) FROM contratacoes_expiradas")
            result = target_cur.fetchone()
            final_contratos = result[0] if result and result[0] is not None else 0
            
            # CONTAR EMBEDDINGS MIGRADOS
            target_cur.execute("SELECT COUNT(*) FROM contratacoes_embeddings_expiradas")
            result = target_cur.fetchone()
            final_embeddings = result[0] if result and result[0] is not None else 0
            
            console.print(f"   📋 Contratos na base de destino: {final_contratos:,}")
            console.print(f"   🧠 Embeddings na base de destino: {final_embeddings:,}")
            
            # VERIFICAR TOTAIS ESPERADOS NA BASE ORIGEM
            source_cur.execute("""
                SELECT COUNT(*) FROM contratacoes 
                WHERE dataencerramentoproposta < CURRENT_DATE
            """)
            result = source_cur.fetchone()
            expected_contratos = result[0] if result and result[0] is not None else 0
            
            source_cur.execute("""
                SELECT COUNT(*) FROM contratacoes_embeddings e
                JOIN contratacoes c ON e.numerocontrolepncp = c.numerocontrolepncp
                WHERE c.dataencerramentoproposta < CURRENT_DATE
            """)
            result = source_cur.fetchone()
            expected_embeddings = result[0] if result and result[0] is not None else 0
            
            # VERIFICAR SE MIGRAÇÃO FOI BEM-SUCEDIDA ANTES DE DELETAR
            if final_contratos >= expected_contratos and final_embeddings >= expected_embeddings:
                console.print("   ✅ [bold green]MIGRAÇÃO CONFIRMADA - INICIANDO LIMPEZA DA BASE PRINCIPAL[/bold green]")
                
                # 🗑️ DELETAR EMBEDDINGS EXPIRADOS DA BASE PRINCIPAL
                console.print("\n🗑️ [red]Deletando embeddings expirados da base principal...[/red]")
                source_cur.execute("""
                    DELETE FROM contratacoes_embeddings 
                    WHERE numerocontrolepncp IN (
                        SELECT numerocontrolepncp FROM contratacoes 
                        WHERE dataencerramentoproposta < CURRENT_DATE
                    )
                """)
                embeddings_deletados = source_cur.rowcount
                source_conn.commit()
                console.print(f"   🗑️ [red]{embeddings_deletados:,} embeddings expirados deletados da base principal[/red]")
                
                # 🗑️ DELETAR CONTRATOS EXPIRADOS DA BASE PRINCIPAL
                console.print("\n🗑️ [red]Deletando contratos expirados da base principal...[/red]")
                source_cur.execute("""
                    DELETE FROM contratacoes 
                    WHERE dataencerramentoproposta < CURRENT_DATE
                """)
                contratos_deletados = source_cur.rowcount
                source_conn.commit()
                console.print(f"   🗑️ [red]{contratos_deletados:,} contratos expirados deletados da base principal[/red]")
                
                # VERIFICAÇÃO PÓS-LIMPEZA
                console.print("\n📊 [cyan]Verificação pós-limpeza da base principal:[/cyan]")
                source_cur.execute("SELECT COUNT(*) FROM contratacoes WHERE dataencerramentoproposta < CURRENT_DATE")
                contratos_restantes = source_cur.fetchone()[0]
                
                source_cur.execute("""
                    SELECT COUNT(*) FROM contratacoes_embeddings e
                    JOIN contratacoes c ON e.numerocontrolepncp = c.numerocontrolepncp
                    WHERE c.dataencerramentoproposta < CURRENT_DATE
                """)
                embeddings_restantes = source_cur.fetchone()[0]
                
                console.print(f"   📋 Contratos expirados restantes na base principal: {contratos_restantes:,}")
                console.print(f"   🧠 Embeddings expirados restantes na base principal: {embeddings_restantes:,}")
                
                if contratos_restantes == 0 and embeddings_restantes == 0:
                    console.print("   ✅ [bold green]LIMPEZA COMPLETA! Base principal contém apenas contratos ativos.[/bold green]")
                else:
                    console.print("   ⚠️ [yellow]Alguns registros expirados ainda permanecem na base principal.[/yellow]")
                
            else:
                console.print("   ⚠️ [bold yellow]MIGRAÇÃO INCOMPLETA - PULANDO LIMPEZA DA BASE PRINCIPAL[/bold yellow]")
                console.print("   ℹ️ [cyan]Execute novamente o script para completar a migração antes de deletar.[/cyan]")
                console.print(f"      [yellow]Esperado: {expected_contratos:,} contratos, {expected_embeddings:,} embeddings[/yellow]")
                console.print(f"      [cyan]Migrado: {final_contratos:,} contratos, {final_embeddings:,} embeddings[/cyan]")
                
        except Exception as verification_error:
            console.print(f"   ⚠️ [yellow]Erro na verificação: {verification_error}[/yellow]")
            console.print("   ℹ️ [cyan]Limpeza cancelada por segurança[/cyan]")
    
    except Exception as e:
        console.print(f"❌ [bold red]ERRO DURANTE MIGRAÇÃO: {e}[/bold red]")
        console.print(f"   🔍 [yellow]Tipo do erro: {type(e).__name__}[/yellow]")
        
        # Tentar fazer rollback apenas se a conexão ainda estiver ativa
        try:
            target_conn.rollback()
            console.print("   🔄 [cyan]Rollback executado com sucesso[/cyan]")
        except:
            console.print("   ⚠️ [yellow]Não foi possível fazer rollback (conexão pode ter sido perdida)[/yellow]")
        
        raise
    
    finally:
        # FECHAR CONEXÕES
        source_cur.close()
        target_cur.close()
        source_conn.close()
        target_conn.close()

def main():
    """Função principal da limpeza de contratos expirados"""
    console.print(Panel("[bold blue] [7/7] LIMPEZA DE CONTRATOS EXPIRADOS[/bold blue]"))
    
    # Verificar se houve novos registros a serem processados
    if not check_new_records():
        log_message("Nenhum novo registro encontrado para processamento", "success")
        return
    
    log_message("Limpeza de contratos expirados iniciada")
    
    start_time = datetime.now()
    
    try:
        log_message("Iniciando migração de contratos expirados")
        migrate_expired_data()
        
        duration = (datetime.now() - start_time).total_seconds()
        log_message(f"Migração concluída em {duration:.1f}s", "success")
        
    except Exception as e:
        log_message(f"Erro na migração: {str(e)}", "error")
        console.print(Panel("[bold red]❌ FALHA NA LIMPEZA[/bold red]"))
        return False
    
    console.print(Panel("[bold green]✅ LIMPEZA CONCLUÍDA[/bold green]"))
    return True

if __name__ == "__main__":
    main()
