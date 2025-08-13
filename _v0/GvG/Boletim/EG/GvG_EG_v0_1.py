#### GvG Embeddings Generator (GvG_EG) v0 ####

import os
import pandas as pd
import numpy as np
import pickle
import faiss
from openai import OpenAI
from datetime import datetime
import math
import re
import unidecode
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn, TimeElapsedColumn

# Configurações
EMBEDDING_MODEL = "text-embedding-3-large"
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\GvG\\EG\\"
GvG_FILE = BASE_PATH + "GvG_Contratações.xlsx"
EMBEDDINGS_PATH = BASE_PATH + "EMBEDDINGS\\"
os.makedirs(EMBEDDINGS_PATH, exist_ok=True)

# Inicializar NLTK
nltk.download('stopwords')
nltk.download('wordnet')

# Console para exibição formatada
console = Console()

# Cliente OpenAI
client = OpenAI(api_key="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")

def preprocess_text(text):
    """Normaliza e limpa o texto para processamento."""
    text = unidecode.unidecode(str(text))
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    sw = set(stopwords.words('portuguese'))
    words = text.split()
    words = [word for word in words if word not in sw]
    lemmatizer = WordNetLemmatizer()
    words = [lemmatizer.lemmatize(word) for word in words]
    return ' '.join(words)

def get_embedding(text, model=EMBEDDING_MODEL):
    """Gera embedding para um único texto."""
    try:
        # Garantir que o texto não está vazio
        if not text or not text.strip():
            text = " "
        
        # Limitar tamanho se necessário
        if len(text) > 8000:
            text = text[:8000]
            
        response = client.embeddings.create(
            model=model,
            input=[text]
        )
        return np.array(response.data[0].embedding, dtype=np.float32)
    except Exception as e:
        console.print(f"[bold red]Erro ao gerar embedding: {str(e)}[/bold red]")
        return None

def get_embeddings_batch(texts, model=EMBEDDING_MODEL):
    """Gera embeddings para uma lista de textos em lotes."""
    embeddings = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=False
    ) as progress:
        task = progress.add_task("Gerando embeddings...", total=len(texts))
        
        for text in texts:
            embedding = get_embedding(text, model)
            if embedding is not None:
                embeddings.append(embedding)
            else:
                # Incluir embedding vazio para manter correspondência com os índices
                embeddings.append(np.zeros(1536, dtype=np.float32))
            progress.update(task, advance=1)
    
    return embeddings

def calculate_confidence(scores):
    """Calcula o nível de confiança com base na diferença entre as pontuações."""
    if len(scores) < 2:
        return 0.0
    
    top_score = scores[0]
    gaps = [top_score - score for score in scores[1:]]
    weights = [1/(i+1) for i in range(len(gaps))]
    
    weighted_gap = sum(g * w for g, w in zip(gaps, weights)) / top_score
    confidence = 100 * (1 - math.exp(-10 * weighted_gap))
    
    return confidence

