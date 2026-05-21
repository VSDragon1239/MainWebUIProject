import csv
import time
import logging
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Конфигурация
SCHEDULE_URL = "https://zabgu.ru/schedule"
OUTPUT_DIR = Path("../WebUIProjectGreenZabGU/zabgu_groups")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_groups_list() -> list[str]:
    """Получает список всех групп с сайта."""
    logging.info(f"Запрос списка групп: {SCHEDULE_URL}")
    try:
        response = requests.get(SCHEDULE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка сети: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    select_tag = soup.find('select')

    if not select_tag:
        logging.error("Тег <select> не найден на странице.")
        return []

    # Извлекаем значения, пропуская пустое ("0") и обрезая пробелы по краям
    groups = [
        opt.get('value', '').strip()
        for opt in select_tag.find_all('option')
        if opt.get('value', '').strip() not in ("0", "")
    ]
    return groups


def save_to_csv(groups: list[str], filename: Path):
    """Сохраняет список групп в CSV."""
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["Группа"])  # Заголовок
        for group in groups:
            writer.writerow([group])
    logging.info(f"✅ Сохранено в CSV: {filename}")


def save_to_md(groups: list[str], filename: Path):
    """Сохраняет список групп в Markdown."""
    with open(filename, mode='w', encoding='utf-8') as f:
        f.write("# Все группы ЗабГУ (по алфавиту)\n\n")
        f.write("| № | Группа |\n")
        f.write("|:--|:-------|\n")
        for idx, group in enumerate(groups, start=1):
            f.write(f"| {idx} | {group} |\n")
    logging.info(f"✅ Сохранено в Markdown: {filename}")


def main():
    time.sleep(0.5)  # Вежливая пауза

    # 1. Получаем группы
    raw_groups = fetch_groups_list()
    if not raw_groups:
        logging.error("Не удалось получить группы. Парсинг прерван.")
        return

    # 2. Сортируем по алфавиту (учитывая правильный порядок русских букв)
    sorted_groups = sorted(raw_groups, key=lambda x: x.lower())
    logging.info(f"Найдено групп: {len(sorted_groups)}. Сортировка завершена.")

    # 3. Сохраняем
    save_to_csv(sorted_groups, OUTPUT_DIR / "all_groups_abc.csv")
    save_to_md(sorted_groups, OUTPUT_DIR / "all_groups_abc.md")

    logging.info("🎉 Готово!")


if __name__ == "__main__":
    main()
