# Standard library imports
import os
import re
import sys
import math
import time
import argparse
import traceback
from pathlib import Path
from typing import List, Dict, Tuple
from urllib.parse import urlparse

# Third-party libraries
import requests
import spacy
import yake
import pytextrank
from keybert import KeyBERT
from spacy.cli import download

# g4f (OpenAI/GPT-like interface)
from g4f.models import gpt_4
from g4f.client import Client

# Rich (console formatting)
from rich.console import Console
from rich.table import Table
from rich.text import Text

PARAMS: Dict = {
    "URL_OR_ID": None,
    "SCAN_DESCRIPTION": False,
    "MODEL": None,
    "PATH": 'data',
    # Необходимо указать DEST(Пункт выдачи. Для поиска). Найти можно в консоле. OPTIONS | search.wb.ru
    "DEST": -1257786,  # г Москва, ул Никольская д. 7-9, стр. 4
    "DEBUG": True,  # Print stages
}

# Define the parser
parser = argparse.ArgumentParser(description='WB Parser')
parser.add_argument('--url', action="store", dest='url_or_id', default="")
parser.add_argument('--desc', action=argparse.BooleanOptionalAction)
parser.add_argument('--model', action="store", dest='model', default="")
parser.add_argument('--dest', action="store", dest='dest', default=-1257786)

YES_ARRAY = ["yes", "y", "да", "д", "1", "true"]
NO_ARRAY = ["no", "n", "нет", "н", "не", "0", "false"]


class Color:
    PURPLE = '\033[95m'
    DARK_CYAN = '\033[36m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


# Header for requests.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0 Win64 x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Headers": "Authorization,Accept,Origin,DNT,User-Agent,Content-Type,Wb-AppType,Wb-AppVersion,Xwbuid,Site-Locale,X-Clientinfo,Storage-Type,Data-Version,Model-Version,__wbl, x-captcha-id",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-control-Allow-Origin": "https://www.wildberries.ru",
    "Content-Encoding": "gzip",
    "Content-Type": "application/json charset=utf-8"
}


def create_config() -> None:
    def wrong_select_msg():
        print(Color.RED + "Неправильный ответ!" + Color.END)
        print(Color.YELLOW + "Пожалуйста, ответьте 1 из этих вариантов:" + Color.END)
        print(Color.YELLOW + '["yes", "y", "да", "д", "1", 1, True, "true"] чтобы ответить "Yes"' + Color.END)
        print(Color.YELLOW + '["no", "n", "нет", "н", "не", "0", 0, False, "false"] чтобы ответить "No"' + Color.END)

    # URL_OR_ID
    while not PARAMS["URL_OR_ID"]:
        print(Color.GREEN + "[CONFIG] " + Color.YELLOW + "Введите ссылку на карточку Wildberries:" + Color.END)

        input_answer = input().strip()

        try:
            if input_answer.isdigit():
                PARAMS["URL_OR_ID"] = int(input_answer)
                break
        except ValueError:
            pass
        try:
            if is_valid_url(input_answer):
                PARAMS["URL_OR_ID"] = input_answer
                break
        except ValueError:
            pass

        print(Color.RED + "Ссылка не валидна!" + Color.END)
        print(Color.YELLOW + "Пожалуйста, введите ссылку." + Color.END)

    # SCAN_DESCRIPTION
    while True:
        print(Color.GREEN + "[CONFIG] " + Color.YELLOW + "Сканировать описание?" + Color.END)
        input_answer = input("Yes/No: ").strip().lower()
        if input_answer in YES_ARRAY:
            PARAMS["SCAN_DESCRIPTION"] = True
            break
        elif input_answer in NO_ARRAY:
            PARAMS["SCAN_DESCRIPTION"] = False
            break
        wrong_select_msg()

    # MODEL
    while True:
        print(
            Color.GREEN + "[CONFIG] " + Color.YELLOW + "Выберете NLP модель:\n[1] spaCy\n[2] YAKE\n[3] KeyBERT\n[4] All\nExperimental: [5] ChatGPT" + Color.END)
        input_answer = input("Yes/No: ").strip().lower()
        if input_answer in ["1", "[1]", "spacy"]:
            PARAMS["MODEL"] = "spaCy"
            break
        elif input_answer in ["2", "[2]", "yake"]:
            PARAMS["MODEL"] = "YAKE"
            break
        elif input_answer in ["3", "[3]", "keybert"]:
            PARAMS["MODEL"] = "KeyBERT"
            break
        elif input_answer in ["4", "[4]", "all"]:
            PARAMS["MODEL"] = "All"
            break
        elif input_answer in ["5", "[5]", "gpt", "chatgpt"]:
            PARAMS["MODEL"] = "ChatGPT"
            break
        wrong_select_msg()

    # # PATH
    # while True:
    #     print(Color.GREEN + "[CONFIG] " + Color.YELLOW + "Укажите путь, куда сохранить? Например:" + Color.END)
    #     print(
    #         Color.DARK_CYAN + "data/result" + Color.END + Color.YELLOW + " - Чтобы сохранить в текущей папке + data/result")
    #     print(
    #         Color.DARK_CYAN + "C:/data/result" + Color.END + Color.YELLOW + " - Можно указать абсолютный путь")
    #     print(
    #         Color.RED + "ВНИМАНИЕ! Если вы укажите существующий путь с файлами. Файлы будут заменены без возможности возврата!" + Color.END)
    #     print(
    #         Color.YELLOW + "Сейчас выбрано: " + Color.DARK_CYAN + "data/" + Color.END)
    #
    #     input_answer = input("Введите путь(или оставьте пустым, чтобы продолжить): ").strip()
    #     if input_answer == "":
    #         break
    #     elif len(input_answer) > 2:
    #         str_arr = input_answer.split("/")
    #         new_arr: List[Any] = list(filter(len, str_arr))
    #         path = "/".join(new_arr)
    #         PARAMS["PATH"] = path
    #         break
    #
    #     print(Color.RED + "Неправильный ответ!" + Color.END)
    #     print(Color.YELLOW + "Пожалуйста, введите корректный путь." + Color.END)


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return all([parsed.scheme in ('http', 'https'), parsed.netloc])


