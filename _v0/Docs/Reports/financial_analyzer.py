#!/usr/bin/env python3
"""
Analisador Financeiro Automático
Integra o conversor universal com assistente OpenAI para análise completa de DRE

Fluxo:
1. Recebe arquivo Excel do Zoho
2. Converte para Markdown usando universal_converter
3. Envia para assistente OpenAI especializado em DRE
4. Salva análise na mesma pasta do arquivo original
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import argparse
from datetime import datetime

# Importar OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("❌ Erro: Biblioteca OpenAI não instalada")
    print("💡 Execute: pip install openai")
    sys.exit(1)

# Importar o conversor universal
try:
    from universal_converter import UniversalToMarkdownConverter
except ImportError:
    print("❌ Erro: universal_converter.py não encontrado")
    print("💡 Certifique-se de que o arquivo está na mesma pasta")
    sys.exit(1)

class FinancialAnalyzer:
    """Analisador financeiro automático com IA"""
    
    def __init__(self, env_file: str = "openai.env"):
        """
        Inicializa o analisador
        
        Args:
            env_file: Arquivo com configurações OpenAI
        """
        self.assistant_id = "asst_G8pkl29kFjPbAhYlS2kAclsU"
        self.client = None
        self.converter = UniversalToMarkdownConverter(decimal_places=4)
        
        # Carregar configurações OpenAI
        self._load_openai_config(env_file)
    
    def _load_openai_config(self, env_file: str):
        """Carrega configurações OpenAI do arquivo .env"""
        try:
            env_path = Path(__file__).parent / env_file
            
            if not env_path.exists():
                raise FileNotFoundError(f"Arquivo {env_file} não encontrado")
            
            # Ler chave da API
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('api_key='):
                        api_key = line.split('=', 1)[1].strip()
                        break
                else:
                    raise ValueError("api_key não encontrada no arquivo .env")
            
            # Inicializar cliente OpenAI
            self.client = OpenAI(api_key=api_key)
            print("✅ Cliente OpenAI inicializado com sucesso")
            
            # Verificar se o assistente existe
            self._verify_assistant()
            
        except Exception as e:
            print(f"❌ Erro ao carregar configurações OpenAI: {e}")
            sys.exit(1)
    
    def _verify_assistant(self):
        """Verifica se o assistente existe e está acessível"""
        try:
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            print(f"✅ Assistente verificado: {assistant.name}")
            return True
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível verificar assistente {self.assistant_id}: {e}")
            print("💡 Continuando mesmo assim...")
            return False
    
    def convert_to_markdown(self, excel_file: str) -> str:
        """
        Converte arquivo Excel para Markdown
        
        Args:
            excel_file: Caminho do arquivo Excel
            
        Returns:
            Caminho do arquivo Markdown gerado
        """
        print("🔄 ETAPA 1: Convertendo Excel para Markdown")
        print("=" * 60)
        
        try:
            # Verificar se arquivo existe
            if not os.path.exists(excel_file):
                raise FileNotFoundError(f"Arquivo não encontrado: {excel_file}")
            
            # Converter usando o conversor universal
            md_file = self.converter.convert_file_to_markdown(excel_file)
            
            print(f"✅ Conversão concluída: {md_file}")
            return md_file
            
        except Exception as e:
            print(f"❌ Erro na conversão: {e}")
            raise
    
    def upload_file_to_openai(self, file_path: str) -> str:
        """
        Faz upload do arquivo para OpenAI
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            ID do arquivo no OpenAI
        """
        print("📤 ETAPA 2: Upload do arquivo para OpenAI")
        print("=" * 60)
        
        try:
            with open(file_path, 'rb') as f:
                file_obj = self.client.files.create(
                    file=f,
                    purpose='assistants'
                )
            
            print(f"✅ Arquivo enviado - ID: {file_obj.id}")
            
            # Aguardar um pouco para processamento
            import time
            time.sleep(5)
            
            return file_obj.id
            
        except Exception as e:
            print(f"❌ Erro no upload: {e}")
            raise
    
    def create_thread_and_run(self, file_id: str, prompt: str = None) -> str:
        """
        Cria thread e executa análise com o assistente
        
        Args:
            file_id: ID do arquivo no OpenAI
            prompt: Prompt personalizado (opcional)
            
        Returns:
            Resposta do assistente
        """
        print("🤖 ETAPA 3: Análise com Assistente IA")
        print("=" * 60)
        
        if not prompt:
            prompt = "Análise focada em 1) variação das grande contas contábeis ao longo do ano e 2) variações críticas das contas contábeis entre os dois últimos meses"

        try:
            # Criar thread
            thread = self.client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "attachments": [
                            {
                                "file_id": file_id,
                                "tools": [{"type": "file_search"}]
                            }
                        ]
                    }
                ]
            )
            
            print(f"📝 Thread criada: {thread.id}")
            
            # Executar assistente
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            print(f"🚀 Execução iniciada: {run.id}")
            
            # Aguardar conclusão com timeout
            print("⏳ Aguardando análise...")
            max_wait_time = 300  # 5 minutos máximo
            wait_time = 0
            check_interval = 3   # Verificar a cada 3 segundos
            
            import time
            while wait_time < max_wait_time:
                try:
                    run_status = self.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                    
                    # Log menos frequente para evitar spam
                    if wait_time % 15 == 0:  # Log a cada 15 segundos
                        elapsed_min = wait_time // 60
                        elapsed_sec = wait_time % 60
                        print(f"📊 Status: {run_status.status} (tempo: {elapsed_min}m{elapsed_sec}s)")
                    
                    if run_status.status == 'completed':
                        break
                    elif run_status.status in ['failed', 'cancelled', 'expired']:
                        error_msg = f"Execução falhou: {run_status.status}"
                        if hasattr(run_status, 'last_error') and run_status.last_error:
                            error_msg += f" - {run_status.last_error}"
                        print(f"❌ {error_msg}")
                        # Aguardar mais um pouco e tentar novamente
                        print("🔄 Aguardando mais tempo...")
                        time.sleep(10)
                        continue
                    elif run_status.status == 'requires_action':
                        print("⚠️ Assistente requer ação - verificando...")
                        if hasattr(run_status, 'required_action') and run_status.required_action:
                            print(f"🔧 Ação requerida: {run_status.required_action}")
                    
                    time.sleep(check_interval)
                    wait_time += check_interval
                    
                except Exception as api_error:
                    print(f"⚠️ Erro ao verificar status: {api_error}")
                    time.sleep(check_interval)
                    wait_time += check_interval
            
            # Verificar se deu timeout
            if wait_time >= max_wait_time:
                print(f"⏰ Timeout após {max_wait_time//60} minutos")
                print("💡 Tentando cancelar execução...")
                try:
                    self.client.beta.threads.runs.cancel(thread_id=thread.id, run_id=run.id)
                    print("✅ Execução cancelada")
                except:
                    print("⚠️ Não foi possível cancelar execução")
                raise Exception(f"Timeout na análise após {max_wait_time//60} minutos")
            
            # Obter resposta
            print("📨 Obtendo resposta do assistente...")
            messages = self.client.beta.threads.messages.list(thread_id=thread.id)
            
            # Buscar última mensagem do assistente
            response_text = ""
            for message in messages.data:
                if message.role == 'assistant':
                    for content in message.content:
                        if hasattr(content, 'text'):
                            response_text += content.text.value
                    break
            
            if not response_text:
                # Tentar obter última mensagem independente do role
                print("⚠️ Nenhuma resposta do assistente encontrada, verificando todas as mensagens...")
                for message in messages.data:
                    print(f"📧 Mensagem de {message.role}: {len(str(message.content))} chars")
                    if len(str(message.content)) > 100:  # Pegar mensagem mais substancial
                        for content in message.content:
                            if hasattr(content, 'text'):
                                response_text += content.text.value
                        break
            
            if not response_text:
                raise Exception("Nenhuma resposta encontrada do assistente")
            
            print("✅ Análise concluída!")
            print(f"📏 Tamanho da resposta: {len(response_text)} caracteres")
            return response_text
            
        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            # Log adicional para debug
            import traceback
            print("🔍 Detalhes do erro:")
            traceback.print_exc()
            raise
    
    def save_analysis(self, analysis: str, original_file: str) -> str:
        """
        Salva a análise na mesma pasta do arquivo original
        
        Args:
            analysis: Texto da análise
            original_file: Arquivo original para determinar pasta
            
        Returns:
            Caminho do arquivo de análise salvo
        """
        print("💾 ETAPA 4: Salvando análise")
        print("=" * 60)
        
        try:
            # Determinar pasta e nome do arquivo
            original_path = Path(original_file)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            analysis_file = original_path.parent / f"{original_path.stem}_ANALISE_{timestamp}.md"
            
            # Criar cabeçalho da análise
            header = f"""# 📊 ANÁLISE FINANCEIRA AUTOMÁTICA

