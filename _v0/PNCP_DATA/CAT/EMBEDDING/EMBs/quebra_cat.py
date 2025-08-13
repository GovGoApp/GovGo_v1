import pandas as pd
import re

def extrair_top_e_score(texto):
    """
    Recebe o conteúdo de 'categoriasTopN' (possivelmente múltiplas linhas),
    separa cada linha até no máximo 5 e extrai:
      - TOP_x: texto antes de '(score=...)'
      - SCORE_x: valor numérico em '(score=...)'
    Retorna duas listas: [TOP_1,...,TOP_5], [SCORE_1,...,SCORE_5]
    """
    if pd.isna(texto):
        return [None]*5, [None]*5
    
    # Garante que seja string e separa em linhas
    linhas = str(texto).strip().split('\n')
    
    tops, scores = [], []
    for i, linha in enumerate(linhas[:5], start=1):
        # Remove espaços extras
        linha = linha.strip()
        
        # Procura por um padrão: "qualquer coisa (score=valor)"
        # Ex.: "MATERIAL; 41-... (score=0.832)"
        padrao = r'^(.*)\(score\s*=\s*([\d.,]+)\)$'
        m = re.search(padrao, linha)
        if m:
            tops.append(m.group(1).strip())
            # Troca eventual vírgula decimal por ponto, se houver
            valor = m.group(2).replace(',', '.')
            try:
                scores.append(float(valor))
            except ValueError:
                scores.append(None)
        else:
            # Se não casar o padrão, colocar tudo em TOP e None em SCORE
            tops.append(linha)
            scores.append(None)
    
    # Completa com None se houver menos de 5 linhas
    while len(tops) < 5:
        tops.append(None)
        scores.append(None)
    
    return tops, scores


def processar_planilha(arquivo_entrada, arquivo_saida=None):
    """
    Lê a planilha 'arquivo_entrada', processa a coluna 'categoriasTopN'
    para criar colunas TOP_1..TOP_5 e SCORE_1..SCORE_5, e salva no
    'arquivo_saida' (por padrão, sobrescreve o arquivo_entrada).
    """

    if arquivo_saida is None:
        arquivo_saida = arquivo_entrada

    # Lê o Excel
    df = pd.read_excel(arquivo_entrada)

    # Aplica a função de extração a cada linha da coluna 'categoriasTopN'
    resultados = df['categoriasTopN'].apply(extrair_top_e_score)
    
    # Monta colunas de TOP e SCORE
    df[['TOP_1','TOP_2','TOP_3','TOP_4','TOP_5']] = pd.DataFrame(
        resultados.apply(lambda x: x[0]).tolist(), index=df.index
    )
    df[['SCORE_1','SCORE_2','SCORE_3','SCORE_4','SCORE_5']] = pd.DataFrame(
        resultados.apply(lambda x: x[1]).tolist(), index=df.index
    )
    
    # Salva tudo de volta
    df.to_excel(arquivo_saida, index=False)

# Exemplo de uso:
processar_planilha("C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\CLASSY\\OUTPUT\\OUTPUT_ADA_NV3_001.xlsx")
