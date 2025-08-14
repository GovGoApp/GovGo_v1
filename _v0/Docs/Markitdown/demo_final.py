"""
Demo interativo do MarkItDown - Teste final
Demonstra varias funcionalidades em um script interativo
"""

from markitdown import MarkItDown
import os
import zipfile
import io

def create_demo_files():
    """Cria arquivos de demonstracao"""
    print("Criando arquivos de demonstracao...")
    
    # Arquivo texto
    with open("relatorio.txt", "w", encoding="utf-8") as f:
        f.write("""RELATORIO ANUAL 2024

RESUMO EXECUTIVO
Este documento apresenta o relatorio anual da empresa.

VENDAS POR TRIMESTRE:
Q1: R$ 250.000
Q2: R$ 320.000  
Q3: R$ 280.000
Q4: R$ 410.000

TOTAL: R$ 1.260.000

CONCLUSOES:
- Crescimento de 15% em relacao ao ano anterior
- Melhor trimestre foi Q4
- Expectativa positiva para 2025
""")
    
    # Arquivo CSV com dados
    with open("vendas.csv", "w", encoding="utf-8") as f:
        f.write("""Mes,Produto,Quantidade,Valor_Unitario,Total
Janeiro,Notebook,12,2500,30000
Janeiro,Mouse,35,25,875
Fevereiro,Notebook,8,2500,20000
Fevereiro,Teclado,20,80,1600
Marco,Tablet,15,800,12000
Marco,Mouse,40,25,1000""")
    
    # HTML com formatacao
    html_content = """<!DOCTYPE html>
<html>
<head><title>Dashboard Vendas</title></head>
<body>
    <header>
        <h1>Dashboard de Vendas - Q1 2024</h1>
    </header>
    
    <main>
        <section>
            <h2>Metricas Principais</h2>
            <ul>
                <li><strong>Receita Total:</strong> R$ 250.000</li>
                <li><strong>Produtos Vendidos:</strong> 130 unidades</li>
                <li><strong>Crescimento:</strong> +18%</li>
            </ul>
        </section>
        
        <section>
            <h2>Top 3 Produtos</h2>
            <table border="1">
                <tr><th>Posicao</th><th>Produto</th><th>Vendas</th></tr>
                <tr><td>1</td><td>Notebook</td><td>45 unidades</td></tr>
                <tr><td>2</td><td>Mouse</td><td>30 unidades</td></tr>
                <tr><td>3</td><td>Teclado</td><td>25 unidades</td></tr>
            </table>
        </section>
        
        <footer>
            <p><em>Gerado automaticamente em 2024</em></p>
        </footer>
    </main>
</body>
</html>"""
    
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # JSON com estrutura complexa
    import json
    json_data = {
        "empresa": {
            "nome": "TechSolutions",
            "cnpj": "12.345.678/0001-99",
            "endereco": {
                "rua": "Av. Paulista, 1000",
                "cidade": "Sao Paulo",
                "estado": "SP"
            }
        },
        "colaboradores": [
            {"nome": "Ana", "cargo": "Dev", "salario": 8000},
            {"nome": "Bruno", "cargo": "Design", "salario": 6000},
            {"nome": "Carlos", "cargo": "Manager", "salario": 12000}
        ],
        "projetos": {
            "ativos": 5,
            "concluidos": 12,
            "receita_total": 500000
        }
    }
    
    with open("empresa.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print("✅ Arquivos criados: relatorio.txt, vendas.csv, dashboard.html, empresa.json")

def demo_individual_conversions():
    """Demonstra conversoes individuais"""
    print("\n" + "="*60)
    print("DEMO: CONVERSOES INDIVIDUAIS")
    print("="*60)
    
    md = MarkItDown()
    
    files_to_convert = [
        ("relatorio.txt", "Arquivo de texto"),
        ("vendas.csv", "Dados CSV"), 
        ("dashboard.html", "HTML Dashboard"),
        ("empresa.json", "Dados JSON")
    ]
    
    for filename, description in files_to_convert:
        if os.path.exists(filename):
            print(f"\n📁 Convertendo: {description}")
            print("-" * 40)
            
            try:
                result = md.convert(filename)
                preview = result.text_content[:300] + "..." if len(result.text_content) > 300 else result.text_content
                print(preview)
                
                # Salvar resultado
                output_name = f"demo_{filename.split('.')[0]}.md"
                with open(output_name, "w", encoding="utf-8") as f:
                    f.write(result.text_content)
                print(f"✅ Salvo em: {output_name}")
                
            except Exception as e:
                print(f"❌ Erro: {e}")

def demo_zip_conversion():
    """Demonstra conversao de ZIP com multiplos arquivos"""
    print(f"\n{'='*60}")
    print("DEMO: CONVERSAO DE ARQUIVO ZIP")
    print("="*60)
    
    # Criar ZIP com todos os arquivos
    with zipfile.ZipFile("demo_files.zip", "w") as zipf:
        for filename in ["relatorio.txt", "vendas.csv", "dashboard.html", "empresa.json"]:
            if os.path.exists(filename):
                zipf.write(filename)
    
    print("📦 Arquivo ZIP criado com 4 arquivos")
    
    # Converter ZIP
    md = MarkItDown()
    try:
        result = md.convert("demo_files.zip")
        print("\n📄 Resultado da conversao ZIP:")
        print("-" * 40)
        print(result.text_content[:800] + "..." if len(result.text_content) > 800 else result.text_content)
        
        with open("demo_zip.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        print(f"\n✅ Conversao ZIP salva em: demo_zip.md")
        
    except Exception as e:
        print(f"❌ Erro na conversao ZIP: {e}")

def demo_streaming():
    """Demonstra conversao via streaming"""
    print(f"\n{'='*60}")
    print("DEMO: CONVERSAO VIA STREAMING")
    print("="*60)
    
    # Conteudo em memoria
    html_stream_content = """
    <html>
    <head><title>Stream Demo</title></head>
    <body>
        <h1>Teste de Streaming</h1>
        <p>Este conteudo esta sendo processado diretamente da memoria.</p>
        <h2>Vantagens do Streaming:</h2>
        <ul>
            <li>Nao precisa salvar arquivos temporarios</li>
            <li>Mais eficiente para dados grandes</li>
            <li>Processamento em tempo real</li>
        </ul>
        <table>
            <tr><th>Metodo</th><th>Vantagem</th></tr>
            <tr><td>Arquivo</td><td>Simples</td></tr>
            <tr><td>Stream</td><td>Eficiente</td></tr>
        </table>
    </body>
    </html>
    """
    
    md = MarkItDown()
    
    try:
        # Converter usando stream
        stream = io.BytesIO(html_stream_content.encode('utf-8'))
        result = md.convert_stream(stream, file_extension='.html')
        
        print("📊 Resultado do streaming:")
        print("-" * 40)
        print(result.text_content)
        
        with open("demo_stream.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        print("✅ Stream convertido salvo em: demo_stream.md")
        
    except Exception as e:
        print(f"❌ Erro no streaming: {e}")

def show_final_summary():
    """Mostra resumo final"""
    print(f"\n{'='*60}")
    print("RESUMO FINAL - ARQUIVOS GERADOS")
    print("="*60)
    
    # Listar todos os arquivos .md gerados
    md_files = [f for f in os.listdir('.') if f.endswith('.md') and (f.startswith('demo_') or f.startswith('resultado_'))]
    
    if md_files:
        total_size = 0
        print(f"📄 Total de arquivos Markdown gerados: {len(md_files)}")
        print("-" * 40)
        
        for file in sorted(md_files):
            size = os.path.getsize(file)
            total_size += size
            print(f"  📝 {file:<25} ({size:>6} bytes)")
        
        print("-" * 40)
        print(f"📊 Tamanho total: {total_size} bytes")
        
        # Mostrar conteudo de um arquivo como exemplo
        if md_files:
            example_file = md_files[0]
            print(f"\n📖 Preview de {example_file}:")
            print("-" * 40)
            with open(example_file, "r", encoding="utf-8") as f:
                content = f.read()[:400]
                print(content + ("..." if len(f.read()) > 400 else ""))
    else:
        print("❌ Nenhum arquivo Markdown encontrado")

def cleanup_demo_files():
    """Limpa arquivos de demonstracao"""
    print(f"\n🧹 Limpando arquivos temporarios...")
    
    temp_files = ["relatorio.txt", "vendas.csv", "dashboard.html", "empresa.json", "demo_files.zip"]
    
    for file in temp_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"  ✅ Removido: {file}")

def main():
    """Funcao principal da demonstracao"""
    print("🚀 DEMO COMPLETO DO MARKITDOWN")
    print("="*60)
    print("Esta demonstracao ira testar varias funcionalidades:")
    print("• Conversao de arquivos texto, CSV, HTML, JSON")
    print("• Processamento de arquivos ZIP")  
    print("• Streaming de dados da memoria")
    print("• Geração de relatorios em Markdown")
    
    try:
        create_demo_files()
        demo_individual_conversions()
        demo_zip_conversion()
        demo_streaming()
        show_final_summary()
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
    
    finally:
        cleanup_demo_files()
    
    print(f"\n🎉 DEMO CONCLUIDO!")
    print("Verifique os arquivos 'demo_*.md' e 'resultado_*.md' gerados.")

if __name__ == "__main__":
    main()
