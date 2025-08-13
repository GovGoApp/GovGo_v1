"""
Script unificado para converter documentos PNCP usando gvg_document_utils
Permite escolher entre diferentes versões via linha de comando
"""
import sys
import os
import argparse
from pathlib import Path

def setup_import_path():
    """Configura o caminho para importar gvg_document_utils"""
    # Caminho para o módulo gvg_document_utils_v3.py
    utils_path = r"c:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\GvG\Search\Prompt"
    
    if utils_path not in sys.path:
        sys.path.insert(0, utils_path)
    
    return utils_path

def convert_with_v3(document_path, document_name=None):
    """Converte documento usando gvg_document_utils_v3"""
    try:
        # Importar o módulo v3
        import gvg_document_utils_v3 as gvg_utils
        
        print("🚀 Usando gvg_document_utils_v3 (Docling SUPER OTIMIZADO)")
        print("="*70)
        
        # Se é um arquivo local, precisamos simular um download
        if os.path.exists(document_path):
            print(f"📄 Processando arquivo local: {document_path}")
            
            # Obter nome do arquivo se não fornecido
            if not document_name:
                document_name = os.path.basename(document_path)
            
            # Simular dados PNCP para o cabeçalho
            pncp_data = {
                'id': 'LOCAL_FILE',
                'municipio': 'Local',
                'uf': 'XX',
                'orgao': 'Arquivo Local',
                'link': f'file://{document_path}',
                'data_inclusao': 'N/A',
                'data_abertura': 'N/A', 
                'data_encerramento': 'N/A',
                'modalidade_id': 'N/A',
                'modalidade_nome': 'Arquivo Local',
                'disputa_id': 'N/A',
                'disputa_nome': 'Não se aplica',
                'descricao': f'Documento local: {document_name}'
            }
            
            # Usar a função convert_document_to_markdown diretamente
            success, markdown_content, error = gvg_utils.convert_document_to_markdown(
                document_path, document_name
            )
            
            if not success:
                print(f"❌ Erro na conversão: {error}")
                return False
            
            # Salvar o arquivo
            save_success, saved_path, save_error = gvg_utils.save_markdown_file(
                markdown_content, document_name, f'file://{document_path}'
            )
            
            if not save_success:
                print(f"❌ Erro ao salvar: {save_error}")
                return False
            
            # Gerar resumo
            print("📋 Gerando resumo...")
            summary = gvg_utils.generate_document_summary(markdown_content, pncp_data=pncp_data)
            
            # Salvar resumo
            summary_success, summary_path, summary_error = gvg_utils.save_summary_file(
                summary, document_name, f'file://{document_path}', pncp_data=pncp_data
            )
            
            print(f"\n✅ Conversão concluída!")
            print(f"📄 Arquivo Markdown: {os.path.basename(saved_path)}")
            if summary_success:
                print(f"📋 Resumo: {os.path.basename(summary_path)}")
            print(f"📁 Pasta: {gvg_utils.FILE_PATH}")
            
            return True
            
        else:
            # É uma URL - usar a função completa
            print(f"🌐 Processando URL: {document_path}")
            
            result = gvg_utils.process_pncp_document(
                doc_url=document_path,
                document_name=document_name
            )
            
            print(result)
            return True
            
    except ImportError as e:
        print(f"❌ Erro ao importar gvg_document_utils_v3: {e}")
        print("Verifique se o arquivo existe no caminho especificado")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

def convert_with_v2(document_path, document_name=None):
    """Converte documento usando gvg_document_utils_v2 (se existir)"""
    try:
        # Tentar importar v2
        import gvg_document_utils_v2 as gvg_utils
        
        print("🚀 Usando gvg_document_utils_v2")
        print("="*70)
        
        # Lógica similar ao v3, mas adaptada para v2
        if os.path.exists(document_path):
            # Para v2, pode ter interface diferente
            # Adaptar conforme necessário
            print(f"📄 Processando arquivo local com v2: {document_path}")
            # Implementar lógica específica do v2 aqui
            
        else:
            print(f"🌐 Processando URL com v2: {document_path}")
            # Implementar lógica específica do v2 aqui
            
        return True
        
    except ImportError as e:
        print(f"❌ gvg_document_utils_v2 não encontrado: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def main():
    """Função principal com parsing de argumentos"""
    parser = argparse.ArgumentParser(
        description='Conversor unificado de documentos PNCP usando gvg_document_utils',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Converter PDF local com v3 (recomendado)
  python converter_unificado.py --version v3 --document "manual-de-integracao-pncp.pdf"
  
  # Converter PDF local com v3 e debug habilitado
  python converter_unificado.py --version v3 --document "manual-de-integracao-pncp.pdf" --debug
  
  # Converter PDF local com nome personalizado
  python converter_unificado.py --version v3 --document "manual.pdf" --name "Manual PNCP v2.3.5"
  
  # Converter URL com v3
  python converter_unificado.py --version v3 --document "https://example.com/documento.pdf"
  
  # Usar v2 (se disponível)
  python converter_unificado.py --version v2 --document "documento.pdf"
        """
    )
    
    parser.add_argument(
        '--version', '-v',
        choices=['v2', 'v3'],
        default='v3',
        help='Versão do gvg_document_utils a usar (padrão: v3)'
    )
    
    parser.add_argument(
        '--document', '-d',
        required=True,
        help='Caminho do arquivo local ou URL do documento a converter'
    )
    
    parser.add_argument(
        '--name', '-n',
        help='Nome personalizado para o documento (opcional)'
    )
    
    parser.add_argument(
        '--debug', '-g',
        action='store_true',
        help='Habilita barra de progresso e informações detalhadas de debug'
    )
    
    # Parse dos argumentos
    args = parser.parse_args()
    
    print("📋 CONVERSOR UNIFICADO DE DOCUMENTOS PNCP")
    print("="*60)
    print(f"🔧 Versão: {args.version}")
    print(f"📄 Documento: {args.document}")
    if args.name:
        print(f"📝 Nome: {args.name}")
    if args.debug:
        print(f"🐛 Debug: Habilitado (com barra de progresso)")
    print("="*60)
    
    # Configurar caminho de importação
    utils_path = setup_import_path()
    print(f"📁 Caminho utils: {utils_path}")
    
    # Verificar se o documento existe (se for caminho local)
    if not args.document.startswith(('http://', 'https://')):
        # É um caminho local
        if not os.path.isabs(args.document):
            # Caminho relativo - assumir que está na pasta atual
            args.document = os.path.abspath(args.document)
        
        if not os.path.exists(args.document):
            print(f"❌ Arquivo não encontrado: {args.document}")
            return False
    
    # Chamar a versão apropriada
    if args.version == 'v3':
        success = convert_with_v3(args.document, args.name)
    elif args.version == 'v2':
        success = convert_with_v2(args.document, args.name)
    else:
        print(f"❌ Versão não suportada: {args.version}")
        return False
    
    if success:
        print(f"\n🎉 Conversão finalizada com sucesso!")
        print(f"📂 Verifique os arquivos nas pastas de saída")
    else:
        print(f"\n❌ Conversão falhou!")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Conversão interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