def get_configs() -> List[str]:
    print(Color.BOLD + Color.PURPLE + "Загружаем конфигурации..." + Color.END)

    Path("configs").mkdir(parents=True, exist_ok=True)

    path_to_json = 'configs/'
    json_files_list = [pos_json for pos_json in os.listdir(path_to_json) if pos_json.endswith('.json')]

    return json_files_list


def config():
    pass


def find_host(route_data: Dict, section: str, route_map_name: str, volume: int) -> str or None:
    route_map_key = f"{route_map_name}_route_map"
    route_entries = route_data.get(section, {}).get(route_map_key, [])

    for entry in route_entries:
        if entry.get('method') != 'range':
            continue
        for host_entry in entry.get('hosts', []):
            if host_entry['vol_range_from'] <= volume <= host_entry['vol_range_to']:
                return host_entry['host']
    return None


def parse() -> tuple[Dict, str, int] or None:
    try:
        if type(PARAMS["URL_OR_ID"]) == int:
            article = PARAMS["URL_OR_ID"]
        else:
            article = urlparse(PARAMS["URL_OR_ID"]).path.split("/")[2]

        base_url = "https://card.wb.ru/cards/detail?&dest={}&nm={}".format(PARAMS["DEST"], article)

        response = requests.get(base_url, headers=HEADERS)
        if response.status_code == 200:
            obj = response.json()
            url = "https://www.wildberries.ru/catalog/{}/detail.aspx".format(article)
            content = extract_main_data(obj)
        else:
            raise ConnectionError("Can't get data from WB")

        # Get description from API
        if PARAMS["SCAN_DESCRIPTION"]:
            # Узнаем на каком host-е находится description
            api_url = "https://cdn.wbbasket.ru/api/v3/upstreams"
            response = requests.get(api_url, headers=HEADERS)
            if response.status_code == 200:
                obj = response.json()
                host = find_host(obj, 'recommend', 'mediabasket', int(str(article)[:(len(article) - 5)]))
            else:
                raise ConnectionError("Can't get data from API")

            card_url = "https://{}/vol{}/part{}/{}/info/ru/card.json".format(host, str(article)[:(len(article) - 5)],
                                                                             str(article)[:(len(article) - 3)],
                                                                             article)

            response = requests.get(card_url, headers=HEADERS)
            if response.status_code == 200:
                obj = response.json()
                content.update(extract_description_data(obj))
            else:
                raise ConnectionError("Can't get card data from API")

        if PARAMS["DEBUG"]:
            print(Color.BOLD + Color.GREEN + "Card parsing completed!" + Color.END)

        return content, url, article

    except Exception as err:
        print(traceback.format_exc())
        print(Color.BOLD + Color.RED + str(err) + Color.END)


