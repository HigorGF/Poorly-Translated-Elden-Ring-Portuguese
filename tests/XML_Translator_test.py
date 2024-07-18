import os
import xml.etree.ElementTree as ET
from googletrans import Translator
from time import sleep, time
import httpx
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import sys

translator = Translator(timeout=httpx.Timeout(8))
translation_cache = {}
last_processed_time = time()  # Inicializa o tempo de último processamento como o tempo atual

cache_lock = threading.Lock()
local = threading.Lock()

def translate_text(base):
    with cache_lock:
        if base in translation_cache:
            return translation_cache[base]

    translations = [base]
    languages = ['pt', 'ig', 'zh-cn', 'si', 'th', 'zu', 'hu', 'el', 'ig', 'gu', 'tr', 'pt'] #Aqui você pode editar a ordem de tradução do jeito que quiser
    
    stop = 0
    for i in range(len(languages) - 1):
        if stop == 1:
            break
        src_lang = languages[i]
        dest_lang = languages[i + 1]

        for attempt in range(0, 10):
            try:
                trad = translator.translate(translations[-1], src=src_lang, dest=dest_lang)
                translations.append(trad.text)
                break
            except Exception as e:
                print(f"Translation error on attempt {attempt + 1}: {e}")
                if attempt != 9:
                    sleep(3)
                    continue
                stop = 1
                
    with cache_lock:
        translation_cache[base] = translations[-1]
    return translations[-1]

def process_element(element, ext_file, tree):
    base = element.text

    if not base or base[0] == "%" or base.isspace() or base[0] == None or base == " \n" or base == "\n" or base == ' ':
        element.text = base
        print(element.text)
        sleep(0.1)
        return

    #Edita variaveis para não serem traduzidas
    index = re.findall(r"&lt.*&gt;", base)
    r = 0
    if index:
        for result in index:
            r += 1
            print("Made Replace")
            base = base.replace(result, f"__{r}__")

    translated_text = translate_text(base)
    
    if index:
        for result in reversed(index):
            try:
                translated_text = translated_text.replace(f"__{r}__", result)
                r -= 1
            except:
                print("Error replacing")
                r -= 1

    element.text = translated_text
    print(base + " --> " + element.text) #Conferir as traduções

    
    with open(ext_file, "w", encoding="utf-8") as createfile:
        tree.write(ext_file, encoding="utf-8", xml_declaration=True)
    
    print(f"File {ext_file} saved.")

    with local:
        global last_processed_time
        last_processed_time = time()

def findfiles(root):
    looplist = os.listdir(root)
    for i in looplist:
        path = os.path.join(root, i)
        if os.path.isfile(path) and os.path.splitext(path)[1] == ".xml":
            ext_dir = "trad_" + root
            ext_file = "trad_" + path
            
            if not os.path.exists(ext_dir):
                os.makedirs(ext_dir)

            print("Editando: " + path)

            with open(path, "r+", encoding="utf-8") as basefile:
                tree = ET.parse(basefile)

            baseline = tree.findall(".//text")
            os.remove(path)

            with ThreadPoolExecutor(max_workers=128) as executor:
                futures = [executor.submit(process_element, element, ext_file, tree) for element in baseline]
                for future in as_completed(futures):
                    try:
                        future.result(timeout=50)
                    except TimeoutError:
                        print("Thread Timed out.")
                        continue
                    except Exception as e:
                        print(f"Thread Error: {e}")
                        continue

            print("Threads Finished")

        elif os.path.isdir(path):
            findfiles(path)


def monitor_threads(interval=40, max_inactive_time=30):
    global last_processed_time
    while True:
        sleep(interval)
        current_time = time()
        if current_time - last_processed_time > max_inactive_time:
            print(f"Nothing happened in the last {max_inactive_time}s. Restarting...")
            restart_python_process()


def restart_python_process():
    python_exe = sys.executable
    sleep(5)
    command = f'"{python_exe}" "{sys.argv[0]}"'
    os.execl(python_exe, command)

if __name__ == "__main__":
    monitor_thread = threading.Thread(target=monitor_threads, args=(40, 30), daemon=True)
    monitor_thread.start()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)


    root = "test"
    findfiles(root)
