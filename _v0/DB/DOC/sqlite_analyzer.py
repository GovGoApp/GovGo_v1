#!/usr/bin/env python3
"""
Script para análise completa de estrutura de database SQLite
Gera relatório detalhado com todas as informações da database
"""

import sqlite3
import sys
import os
from datetime import datetime

def analyze_sqlite_database(db_path):
    """
    Analisa completamente uma database SQLite e gera relatório
    
    Args:
        db_path (str): Caminho para o arquivo SQLite
    """
    
    if not os.path.exists(db_path):
        print(f"❌ Arquivo não encontrado: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("="*80)
        print(f"📊 ANÁLISE DE ESTRUTURA SQLite")
        print("="*80)
        print(f"📁 Arquivo: {db_path}")
        print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # 1. INFORMAÇÕES GERAIS
        print("\n🔍 1. INFORMAÇÕES GERAIS")
        print("-" * 40)
        
        cursor.execute("PRAGMA database_list;")
        databases = cursor.fetchall()
        print(f"Databases: {len(databases)}")
        for db in databases:
            print(f"  - {db[1]}: {db[2] if db[2] else 'main'}")
        
        cursor.execute("PRAGMA user_version;")
        version = cursor.fetchone()[0]
        print(f"Versão do usuário: {version}")
        
        cursor.execute("PRAGMA page_count;")
        page_count = cursor.fetchone()[0]
        print(f"Páginas: {page_count}")
        
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]
        print(f"Tamanho da página: {page_size} bytes")
        
        cursor.execute("PRAGMA freelist_count;")
        freelist = cursor.fetchone()[0]
        print(f"Páginas livres: {freelist}")
        
        # 2. TABELAS
        print("\n📋 2. TABELAS")
        print("-" * 40)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        print(f"Total de tabelas: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            print(f"\n🔸 Tabela: {table_name}")
            
            # Informações da tabela
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            print(f"  Colunas: {len(columns)}")
            for col in columns:
                pk = " [PK]" if col[5] else ""
                not_null = " [NOT NULL]" if col[3] else ""
                default = f" [DEFAULT: {col[4]}]" if col[4] else ""
                print(f"    {col[1]}: {col[2]}{pk}{not_null}{default}")
            
            # Contagem de registros
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"  Registros: {count:,}")
            except Exception as e:
                print(f"  Registros: Erro ao contar - {e}")
        
        # 3. ÍNDICES
        print("\n🔍 3. ÍNDICES")
        print("-" * 40)
        
        cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name;")
        indexes = cursor.fetchall()
        
        print(f"Total de índices: {len(indexes)}")
        
        current_table = None
        for index in indexes:
            if index[1] != current_table:
                current_table = index[1]
                print(f"\n🔸 Tabela: {current_table}")
            
            print(f"  📌 {index[0]}")
            if index[2]:
                print(f"    SQL: {index[2]}")
        
        # 4. VIEWS
        print("\n👁️ 4. VIEWS")
        print("-" * 40)
        
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='view' ORDER BY name;")
        views = cursor.fetchall()
        
        print(f"Total de views: {len(views)}")
        
        for view in views:
            print(f"\n🔸 View: {view[0]}")
            print(f"  SQL: {view[1]}")
        
        # 5. TRIGGERS
        print("\n⚡ 5. TRIGGERS")
        print("-" * 40)
        
        cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger' ORDER BY tbl_name, name;")
        triggers = cursor.fetchall()
        
        print(f"Total de triggers: {len(triggers)}")
        
        current_table = None
        for trigger in triggers:
            if trigger[1] != current_table:
                current_table = trigger[1]
                print(f"\n🔸 Tabela: {current_table}")
            
            print(f"  ⚡ {trigger[0]}")
            if trigger[2]:
                print(f"    SQL: {trigger[2]}")
        
        # 6. CHAVES ESTRANGEIRAS
        print("\n🔗 6. CHAVES ESTRANGEIRAS")
        print("-" * 40)
        
        fk_found = False
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            fkeys = cursor.fetchall()
            
            if fkeys:
                if not fk_found:
                    fk_found = True
                
                print(f"\n🔸 Tabela: {table_name}")
                for fk in fkeys:
                    print(f"  🔗 {fk[3]} -> {fk[2]}.{fk[4]}")
        
        if not fk_found:
            print("Nenhuma chave estrangeira encontrada")
        
        # 7. CREATE STATEMENTS
        print("\n📄 7. CREATE STATEMENTS")
        print("-" * 40)
        
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name;")
        creates = cursor.fetchall()
        
        for create in creates:
            print(f"\n🔸 {create[0]}:")
            print(f"{create[1]}")
        
        # 8. VERIFICAÇÃO DE INTEGRIDADE
        print("\n✅ 8. VERIFICAÇÃO DE INTEGRIDADE")
        print("-" * 40)
        
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchall()
        
        for check in integrity:
            print(f"  {check[0]}")
        
        conn.close()
        
        print("\n" + "="*80)
        print("✅ Análise concluída!")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Erro ao analisar database: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Função principal"""
    if len(sys.argv) != 2:
        print("Uso: python sqlite_analyzer.py <caminho_database.db>")
        print("\nExemplo:")
        print("  python sqlite_analyzer.py database.db")
        print("  python sqlite_analyzer.py /path/to/database.sqlite")
        return
    
    db_path = sys.argv[1]
    analyze_sqlite_database(db_path)

if __name__ == "__main__":
    main()
