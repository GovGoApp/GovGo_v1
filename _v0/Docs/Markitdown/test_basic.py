"""
Teste básico da biblioteca MarkItDown
Demonstra conversão de diferentes tipos de arquivo para Markdown
"""

from markitdown import MarkItDown
import os

def test_basic_conversion():
    """Teste básico de conversão"""
    # Inicializar o MarkItDown
    md = MarkItDown()
    
    print("=== Teste Básico MarkItDown ===\n")
    
    # Criar um arquivo de teste simples
    test_html = """
    <html>
    <head><title>Teste HTML</title></head>
    <body>
        <h1>Título Principal</h1>
        <p>Este é um parágrafo de teste.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        <table>
            <tr><th>Nome</th><th>Idade</th></tr>
            <tr><td>João</td><td>30</td></tr>
            <tr><td>Maria</td><td>25</td></tr>
        </table>
    </body>
    </html>
    """
    
    # Salvar arquivo HTML temporário
    with open("test.html", "w", encoding="utf-8") as f:
        f.write(test_html)
    
    try:
        # Converter HTML para Markdown
        result = md.convert("test.html")
        print("Conversão HTML -> Markdown:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        # Salvar resultado
        with open("output_html.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("✅ Conversão HTML salva em: output_html.md\n")
        
    except Exception as e:
        print(f"❌ Erro na conversão HTML: {e}\n")
    
    finally:
        # Limpar arquivo temporário
        if os.path.exists("test.html"):
            os.remove("test.html")

def test_text_formats():
    """Teste com formatos de texto"""
    md = MarkItDown()
    
    print("=== Teste Formatos de Texto ===\n")
    
    # Teste CSV
    csv_content = """Nome,Idade,Cidade
João,30,São Paulo
Maria,25,Rio de Janeiro
Pedro,35,Belo Horizonte"""
    
    with open("test.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    try:
        result = md.convert("test.csv")
        print("Conversão CSV -> Markdown:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        with open("output_csv.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("✅ Conversão CSV salva em: output_csv.md\n")
        
    except Exception as e:
        print(f"❌ Erro na conversão CSV: {e}\n")
    
    finally:
        if os.path.exists("test.csv"):
            os.remove("test.csv")
    
    # Teste JSON
    json_content = """{
    "nome": "João Silva",
    "idade": 30,
    "endereço": {
        "rua": "Rua das Flores, 123",
        "cidade": "São Paulo",
        "cep": "01234-567"
    },
    "hobbies": ["leitura", "música", "programação"]
}"""
    
    with open("test.json", "w", encoding="utf-8") as f:
        f.write(json_content)
    
    try:
        result = md.convert("test.json")
        print("Conversão JSON -> Markdown:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        with open("output_json.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("✅ Conversão JSON salva em: output_json.md\n")
        
    except Exception as e:
        print(f"❌ Erro na conversão JSON: {e}\n")
    
    finally:
        if os.path.exists("test.json"):
            os.remove("test.json")

if __name__ == "__main__":
    test_basic_conversion()
    test_text_formats()
    print("=== Testes Concluídos ===")