def extract_description_data(data) -> Dict or None:
    description = data.get("description", data["description"])

    options = data.get("options", None)
    characteristics = []

    if len(options):
        for option in options:
            characteristics.append({"name": option["name"], "value": option["value"]})

    product_info = {
        "Description": description,
        "Characteristics": characteristics,
        "Contents": data.get("contents", None)
    }

    return product_info


def extract_main_data(data) -> Dict or None:
    products = data.get("data", {}).get("products", [])

    product_info = {}

    for product in products:
        product_id = product.get("id", None)
        name = product.get("name", None)
        brand = product.get("brand", None)
        price = int(product.get("priceU", 0) / 100)
        sale_price = int(product.get("salePriceU", 0) / 100)
        description = product.get("description", None)
        rating = product.get("supplierRating", None)
        sale = product.get("sale", None)
        total_quantity = product.get("totalQuantity", None)

        product_info = {
            "ID": product_id,
            "Name": name,
            "Brand": brand,
            "Price": price,
            "SalePrice": sale_price,
            "Description": description,
            "Rating": str(rating),
            "Sale": str(sale),
            "Stock": total_quantity
        }

    return product_info


def load_spacy_model(model_name, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return spacy.load(model_name)
        except OSError:
            print(f"Model '{model_name}' not found. Downloading...")
            download(model_name)
        except Exception as e:
            print(f"Error loading model '{model_name}': {e}")
            time.sleep(delay)
    # Final attempt after potential download
    try:
        return spacy.load(model_name)
    except Exception as e:
        raise RuntimeError(f"Failed to load model '{model_name}' after retries. Last error: {e}")


def is_valid_phrase(text: str, min_length: int = 2, blacklist_pattern=r"^[^\w]+$") -> bool:
    # Exclude phrases that are too short or only punctuation/symbols
    if len(text.strip()) < min_length:
        return False
    if re.match(blacklist_pattern, text):
        return False
    return True


def extract_keywords(doc, min_rank: float = 0.03, min_length: int = 3, max_results: int = 10) -> List[Dict]:
    keywords = []
    for phrase in doc._.phrases:
        if phrase.rank < min_rank:
            continue
        if not is_valid_phrase(phrase.text, min_length=min_length):
            continue
        keywords.append({
            "text": phrase.text,
            "rank": phrase.rank,
            "count": phrase.count,
        })
        if len(keywords) >= max_results:
            break
    return keywords


def extract_keywords_yake(text: str, max_keywords: int = 10) -> Dict[str, List[Tuple[str, float, int]]]:
    # Define YAKE keyword extractor with Russian language
    kw_extractor = yake.KeywordExtractor(
        lan="ru",  # Russian
        n=2,  # Unigrams and bigrams
        top=max_keywords,
        features=None
    )

    keywords: dict = {"ru": kw_extractor.extract_keywords(text)}

    # Define YAKE keyword extractor with English language
    kw_extractor.lan = "en"

    keywords["en"] = kw_extractor.extract_keywords(text)

    return keywords


def extract_keywords_spacy(
        text: str,
        min_rank: float = 0.03,
        min_length: int = 3,
        max_keywords: int = 10
) -> Dict[str, List[Dict]]:
    nlp_en = load_spacy_model("en_core_web_trf")
    nlp_ru = load_spacy_model("ru_core_news_lg")

    # Add PyTextRank if not already in pipeline
    if "textrank" not in nlp_en.pipe_names:
        nlp_en.add_pipe("textrank")
    if "textrank" not in nlp_ru.pipe_names:
        nlp_ru.add_pipe("textrank")

    results = {
        "en": extract_keywords(nlp_en(text), min_rank, min_length, max_keywords),
        "ru": extract_keywords(nlp_ru(text), min_rank, min_length, max_keywords),
    }
    return results


def extract_keywords_keybert(text: str, max_keywords: int = 10) -> List:
    kw_model = KeyBERT("paraphrase-multilingual-MiniLM-L12-v2")

    text = text[:4000]  # Truncate to avoid token overflow

    keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        top_n=max_keywords
    )
    return keywords


