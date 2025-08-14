import os
import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

# --- Configurações e Variáveis Globais ---
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

# --- Funções de Lógica (adaptadas de reports_v8.py) ---

# Nesta função, o ideal é que a consulta em linguagem natural
# seja convertida em SQL por meio de interação com a API OpenAI.
# Aqui, para demonstração, retornamos um SQL de exemplo.
def generate_sql_from_nl(nl_query: str) -> str:
    # Em ambiente real, você chamaria get_assistant_response() e extrairia o SQL.
    # Exemplo: "SELECT * FROM contrato LIMIT 100;" ou uma query derivada de nl_query.
    return "SELECT * FROM contrato LIMIT 100;"

# A função para gerar o nome do arquivo a partir do SQL pode ser mais sofisticada.
# Aqui, usaremos um exemplo simples.
def generate_report_filename(sql: str) -> str:
    # Exemplo: Se o SQL fizer referência à tabela "contrato", retornamos "CONTRATO_REPORT.xlsx"
    base_name = "REPORT"
    if "contrato" in sql.lower():
        base_name = "CONTRATO_REPORT"
    elif "plan" in sql.lower():
        base_name = "PLANO_REPORT"
    # Garante que o nome esteja em maiúsculas e termine com .xlsx
    file_name = base_name.upper()
    if not file_name.endswith(".XLSX"):
        file_name += ".xlsx"
    return file_name

# Executa a query SQL no banco de dados e retorna o DataFrame com os resultados.
def execute_report_base(sql: str) -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(sql, conn)
        conn.close()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao executar a query:\n{e}")
        return None
    return df

