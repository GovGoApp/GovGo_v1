# 🚀 Setup - GvG Search Terminal v9

Guia completo de instalação e configuração do sistema de busca PNCP.

## 📋 Pré-requisitos

### 🐍 Python
- **Python 3.8+** (recomendado 3.10 ou superior)
- pip (gerenciador de pacotes)

### 🗃️ Banco de Dados
- **PostgreSQL 12+** com extensão **pgvector**
- Acesso ao banco Supabase ou instância local

### 🔑 APIs
- **OpenAI API Key** (para processamento inteligente)
- Conta Supabase (se usando serviço hospedado)

---

## ⚡ Instalação Rápida

### 1️⃣ Clone e Navegue
```bash
cd /caminho/para/GvG/Search/Prompt
```

### 2️⃣ Instale Dependências
```bash
pip install -r requirements.txt
```

### 3️⃣ Configure Ambiente
```bash
# Copie o arquivo de exemplo
cp supabase_v0.env.example supabase_v0.env

# Configure suas credenciais
notepad supabase_v0.env  # Windows
nano supabase_v0.env     # Linux/Mac
```

### 4️⃣ Configure OpenAI
```bash
# Opção 1: Variável de ambiente
set OPENAI_API_KEY=sua_chave_aqui  # Windows
export OPENAI_API_KEY=sua_chave_aqui  # Linux/Mac

# Opção 2: Arquivo .env
echo "OPENAI_API_KEY=sua_chave_aqui" >> .env
```

### 5️⃣ Teste a Instalação
```bash
python GvG_SP_Search_Terminal_v9.py
```

---

## 🔧 Configuração Detalhada

### 📁 Estrutura de Arquivos
```
/Prompt/
├── GvG_SP_Search_Terminal_v9.py    # 🖥️  Interface terminal principal
├── GvG_Search_Prompt_v0.py         # 📝 Interface linha de comando
├── gvg_search_utils_v3.py          # 🔧 Motor de busca v3
├── gvg_pre_processing_v3.py        # 🤖 Processamento inteligente
├── gvg_document_utils_v3_o.py      # 📄 Análise de documentos (Docling)
├── gvg_document_utils_v2.py        # 📄 Análise de documentos (MarkItDown)
├── supabase_v0.env                 # 🔑 Credenciais do banco
├── relevance_pncp_v2.txt           # 🎯 Prompts restritivos
├── relevance_pncp_v3.txt           # 🎯 Prompts flexíveis
├── requirements.txt                # 📦 Dependências Python
├── README.md                       # 📖 Documentação principal
└── SETUP.md                        # 🚀 Este arquivo
```

### 🗃️ Configuração do Banco

#### Supabase (Recomendado)
```env
# supabase_v0.env
host=seu-projeto.supabase.co
dbname=postgres
user=postgres
password=sua_senha_aqui
port=5432
```

#### PostgreSQL Local
```env
# supabase_v0.env
host=localhost
dbname=govgo
user=postgres
password=sua_senha_local
port=5432
```

### 🔑 Configuração OpenAI

#### Método 1: Variável de Ambiente
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-proj-sua_chave_aqui"

# Windows (CMD)
set OPENAI_API_KEY=sk-proj-sua_chave_aqui

# Linux/Mac
export OPENAI_API_KEY=sk-proj-sua_chave_aqui
```

#### Método 2: Arquivo .env
```env
# .env
OPENAI_API_KEY=sk-proj-sua_chave_aqui
```

---

## 🧪 Verificação da Instalação

### ✅ Teste de Conectividade
```python
python -c "
from gvg_search_utils_v3 import test_connection
print('✅ Testando conexão...')
result = test_connection()
print('✅ Sucesso!' if result else '❌ Falhou!')
"
```

### 🔍 Teste de Busca Simples
```bash
python GvG_Search_Prompt_v0.py --prompt "teste básico" --max_results 5
```

### 🤖 Teste do Processamento Inteligente
```python
python -c "
from gvg_search_utils_v3 import get_intelligent_status
status = get_intelligent_status()
print(f'Processamento Inteligente: {status}')
"
```

---

## 🚨 Solução de Problemas

### ❌ Erro: "gvg_search_utils_v3 não encontrado"
**Solução**: Verifique se todos os arquivos estão na mesma pasta
```bash
ls -la *.py  # Linux/Mac
dir *.py     # Windows
```

### ❌ Erro: "Conexão com banco falhou"
**Possíveis causas**:
1. Credenciais incorretas em `supabase_v0.env`
2. Firewall bloqueando conexão
3. Serviço Supabase inativo

**Solução**:
```bash
# Teste manual de conexão
python -c "
import os
from dotenv import load_dotenv
load_dotenv('supabase_v0.env')
print('Host:', os.getenv('host'))
print('Database:', os.getenv('dbname'))
print('User:', os.getenv('user'))
"
```

### ❌ Erro: "OpenAI API key não configurada"
**Solução**: Defina a variável de ambiente
```bash
echo $OPENAI_API_KEY  # Linux/Mac - deve mostrar sua chave
echo %OPENAI_API_KEY% # Windows - deve mostrar sua chave
```

### ❌ Erro: "Docling não disponível"
**Solução**: Instale dependências específicas
```bash
pip install docling pypdfium2
```

### ❌ Erro: "Rich não encontrado"
**Solução**: Instale interface Rica
```bash
pip install rich>=13.0.0
```

---

## 🔄 Atualizações

### Atualizar Dependências
```bash
pip install -r requirements.txt --upgrade
```

### Verificar Versão dos Módulos
```bash
pip list | grep -E "(openai|rich|docling|pandas)"
```

### Backup de Configurações
```bash
# Fazer backup das configurações
cp supabase_v0.env supabase_v0.env.backup
cp .env .env.backup
```

---

## 🎯 Configurações Avançadas

### ⚡ Performance
```python
# No início de gvg_search_utils_v3.py
MAX_RESULTS = 50        # Reduzir para melhor performance
CACHE_EMBEDDINGS = True # Ativar cache de embeddings
```

### 🐛 Debug Avançado
```python
# Ativar logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 🔒 Segurança
```bash
# Proteger arquivo de credenciais
chmod 600 supabase_v0.env  # Linux/Mac
```

---

## 📞 Suporte

### 🆘 Problemas Comuns
1. **ImportError**: Verifique requirements.txt
2. **ConnectionError**: Teste credenciais do banco
3. **AuthenticationError**: Verifique OpenAI API key
4. **ModuleNotFoundError**: Instale dependência específica

### 📧 Contato
- **Mantenedor**: Haroldo Duraes
- **GitHub**: [Repositório do projeto]
- **Issues**: Abra uma issue para reportar problemas

### 📝 Logs
Logs do sistema ficam em:
- Windows: `%TEMP%/govgo_logs/`
- Linux/Mac: `/tmp/govgo_logs/`

---

**🎉 Instalação concluída com sucesso!**

Agora você pode usar:
- `python GvG_SP_Search_Terminal_v9.py` (interface rica)
- `python GvG_Search_Prompt_v0.py --prompt "sua busca"` (linha de comando)