def extract_keywords_chatgpt(text: str, max_keywords: int = 10) -> List:
    client = Client()

    content = f"""
###BEGIN_FORMAT###
keyword1ζkeyword2ζkeyword3ζ...ζkeyword10
###END_FORMAT###
Give me top {max_keywords} keywords for search in shops:
\"{text}\"
    """

    response = client.chat.completions.create(
        model=gpt_4,
        messages=[{"role": "user", "content": content}],
    )

    answer = response.choices[0].message.content
    if answer[:16] == "New g4f version:":
        try:
            answer = answer.split("pip install -U g4f")[1].strip()
        except IndexError:
            answer = None

    if answer:
        if "###END_FORMAT###" in answer:
            answer = answer.split("###END_FORMAT###")[0]
        if "###BEGIN_FORMAT###" in answer:
            answer = answer.split("###BEGIN_FORMAT###")[1]
        answer = answer.replace("```", "").replace("\n", " ").replace("  ", " ").strip()

        keywords = [s for s in answer.split("ζ") if s]
        return keywords
    else:
        return []


def find_keywords(content: Dict) -> List:
    total_text = content["Name"] + "\n" + content["Brand"]

    if PARAMS["SCAN_DESCRIPTION"]:
        for characteristic in content["Characteristics"]:
            total_text += characteristic["value"] + "\n"

        if content["Description"]:
            total_text += content["Description"] + "\n"

        if content["Contents"]:
            total_text += content["Contents"] + "\n"

        total_text += content["Description"] + "\n"

    total_keywords: set = set()

    if PARAMS["MODEL"] == "spaCy" or PARAMS["MODEL"] == "All":
        keywords = extract_keywords_spacy(total_text, min_rank=0.03, min_length=3, max_keywords=10)
        all_texts = [item['text'] for lang in keywords.values() for item in lang]
        total_keywords.update(all_texts)

    if PARAMS["MODEL"] == "YAKE" or PARAMS["MODEL"] == "All":
        keywords = extract_keywords_yake(total_text, max_keywords=10)
        all_texts = [item[0] for lang in keywords.values() for item in lang]
        total_keywords.update(all_texts)

    if PARAMS["MODEL"] == "KeyBERT" or PARAMS["MODEL"] == "All":
        keywords = extract_keywords_keybert(total_text, max_keywords=10)
        all_texts = [text for text, _ in keywords]
        total_keywords.update(all_texts)

    if PARAMS["MODEL"] == "ChatGPT":
        keywords = extract_keywords_chatgpt(total_text, max_keywords=10)
        total_keywords.update(keywords)

    seen: set = set()
    unique_texts = []
    for text in total_keywords:
        lowered = text.lower()
        if lowered not in seen:
            seen.add(lowered)
            unique_texts.append(text)

    # Optional: sort for readability
    unique_texts.sort()

    return unique_texts


def search_position(query: str, url: str, article: str) -> Dict:
    if PARAMS["DEBUG"]:
        sys.stdout.write(
            Color.BOLD + Color.DARK_CYAN + f"[*] Searching for card positions by \"{query}\" query..." + Color.END)
        sys.stdout.flush()

    res = {"hits": 0, "total_position": 0, "total_pages": 0, "page": 0, "page_position": 0, }

    page = 1
    dest = PARAMS["DEST"]
    position = 0

    search_url = "https://search.wb.ru/exactmatch/sng/common/v13/search?curr=rub&dest={}&lang=ru&page={}&query={}&resultset=catalog&sort=popular".format(
        dest, page, query)

    try:
        response = requests.get(search_url, headers=HEADERS)
        if response.status_code == 200:
            obj = response.json()
        else:
            raise ConnectionError("Can't get data from WB")

        hits = obj.get("data", {}).get('total', 0)
        if hits == 0:
            if PARAMS["DEBUG"]:
                clear_line()
                print(Color.BOLD + Color.RED + f"[-] Items not found for query \"{query}\"." + Color.END)
            return res

        res["hits"] = hits
        total_pages = math.ceil(hits / 100)
        res["total_pages"] = total_pages

        products = obj.get("data", {}).get('products', [])
        for idx, product in enumerate(products):
            position += 1
            if product.get("id", None) == int(article):
                res["total_position"] = position
                res["page"] = page
                res["page_position"] = idx + 1
                if PARAMS["DEBUG"]:
                    clear_line()
                    print(Color.BOLD + Color.GREEN + f"[+] Search \"{query}\" parsing completed!" + Color.END)
                return res

        for page in range(2, total_pages + 1):
            search_url = "https://search.wb.ru/exactmatch/sng/common/v13/search?curr=rub&dest={}&lang=ru&page={}&query={}&resultset=catalog&sort=popular".format(
                dest, page, query)
            response = requests.get(search_url, headers=HEADERS)
            if response.status_code == 200:
                obj = response.json()
            else:
                raise ConnectionError("Can't get data from WB")

            products = obj.get("data", {}).get('products', [])
            for idx, product in enumerate(products):
                position += 1
                if product.get("id", None) == int(article):
                    res["total_position"] = position
                    res["page"] = page
                    res["page_position"] = idx + 1
                    if PARAMS["DEBUG"]:
                        # Clear line and print completion
                        clear_line()
                        print(Color.BOLD + Color.GREEN + f"[+] Search \"{query}\" parsing completed!" + Color.END)
                    return res

    except Exception as err:
        print(traceback.format_exc())
        print(Color.BOLD + Color.RED + str(err) + Color.END)

    if PARAMS["DEBUG"]:
        # Print a warning if not found
        clear_line()
        print(Color.BOLD + Color.YELLOW + f"[!] Article {article} not found for query \"{query}\"." + Color.END)
    return res


