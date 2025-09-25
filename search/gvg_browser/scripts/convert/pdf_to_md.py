import argparse
import os
import sys
from datetime import datetime

# Permite execução direta a partir do repo sem instalar pacote
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from gvg_documents import convert_document_to_markdown, create_safe_filename


def main():
    parser = argparse.ArgumentParser(description='Converter PDF em Markdown via Docling (subprocesso).')
    parser.add_argument('pdf', help='Caminho do arquivo PDF de entrada')
    parser.add_argument('--output', '-o', help='Arquivo .md de saída (opcional). Se omitido, salva em scripts/convert/output/.')
    args = parser.parse_args()

    pdf_path = args.pdf
    if not os.path.isfile(pdf_path):
        print(f"Erro: arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    original_filename = os.path.basename(pdf_path)
    ok, md, err = convert_document_to_markdown(pdf_path, original_filename)
    if not ok:
        print(f"Falha na conversão: {err}")
        sys.exit(2)

    # Destino
    if args.output:
        out_path = args.output
        out_dir = os.path.dirname(out_path) or '.'
        os.makedirs(out_dir, exist_ok=True)
    else:
        out_dir = os.path.join(CURRENT_DIR, 'output')
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.splitext(original_filename)[0]
        safe = create_safe_filename(base)
        out_name = f"DOCLING_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        out_path = os.path.join(out_dir, out_name)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(md)

    print(out_path)


if __name__ == '__main__':
    main()
