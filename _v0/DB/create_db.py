import os
import sqlite3
from rich.console import Console

console = Console()

# Definindo os caminhos conforme solicitado
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = BASE_PATH + "DB\\"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)
db_file = os.path.join(DB_PATH, "pncp.db")


console.log(f"Criando o banco de dados em: {db_file}")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

# Tabela Contratação – utilizando os nomes mapeados (ponto substituído por underlines)
cursor.execute("""
CREATE TABLE IF NOT EXISTS contratacao (
    ID_CONTRATACAO INTEGER PRIMARY KEY AUTOINCREMENT,
    numeroControlePNCP TEXT,
    modoDisputaId TEXT,
    amparoLegal_codigo TEXT,
    amparoLegal_descricao TEXT,
    amparoLegal_nome TEXT,
    dataAberturaProposta TEXT,
    dataEncerramentoProposta TEXT,
    srp TEXT,
    orgaoEntidade_cnpj TEXT,
    orgaoEntidade_razaosocial TEXT,
    orgaoEntidade_poderId TEXT,
    orgaoEntidade_esferaId TEXT,
    anoCompra TEXT,
    sequencialCompra TEXT,
    informacaoComplementar TEXT,
    processo TEXT,
    objetoCompra TEXT,
    linkSistemaOrigem TEXT,
    justificativaPresencial TEXT,
    unidadeSubRogada TEXT,
    orgaoSubRogado TEXT,
    valorTotalHomologado REAL,
    dataInclusao TEXT,
    dataPublicacaoPncp TEXT,
    dataAtualizacao TEXT,
    numeroCompra TEXT,
    unidadeOrgao_ufNome TEXT,
    unidadeOrgao_ufSigla TEXT,
    unidadeOrgao_municipioNome TEXT,
    unidadeOrgao_codigoUnidade TEXT,
    unidadeOrgao_nomeUnidade TEXT,
    unidadeOrgao_codigoIbge TEXT,
    modalidadeId TEXT,
    linkProcessoEletronico TEXT,
    dataAtualizacaoGlobal TEXT,
    tipoInstrumentoConvocatorioNome TEXT,
    tipoInstrumentoConvocatorioCodigo TEXT,
    valorTotalEstimado REAL,
    modalidadeNome TEXT,
    modoDisputaNome TEXT,
    situacaoCompraId TEXT,
    situacaoCompraNome TEXT,
    usuarioNome TEXT
);
""")
console.log("Tabela 'contratacao' criada.")

# Tabela Item_Contratação
cursor.execute("""
CREATE TABLE IF NOT EXISTS item_contratacao (
    ID_ITEM_CONTRATACAO INTEGER PRIMARY KEY AUTOINCREMENT,
    numeroControlePNCP TEXT,
    numeroItem TEXT,
    descricao TEXT,
    materialOuServico TEXT,
    materialOuServicoNome TEXT,
    valorUnitarioEstimado REAL,
    valorTotal REAL,
    quantidade REAL,
    unidadeMedida TEXT,
    orcamentoSigiloso TEXT,
    itemCategoriaId TEXT,
    itemCategoriaNome TEXT,
    patrimonio TEXT,
    codigoRegistroImobiliario TEXT,
    criterioJulgamentoId TEXT,
    criterioJulgamentoNome TEXT,
    situacaoCompraItem TEXT,
    situacaoCompraItemNome TEXT,
    tipoBeneficio TEXT,
    tipoBeneficioNome TEXT,
    incentivoProdutivoBasico TEXT,
    dataInclusao TEXT,
    dataAtualizacao TEXT,
    temResultado TEXT,
    imagem TEXT,
    aplicabilidadeMargemPreferenciaNormal TEXT,
    aplicabilidadeMargemPreferenciaAdicional TEXT,
    percentualMargemPreferenciaNormal REAL,
    percentualMargemPreferenciaAdicional REAL,
    ncmNbsCodigo TEXT,
    ncmNbsDescricao TEXT,
    catalogo TEXT,
    categoriaItemCatalogo TEXT,
    catalogoCodigoItem TEXT,
    informacaoComplementar TEXT
);
""")
console.log("Tabela 'item_contratacao' criada.")

# Tabela Contrato
cursor.execute("""
CREATE TABLE IF NOT EXISTS contrato (
    ID_CONTRATO INTEGER PRIMARY KEY AUTOINCREMENT,
    numeroControlePncpCompra TEXT,
    numeroControlePNCP TEXT,
    numeroContratoEmpenho TEXT,
    anoContrato TEXT,
    dataAssinatura TEXT,
    dataVigenciaInicio TEXT,
    dataVigenciaFim TEXT,
    niFornecedor TEXT,
    tipoPessoa TEXT,
    sequencialContrato TEXT,
    informacaoComplementar TEXT,
    processo TEXT,
    nomeRazaoSocialFornecedor TEXT,
    numeroParcelas TEXT,
    numeroRetificacao TEXT,
    objetoContrato TEXT,
    valorInicial REAL,
    valorParcela REAL,
    valorGlobal REAL,
    dataAtualizacaoGlobal TEXT,
    usuarioNome TEXT,
    tipoContrato_id TEXT,
    tipoContrato_nome TEXT,
    orgaoEntidade_cnpj TEXT,
    orgaoEntidade_razaosocial TEXT,
    orgaoEntidade_poderId TEXT,
    orgaoEntidade_esferaId TEXT,
    categoriaProcesso_id TEXT,
    categoriaProcesso_nome TEXT,
    unidadeOrgao_ufNome TEXT,
    unidadeOrgao_codigoUnidade TEXT,
    unidadeOrgao_nomeUnidade TEXT,
    unidadeOrgao_ufSigla TEXT,
    unidadeOrgao_municipioNome TEXT,
    unidadeOrgao_codigoIbge TEXT,
    vigenciaAno TEXT
);
""")

console.log("Tabela 'contrato' criada.")

conn.commit()
conn.close()
console.log("Banco de dados criado com sucesso!")
