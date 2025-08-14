"""
Teste avançado de MarkItDown
Demonstra funcionalidades avançadas como plugins e streaming
"""

from markitdown import MarkItDown
import io
import os

def test_plugins():
    """Teste de plugins"""
    print("=== Teste Plugins ===\n")
    
    # MarkItDown com plugins habilitados
    md_with_plugins = MarkItDown(enable_plugins=True)
    md_without_plugins = MarkItDown(enable_plugins=False)
    
    print("MarkItDown inicializado com plugins:", md_with_plugins)
    print("MarkItDown inicializado sem plugins:", md_without_plugins)
    print()

def test_streaming():
    """Teste de conversão com streams"""
    print("=== Teste Streaming ===\n")
    
    md = MarkItDown()
    
    # Criar conteúdo em memória
    html_content = """
    <html>
    <head><title>Stream Test</title></head>
    <body>
        <h1>Teste de Stream</h1>
        <p>Este conteúdo está sendo processado via stream.</p>
        <ul>
            <li>Streaming permite processar dados grandes</li>
            <li>Não precisa salvar arquivos temporários</li>
            <li>Mais eficiente para memória</li>
        </ul>
    </body>
    </html>
    """
    
    try:
        # Converter usando stream de bytes
        stream = io.BytesIO(html_content.encode('utf-8'))
        result = md.convert_stream(stream, file_extension='.html')
        
        print("Conversão via Stream -> Markdown:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        # Salvar resultado
        with open("output_stream.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("✅ Conversão via stream salva em: output_stream.md\n")
        
    except Exception as e:
        print(f"❌ Erro na conversão via stream: {e}\n")

def test_zip_conversion():
    """Teste de conversão de arquivo ZIP"""
    print("=== Teste Conversão ZIP ===\n")
    
    md = MarkItDown()
    
    # Criar alguns arquivos e compactar em ZIP
    import zipfile
    
    files_content = {
        "readme.txt": "Este é um arquivo README\nContém informações importantes do projeto.",
        "data.csv": "Nome,Valor\nTeste,123\nExemplo,456",
        "info.json": '{"projeto": "MarkItDown Test", "versao": "1.0", "autor": "Teste"}'
    }
    
    # Criar ZIP
    with zipfile.ZipFile("test_archive.zip", "w") as zipf:
        for filename, content in files_content.items():
            zipf.writestr(filename, content)
    
    print("✅ Arquivo ZIP de teste criado: test_archive.zip")
    
    try:
        # Converter ZIP
        result = md.convert("test_archive.zip")
        
        print("Conversão ZIP -> Markdown:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        # Salvar resultado
        with open("output_zip.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("✅ Conversão ZIP salva em: output_zip.md\n")
        
    except Exception as e:
        print(f"❌ Erro na conversão ZIP: {e}\n")
    
    finally:
        # Limpar arquivo temporário
        if os.path.exists("test_archive.zip"):
            os.remove("test_archive.zip")

def test_xml_conversion():
    """Teste de conversão XML"""
    print("=== Teste Conversão XML ===\n")
    
    md = MarkItDown()
    
    # Criar XML de teste
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<biblioteca>
    <livro id="1">
        <titulo>1984</titulo>
        <autor>George Orwell</autor>
        <ano>1949</ano>
        <genero>Ficção Científica</genero>
        <preco>29.90</preco>
    </livro>
    <livro id="2">
        <titulo>Dom Casmurro</titulo>
        <autor>Machado de Assis</autor>
        <ano>1899</ano>
        <genero>Romance</genero>
        <preco>19.90</preco>
    </livro>
    <estatisticas>
        <total_livros>2</total_livros>
        <valor_total>49.80</valor_total>
    </estatisticas>
</biblioteca>"""
    
    # Salvar XML
    with open("biblioteca.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    try:
        # Converter XML
        result = md.convert("biblioteca.xml")
        
        print("Conversão XML -> Markdown:")
        print("-" * 40)
        print(result.text_content)
        print("-" * 40)
        
        # Salvar resultado
        with open("output_xml.md", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        print("✅ Conversão XML salva em: output_xml.md\n")
        
    except Exception as e:
        print(f"❌ Erro na conversão XML: {e}\n")
    
    finally:
        # Limpar arquivo temporário
        if os.path.exists("biblioteca.xml"):
            os.remove("biblioteca.xml")

def show_markitdown_info():
    """Mostra informações sobre o MarkItDown"""
    print("=== Informações MarkItDown ===\n")
    
    md = MarkItDown()
    
    print(f"Versão do MarkItDown: {getattr(md, '__version__', 'Não disponível')}")
    print(f"Objeto MarkItDown: {md}")
    print(f"Tipo: {type(md)}")
    
    # Tentar listar conversores disponíveis
    try:
        if hasattr(md, '_converters'):
            print(f"Conversores disponíveis: {list(md._converters.keys())}")
        elif hasattr(md, 'converters'):
            print(f"Conversores disponíveis: {list(md.converters.keys())}")
    except:
        print("Não foi possível listar conversores")
    
    print()

if __name__ == "__main__":
    show_markitdown_info()
    test_plugins()
    test_streaming()
    test_zip_conversion()
    test_xml_conversion()
    print("=== Testes Avançados Concluídos ===")
