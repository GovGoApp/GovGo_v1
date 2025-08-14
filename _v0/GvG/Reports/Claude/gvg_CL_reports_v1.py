import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
import io
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QTextEdit, QLabel, QTableWidget, 
                            QTableWidgetItem, QScrollArea, QFrame, QSplitter,
                            QStatusBar, QMessageBox, QFileDialog, QLineEdit)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPalette
from openai import OpenAI

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
                self.error.emit("Falha ao gerar SQL")
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

class QueryBubble(QFrame):
    """Custom widget for displaying query examples"""
    clicked = pyqtSignal(str, str)
    
    def __init__(self, nl_query, sql_query, parent=None):
        super().__init__(parent)
        self.nl_query = nl_query
        self.sql_query = sql_query
        
        # Setup styling
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QueryBubble {
                background-color: #E6F2FF;
                border-radius: 20px;
                padding: 10px;
                margin: 5px;
            }
            QLabel {
                background-color: transparent;
            }
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        
        # NL query text
        self.nl_label = QLabel(nl_query)
        self.nl_label.setFont(QFont("Arial", 11))
        self.nl_label.setWordWrap(True)
        self.nl_label.setStyleSheet("color: #004080; font-weight: bold;")
        layout.addWidget(self.nl_label)
        
        # SQL query text
        self.sql_label = QLabel(sql_query)
        self.sql_label.setFont(QFont("Consolas", 9))
        self.sql_label.setWordWrap(True)
        self.sql_label.setStyleSheet("color: #303030;")
        layout.addWidget(self.sql_label)
        
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.nl_query, self.sql_query)
        super().mousePressEvent(event)

