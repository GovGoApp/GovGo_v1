# 🤖 OpenAI Assistants do GovGo V0 - Inventário Completo

**Todos os assistants OpenAI encontrados no sistema V0 e migrados para V1**

---

## 📊 **RESUMO EXECUTIVO**

**Total de Assistants encontrados:** 16 únicos  
**Categorias principais:** 4 (Busca, Relatórios, Categorização, Análise)  
**Status:** Todos migrados para `.env.template` do V1  

---

## 🔍 **ASSISTANTS POR CATEGORIA**

### **1. SISTEMA DE BUSCA E RELEVÂNCIA**

#### **Relevância (Nível de Filtro)**
```env
# Nível 2 - Flexível (mais resultados)
OPENAI_ASSISTANT_FLEXIBLE=asst_tfD5oQxSgoGhtqdKQHK9UwRi
# Arquivo: relevance_pncp_v3.txt
# Usado em: Terminal_v9, Prompt_v0

# Nível 3 - Restritivo (resultados precisos)  
OPENAI_ASSISTANT_RESTRICTIVE=asst_XmsefQEKbuVWu51uNST7kpYT
# Arquivo: relevance_pncp_v2.txt
# Usado em: Terminal_v9, Prompt_v0
```

#### **Pré-processamento**
```env
# Processamento inteligente de consultas
OPENAI_ASSISTANT_PREPROCESSING=asst_argxuo1SK6KE3HS5RGo4VRBV
# Arquivo: SUPABASE_SEARCH_v0.txt
# Usado em: gvg_pre_processing_v3.py
```

#### **Filtro de Busca**
```env
# Filtro de relevância secundário
OPENAI_ASSISTANT_SEARCH_FILTER=asst_sc5so6LwQEhB6G9FcVSten0S
# Usado em: gvg_search_utils_v3.py, Terminal_v9
```

### **2. SISTEMA DE RELATÓRIOS (6 Versões)**

#### **Série PNCP_SQL (5 versões evolutivas)**
```env
# V0 - Assistente original
OPENAI_ASSISTANT_REPORTS_V0=asst_LkOV3lLggXAavj40gdR7hZ4D
# Usado em: reports_v2.py até reports_v8.py

# V1 - Campos retirados
OPENAI_ASSISTANT_REPORTS_V1=asst_o7FQefGAlMuBz0yETyR7b3mA
# Usado em: gvg_CL_reports_v3.py

# V2 - Campos essenciais
OPENAI_ASSISTANT_REPORTS_V2=asst_Lf3lJg6enUnmtiT9LTevrDs8
# Usado em: gvg_CL_reports_v3.py

# V3 - Resumido
OPENAI_ASSISTANT_REPORTS_V3=asst_I2ORXWjoGDiumco9AAknbX4z
# Usado em: gvg_CL_reports_v3.py

# V4 - Classificação de itens
OPENAI_ASSISTANT_REPORTS_V4=asst_FHf43YVJk8a6DGl4C0dGYDVC
# Usado em: gvg_CL_reports_v3.py
```

#### **Relatórios Supabase**
```env
# SUPABASE_SQL_v0 Assistant
OPENAI_ASSISTANT_SUPABASE_REPORTS=asst_MoxO9SNrQt4313fJ8Lzqt7iA
# Usado em: GvG_SU_Report_v0.py, v1.py, v2.py
```

### **3. SISTEMA DE CATEGORIZAÇÃO**

```env
# Cat Finder (GPT-3.5 Turbo)
OPENAI_ASSISTANT_CATEGORY_FINDER=asst_Gxxpxxy951ai6CJoLkf6k6IJ
# Usado em: cat_finder_v0.py, v1.py, v2.py

# Category Validator
OPENAI_ASSISTANT_CATEGORY_VALIDATOR=asst_mnqJ7xzDWphZXH18aOazymct
# Usado em: av_v0.py, av_v1.py, av_v2.py (Classy Validator)

# Items Classifier (MSOCIT_to_TEXT)
OPENAI_ASSISTANT_ITEMS_CLASSIFIER=asst_Rqb93ZDsLBPDTyYAc6JhHiYz
# Usado em: ci_v0_3.py (Classy Itens)
```

### **4. SISTEMA DE ANÁLISE E DOCUMENTOS**

