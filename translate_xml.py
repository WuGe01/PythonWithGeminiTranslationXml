import os
import google.generativeai as genai
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk # 引入 ttk 來使用進度條
import webbrowser
import threading # 引入多執行緒模組
import re # 引入正則表達式模組

# --- 1. 核心翻譯函式 (優化版) ---
# 增加了穩健的 API 呼叫 (指數退避重試) 和更強的 Prompt
def translate_xml_content(xml_string, target_language, model):
    """
    使用 Gemini API 翻譯 XML 字串，並包含指數退避重試機制。
    """
    if not xml_string:
        return ""

    # 1. 全新的 Prompt：更明確、更強制，並提供更相關的範例
    prompt = (
        f"You are a professional game localization translator. Your task is to translate the text content within the XML tags to {target_language}. "
        "You MUST translate ALL content, including proper nouns, names, titles, and labels, as they are part of the game's content. "
        "Do not translate the XML tag names or attributes. "
        "Return ONLY the complete and valid XML structure with the translated content. "
        "IMPORTANT: Do not add any extra text, comments, or code block markers (like ```xml) before or after the XML content.\n\n"
        "Example:\n"
        "<LanguageData>\n"
        "  <Pawn_Smith.label>Smith</Pawn_Smith.label>\n"
        "  <Weapon_FireSword.label>Fire Sword</Weapon_FireSword.label>\n"
        "</LanguageData>\n\n"
        f"Translated to Traditional Chinese would be:\n"
        "<LanguageData>\n"
        "  <Pawn_Smith.label>史密斯</Pawn_Smith.label>\n"
        "  <Weapon_FireSword.label>火焰之劍</Weapon_FireSword.label>\n"
        "</LanguageData>\n\n"
        "Now, translate the following XML content:\n\n"
        f"{xml_string}"
    )

    # 2. 更穩健的 API 呼叫 (指數退避重試)
    max_retries = 5
    base_delay = 5 # 基礎延遲秒數，與您原先的設定有關
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            # 3. 清理模型可能多餘的輸出
            # 移除模型可能回傳的 ```xml ... ``` 標記
            cleaned_text = re.sub(r'^```xml\n|```$', '', response.text.strip(), flags=re.MULTILINE)
            return cleaned_text
        except Exception as e:
            # 只在特定錯誤 (如 ResourceExhausted) 或最後一次嘗試時才印出錯誤
            if "ResourceExhausted" in str(e) or attempt == max_retries - 1:
                print(f"翻譯時發生錯誤 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 指數退避，等待時間越來越長
                    wait_time = base_delay * (2 ** attempt)
                    print(f"API 速率限制，將在 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    # 所有重試失敗後，返回原始字串以避免資料遺失
                    print("所有重試均失敗，將跳過此檔案。")
                    return f"\n{xml_string}"
            else:
                 # 對於其他類型的錯誤，可能直接失敗更合適
                 print(f"發生非預期的翻譯錯誤: {e}")
                 return f"\n{xml_string}"

    return f"\n{xml_string}" # 最終防線


# --- 2. GUI 主程式 (優化版) ---
class XMLTranslatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gemini XML 翻譯工具 (優化版)")
        self.geometry("600x500") # 增加高度以容納進度條
        self.create_widgets()
        # 用於執行緒間通訊的佇列 (此處簡化為直接調用 update_status)
        # 在更複雜的應用中，使用 queue.Queue 會更安全
        self.after(100, self.process_worker_thread) # 檢查執行緒是否完成

    def create_widgets(self):
        tk.Label(self, text="Gemini XML 翻譯工具", font=("Helvetica", 16, "bold")).pack(pady=10)
        input_frame = tk.Frame(self)
        input_frame.pack(fill='x', padx=20, pady=5)

        tk.Label(input_frame, text="API 金鑰:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.api_key_entry = tk.Entry(input_frame, width=40, show="*")
        self.api_key_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(input_frame, text="取得金鑰", command=self.open_api_key_link, relief=tk.FLAT, fg="blue", cursor="hand2").grid(row=0, column=2, padx=5)
        default_api_key = os.environ.get('GOOGLE_API_KEY', '')
        self.api_key_entry.insert(0, default_api_key)

        tk.Label(input_frame, text="模型名稱:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        # 更新模型選項
        self.model_options = ["gemini-1.5-flash", "gemini-1.5-pro","gemini-2.5-flash", "gemini-2.5-pro"]
        self.model_var = tk.StringVar(self)
        self.model_var.set(self.model_options[0]) # 預設使用較快且便宜的 flash
        model_menu = tk.OptionMenu(input_frame, self.model_var, *self.model_options)
        model_menu.grid(row=1, column=1, sticky='we', padx=5, pady=5, columnspan=2)

        tk.Label(input_frame, text="輸入資料夾:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.input_path_entry = tk.Entry(input_frame, width=50)
        self.input_path_entry.grid(row=2, column=1, padx=5, pady=5)
        tk.Button(input_frame, text="瀏覽...", command=self.browse_input_folder).grid(row=2, column=2, padx=5)

        tk.Label(input_frame, text="輸出資料夾:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.output_path_entry = tk.Entry(input_frame, width=50)
        self.output_path_entry.grid(row=3, column=1, padx=5, pady=5)
        tk.Button(input_frame, text="瀏覽...", command=self.browse_output_folder).grid(row=3, column=2, padx=5)
        self.output_path_entry.insert(0, 'output')

        tk.Label(input_frame, text="目標語言:").grid(row=4, column=0, sticky='w', padx=5, pady=5)
        self.language_options = ["繁體中文", "簡體中文", "English", "日本語"]
        self.language_var = tk.StringVar(self)
        self.language_var.set(self.language_options[0])
        lang_menu = tk.OptionMenu(input_frame, self.language_var, *self.language_options)
        lang_menu.grid(row=4, column=1, sticky='we', padx=5, pady=5, columnspan=2)

        # 狀態和進度顯示
        self.status_label = tk.Label(self, text="請輸入資訊並點擊開始翻譯。", fg="blue")
        self.status_label.pack(pady=(10, 0))
        
        # 4. 增加進度條
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(pady=5)

        self.start_button = tk.Button(self, text="開始翻譯", command=self.start_translation_thread, width=20, height=2)
        self.start_button.pack(pady=20)

        self.worker_thread = None

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

    def open_api_key_link(self):
        webbrowser.open("[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)")

    def update_status(self, message, color="blue"):
        self.status_label.config(text=message, fg=color)
        self.update_idletasks() # 即時更新 UI

    def start_translation_thread(self):
        """啟動一個新的執行緒來執行翻譯任務，避免 GUI 卡住"""
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("警告", "一個翻譯任務已在執行中。")
            return
            
        # 禁用按鈕，重設進度條
        self.start_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        
        # 啟動背景執行緒
        self.worker_thread = threading.Thread(target=self._translation_worker)
        self.worker_thread.daemon = True # 確保主視窗關閉時執行緒也會結束
        self.worker_thread.start()

    def process_worker_thread(self):
        """定期檢查背景執行緒是否已經完成"""
        if self.worker_thread and not self.worker_thread.is_alive():
            # 執行緒已結束，可以重新啟用按鈕
            self.start_button.config(state=tk.NORMAL)
        # 100ms 後再次檢查
        self.after(100, self.process_worker_thread)

    def _translation_worker(self):
        """實際執行翻譯工作的函式，此函式在背景執行緒中執行"""
        self.update_status("正在初始化...", "orange")

        # 獲取參數
        api_key = self.api_key_entry.get()
        input_folder = self.input_path_entry.get()
        output_folder = self.output_path_entry.get()
        model_name = self.model_var.get()
        target_language_display = self.language_var.get()
        language_mapping = {"繁體中文": "Traditional Chinese", "簡體中文": "Simplified Chinese", "English": "English", "日本語": "Japanese"}
        target_language = language_mapping.get(target_language_display)

        # 驗證輸入
        if not api_key:
            self.update_status("錯誤：請輸入 API 金鑰。", "red")
            return
        if not os.path.isdir(input_folder):
            self.update_status(f"錯誤：找不到輸入資料夾 '{input_folder}'。", "red")
            return

        # 設定模型
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            self.update_status(f"API 或模型設定錯誤：{e}", "red")
            return
            
        # 準備檔案列表
        xml_files_to_process = []
        for root, _, files in os.walk(input_folder):
            for file_name in files:
                if file_name.endswith('.xml'):
                    input_file_path = os.path.join(root, file_name)
                    relative_path = os.path.relpath(root, input_folder)
                    output_subfolder = os.path.join(output_folder, relative_path)
                    output_file_path = os.path.join(output_subfolder, file_name)
                    xml_files_to_process.append((input_file_path, output_file_path, output_subfolder))
        
        if not xml_files_to_process:
            self.update_status("警告：在輸入資料夾中找不到任何 XML 檔案。", "orange")
            return

        total_files = len(xml_files_to_process)
        self.progress['maximum'] = total_files

        # 開始處理
        try:
            for i, (input_path, output_path, out_folder) in enumerate(xml_files_to_process):
                if not os.path.exists(out_folder):
                    os.makedirs(out_folder)
                
                file_name = os.path.basename(input_path)
                self.update_status(f"翻譯中 ({i+1}/{total_files}): {file_name}", "blue")

                with open(input_path, 'r', encoding='utf-8') as f_in:
                    xml_content = f_in.read()
                
                translated_content = translate_xml_content(xml_content, target_language, model)

                with open(output_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(translated_content)
                
                self.progress['value'] = i + 1

            self.update_status(f"翻譯完成！總共處理了 {total_files} 個檔案。", "green")

        except Exception as e:
            self.update_status(f"翻譯過程中發生未預期錯誤：{e}", "red")

if __name__ == "__main__":
    app = XMLTranslatorApp()
    app.mainloop()