def print_table_of_result(obj):
    console = Console()

    # Print "PARSING RESULT" title
    console.print(Text("PARSING RESULT", style="bold"), justify="center")

    # Info table
    info_table = Table(show_header=False, box=None)
    info_table.add_row("URL", obj["url"])
    info_table.add_row("Article", str(obj["article"]))
    console.print(info_table)

    # Main table header
    result_table = Table(title="Parsed Data", header_style="bold magenta")
    result_table.add_column("Query", style="cyan", no_wrap=True)
    result_table.add_column("Search Position", justify="center")
    result_table.add_column("Per Page Position", justify="center")
    result_table.add_column("Page", justify="center")
    result_table.add_column("Pages", justify="center")
    result_table.add_column("Hits", justify="center")

    # Extract and sort data
    entries = []
    for key, value in obj.items():
        if isinstance(value, dict):
            entries.append({
                "query": key,
                "search": value.get("total_position", 0),
                "per_page": value.get("page_position", 0),
                "page": value.get("page", 0),
                "pages": value.get("total_pages", 0),
                "hits": value.get("hits", 0),
            })

    # Sorting logic:
    # - First by non-zero search positions (ascending)
    # - Then by zero search positions, sorted by hits descending
    sorted_entries = sorted(
        entries,
        key=lambda e: (
            1 if e["search"] == 0 else 0,  # 0 for non-zero search, 1 for zero
            e["search"] if e["search"] != 0 else -e["hits"]
        )
    )

    # Add rows
    for e in sorted_entries:
        result_table.add_row(
            e["query"],
            str(e["search"]),
            str(e["per_page"]),
            str(e["page"]),
            str(e["pages"]),
            str(e["hits"])
        )

    console.print(result_table)


def clear_line():
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()


def arg_parse():
    args = parser.parse_args()
    PARAMS["DEST"] = args.dest
    PARAMS["MODEL"] = args.model
    PARAMS["URL_OR_ID"] = args.url_or_id

    try:
        if PARAMS["URL_OR_ID"].isdigit():
            PARAMS["URL_OR_ID"] = int(PARAMS["URL_OR_ID"])
    except ValueError:
        pass

    PARAMS["SCAN_DESCRIPTION"] = args.desc

    return True if args.url_or_id else False


def main():
    is_parsed = arg_parse()

    if is_parsed:
        PARAMS["DEBUG"] = False
    else:
        json_files = get_configs()

        if len(json_files):
            print("Список конфигураций загружены!")
        else:
            print(Color.YELLOW + "Конфигурации не найдены! Создаём первую конфигурацию..." + Color.END)
            create_config()

        while len(json_files):
            print(
                Color.BOLD + Color.GREEN + "[ACTION]" + Color.END + Color.GREEN + "Выберете действие:" + Color.END)
            print(Color.DARK_CYAN + "1) Выбрать готовую конфигурацию" + Color.END)
            print(Color.DARK_CYAN + "2) Создать новую конфигурацию" + Color.END)
            answer = input("Укажите целое число 1 или 2: ")
            if answer == "1":
                break
            elif answer == "2":
                create_config()

            print(Color.RED + "Неправильный ответ!" + Color.END)
            print(Color.YELLOW + "Пожалуйста, введите 1 из доступных чисел: [1, 2]" + Color.END)

        print(Color.BOLD + Color.PURPLE + "Скрипт запущен!" + Color.END)

    # Parsing card
    content, url, article = parse()

    # Finding keywords
    keywords = find_keywords(content)
    if PARAMS["DEBUG"]:
        print("Keywords: ", keywords)

    table = {"url": url, "article": article}

    # Search positions by keywords
    for query in keywords:
        res = search_position(query, url, article)
        table[query] = res

    print_table_of_result(table)


if __name__ == "__main__":
    main()
