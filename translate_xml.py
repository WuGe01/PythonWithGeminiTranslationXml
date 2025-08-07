import os
import google.generativeai as genai
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# --- 1. 設定 ---
# 移除了 genai.configure 的 try-except 區塊，因為 API key 會由 GUI 介面輸入
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. 核心翻譯函式 (保留不變) ---
def translate_xml_content(xml_string, target_language):
    """
    使用 Gemini API 一次性翻譯整個 XML 字串，並保留其結構。
    """
    if not xml_string:
        return ""

    prompt = (
        f"Translate only the text content within the XML tags to {target_language}. "
        "Do not translate the tag names or attributes. "
        "Return the entire XML structure with the translated content.\n\n"
        "Example:\n"
        "<product>\n"
        "  <name>Smart Coffee Maker</name>\n"
        "  <description>Make perfect coffee with your smartphone.</description>\n"
        "</product>\n"
        "Translated to Traditional Chinese would be:\n"
        "<product>\n"
        "  <name>智慧咖啡機</name>\n"
        "  <description>用你的智慧型手機沖泡完美的咖啡。</description>\n"
        "</product>\n\n"
        "Now, translate the following XML content:\n\n"
        f"{xml_string}"
    )

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"翻譯時發生錯誤: {e}")
        return f"\n{xml_string}"

# --- 3. GUI 主程式 ---
class XMLTranslatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gemini XML 翻譯工具")
        self.geometry("600x400")
        self.create_widgets()

    def create_widgets(self):
        # 標題
        tk.Label(self, text="Gemini XML 翻譯工具", font=("Helvetica", 16, "bold")).pack(pady=10)

        # 框架用於組織輸入
        input_frame = tk.Frame(self)
        input_frame.pack(fill='x', padx=20, pady=5)

        # API 金鑰設定
        tk.Label(input_frame, text="API 金鑰:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.api_key_entry = tk.Entry(input_frame, width=50)
        self.api_key_entry.grid(row=0, column=1, padx=5, pady=5)

        # API 金鑰連結
        tk.Button(input_frame, text="取得金鑰", command=self.open_api_key_link, relief=tk.FLAT, fg="blue").grid(row=0, column=2, padx=5)
        
        # 嘗試從環境變數載入金鑰
        default_api_key = os.environ.get('GOOGLE_API_KEY', '')
        self.api_key_entry.insert(0, default_api_key)

        # 輸入資料夾路徑
        tk.Label(input_frame, text="輸入資料夾:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.input_path_entry = tk.Entry(input_frame, width=50)
        self.input_path_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(input_frame, text="瀏覽...", command=self.browse_input_folder).grid(row=1, column=2, padx=5)

        # 輸出資料夾路徑
        tk.Label(input_frame, text="輸出資料夾:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.output_path_entry = tk.Entry(input_frame, width=50)
        self.output_path_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Button(input_frame, text="瀏覽...", command=self.browse_output_folder).grid(row=2, column=2, padx=5)
        
        # 預設輸出資料夾為 'output'
        self.output_path_entry.insert(0, 'output')

        # 目標語言選擇
        tk.Label(input_frame, text="目標語言:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.language_options = ["Traditional Chinese", "Simplified Chinese", "English", "Japanese"]
        self.language_var = tk.StringVar(self)
        self.language_var.set(self.language_options[0])  # 預設為繁體中文
        tk.OptionMenu(input_frame, self.language_var, *self.language_options).grid(row=3, column=1, sticky='w', padx=5, pady=5)

        # 狀態顯示
        self.status_label = tk.Label(self, text="請輸入資訊並點擊開始翻譯。", fg="blue")
        self.status_label.pack(pady=10)

        # 開始按鈕
        self.start_button = tk.Button(self, text="開始翻譯", command=self.start_translation, width=20, height=2)
        self.start_button.pack(pady=20)

    def open_api_key_link(self):
        """
        開啟瀏覽器連結到 Google AI Studio 頁面以取得 API Key。
        """
        import webbrowser
        webbrowser.open("https://aistudio.google.com/app/apikey")
        
    def browse_input_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.input_path_entry.delete(0, tk.END)
            self.input_path_entry.insert(0, folder_path)

    def browse_output_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_path_entry.delete(0, tk.END)
            self.output_path_entry.insert(0, folder_path)

    def update_status(self, message, color="blue"):
        self.status_label.config(text=message, fg=color)
        self.update_idletasks() # 強制更新 GUI

    def start_translation(self):
        # 鎖定按鈕避免重複點擊
        self.start_button.config(state=tk.DISABLED)
        self.update_status("正在初始化...")
        
        # 取得使用者輸入
        api_key = self.api_key_entry.get()
        input_folder = self.input_path_entry.get()
        output_folder = self.output_path_entry.get()
        target_language = 'Traditional Chinese' # 這裡硬編碼為繁體中文，可修改為下拉選單

        # 驗證輸入
        if not api_key:
            self.update_status("錯誤：請輸入 API 金鑰。", "red")
            self.start_button.config(state=tk.NORMAL)
            return

        if not os.path.isdir(input_folder):
            self.update_status(f"錯誤：找不到輸入資料夾 '{input_folder}'。", "red")
            self.start_button.config(state=tk.NORMAL)
            return

        # 設定 API 金鑰
        genai.configure(api_key=api_key)

        try:
            # 確保輸出資料夾存在
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            
            # 翻譯核心邏輯
            file_count = 0
            self.update_status("開始翻譯...")
            for root, dirs, files in os.walk(input_folder):
                relative_path = os.path.relpath(root, input_folder)
                output_subfolder = os.path.join(output_folder, relative_path)

                if not os.path.exists(output_subfolder):
                    os.makedirs(output_subfolder)

                for file_name in files:
                    if file_name.endswith('.xml'):
                        input_file_path = os.path.join(root, file_name)
                        output_file_path = os.path.join(output_subfolder, file_name)
                        
                        self.update_status(f"正在翻譯: {file_name}...", "orange")
                        
                        with open(input_file_path, 'r', encoding='utf-8') as f:
                            xml_string_to_translate = f.read()

                        translated_xml_string = translate_xml_content(xml_string_to_translate, target_language)
                        
                        with open(output_file_path, 'w', encoding='utf-8') as f:
                            f.write(translated_xml_string)
                        
                        file_count += 1
                        time.sleep(10) # 每次翻譯後延遲10秒

            if file_count == 0:
                self.update_status("警告：找不到任何 XML 檔案進行翻譯。", "red")
            else:
                self.update_status(f"翻譯完成！總共翻譯了 {file_count} 個檔案。", "green")

        except Exception as e:
            self.update_status(f"發生錯誤：{e}", "red")

        # 恢復按鈕狀態
        self.start_button.config(state=tk.NORMAL)


if __name__ == "__main__":
    app = XMLTranslatorApp()
    app.mainloop()