**Arquivo Original:** {original_path.name}
**Data da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**Assistente IA:** {self.assistant_id}

---

"""
            
            # Salvar análise
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write(header + analysis)
            
            print(f"✅ Análise salva: {analysis_file}")
            return str(analysis_file)
            
        except Exception as e:
            print(f"❌ Erro ao salvar análise: {e}")
            raise
    
    def cleanup_openai_file(self, file_id: str):
        """Remove arquivo do OpenAI após análise"""
        try:
            self.client.files.delete(file_id)
            print(f"🗑️ Arquivo removido do OpenAI: {file_id}")
        except Exception as e:
            print(f"⚠️ Erro ao remover arquivo: {e}")
    
    def create_emergency_analysis(self, md_file_path: str) -> str:
        """
        Cria análise básica como fallback quando o assistente falha
        
        Args:
            md_file_path: Caminho do arquivo MD
            
        Returns:
            Análise básica do arquivo
        """
        print("🚨 Criando análise de emergência...")
        
        try:
            # Ler arquivo MD
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Análise básica
            lines = content.split('\n')
            total_lines = len(lines)
            
            analysis = f"""# 🚨 ANÁLISE DE EMERGÊNCIA

⚠️ **NOTA**: Esta é uma análise básica gerada automaticamente porque o assistente IA não respondeu a tempo.