```env
# Financial Analyzer
OPENAI_ASSISTANT_FINANCIAL_ANALYZER=asst_G8pkl29kFjPbAhYlS2kAclsU
# Usado em: financial_analyzer.py, monthly_report_processor.py

# PDF Processor V0 (RESUMEE_v0)
OPENAI_ASSISTANT_PDF_PROCESSOR_V0=asst_MuNzNFI5wiG481ogsVWQv52p
# Usado em: pdf_report_processor.py, simple_processor.py

# PDF Processor V1 (RESUMEE_v1) 
OPENAI_ASSISTANT_PDF_PROCESSOR_V1=asst_qPkntEzl6JPch7UV08RW52i4
# Usado em: pdf_report_processor_v2.py, v3.py, v4.py
```

---

## 📁 **LOCALIZAÇÃO DOS ASSISTANTS NO V0**

### **Por Módulo/Diretório:**

#### **GvG/Search/Prompt/ (Sistema Principal de Busca)**
- `asst_tfD5oQxSgoGhtqdKQHK9UwRi` - Relevância flexível
- `asst_XmsefQEKbuVWu51uNST7kpYT` - Relevância restritiva  
- `asst_argxuo1SK6KE3HS5RGo4VRBV` - Pré-processamento
- `asst_sc5so6LwQEhB6G9FcVSten0S` - Filtro de busca

#### **REPORTS/ (Relatórios Principais)**
- `asst_LkOV3lLggXAavj40gdR7hZ4D` - 7 arquivos (reports_v2 a v8)

#### **GvG/Reports/ (Relatórios Especializados)**
- `asst_LkOV3lLggXAavj40gdR7hZ4D` - Claude reports
- `asst_o7FQefGAlMuBz0yETyR7b3mA` - SQL v1
- `asst_Lf3lJg6enUnmtiT9LTevrDs8` - SQL v2  
- `asst_I2ORXWjoGDiumco9AAknbX4z` - SQL v3
- `asst_FHf43YVJk8a6DGl4C0dGYDVC` - SQL v4
- `asst_MoxO9SNrQt4313fJ8Lzqt7iA` - Supabase reports

#### **PNCP_DATA/CAT/ (Sistema de Categorização)**
- `asst_Gxxpxxy951ai6CJoLkf6k6IJ` - Cat finder (3 versões)
- `asst_mnqJ7xzDWphZXH18aOazymct` - Validator (3 versões)
- `asst_Rqb93ZDsLBPDTyYAc6JhHiYz` - Items classifier

#### **Docs/ (Análise de Documentos)**
- `asst_G8pkl29kFjPbAhYlS2kAclsU` - Financial analyzer
- `asst_MuNzNFI5wiG481ogsVWQv52p` - PDF processor V0
- `asst_qPkntEzl6JPch7UV08RW52i4` - PDF processor V1

---

## ⚙️ **CONFIGURAÇÃO NO V1**

### **Arquivo: `.env.template`**
```env
# ===============================
# ASSISTANTS OPENAI (V0 System)
# ===============================

# Sistema de relevância (Search/Prompt)
OPENAI_ASSISTANT_FLEXIBLE=asst_tfD5oQxSgoGhtqdKQHK9UwRi
OPENAI_ASSISTANT_RESTRICTIVE=asst_XmsefQEKbuVWu51uNST7kpYT

# Sistema de busca e pré-processamento
OPENAI_ASSISTANT_PREPROCESSING=asst_argxuo1SK6KE3HS5RGo4VRBV
OPENAI_ASSISTANT_SEARCH_FILTER=asst_sc5so6LwQEhB6G9FcVSten0S

# Sistema de relatórios (5 versões)
OPENAI_ASSISTANT_REPORTS_V0=asst_LkOV3lLggXAavj40gdR7hZ4D
OPENAI_ASSISTANT_REPORTS_V1=asst_o7FQefGAlMuBz0yETyR7b3mA
OPENAI_ASSISTANT_REPORTS_V2=asst_Lf3lJg6enUnmtiT9LTevrDs8
OPENAI_ASSISTANT_REPORTS_V3=asst_I2ORXWjoGDiumco9AAknbX4z
OPENAI_ASSISTANT_REPORTS_V4=asst_FHf43YVJk8a6DGl4C0dGYDVC

# Sistema de relatórios Supabase
OPENAI_ASSISTANT_SUPABASE_REPORTS=asst_MoxO9SNrQt4313fJ8Lzqt7iA

# Sistema de categorização
OPENAI_ASSISTANT_CATEGORY_FINDER=asst_Gxxpxxy951ai6CJoLkf6k6IJ
OPENAI_ASSISTANT_CATEGORY_VALIDATOR=asst_mnqJ7xzDWphZXH18aOazymct
OPENAI_ASSISTANT_ITEMS_CLASSIFIER=asst_Rqb93ZDsLBPDTyYAc6JhHiYz

# Sistema de análise financeira e documentos
OPENAI_ASSISTANT_FINANCIAL_ANALYZER=asst_G8pkl29kFjPbAhYlS2kAclsU
OPENAI_ASSISTANT_PDF_PROCESSOR_V0=asst_MuNzNFI5wiG481ogsVWQv52p
OPENAI_ASSISTANT_PDF_PROCESSOR_V1=asst_qPkntEzl6JPch7UV08RW52i4
```

