import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
import time
from langdetect import detect
from google import genai
from google.genai import types



# === CONFIGURATION ===
SYSTEM_PROMPT = (
    "You are a friendly chatbot that knows everything about Universidad de las Américas Puebla (UDLAP). "
    "You can answer questions about admissions, faculties, student life, events, scholarships, and services. "
    "Keep answers concise, friendly, and helpful — like a student ambassador."
)

# === UTILITY FUNCTIONS ===
def should_use_web_search(user_message):
    keywords = ["when", "where", "who", "how much", "schedule", "event", "deadline",
                "admission", "scholarship", "requirements", "cost", "faculty", "address", "date"]
    return any(word.lower() in user_message.lower() for word in keywords)

def web_search_placeholder(query, max_results=3):
    """Simulate web search results for demonstration."""
    return [f"Simulated snippet {i+1} for query: {query}" for i in range(max_results)]

def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

def ask_gemini(prompt):
    # Initialize the client
    client = genai.Client(api_key = "AIzaSyDMKXeZEIN-Af1hKreJevGd6dRaW_bN1OM")

    content_part = types.Part.from_text(text=prompt)
    contents = [types.Content(parts=[content_part])]

    # Generate text using Gemini 2.5
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.7)
    )
    return response.text

# === CHATBOT APP ===
class UDLAPChatbotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UDLAP Chatbot 💬")
        self.root.geometry("520x720")
        self.root.config(bg="#ECE5DD")

        # Header
        header = tk.Frame(root, bg="#075E54", height=60)
        header.pack(fill=tk.X)
        tk.Label(header, text="Inteligencia Azteca 🤖", fg="white", bg="#075E54",
                 font=("Arial", 16, "bold"), pady=15).pack()

        # Chat area
        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, bg="#ECE5DD",
                                                   font=("Arial", 11), state="disabled", bd=0)
        self.chat_area.pack(padx=10, pady=(10, 0), fill=tk.BOTH, expand=True)

        # Typing indicator
        self.typing_label = tk.Label(root, text="", bg="#ECE5DD", fg="gray", font=("Arial", 10, "italic"))
        self.typing_label.pack(pady=(0, 5))

        # Input frame
        input_frame = tk.Frame(root, bg="#ECE5DD")
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        self.entry_field = tk.Entry(input_frame, font=("Arial", 12))
        self.entry_field.pack(padx=(0, 5), pady=5, fill=tk.X, side=tk.LEFT, expand=True)
        self.entry_field.bind("<Return>", self.send_message)

        self.send_button = tk.Button(input_frame, text="Send", bg="#25D366", fg="white",
                                     font=("Arial", 11, "bold"), command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Download button
        self.download_button = tk.Button(root, text="📄 Download Conversation", bg="#128C7E",
                                         fg="white", font=("Arial", 11, "bold"),
                                         command=self.download_conversation)
        self.download_button.pack(pady=(0, 10))

        # Conversation history
        self.conversation = []
        self.history_plaintext = []

    def display_bubble(self, sender, message, align="left", color="#FFFFFF"):
        self.chat_area.config(state="normal")
        tag_name = f"tag_{align}_{len(self.conversation)}"
        bubble = f"{sender}:\n{message}\n\n"
        self.chat_area.insert(tk.END, bubble, tag_name)
        self.chat_area.tag_config(tag_name, justify=align, background=color, lmargin1=10,
                                  lmargin2=10, rmargin=10, spacing3=5, wrap="word")
        if align == "right":
            self.chat_area.tag_config(tag_name, foreground="black", justify="right", background="#DCF8C6")
        else:
            self.chat_area.tag_config(tag_name, foreground="black", justify="left", background="#FFFFFF")
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def send_message(self, event=None):
        user_message = self.entry_field.get().strip()
        if not user_message:
            return

        self.display_bubble("You", user_message, align="right", color="#DCF8C6")
        self.history_plaintext.append(f"User: {user_message}")
        self.entry_field.delete(0, tk.END)

        self.typing_label.config(text="Typing...")
        self.root.update_idletasks()

        threading.Thread(target=self.get_bot_response, args=(user_message,), daemon=True).start()

    def get_bot_response(self, user_message):
        try:
            user_lang = detect_language(user_message)
            context = f"Respond in the same language as the user ({user_lang})."

            if should_use_web_search(user_message):
                snippets = web_search_placeholder(user_message)
                context += "\nWeb search results:\n" + "\n".join(snippets)

            prompt = SYSTEM_PROMPT + "\n" + context + "\nUser: " + user_message + "\nBot:"
            time.sleep(1.2)
            bot_reply = ask_gemini(prompt)

            self.typing_label.config(text="")
            self.display_bubble("Inteligencia Azteca 🤖", bot_reply, align="left", color="#FFFFFF")
            self.conversation.append({"role": "assistant", "content": bot_reply})
            self.history_plaintext.append(f"Bot: {bot_reply}")

        except Exception as e:
            self.typing_label.config(text="")
            self.display_bubble("System", f"⚠️ Error: {e}", align="left", color="#FFCCCC")

    def download_conversation(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text files", "*.txt")],
                                                 title="Save conversation as...")
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("IA conversation\n")
                f.write("="*35 + "\n\n")
                for line in self.history_plaintext:
                    f.write(line + "\n")
            self.display_bubble("System", f"✅ Conversation saved to {file_path}", align="left", color="#E1FFC7")
        except Exception as e:
            self.display_bubble("System", f"⚠️ Could not save file: {e}", align="left", color="#FFCCCC")

# === RUN APP ===
if __name__ == "__main__":
    root = tk.Tk()
    app = UDLAPChatbotApp(root)
    root.mainloop()