class ContratacoesBD:
    def __init__(self, excel_path=None):
        """Inicializa a base de dados de contratações."""
        self.df = None
        self.embeddings = None
        self.index = None
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # Carregar dados se um caminho for fornecido
        if excel_path:
            self.carregar_excel(excel_path)
    
    def carregar_excel(self, excel_path):
        """Carrega os dados do Excel."""
        try:
            self.df = pd.read_excel(excel_path)
            console.print(f"[green]Carregados {len(self.df)} registros do Excel.[/green]")
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar arquivo Excel: {str(e)}[/bold red]")
            raise
    
    def processar_descricoes(self):
        """Pré-processa as descrições de contratações."""
        if self.df is None:
            console.print("[bold red]Nenhum dado carregado. Carregue um arquivo Excel primeiro.[/bold red]")
            return
        
        console.print("[bold magenta]Processando descrições...[/bold magenta]")
        self.df['descricao_processada'] = self.df['descricaoCompleta'].apply(preprocess_text)
        console.print("[green]Descrições processadas com sucesso.[/green]")
    
    def gerar_embeddings(self):
        """Gera embeddings para as descrições processadas."""
        if self.df is None or 'descricao_processada' not in self.df.columns:
            console.print("[bold red]Descrições não processadas. Execute 'processar_descricoes' primeiro.[/bold red]")
            return
        
        console.print("[bold magenta]Gerando embeddings para as descrições...[/bold magenta]")
        textos = self.df['descricao_processada'].tolist()
        self.embeddings = get_embeddings_batch(textos)
        console.print(f"[green]Embeddings gerados: {len(self.embeddings)}[/green]")
    
    def criar_indice_faiss(self):
        """Cria um índice FAISS para busca por similaridade."""
        if self.embeddings is None:
            console.print("[bold red]Embeddings não gerados. Execute 'gerar_embeddings' primeiro.[/bold red]")
            return
        
        console.print("[bold magenta]Criando índice FAISS...[/bold magenta]")
        embeddings_array = np.array(self.embeddings, dtype=np.float32)
        
        # Criar índice de produto interno (similaridade de cosseno)
        dimension = embeddings_array.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        
        # Normalizar vetores para garantir similaridade de cosseno
        faiss.normalize_L2(embeddings_array)
        
        # Adicionar vetores ao índice
        self.index.add(embeddings_array)
        console.print(f"[green]Índice FAISS criado com {self.index.ntotal} vetores.[/green]")
    
    # Corrigir formatação das strings nos caminhos de arquivo
    def salvar_base(self, prefix="contratacoes"):
        """Salva a base de dados, embeddings e índice FAISS."""
        if self.df is None:
            console.print("[bold red]Nenhum dado para salvar.[/bold red]")
            return
        
        try:
            # Criar nome de arquivo com timestamp
            filename_base = f"{prefix}_{self.timestamp}"
            
            # Salvar DataFrame
            df_path = f"{BASE_PATH}{filename_base}.xlsx"
            self.df.to_excel(df_path, index=False)
            console.print(f"[green]DataFrame salvo em {df_path}[/green]")
            
            # Salvar embeddings
            if self.embeddings is not None:
                embedding_file = f"{EMBEDDINGS_PATH}{filename_base}_embeddings.pkl"
                with open(embedding_file, 'wb') as f:
                    pickle.dump(self.embeddings, f)
                console.print(f"[green]Embeddings salvos em {embedding_file}[/green]")
            
            # Salvar índice FAISS
            if self.index is not None:
                index_file = f"{EMBEDDINGS_PATH}{filename_base}_faiss.index"
                faiss.write_index(self.index, index_file)
                console.print(f"[green]Índice FAISS salvo em {index_file}[/green]")
            
            # Salvar metadados
            metadata = {
                'df_path': df_path,
                'embeddings_path': embedding_file if self.embeddings is not None else None,
                'index_path': index_file if self.index is not None else None,
                'timestamp': self.timestamp,
                'num_records': len(self.df),
                'embedding_model': EMBEDDING_MODEL
            }
            
            metadata_path = f"{EMBEDDINGS_PATH}{filename_base}_metadata.pkl"
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            console.print(f"[green]Metadados salvos em {metadata_path}[/green]")
            
            return metadata_path
            
        except Exception as e:
            console.print(f"[bold red]Erro ao salvar base: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())

    def carregar_base(self, metadata_path):
        """Carrega a base de dados a partir do arquivo de metadados."""
        try:
            # Carregar metadados
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            console.print(f"[bold magenta]Carregando base de {metadata['timestamp']}...[/bold magenta]")
            
            # Carregar DataFrame
            self.df = pd.read_excel(metadata['df_path'])
            console.print(f"[green]DataFrame carregado com {len(self.df)} registros.[/green]")
            
            # Carregar embeddings
            if metadata['embeddings_path'] and os.path.exists(metadata['embeddings_path']):
                with open(metadata['embeddings_path'], 'rb') as f:
                    self.embeddings = pickle.load(f)
                console.print(f"[green]Embeddings carregados: {len(self.embeddings)}[/green]")
            
            # Carregar índice FAISS
            if metadata['index_path'] and os.path.exists(metadata['index_path']):
                self.index = faiss.read_index(metadata['index_path'])
                console.print(f"[green]Índice FAISS carregado com {self.index.ntotal} vetores.[/green]")
            
            self.timestamp = metadata['timestamp']
            return True
            
        except Exception as e:
            console.print(f"[bold red]Erro ao carregar base: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())
            return False
    
    def processar_pipeline_completo(self, excel_path, salvar=True):
        """Executa o pipeline completo de processamento."""
        try:
            self.carregar_excel(excel_path)
            self.processar_descricoes()
            self.gerar_embeddings()
            self.criar_indice_faiss()
            
            if salvar:
                metadata_path = self.salvar_base()
                return metadata_path
                
        except Exception as e:
            console.print(f"[bold red]Erro no pipeline de processamento: {str(e)}[/bold red]")
            import traceback
            console.print(traceback.format_exc())

class BuscaContratacoes:
    def __init__(self, contratacoes_bd=None, metadata_path=None):
        """Inicializa o sistema de busca de contratações."""
        self.contratacoes_bd = contratacoes_bd or ContratacoesBD()
        
        # Se um caminho de metadados for fornecido, carregar a base
        if metadata_path:
            self.contratacoes_bd.carregar_base(metadata_path)
    
    def buscar(self, consulta, top_n=5):
        """Realiza uma busca por similaridade na base de contratações."""
        if self.contratacoes_bd.index is None:
            console.print("[bold red]Índice FAISS não disponível. Carregue ou crie um índice primeiro.[/bold red]")
            return None
            
        # Pré-processar a consulta
        consulta_processada = preprocess_text(consulta)
        
        # Gerar embedding para a consulta
        console.print(f"[cyan]Gerando embedding para a consulta: \"{consulta}\"[/cyan]")
        consulta_embedding = get_embedding(consulta_processada)
        
        if consulta_embedding is None:
            console.print("[bold red]Falha ao gerar embedding para a consulta.[/bold red]")
            return None
        
        # Normalizar o embedding da consulta
        consulta_embedding = consulta_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(consulta_embedding)
        
        # Realizar a busca no índice FAISS
        console.print("[cyan]Buscando contratações similares...[/cyan]")
        D, I = self.contratacoes_bd.index.search(consulta_embedding, top_n)
        
        # Organizar resultados
        resultados = []
        scores = D[0].tolist()
        
        for i, (idx, score) in enumerate(zip(I[0], scores)):
            if idx >= 0:  # Verificar se o índice é válido
                resultado = {
                    'posicao': i + 1,
                    'score': float(score),
                    'numeroControlePNCP': self.contratacoes_bd.df.iloc[idx].get('numeroControlePNCP', ''),
                    'descricaoCompleta': self.contratacoes_bd.df.iloc[idx].get('descricaoCompleta', ''),
                    'valorTotalHomologado': self.contratacoes_bd.df.iloc[idx].get('valorTotalHomologado', ''),
                    'unidadeOrgao_ufSigla': self.contratacoes_bd.df.iloc[idx].get('unidadeOrgao_ufSigla', ''),
                    'unidadeOrgao_municipioNome': self.contratacoes_bd.df.iloc[idx].get('unidadeOrgao_municipioNome', ''),
                    'unidadeOrgao_nomeUnidade': self.contratacoes_bd.df.iloc[idx].get('unidadeOrgao_nomeUnidade', ''),
                    'orgaoEntidade_razaosocial': self.contratacoes_bd.df.iloc[idx].get('orgaoEntidade_razaosocial', '')
                }
                resultados.append(resultado)
        
        # Calcular nível de confiança
        confidence = calculate_confidence(scores)
        
        return {
            'consulta': consulta,
            'consulta_processada': consulta_processada,
            'resultados': resultados,
            'confidence': confidence,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def exibir_resultados(self, resultados):
        """Exibe os resultados de forma formatada."""
        if not resultados:
            console.print("[bold red]Nenhum resultado disponível.[/bold red]")
            return
        
        console.print(f"\n[bold magenta]{'='*80}[/bold magenta]")
        console.print(f"[bold magenta]RESULTADOS DA CONSULTA: \"{resultados['consulta']}\"[/bold magenta]")
        console.print(f"[bold magenta]{'='*80}[/bold magenta]")
        console.print(f"Consulta processada: {resultados['consulta_processada']}")
        console.print(f"Confiança: {resultados['confidence']:.2f}%")
        console.print(f"Data/hora: {resultados['timestamp']}\n")
        
        for resultado in resultados['resultados']:
            console.print(f"[bold green]{'='*60}[/bold green]")
            console.print(f"[bold cyan]Posição {resultado['posicao']} - Similaridade: {resultado['score']:.4f}[/bold cyan]")
            console.print(f"[bold yellow]Número: {resultado['numeroControlePNCP']}[/bold yellow]")
            console.print(f"[bold white]Descrição: {resultado['descricaoCompleta']}[/bold white]")
            console.print(f"Valor: R$ {resultado['valorTotalHomologado']}")
            console.print(f"Localização: {resultado['unidadeOrgao_municipioNome']}/{resultado['unidadeOrgao_ufSigla']}")
            console.print(f"Unidade: {resultado['unidadeOrgao_nomeUnidade']}")
            console.print(f"Órgão: {resultado['orgaoEntidade_razaosocial']}")
            console.print(f"[bold green]{'='*60}[/bold green]\n")

def main():
    """Função principal que coordena o processamento e consultas."""
    console.print("[bold magenta]SISTEMA DE BUSCA POR SIMILARIDADE EM CONTRATAÇÕES[/bold magenta]")
    console.print("[bold cyan]Baseado em OpenAI Embeddings e FAISS[/bold cyan]\n")
    
    # Verificar se já existem metadados salvos
    metadados_existentes = [f for f in os.listdir(EMBEDDINGS_PATH) if f.endswith('_metadata.pkl')]
    
    if metadados_existentes:
        console.print("[bold yellow]Encontrados metadados de processamento anterior:[/bold yellow]")
        for i, metadata_file in enumerate(metadados_existentes, 1):
            console.print(f"{i}. {metadata_file}")
        
        escolha = input("\nDeseja carregar um processamento existente (digite o número) ou criar um novo (N)? ")
        
        if escolha.upper() == 'N':
            # Criar novo processamento
            bd = ContratacoesBD()
            metadata_path = bd.processar_pipeline_completo(GvG_FILE)
        else:
            try:
                idx = int(escolha) - 1
                metadata_path = os.path.join(EMBEDDINGS_PATH, metadados_existentes[idx])
                bd = ContratacoesBD()
                bd.carregar_base(metadata_path)
            except (ValueError, IndexError):
                console.print("[bold red]Escolha inválida. Criando novo processamento.[/bold red]")
                bd = ContratacoesBD()
                metadata_path = bd.processar_pipeline_completo(GvG_FILE)
    else:
        console.print("[bold yellow]Nenhum processamento anterior encontrado. Criando novo.[/bold yellow]")
        bd = ContratacoesBD()
        metadata_path = bd.processar_pipeline_completo(GvG_FILE)
    
    # Criar sistema de busca
    buscador = BuscaContratacoes(contratacoes_bd=bd)
    
    # Modo interativo de consultas
    console.print("\n[bold magenta]MODO DE CONSULTA INTERATIVA[/bold magenta]")
    console.print("[cyan]Digite 'sair' para encerrar[/cyan]\n")
    
    while True:
        consulta = input("\nDigite sua consulta: ")
        
        if consulta.lower() == 'sair':
            break
            
        top_n = int(input("Número de resultados (padrão: 5): ") or 5)
        
        resultados = buscador.buscar(consulta, top_n=top_n)
        buscador.exibir_resultados(resultados)
    
    console.print("\n[bold green]SISTEMA ENCERRADO![/bold green]")

if __name__ == "__main__":
    main()