## 📄 INFORMAÇÕES DO ARQUIVO

- **Tamanho**: {len(content):,} caracteres
- **Linhas**: {total_lines:,}
- **Arquivo MD**: {md_file_path}

## 🔍 ANÁLISE BÁSICA

O arquivo foi convertido com sucesso para Markdown, mas a análise detalhada do assistente IA falhou.

### Próximos passos recomendados:

1. **Verificar conectividade**: Tente novamente em alguns minutos
2. **Arquivo manual**: Abra o arquivo MD gerado para análise manual
3. **Assistente alternativo**: Use outro método de análise
4. **Suporte técnico**: Entre em contato se o problema persistir

## 📊 ARQUIVO GERADO

O arquivo Markdown foi gerado com sucesso e contém os dados convertidos do Excel original.
Você pode abrir este arquivo em qualquer editor de texto ou visualizador Markdown.

### Como proceder:

1. Abra o arquivo MD gerado
2. Localize as seções de grupos contábeis
3. Identifique manualmente as variações críticas
4. Calcule os indicadores principais (CMV%, Pessoal%, Admin%)

"""
            return analysis
            
        except Exception as e:
            return f"""# 🚨 ANÁLISE DE EMERGÊNCIA - ERRO

Não foi possível gerar nem mesmo uma análise básica.

**Erro**: {e}

**Arquivo MD**: {md_file_path}

