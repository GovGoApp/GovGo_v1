import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from openai import OpenAI
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QTextEdit, QLabel, QTableWidget, 
                             QTableWidgetItem, QFileDialog, QProgressBar, QMessageBox,
                             QSplitter, QFrame, QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette

# Base paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = os.path.join(BASE_PATH, "DB")
DB_FILE = os.path.join(DB_PATH, "pncp.db")
REPORTS_PATH = os.path.join(BASE_PATH, "REPORTS")
if not os.path.exists(REPORTS_PATH):
    os.makedirs(REPORTS_PATH)

# OpenAI configuration
client = OpenAI(api_key="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")
thread = client.beta.threads.create()
assistant_id = "asst_LkOV3lLggXAavj40gdR7hZ4D"
model_id = "gpt-4o"

class SqlGenerationWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, nl_query):
        super().__init__()
        self.nl_query = nl_query
    
    def run(self):
        try:
            sql = self.generate_sql_from_nl(self.nl_query)
            if sql:
                self.finished.emit(sql)
            else:
                self.error.emit("Failed to generate SQL")
        except Exception as e:
            self.error.emit(str(e))
    
    def send_user_message(self, content):
        formatted_content = [{"type": "text", "text": content}]
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=formatted_content
        )
    
    def poll_run(self):
        return client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )
    
    def get_latest_assistant_message(self):
        messages = list(client.beta.threads.messages.list(thread_id=thread.id))
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        return assistant_messages[0] if assistant_messages else None
    
    def extract_sql_from_message(self, message):
        blocks = message.content if isinstance(message.content, list) else [message.content]
        sql_parts = []
        for block in blocks:
            if isinstance(block, dict) and "text" in block:
                sql_parts.append(block["text"])
            elif hasattr(block, "text") and hasattr(block.text, "value"):
                sql_parts.append(block.text.value)
            else:
                sql_parts.append(str(block))
        sql_query = " ".join(sql_parts)
        return " ".join(sql_query.replace("\n", " ").split())
    
    def get_assistant_response(self, user_query):
        self.send_user_message(user_query)
        run = self.poll_run()
        if run.status == 'completed':
            last_message = self.get_latest_assistant_message()
            if not last_message:
                return None
            return last_message
        return None
    
    def generate_sql_from_nl(self, nl_query):
        assistant_message = self.get_assistant_response(nl_query)
        if assistant_message:
            return self.extract_sql_from_message(assistant_message)
        return None

