import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

class ChatFrame(ttk.Frame):
    def __init__(self, master, title, send_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.send_callback = send_callback

        # Título do chat
        self.label_title = ttk.Label(self, text=title, font=("Helvetica", 12, "bold"))
        self.label_title.pack(padx=5, pady=5)

        # Área para exibir o histórico (chat log)
        self.chat_log = scrolledtext.ScrolledText(self, width=40, height=20, state=tk.DISABLED)
        self.chat_log.pack(padx=5, pady=5)

        # Caixa para entrada de mensagens
        self.entry_message = ttk.Entry(self, width=40)
        self.entry_message.pack(padx=5, pady=(0,5), side=tk.LEFT, expand=True, fill=tk.X)
        self.entry_message.bind("<Return>", self.send_message)

        # Botão para enviar mensagem
        self.btn_send = ttk.Button(self, text="Enviar", command=self.send_message)
        self.btn_send.pack(padx=5, pady=(0,5), side=tk.LEFT)

    def send_message(self, event=None):
        message = self.entry_message.get().strip()
        if message:
            # Adiciona a mensagem no chat log
            self.append_message("Você", message)
            # Chama o callback para processar a mensagem
            self.send_callback(message)
            self.entry_message.delete(0, tk.END)

    def append_message(self, sender, message):
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.insert(tk.END, f"{sender}: {message}\n")
        self.chat_log.see(tk.END)
        self.chat_log.config(state=tk.DISABLED)

class GovGoChatUI:
    def __init__(self, master):
        master.title("GovGo - Interface de Chat PNCP")
        master.geometry("1000x600")

        # Frame principal para organizar os dois chats lado a lado
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame do chat da esquerda (consulta do usuário)
        self.frame_left = ChatFrame(self.main_frame, "Chat - Consultas", self.handle_user_message)
        self.frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Frame do chat da direita (respostas/assistente)
        self.frame_right = ChatFrame(self.main_frame, "Chat - Respostas", self.handle_assistant_message)
        self.frame_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

    def handle_user_message(self, message):
        # Aqui você integraria a lógica para processar a consulta
        # Por exemplo, chamar a API para converter a consulta NL em SQL
        # ou registrar a mensagem em um histórico.
        # Por enquanto, apenas ecoamos a mensagem no chat da direita como resposta.
        resposta = self.processar_consulta(message)
        self.frame_right.append_message("Assistente", resposta)

    def handle_assistant_message(self, message):
        # Se for necessário, permite o envio de mensagens pelo chat da direita
        # (por exemplo, para correções ou confirmações do assistente).
        # Aqui, apenas adicionamos a mensagem no próprio chat.
        self.frame_right.append_message("Assistente", message)

    def processar_consulta(self, message):
        # Esta função é um placeholder para a lógica de processamento.
        # Por exemplo, transformar a consulta natural em SQL,
        # executar no banco e retornar algum resumo ou preview dos dados.
        # Aqui retornamos uma resposta genérica para exemplificação.
        return f"Processando sua consulta: '{message}'. [Resposta fictícia]"

def main():
    root = tk.Tk()
    app = GovGoChatUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