Por favor, verifique o arquivo manualmente.
"""
    
    def analyze_financial_report(self, excel_file: str, custom_prompt: str = None, cleanup: bool = True) -> Tuple[str, str]:
        """
        Processo completo: conversão + análise + salvamento
        
        Args:
            excel_file: Arquivo Excel do Zoho
            custom_prompt: Prompt personalizado (opcional)
            cleanup: Se deve limpar arquivo do OpenAI (padrão: True)
            
        Returns:
            Tupla com (caminho_markdown, caminho_analise)
        """
        print("🎯 INICIANDO ANÁLISE FINANCEIRA AUTOMÁTICA")
        print("=" * 80)
        print(f"📁 Arquivo: {excel_file}")
        print(f"🤖 Assistente: {self.assistant_id}")
        print("=" * 80)
        
        md_file = None
        file_id = None
        analysis = None
        
        try:
            # 1. Converter para Markdown
            md_file = self.convert_to_markdown(excel_file)
            
            # 2. Upload para OpenAI
            file_id = self.upload_file_to_openai(md_file)
            
            # 3. Análise com IA
            analysis = self.create_thread_and_run(file_id, custom_prompt)
            
            # 4. Salvar análise
            analysis_file = self.save_analysis(analysis, excel_file)
            
            # 5. Limpeza (opcional)
            if cleanup and file_id:
                self.cleanup_openai_file(file_id)
            
            print("\n" + "=" * 80)
            print("🎉 ANÁLISE CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print(f"📄 Markdown: {md_file}")
            print(f"📊 Análise: {analysis_file}")
            
            return md_file, analysis_file
            
        except Exception as e:
            print(f"\n❌ ERRO NA ANÁLISE: {e}")
            
            # Tentar limpeza em caso de erro
            if cleanup and file_id:
                try:
                    self.cleanup_openai_file(file_id)
                except:
                    pass
            
            raise

def parse_arguments():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description="Analisador Financeiro Automático - Excel → Markdown → Análise IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Análise básica
  python financial_analyzer.py relatorio.xlsx
  
  # Com prompt personalizado
  python financial_analyzer.py relatorio.xlsx --prompt "Foque apenas no CMV e pessoal"
  
  # Manter arquivo no OpenAI (não limpar)
  python financial_analyzer.py relatorio.xlsx --no-cleanup
  
  # Especificar arquivo de configuração
  python financial_analyzer.py relatorio.xlsx --env custom.env

Arquivos gerados:
- ARQUIVO_dec4_YYYYMMDD_HHMMSS.md (Markdown convertido)
- ARQUIVO_ANALISE_YYYYMMDD_HHMMSS.md (Análise IA)
        """
    )
    
    parser.add_argument(
        'excel_file',
        help='Arquivo Excel do Zoho para análise'
    )
    
    parser.add_argument(
        '--prompt',
        help='Prompt personalizado para o assistente'
    )
    
    parser.add_argument(
        '--env',
        default='openai.env',
        help='Arquivo de configuração OpenAI (padrão: openai.env)'
    )
    
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Não remover arquivo do OpenAI após análise'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Analisador Financeiro Automático v1.0'
    )
    
    return parser.parse_args()

def main():
    """Função principal"""
    args = parse_arguments()
    
    try:
        # Verificar se arquivo existe
        if not os.path.exists(args.excel_file):
            print(f"❌ Arquivo não encontrado: {args.excel_file}")
            return
        
        # Verificar se é arquivo Excel
        if not args.excel_file.lower().endswith(('.xlsx', '.xls')):
            print(f"❌ Arquivo deve ser Excel (.xlsx ou .xls): {args.excel_file}")
            return
        
        # Criar analisador
        analyzer = FinancialAnalyzer(env_file=args.env)
        
        # Executar análise completa
        md_file, analysis_file = analyzer.analyze_financial_report(
            excel_file=args.excel_file,
            custom_prompt=args.prompt,
            cleanup=not args.no_cleanup
        )
        
        print(f"\n🎯 ARQUIVOS GERADOS:")
        print(f"📄 {md_file}")
        print(f"📊 {analysis_file}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Análise interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante a análise: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Se há argumentos, usar função principal
    if len(sys.argv) > 1:
        main()
    else:
        # Exemplo de uso direto
        print("💡 Modo de exemplo - usando arquivo específico")
        print("💡 Use --help para ver opções de linha de comando")
        
        # Arquivo de exemplo
        example_file = r"C:\Users\Haroldo Duraes\Desktop\Grupo\Relatorios\RESULTADO_ANALITICO_-_MELHOR.xlsx"
        
        if os.path.exists(example_file):
            try:
                analyzer = FinancialAnalyzer()
                md_file, analysis_file = analyzer.analyze_financial_report(example_file)
                print(f"\n🎯 Análise de exemplo concluída!")
                print(f"📄 {md_file}")
                print(f"📊 {analysis_file}")
            except Exception as e:
                print(f"❌ Erro na análise de exemplo: {e}")
        else:
            print(f"❌ Arquivo de exemplo não encontrado: {example_file}")
            print("💡 Execute com: python financial_analyzer.py seu_arquivo.xlsx")
