import os
import requests
import json
import time
import datetime
from html import escape
from telegram import send_telegram
from email_sendler import send_email
from dotenv import load_dotenv
load_dotenv()
logs = os.getenv("logs")
log = os.getenv("log")
def get_datetime ():
    time.log = datetime.datetime.now().strftime('%Y.%m.%d %H:%M')
    return time.log
def get_all_records():
    global log
    BASE_URL = "https://pub.fsa.gov.ru"

    USERNAME = "anonymous"
    PASSWORD = "hrgesf7HDR67Bd"

    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:159.0) Gecko/20100101 Firefox/159.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/ral",
        "Authorization": "Bearer null",
        "lkId": "",
        "orgId": ""
    })

    # 1. Открываем страницу, чтобы получить session-cookie
    r = session.get(f"{BASE_URL}/ral", timeout=30)
    r.raise_for_status()
    log += f"{get_datetime()} Страница: {r.status_code}\n"
    log += f"{get_datetime()} Cookie получена: + {bool(session.cookies)}\n"

    # 2. Авторизуемся
    login = session.post(
        f"{BASE_URL}/login",
        json={
            "username": USERNAME,
            "password": PASSWORD
        },
        timeout=30
    )

    log += f"{get_datetime()} Login: {login.status_code}\n"

    # 3. Забираем токен из response headers
    token = login.headers.get("authorization")

    if not token:
        raise RuntimeError("Сервер не вернул authorization в заголовках")

    log += f"{get_datetime()} Токен получен: True\n"

    # 4. Устанавливаем токен для следующих запросов
    session.headers["Authorization"] = token

    # 5. Получаем записи реестра
    all_records = []
    page = 0
    while True:
        payload = {
            "idStatus": [15, 19],
            "idAddressSubject": [
                "29251dcf-00a1-4e34-98d4-5c47484a36d4",
                "0c5b2444-70a0-4932-980c-b4dc0d3f02b5"
            ],
            "idType": [10],
            "columns": [],
            "sort": ["-id"],
            "limit": 100,
            "offset": page,
            "sortBy": "id",
            "sortDest": "desc",
            "numberOfAllRecords": False,
            "page": page
        }

        response = session.post(
                f"{BASE_URL}/api/v1/ral/common/showcases/get",
                json=payload,
                timeout=30
        )

        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        total = data.get("total", 0)

        if not items:
            break

        all_records.extend(items)

        log += f"{get_datetime()} Страница {page + 1}: получено {len(items)} записей. Всего загружено: {len(all_records)} из {total}\n"

        if len(all_records) >= total:
            break

        page += 1
        time.sleep(1)

    log += f"{get_datetime()} \nЗагрузка завершена. Всего записей: {len(all_records)}\n"
    # with open(datetime.datetime.now().strftime('%Y.%m.%d')+"_registry.json", "w", encoding="utf-8") as file:
    #     json.dump(all_records, file, ensure_ascii=False, indent=2)
    return all_records

def compare_records(new_records, filename="registry.json"):
    global log
    # Если предыдущей выгрузки ещё нет
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(new_records, file, ensure_ascii=False, indent=2)

        log += f"{get_datetime()} Создана первоначальная база реестра.\n"
        return [], [], []

    # Загружаем предыдущую выгрузку
    with open(filename, "r", encoding="utf-8") as file:
        old_records = json.load(file)

    old_dict = {record["id"]: record for record in old_records}
    new_dict = {record["id"]: record for record in new_records}

    added = []
    changed = []
    deleted = []

    # Ищем новые записи и изменения статусов
    for record_id, new_record in new_dict.items():

        if record_id not in old_dict:
            added.append(new_record)
            continue

        old_record = old_dict[record_id]

        if old_record.get("idStatus") != new_record.get("idStatus"):
            changed.append({
                "old": old_record,
                "new": new_record
            })

    # Ищем удалённые записи
    for record_id, old_record in old_dict.items():
        if record_id not in new_dict:
            deleted.append(old_record)

    # Сохраняем актуальную выгрузку
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(new_records, file, ensure_ascii=False, indent=2)
    return added, changed, deleted

def send_notifications(added, changed):
    global log
    messages = []

    for record in added:
        message = (
            "🆕 <b>Новая запись в реестре</b>\n\n"
            f"Организация: {escape(str(record.get('fullName') or 'Не указано'))}\n"
            f"Номер: <code>{escape(str(record.get('regNumber') or 'Не указан'))}</code>\n"
            f"Статус: {escape(str(record.get('nameStatus') or 'Не указан'))}"
        )

        messages.append(message)

    for change in changed:
        old = change["old"]
        new = change["new"]

        message = (
            "⚠️ <b>Изменение статуса организации</b>\n\n"
            f"Организация: {escape(str(new.get('fullName') or 'Не указано'))}\n"
            f"Номер: <code>{escape(str(new.get('regNumber') or 'Не указан'))}</code>\n\n"
            f"Было: {escape(str(old.get('nameStatus') or 'Не указан'))}\n"
            f"Стало: <b>{escape(str(new.get('nameStatus') or 'Не указан'))}</b>"
        )

        messages.append(message)
    if messages == []:
        message = (
            "<b>Результаты сравнения:</b>"
            f"Новых записей: {len(added)}\n"
            f"Изменений статуса: {len(changed)}\n"
            f"Удалённых записей: {len(deleted)}\n"
        )
        messages.append(message)

    # Отправляем сообщения в Telegram
    for message in messages:
        try:
            send_telegram(message)
            time.sleep(0.5)
        except Exception as e:
            log += f"{get_datetime()} Ошибка отправки в Telegram: {e}\n"

    # Отправляем одно общее письмо
    try:
        email_body = "\n\n------------------------------\n\n".join(
            messages
        )

        send_email(
            subject=f"Изменения в реестре ФСА: {len(messages)}",
            body=email_body
        )

    except Exception as e:
        log += get_datetime() + f"Ошибка отправки email: {e}"+ "\n"

records = get_all_records()
added, changed, deleted = compare_records(records)
send_notifications(added, changed)
log += f"{get_datetime()}\nРезультаты сравнения:\n"
log += f"Новых записей: {len(added)}\n"
log += f"Изменений статуса: {len(changed)}\n"
log += f"Удалённых записей: {len(deleted)}\n"

for record in added:
    log += f"{get_datetime()}\nНОВАЯ ЗАПИСЬ:\n"
    log += f"Организация: {record.get('fullName')}\n"
    log += f"Номер: {record.get('regNumber')}\n"
    log += f"Статус: {record.get('nameStatus')}\n"

for change in changed:
    old = change["old"]
    new = change["new"]

    log += f"{get_datetime()}\nИЗМЕНЕНИЕ СТАТУСА:\n"
    log += f"Организация: {new.get('fullName')}\n"
    log += f"Номер: {new.get('regNumber')}\n"
    log += f"Было: {old.get('nameStatus')}\n"
    log += f"Стало: {new.get('nameStatus')}\n"

for record in deleted:
    log += f"{get_datetime()}\nУДАЛЕНА ЗАПИСЬ:\n"
    log += f"Организация: {record.get('fullName')}\n"
    log += f"Номер: {record.get('regNumber')}\n"

if logs == "True":
    with open(datetime.datetime.now().strftime('%Y.%m.%d')+".log", "a", encoding="utf-8") as file:
        file.write(log)