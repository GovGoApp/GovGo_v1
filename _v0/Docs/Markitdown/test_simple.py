"""
Teste simples da biblioteca MarkItDown
"""

from markitdown import MarkItDown
import os

def test_simple_html():
    """Teste simples com HTML"""
    print("=== Teste Simples HTML ===")
    
    # Criar MarkItDown
    md = MarkItDown()
    
    # HTML simples
    html_content = """<html>
<head><title>Teste</title></head>
<body>
    <h1>Titulo Principal</h1>
    <p>Este e um paragrafo de teste.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
</body>
</html>"""
    
    # Salvar arquivo
    with open("teste.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    try:
        # Converter
        result = md.convert("teste.html")
        print("Resultado da conversao:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        # Salvar resultado
        with open("resultado.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("Conversao salva em: resultado.md")
        
    except Exception as e:
        print(f"Erro: {e}")
    
    finally:
        # Limpar
        if os.path.exists("teste.html"):
            os.remove("teste.html")

def test_simple_csv():
    """Teste simples com CSV"""
    print("\n=== Teste Simples CSV ===")
    
    md = MarkItDown()
    
    # CSV simples
    csv_content = """Nome,Idade,Cidade
Joao,30,Sao Paulo
Maria,25,Rio de Janeiro"""
    
    with open("teste.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    try:
        result = md.convert("teste.csv")
        print("Resultado CSV:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        with open("resultado_csv.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("CSV convertido salvo em: resultado_csv.md")
        
    except Exception as e:
        print(f"Erro CSV: {e}")
    
    finally:
        if os.path.exists("teste.csv"):
            os.remove("teste.csv")

if __name__ == "__main__":
    test_simple_html()
    test_simple_csv()
    print("\nTestes concluidos!")
