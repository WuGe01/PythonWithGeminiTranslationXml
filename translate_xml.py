import os
import google.generativeai as genai
from dotenv import load_dotenv
import time

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

def main():
    """
    主執行函式，使用 os.walk 遞迴處理資料夾結構
    """
    input_folder = 'input'
    output_folder = 'output'
    target_language = 'Traditional Chinese'

    if not os.path.exists(input_folder):
        print(f"錯誤：找不到輸入資料夾 '{input_folder}'")
        exit()

    if not os.path.exists(output_folder):
        print(f"建立輸出資料夾: {output_folder}")
        os.makedirs(output_folder)

    print(f"開始遞迴處理 '{input_folder}' 資料夾中的所有 XML 檔案...")
    print(f"翻譯成 {target_language} 並儲存到 '{output_folder}'...")

    file_count = 0

    for root, dirs, files in os.walk(input_folder):

        relative_path = os.path.relpath(root, input_folder)
        output_subfolder = os.path.join(output_folder, relative_path)

        if not os.path.exists(output_subfolder):
            os.makedirs(output_subfolder)
            print(f"已建立輸出子資料夾: {output_subfolder}")

        for file_name in files:
            if file_name.endswith('.xml'):
                input_file_path = os.path.join(root, file_name)
                output_file_path = os.path.join(output_subfolder, file_name)
                
                print(f"\n--- 正在處理檔案: {input_file_path} ---")
                try:
                    with open(input_file_path, 'r', encoding='utf-8') as f:
                        xml_string_to_translate = f.read()

                    translated_xml_string = translate_xml_content(xml_string_to_translate, target_language)
                    
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        f.write(translated_xml_string)
                    
                    print(f"翻譯完成，已儲存至: {output_file_path}")
                    file_count += 1
                
                except Exception as e:
                    print(f"檔案 '{input_file_path}' 發生未預期的錯誤: {e}")

                print("等待 10 秒以避免觸發配額限制...")
                time.sleep(10)

    if file_count == 0:
        print(f"\n警告：在 '{input_folder}' 資料夾及其子資料夾中找不到任何 .xml 檔案。")
    else:
        print(f"\n恭喜！總共翻譯了 {file_count} 個檔案。")

if __name__ == "__main__":
    main()