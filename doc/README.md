# 🚀 GOVGO V1 - SETUP E PRIMEIROS PASSOS

Este guia orienta a configuração inicial da GovGo v1.

## 📋 **PRÉ-REQUISITOS**

### **🐍 Python 3.11+**
```bash
python --version  # Deve ser 3.11 ou superior
```

### **🗄️ Supabase Pro**
- Conta Supabase Pro (para volume de dados)
- Instância PostgreSQL com pgvector habilitado
- URL e chaves de API

### **🤖 OpenAI API**
- Conta OpenAI com acesso à API
- Chave de API válida

## ⚙️ **CONFIGURAÇÃO INICIAL**

### **1. Clone e Navegue**
```bash
cd "c:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\v1"
```

### **2. Instale Dependências**
```bash
pip install -r requirements.txt
```

### **3. Configure Variáveis de Ambiente**
```bash
# Copie o template
cp .env.template .env

# Edite o arquivo .env com suas credenciais
notepad .env
```

**📝 Preencha no `.env`:**
```env
SUPABASE_URL=https://sua-instancia.supabase.co
SUPABASE_KEY=sua_chave_aqui
SUPABASE_DB_URL=postgresql://postgres:senha@...
OPENAI_API_KEY=sk-sua_chave_aqui
```

### **4. Crie Estrutura do Banco**

**❓ POSSO CRIAR O SCRIPT DE SETUP DO BANCO?**

Depois de confirmar, execute:
```bash
python setup_database.py
```

## 🏗️ **ESTRUTURA CRIADA**

```
v1/
├── 📁 core/                    # ✅ Módulos principais
│   ├── config.py              # ✅ Configuração centralizada
│   ├── database.py            # ✅ Gerenciador de banco
│   ├── models.py              # ✅ Modelos de dados
│   └── utils.py               # ✅ Utilitários comuns
├── 📁 collectors/              # 🔄 Coletores de dados PNCP
├── 📁 processors/              # 🔄 Processamento e embeddings
├── 📁 search/                  # 🔄 Sistema de busca
├── 📁 interfaces/              # 🔄 Interfaces do usuário
├── 📄 requirements.txt         # ✅ Dependências
├── 📄 .env.template           # ✅ Template de configuração
└── 📄 ARQUITETURA_V1.md       # ✅ Documentação completa
```

## 🧪 **TESTE DA CONFIGURAÇÃO**

**❓ POSSO CRIAR O SCRIPT DE TESTE?**

Depois de confirmar, execute:
```bash
python test_setup.py
```

Deve exibir:
```
✅ Configuração validada
✅ Conexão Supabase OK
✅ OpenAI API OK
✅ Estrutura de banco OK
🎉 Sistema pronto para uso!
```

## 📚 **PRÓXIMOS PASSOS**

1. **Implemente Coletores** (collectors/)
2. **Configure Processamento** (processors/)
3. **Setup Sistema de Busca** (search/)
4. **Execute Pipeline** (govgo_v1_pipeline.py)

## 🆘 **TROUBLESHOOTING**

### **Erro de Conexão Supabase**
- Verifique URL e chave
- Confirme que pgvector está habilitado
- Teste conectividade de rede

### **Erro OpenAI API**
- Verifique chave de API
- Confirme créditos disponíveis
- Teste com chamada simples

### **Erro de Dependências**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## 📞 **SUPORTE**

- 📧 Email: [seu-email]
- 🐛 Issues: GitHub repo
- 📚 Docs: ./ARQUITETURA_V1.md

---

*Sistema GovGo v1 - Portal Nacional de Contratações Públicas*