class ResultFrame(QFrame):
    """Custom widget for displaying query results"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("""
            ResultFrame {
                border: 1px solid #C0C0C0;
                border-radius: 10px;
                background-color: white;
                margin: 10px;
            }
        """)
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Table for results
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #F0F8FF;")
        self.layout.addWidget(self.table)
        
        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignRight)
        
        # Download button
        self.download_btn = QPushButton()
        self.download_btn.setIcon(QIcon("download_icon.png"))  # Replace with actual icon
        self.download_btn.setIconSize(QSize(24, 24))
        self.download_btn.setFixedSize(32, 32)
        self.download_btn.setToolTip("Baixar como Excel")
        btn_layout.addWidget(self.download_btn)
        
        # Cloud button
        self.cloud_btn = QPushButton()
        self.cloud_btn.setIcon(QIcon("cloud_icon.png"))  # Replace with actual icon
        self.cloud_btn.setIconSize(QSize(24, 24))
        self.cloud_btn.setFixedSize(32, 32)
        self.cloud_btn.setToolTip("Salvar na nuvem")
        btn_layout.addWidget(self.cloud_btn)
        
        # Share button
        self.share_btn = QPushButton()
        self.share_btn.setIcon(QIcon("share_icon.png"))  # Replace with actual icon
        self.share_btn.setIconSize(QSize(24, 24))
        self.share_btn.setFixedSize(32, 32)
        self.share_btn.setToolTip("Compartilhar")
        btn_layout.addWidget(self.share_btn)
        
        self.layout.addLayout(btn_layout)
        
        # Connect signals
        self.download_btn.clicked.connect(self.download_results)
    
    def display_data(self, df):
        # Clear previous data
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        
        self.df = df  # Store reference to the dataframe
        
        if df.empty:
            return
        
        # Set column headers
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)
        
        # Populate the table with data
        row_limit = min(1000, len(df))  # Limit display to 1000 rows for performance
        self.table.setRowCount(row_limit)
        
        for row_idx in range(row_limit):
            for col_idx, value in enumerate(df.iloc[row_idx]):
                item = QTableWidgetItem(str(value))
                self.table.setItem(row_idx, col_idx, item)
        
        # Auto-adjust column widths
        self.table.resizeColumnsToContents()
    
    def download_results(self):
        if not hasattr(self, 'df') or self.df is None or self.df.empty:
            QMessageBox.warning(self, "Aviso", "Não há dados para baixar.")
            return
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"RELATORIO_{timestamp}.xlsx"
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Salvar Relatório", 
                os.path.join(REPORTS_PATH, filename),
                "Excel Files (*.xlsx)"
            )
            
            if not filepath:
                return
                
            if not filepath.endswith('.xlsx'):
                filepath += '.xlsx'
                
            self.df.to_excel(filepath, index=False)
            QMessageBox.information(self, "Sucesso", f"Relatório salvo em: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar relatório: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.results = []  # Store result frames
        self.initUI()
        
    def initUI(self):
        # Window setup
        self.setWindowTitle('GOvGO')
        self.setGeometry(100, 100, 1280, 800)
        self.setStyleSheet("background-color: #F0F0F0;")
        
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Queries
        left_widget = QWidget()
        left_widget.setStyleSheet("background-color: #E0EAF9;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("govgo_logo.png")  # Replace with actual logo path
        logo_label.setPixmap(logo_pixmap.scaledToWidth(150))
        left_layout.addWidget(logo_label)
        
        # Scroll area for query bubbles
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: #E0EAF9;")
        
        # Container for query bubbles
        scroll_content = QWidget()
        self.queries_layout = QVBoxLayout(scroll_content)
        self.queries_layout.setAlignment(Qt.AlignTop)
        
        # Add example query bubbles
        self.add_example_queries()
        
        scroll_area.setWidget(scroll_content)
        left_layout.addWidget(scroll_area, 1)
        
        # Query input area
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: white; border-radius: 20px;")
        input_layout = QHBoxLayout(input_frame)
        
        # Query input field
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Faça uma pergunta...")
        self.query_input.setStyleSheet("""
            QLineEdit {
                border: none;
                padding: 8px;
                background-color: transparent;
            }
        """)
        self.query_input.returnPressed.connect(self.execute_query)
        input_layout.addWidget(self.query_input, 1)
        
        # Submit button
        submit_btn = QPushButton()
        submit_btn.setIcon(QIcon("arrow_icon.png"))  # Replace with actual icon
        submit_btn.setIconSize(QSize(20, 20))
        submit_btn.setFixedSize(32, 32)
        submit_btn.clicked.connect(self.execute_query)
        input_layout.addWidget(submit_btn)
        
        left_layout.addWidget(input_frame)
        
        # Right panel - Results
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: #F5F5F5;")
        right_layout = QVBoxLayout(right_widget)
        
        # Scroll area for results
        results_scroll = QScrollArea()
        results_scroll.setWidgetResizable(True)
        results_scroll.setStyleSheet("border: none; background-color: #F5F5F5;")
        
        # Container for results
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignTop)
        results_scroll.setWidget(self.results_container)
        
        right_layout.addWidget(results_scroll)
        
        # Add panels to splitter
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(right_widget)
        self.main_splitter.setSizes([400, 880])  # Set initial sizes
        
        main_layout.addWidget(self.main_splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Pronto")
    
    def add_example_queries(self):
        """Add example query bubbles to the left panel"""
        # Example 1: Software contracts since 2024
        nl_query1 = "Quero as contratações de software no ES desde 2024"
        sql_query1 = """SELECT ct.* FROM contrato WHERE 
                       ct.anoContrato >= 2024 AND 
                       ct.unidadeOrgao_ufSigla = 'ES' AND 
                       fc.descricao LIKE '%software%';"""
        bubble1 = QueryBubble(nl_query1, sql_query1)
        bubble1.clicked.connect(self.handle_bubble_click)
        self.queries_layout.addWidget(bubble1)
        
        # Example 2: Suppliers info
        nl_query2 = "Quero saber quem são os fornecedores, quais as cidades, os valores e os órgãos"
        sql_query2 = """SELECT fornecedor, cidade, orgao, 
                       descricao FROM contrato WHERE 
                       c.anoCompra >= 2024 AND 
                       uf = 'ES' AND i.descricao LIKE 
                       '%software%';"""
        bubble2 = QueryBubble(nl_query2, sql_query2)
        bubble2.clicked.connect(self.handle_bubble_click)
        self.queries_layout.addWidget(bubble2)
        
        # Add spacing at the end
        self.queries_layout.addStretch()
    
    def handle_bubble_click(self, nl_query, sql_query):
        """Handle click on a query bubble"""
        self.query_input.setText(nl_query)
        self.execute_query(sql_query)
    
    def execute_query(self, predefined_sql=None):
        """Execute either a predefined SQL query or generate SQL from the input field"""
        if predefined_sql and isinstance(predefined_sql, str):
            # Use the predefined SQL
            sql = predefined_sql
            self.execute_sql_query(sql)
        else:
            # Generate SQL from natural language
            nl_query = self.query_input.text().strip()
            if not nl_query:
                QMessageBox.warning(self, "Atenção", "Por favor, digite uma consulta.")
                return
            
            self.statusBar.showMessage("Gerando SQL...")
            
            # Generate SQL from natural language
            self.sql_worker = SqlGenerationWorker(nl_query)
            self.sql_worker.finished.connect(self.execute_sql_query)
            self.sql_worker.error.connect(self.handle_error)
            self.sql_worker.start()
    
    def execute_sql_query(self, sql):
        """Execute the SQL query and display results"""
        self.statusBar.showMessage("Executando consulta...")
        
        # Create a new query bubble for this query if it was user-entered
        if not any(b.sql_query == sql for b in self.findChildren(QueryBubble)):
            nl_query = self.query_input.text().strip()
            if nl_query:
                bubble = QueryBubble(nl_query, sql)
                bubble.clicked.connect(self.handle_bubble_click)
                self.queries_layout.insertWidget(self.queries_layout.count() - 1, bubble)
                
        # Execute the query
        self.data_worker = DataQueryWorker(sql)
        self.data_worker.finished.connect(self.display_results)
        self.data_worker.error.connect(self.handle_error)
        self.data_worker.start()
    
    def display_results(self, df):
        """Display query results in a new result frame"""
        # Create new result frame
        result_frame = ResultFrame()
        result_frame.display_data(df)
        
        # Add to results layout
        self.results_layout.insertWidget(0, result_frame)
        
        # Keep track of results
        self.results.append(result_frame)
        
        # Clear input field and update status
        self.query_input.clear()
        self.statusBar.showMessage(f"Consulta concluída. {len(df)} registros encontrados.")
    
    def handle_error(self, error_msg):
        """Handle errors from workers"""
        self.statusBar.showMessage(f"Erro: {error_msg}")
        QMessageBox.critical(self, "Erro", f"Ocorreu um erro: {error_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())