### **Arquivo: `src/config/models.py`**
```python
# Os IDs dos assistants vêm do .env
# Este arquivo apenas documenta e provê funções helper

config = get_model_config()
assistants = config.get_assistants()

# Buscar assistant específico
search_assistant = get_assistant_by_category(config, "search", "flexible")
reports_assistant = get_assistant_by_category(config, "reports", "v0")

# Documentação disponível
from src.config import ASSISTANTS_DOCUMENTATION
print(ASSISTANTS_DOCUMENTATION["search"]["flexible"])
# Output: "Filtro suave via IA - mais resultados (relevance_pncp_v3.txt)"
```

---

## 🔄 **EVOLUÇÃO DOS ASSISTANTS**

### **Sistema de Relatórios (Evolução)**
1. **V0** (`asst_LkOV3lLggXAavj40gdR7hZ4D`) - Original completo
2. **V1** (`asst_o7FQefGAlMuBz0yETyR7b3mA`) - Campos retirados  
3. **V2** (`asst_Lf3lJg6enUnmtiT9LTevrDs8`) - Campos essenciais
4. **V3** (`asst_I2ORXWjoGDiumco9AAknbX4z`) - Resumido
5. **V4** (`asst_FHf43YVJk8a6DGl4C0dGYDVC`) - Classificação de itens

### **Sistema de PDF (Evolução)**
1. **V0** (`asst_MuNzNFI5wiG481ogsVWQv52p`) - RESUMEE_v0
2. **V1** (`asst_qPkntEzl6JPch7UV08RW52i4`) - RESUMEE_v1 (atual)

### **Sistema de Categorização (Especialização)**
1. **Finder** (`asst_Gxxpxxy951ai6CJoLkf6k6IJ`) - Busca categorias
2. **Validator** (`asst_mnqJ7xzDWphZXH18aOazymct`) - Valida categorias
3. **Classifier** (`asst_Rqb93ZDsLBPDTyYAc6JhHiYz`) - Classifica itens

---

## 🎯 **USO NO V1**

### **Prioridades de Migração:**
1. **🔥 Críticos:** Sistema de relevância (flexível + restritivo)
2. **📊 Importantes:** Relatórios V0 e Supabase
3. **🏷️ Úteis:** Sistema de categorização
4. **📄 Opcionais:** Análise de documentos

### **Configuração Recomendada V1:**
```python
# Uso limpo - os IDs vêm do .env
from src.config import get_model_config, get_assistant_by_category

config = get_model_config()

# Assistants essenciais
search_flexible = get_assistant_by_category(config, "search", "flexible")
search_restrictive = get_assistant_by_category(config, "search", "restrictive") 
reports_main = get_assistant_by_category(config, "reports", "v0")
supabase_reports = get_assistant_by_category(config, "reports", "supabase")

# Verificar se estão configurados
essential_assistants = {
    "search_flexible": search_flexible,
    "search_restrictive": search_restrictive,
    "reports_main": reports_main,
    "supabase_reports": supabase_reports
}

# Validar
missing = [name for name, aid in essential_assistants.items() if not aid]
if missing:
    print(f"⚠️  Assistants não configurados: {missing}")
else:
    print("✅ Todos os assistants essenciais configurados!")
```

---

## ✅ **RESULTADO**

**16 assistants OpenAI** foram identificados e catalogados no sistema V0:
- ✅ **Todos mapeados** por categoria e função
- ✅ **Migrados para V1** (.env.template + models.py)
- ✅ **Documentados** com propósito e localização
- ✅ **Estruturados** para uso modular no V1

**O GovGo V1 agora tem acesso completo a todos os assistants especializados do V0, mantendo total compatibilidade e expandindo funcionalidades.**