# --- Interface Gráfica (GUI) usando Tkinter ---
class GovGoUI:
    def __init__(self, master):
        self.master = master
        master.title("GovGo Assistente PNCP")
        master.geometry("800x600")

        # Criação dos frames para organização dos elementos
        self.top_frame = ttk.Frame(master)
        self.top_frame.pack(padx=10, pady=10, fill=tk.X)

        self.middle_frame = ttk.Frame(master)
        self.middle_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.bottom_frame = ttk.Frame(master)
        self.bottom_frame.pack(padx=10, pady=10, fill=tk.X)

        # Campo de entrada para a consulta em linguagem natural
        self.label_query = ttk.Label(self.top_frame, text="Consulta (Linguagem Natural):")
        self.label_query.pack(side=tk.TOP, anchor="w")

        self.text_query = scrolledtext.ScrolledText(self.top_frame, height=3)
        self.text_query.pack(fill=tk.X)

        # Botão para gerar o SQL a partir da consulta
        self.btn_generate = ttk.Button(self.top_frame, text="Gerar SQL", command=self.gerar_sql)
        self.btn_generate.pack(pady=5)

        # Área para exibição do SQL gerado
        self.label_sql = ttk.Label(self.top_frame, text="SQL Gerado:")
        self.label_sql.pack(anchor="w")
        self.text_sql = scrolledtext.ScrolledText(self.top_frame, height=2, state=tk.DISABLED)
        self.text_sql.pack(fill=tk.X)

        # Barra de progresso para indicar atividades em segundo plano
        self.progress = ttk.Progressbar(self.bottom_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=5)

        # Botões de execução e salvamento do relatório
        self.btn_executar = ttk.Button(self.bottom_frame, text="Executar Relatório", command=self.executar_relatorio)
        self.btn_executar.pack(side=tk.LEFT, padx=5)

        self.btn_salvar = ttk.Button(self.bottom_frame, text="Salvar Relatório", command=self.salvar_relatorio, state=tk.DISABLED)
        self.btn_salvar.pack(side=tk.LEFT, padx=5)

        # Área (Treeview) para exibição do preview dos dados
        self.tree = None
        self.df_preview = None
        self.current_df = None

    def gerar_sql(self):
        nl_query = self.text_query.get("1.0", tk.END).strip()
        if not nl_query:
            messagebox.showwarning("Aviso", "Por favor, insira uma consulta em linguagem natural.")
            return
        self.progress.start()
        # Aqui, é chamada a função que gera o SQL e atualiza a interface
        self.master.after(100, self._gerar_sql_thread, nl_query)

    def _gerar_sql_thread(self, nl_query: str):
        sql = generate_sql_from_nl(nl_query)
        self.text_sql.config(state=tk.NORMAL)
        self.text_sql.delete("1.0", tk.END)
        self.text_sql.insert(tk.END, sql)
        self.text_sql.config(state=tk.DISABLED)
        self.progress.stop()

    def executar_relatorio(self):
        sql = self.text_sql.get("1.0", tk.END).strip()
        if not sql:
            messagebox.showwarning("Aviso", "Nenhum SQL gerado para execução.")
            return
        self.progress.start()
        self.master.after(100, self._executar_relatorio_thread, sql)

    def _executar_relatorio_thread(self, sql: str):
        df = execute_report_base(sql)
        self.progress.stop()
        if df is None:
            return
        self.current_df = df
        total_rows = len(df)
        # Cria um preview com as 10 primeiras linhas e até 7 colunas
        preview_df = df.iloc[:10, :min(7, len(df.columns))]
        self.df_preview = preview_df
        # Se houver uma Treeview anterior, destruí-la
        if self.tree:
            self.tree.destroy()
        self.tree = ttk.Treeview(self.middle_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        # Configura as colunas da Treeview
        self.tree["columns"] = list(preview_df.columns)
        self.tree["show"] = "headings"
        for col in preview_df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        # Insere as linhas do preview
        for _, row in preview_df.iterrows():
            self.tree.insert("", tk.END, values=list(row))
        # Exibe uma mensagem informativa
        messagebox.showinfo("Informação", f"Total de linhas retornadas: {total_rows}\nSQL Gerado:\n{sql}")
        # Habilita o botão para salvar relatório
        self.btn_salvar.config(state=tk.NORMAL)

    def salvar_relatorio(self):
        if self.current_df is None:
            messagebox.showwarning("Aviso", "Nenhum relatório a ser salvo.")
            return
        resposta = messagebox.askyesno("Salvar Relatório", "Deseja salvar o relatório?")
        if not resposta:
            return
        # Gera o nome do arquivo a partir do SQL
        sql = self.text_sql.get("1.0", tk.END).strip()
        file_name = generate_report_filename(sql)
        # Permite que o usuário escolha o local do arquivo (pasta REPORTS_PATH por padrão)
        file_path = filedialog.asksaveasfilename(initialdir=REPORTS_PATH,
                                                 initialfile=file_name,
                                                 defaultextension=".xlsx",
                                                 filetypes=[("Excel files", "*.xlsx")])
        if not file_path:
            return
        total_rows = len(self.current_df)
        try:
            if total_rows > 1048576:
                messagebox.showwarning("Atenção", f"O resultado possui {total_rows} linhas, excedendo o limite de 1.048.576 linhas por planilha do Excel.\nOs dados serão divididos em múltiplas abas.")
                max_rows_per_sheet = 1048575  # Considera a linha de cabeçalho
                num_sheets = (total_rows + max_rows_per_sheet - 1) // max_rows_per_sheet
                with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                    for i in range(num_sheets):
                        start_row = i * max_rows_per_sheet
                        end_row = min((i + 1) * max_rows_per_sheet, total_rows)
                        sheet_name = f"Dados_{i+1}"
                        self.current_df.iloc[start_row:end_row].to_excel(writer, sheet_name=sheet_name, index=False)
                messagebox.showinfo("Sucesso", f"Relatório dividido em {num_sheets} abas e salvo com sucesso em:\n{file_path}")
            else:
                self.current_df.to_excel(file_path, index=False)
                messagebox.showinfo("Sucesso", f"Relatório salvo com sucesso em:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar relatório:\n{e}")

def main():
    root = tk.Tk()
    app = GovGoUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
