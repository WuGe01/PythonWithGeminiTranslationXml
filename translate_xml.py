import os
import google.generativeai as genai
from dotenv import load_dotenv
import glob
import time
# 不需要 xml.etree.ElementTree，因為我們不再遍歷 XML 樹
# import xml.etree.ElementTree as ET 
# 也不需要 ThreadPoolExecutor 了
# from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 在程式碼一開始就載入 .env 檔案 ---
load_dotenv()

# --- 1. 設定 ---
try:
    genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
except KeyError:
    print("錯誤：請確認 'GOOGLE_API_KEY' 已在環境變數或 .env 檔案中設定。")
    exit()

# 設定要使用的模型
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. 核心翻譯函式 (修改為一次翻譯整個 XML 字串) ---
def translate_xml_content(xml_string, target_language):
    """
    使用 Gemini API 一次性翻譯整個 XML 字串，並保留其結構。
    """
    if not xml_string:
        return ""

    # 設計一個精準的 Prompt，要求 AI 翻譯 XML 標籤內的文字
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
        # 這裡就不需要延遲了，因為我們只發送一個請求
        # time.sleep(10) # 如果你仍然擔心，可以在這裡加上延遲
        return response.text.strip()
    except Exception as e:
        print(f"翻譯時發生錯誤: {e}")
        return f"\n{xml_string}"

# --- 3. 主程式 (修改為處理資料夾和檔案) ---
def main():
    """
    主執行函式
    """
    input_folder = 'input'
    output_folder = 'output'
    target_language = 'Traditional Chinese'

    if not os.path.exists(output_folder):
        print(f"建立輸出資料夾: {output_folder}")
        os.makedirs(output_folder)

    if not os.path.exists(input_folder):
        print(f"錯誤：找不到輸入資料夾 '{input_folder}'")
        exit()

    input_files = glob.glob(os.path.join(input_folder, '*.xml'))

    if not input_files:
        print(f"警告：在 '{input_folder}' 資料夾中找不到任何 .xml 檔案。")
        return

    print(f"在 '{input_folder}' 資料夾中找到 {len(input_files)} 個 XML 檔案。")
    print(f"開始翻譯成 {target_language}...")
    
    for input_file_path in input_files:
        file_name = os.path.basename(input_file_path)
        output_file_path = os.path.join(output_folder, file_name)

        print(f"\n--- 正在處理檔案: {file_name} ---")
        try:
            # 讀取整個檔案的內容為字串
            with open(input_file_path, 'r', encoding='utf-8') as f:
                xml_string_to_translate = f.read()

            print(f"正在將整個檔案送出進行翻譯...")
            translated_xml_string = translate_xml_content(xml_string_to_translate, target_language)
            
            print(f"翻譯完成！")

            # 將翻譯後的字串寫入新檔案
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(translated_xml_string)
            
            print(f"已儲存翻譯後的檔案: {output_file_path}")

        except Exception as e:
            print(f"檔案 '{file_name}' 發生未預期的錯誤: {e}")
        
        # 每次處理完一個檔案後，可以加入延遲
        # 這樣即使有很多檔案，也可以避免短時間內連續發送請求
        # 10秒的延遲是個安全的選擇
        print("等待 10 秒以避免觸發配額限制...")
        time.sleep(10)


if __name__ == "__main__":
    main()