class DataQueryWorker(QThread):
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)
    
    def __init__(self, sql):
        super().__init__()
        self.sql = sql
    
    def run(self):
        try:
            conn = sqlite3.connect(DB_FILE)
            df = pd.read_sql_query(self.sql, conn)
            conn.close()
            self.finished.emit(df)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_df = None
        self.current_sql = None
        self.initUI()
    
    def initUI(self):
        # Set window properties
        self.setWindowTitle('PNCP AI Assistant')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for top and bottom sections
        splitter = QSplitter(Qt.Vertical)
        
        # Top section - Query input
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Query input label
        query_label = QLabel("Consulta em linguagem natural:")
        query_label.setFont(QFont("Arial", 12, QFont.Bold))
        top_layout.addWidget(query_label)
        
        # Query input text field
        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText("Digite sua consulta aqui... (ex: Mostre todos os contratos de 2024 acima de 1 milhão de reais)")
        self.query_input.setMinimumHeight(100)
        self.query_input.setFont(QFont("Arial", 11))
        top_layout.addWidget(self.query_input)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Execute query button
        self.execute_btn = QPushButton("Executar Consulta")
        self.execute_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.execute_btn.setMinimumHeight(40)
        self.execute_btn.clicked.connect(self.execute_query)
        button_layout.addWidget(self.execute_btn)
        
        # Save report button
        self.save_btn = QPushButton("Salvar Relatório")
        self.save_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_report)
        button_layout.addWidget(self.save_btn)
        
        top_layout.addLayout(button_layout)
        
        # SQL display section
        sql_frame = QFrame()
        sql_layout = QVBoxLayout(sql_frame)
        
        sql_label = QLabel("SQL Gerado:")
        sql_label.setFont(QFont("Arial", 11, QFont.Bold))
        sql_layout.addWidget(sql_label)
        
        self.sql_display = QTextEdit()
        self.sql_display.setReadOnly(True)
        self.sql_display.setFont(QFont("Consolas", 10))
        self.sql_display.setMaximumHeight(100)
        sql_layout.addWidget(self.sql_display)
        
        top_layout.addWidget(sql_frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Pronto")
        self.progress_bar.setValue(0)
        top_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(top_widget)
        
        # Bottom section - Results
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        results_label = QLabel("Resultados:")
        results_label.setFont(QFont("Arial", 12, QFont.Bold))
        bottom_layout.addWidget(results_label)
        
        # Data table
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setFont(QFont("Arial", 10))
        bottom_layout.addWidget(self.results_table)
        
        # Results info
        self.results_info = QLabel("Sem resultados para exibir")
        self.results_info.setFont(QFont("Arial", 10))
        bottom_layout.addWidget(self.results_info)
        
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 500])
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Pronto")
    
    def execute_query(self):
        nl_query = self.query_input.toPlainText().strip()
        if not nl_query:
            QMessageBox.warning(self, "Atenção", "Por favor, digite uma consulta.")
            return
        
        self.progress_bar.setValue(25)
        self.progress_bar.setFormat("Gerando SQL...")
        self.statusBar.showMessage("Gerando SQL...")
        self.execute_btn.setEnabled(False)
        
        # Generate SQL from natural language
        self.sql_worker = SqlGenerationWorker(nl_query)
        self.sql_worker.finished.connect(self.on_sql_generated)
        self.sql_worker.error.connect(self.on_error)
        self.sql_worker.start()
    
    def on_sql_generated(self, sql):
        self.current_sql = sql
        self.sql_display.setText(sql)
        
        self.progress_bar.setValue(50)
        self.progress_bar.setFormat("Executando consulta...")
        self.statusBar.showMessage("Executando consulta...")
        
        # Execute SQL query
        self.data_worker = DataQueryWorker(sql)
        self.data_worker.finished.connect(self.on_data_loaded)
        self.data_worker.error.connect(self.on_error)
        self.data_worker.start()
    
    def on_data_loaded(self, df):
        self.current_df = df
        self.display_data(df)
        
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Concluído")
        self.statusBar.showMessage(f"Consulta concluída. {len(df)} registros encontrados.")
        self.execute_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
    
    def on_error(self, error_msg):
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Erro")
        self.statusBar.showMessage(f"Erro: {error_msg}")
        self.execute_btn.setEnabled(True)
        QMessageBox.critical(self, "Erro", f"Ocorreu um erro: {error_msg}")
    
    def display_data(self, df):
        # Clear previous data
        self.results_table.clear()
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(0)
        
        if df.empty:
            self.results_info.setText("A consulta não retornou resultados.")
            return
        
        # Set column headers
        self.results_table.setColumnCount(len(df.columns))
        self.results_table.setHorizontalHeaderLabels(df.columns)
        
        # Populate the table with data
        row_limit = min(1000, len(df))  # Limit display to 1000 rows for performance
        self.results_table.setRowCount(row_limit)
        
        for row_idx in range(row_limit):
            for col_idx, value in enumerate(df.iloc[row_idx]):
                item = QTableWidgetItem(str(value))
                self.results_table.setItem(row_idx, col_idx, item)
        
        # Auto-adjust column widths
        self.results_table.resizeColumnsToContents()
        
        # Update info text
        if len(df) > row_limit:
            self.results_info.setText(f"Exibindo {row_limit} de {len(df)} registros. Salve o relatório para ver todos os dados.")
        else:
            self.results_info.setText(f"Total: {len(df)} registros.")
    
    def save_report(self):
        if self.current_df is None:
            QMessageBox.warning(self, "Atenção", "Nenhum dado para salvar.")
            return
        
        try:
            # Generate filename based on SQL query
            suggested_name = self.generate_report_filename(self.current_sql)
            
            # Ask user for save location
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Salvar Relatório", 
                os.path.join(REPORTS_PATH, suggested_name),
                "Excel Files (*.xlsx)"
            )
            
            if not filepath:
                return
            
            # Add .xlsx extension if not present
            if not filepath.endswith('.xlsx'):
                filepath += '.xlsx'
            
            self.progress_bar.setValue(25)
            self.progress_bar.setFormat("Salvando relatório...")
            self.statusBar.showMessage("Salvando relatório...")
            
            # Handle large datasets
            total_rows = len(self.current_df)
            if total_rows > 1048576:
                with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                    # Calculate how many sheets needed
                    max_rows_per_sheet = 1048575  # Excel limit minus header
                    num_sheets = (total_rows + max_rows_per_sheet - 1) // max_rows_per_sheet
                    
                    for i in range(num_sheets):
                        start_row = i * max_rows_per_sheet
                        end_row = min((i + 1) * max_rows_per_sheet, total_rows)
                        sheet_name = f"Dados_{i+1}"
                        
                        # Save the subset to current sheet
                        self.current_df.iloc[start_row:end_row].to_excel(
                            writer, sheet_name=sheet_name, index=False)
                        
                        self.progress_bar.setValue(25 + (75 * (i + 1) // num_sheets))
                
                msg = f"Relatório dividido em {num_sheets} abas devido ao tamanho ({total_rows} linhas)."
            else:
                # Normal save
                self.current_df.to_excel(filepath, index=False)
                msg = f"Relatório salvo com {total_rows} linhas."
            
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Relatório salvo")
            self.statusBar.showMessage(f"Relatório salvo em: {filepath}")
            QMessageBox.information(self, "Sucesso", f"{msg}\nSalvo em: {filepath}")
        
        except Exception as e:
            self.statusBar.showMessage(f"Erro ao salvar: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Erro ao salvar relatório: {str(e)}")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Erro")
    
    def generate_report_filename(self, sql):
        """Generate filename for the report using OpenAI to analyze SQL query"""
        try:
            system_msg = (
                "Você é um assistente especialista em geração de nomes de arquivos para relatórios, "
                "seguindo o padrão: {QUAL}_{COMO}_{O QUÊ}_{ONDE}_{QUANDO}. "
                "QUAL é a tabela principal, COMO é a função ou agregação (ex: CONTAGEM, SOMA, MÉDIA), "
                "O QUÊ é o objeto da compra ou contrato, ONDE é a região/estado/município/entidade/órgão, QUANDO é o período (mês/ano). "
                "A resposta deve conter somente o nome completo do arquivo em letra maiúscula."
            )
            
            user_prompt = f"SQL: {sql}\n\nGere o nome do relatório seguindo o padrão."
            
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=50
            )
            
            file_name = response.choices[0].message.content.strip().upper()
            
            # Ensure filename ends with .xlsx
            if not file_name.endswith(".xlsx"):
                file_name += ".xlsx"
                
            return file_name
            
        except Exception as e:
            # Default filename if there's an error
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"RELATORIO_{timestamp}.xlsx"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Apply custom palette for a modern look
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())