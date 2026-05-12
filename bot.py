"""
Финансовый бот для Telegram с записью в Google Sheets.

Формат ввода:
  500 расход                          → выбор категории, без описания
  500 расход обед с Леной             → выбор категории, с описанием
  500 расход 12.05.25                 → с датой, без описания
  500 расход 12.05.25 обед с Леной    → с датой и описанием
  500 доход клиент по контракту       → доход + описание
  5000 доход                          → доход без описания

Команды:
  /balance — текущий баланс
  /start   — приветствие и подсказка
"""

import os
import json
import telebot
import gspread
from google.oauth2.service_account import Credentials
from telebot import types
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# 1. НАСТРОЙКИ из переменных окружения (безопасно!)
# ═══════════════════════════════════════════════════════════
API_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1JwZWJbjORChtUmuJQiJisSZMrBr5TaBjKSxxuA1HdEU')
GOOGLE_CREDS_JSON = os.environ.get('GOOGLE_CREDS_JSON')  # JSON строка

if not API_TOKEN:
    raise RuntimeError(
        "Не задана переменная окружения TELEGRAM_TOKEN. "
        "Установи её в настройках Railway → Variables."
    )

# ═══════════════════════════════════════════════════════════
# 2. КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════
EXPENSE_CATS = [
    "🛒 Продукты", "🏫 София: Школа", "💊 Аптека", "🏥 Здоровье",
    "👧 София: Зож", "🧴 Красота: Уход", "💅 Красота: Проц", "👗 Одежда",
    "🍕 Кафе", "🚗 Авто", "✈️ Поездки", "🎁 Подарки",
    "📚 Обучение", "🏠 Дом", "💳 Кредиты", "🧩 Другое"
]

INCOME_CATS = [
    "💳 Зарплата", "🏢 Див: Тушино", "🔑 Див: Николь", "🩺 Див: Клиника",
    "🔙 Возврат", "📈 Инвест", "🎲 Случайно", "🎁 Подарки"
]

# ═══════════════════════════════════════════════════════════
# 3. ПОДКЛЮЧЕНИЕ
# ═══════════════════════════════════════════════════════════
bot = telebot.TeleBot(API_TOKEN)
scopes = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']

if GOOGLE_CREDS_JSON:
    # На сервере (Railway) — креды из переменной окружения
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
else:
    # Локально — из файла
    creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)

client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

print("Бот запущен!")

# ═══════════════════════════════════════════════════════════
# 4. ВРЕМЕННОЕ ХРАНИЛИЩЕ ОПИСАНИЙ
# ═══════════════════════════════════════════════════════════
# Telegram ограничивает callback_data 64 байтами, поэтому описание
# мы держим в памяти, а в callback кладём только короткий ID.
pending = {}  # {entry_id: {'desc': str, 'amount': str, 'date': str, 'is_inc': bool}}
_counter = [0]


def make_entry_id():
    _counter[0] += 1
    return str(_counter[0] % 10000)


# ═══════════════════════════════════════════════════════════
# 5. КОМАНДЫ
# ═══════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(message):
    help_text = (
        "👋 Привет! Я твой финансовый бот.\n\n"
        "*Как записать расход или доход:*\n\n"
        "💸 `500 расход` — спросит категорию\n"
        "💸 `500 расход обед с Леной` — с описанием\n"
        "💸 `500 расход 12.05.25` — с датой\n"
        "💸 `500 расход 12.05.25 обед с Леной` — всё вместе\n\n"
        "💰 `30000 доход` — доход\n"
        "💰 `30000 доход бонус от клиента` — с описанием\n\n"
        "*Команды:*\n"
        "/balance — текущий баланс"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


@bot.message_handler(commands=['balance'])
def cmd_balance(message):
    try:
        all_data = sheet.get_all_records()
        total_inc = 0.0
        total_exp = 0.0
        for row in all_data:
            try:
                val = float(str(row.get('Сумма', 0)).replace(',', '.').replace(' ', ''))
            except ValueError:
                continue
            if row.get('Доход/Расход') == 'Доход':
                total_inc += val
            elif row.get('Доход/Расход') == 'Расход':
                total_exp += val

        balance = total_inc - total_exp
        text = (
            f"💰 *Баланс:* {balance:,.0f} ₽\n\n"
            f"📈 Доходы: {total_inc:,.0f} ₽\n"
            f"📉 Расходы: {total_exp:,.0f} ₽"
        ).replace(',', ' ')
        bot.reply_to(message, text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"Ошибка при расчете: {e}")


# ═══════════════════════════════════════════════════════════
# 6. ОСНОВНОЙ ОБРАБОТЧИК
# ═══════════════════════════════════════════════════════════
def parse_message(text):
    """Разбирает сообщение на: amount, is_inc, date, description.
    Возвращает (amount, is_inc, date, desc) или (None, None, None, None) если не подошло.
    """
    parts = text.split()
    if len(parts) < 2:
        return None, None, None, None

    # Сумма
    amount = "".join(filter(str.isdigit, parts[0]))
    if not amount:
        return None, None, None, None

    # Тип
    type_word = parts[1].lower()
    if 'доход' in type_word:
        is_inc = True
    elif 'расход' in type_word:
        is_inc = False
    else:
        return None, None, None, None

    # Остальные слова — это либо дата, либо описание
    rest = parts[2:]
    date_to_save = datetime.now().strftime("%d.%m.%y")
    desc_parts = []

    if rest:
        # Проверяем первое слово — это дата?
        first = rest[0]
        is_date = False
        try:
            input_date = datetime.strptime(first, "%d.%m.%y")
            if input_date <= datetime.now():
                date_to_save = first
                is_date = True
                desc_parts = rest[1:]
            else:
                return None, None, "future", None  # сигнал об ошибке
        except ValueError:
            # Может это формат %d.%m.%Y?
            try:
                input_date = datetime.strptime(first, "%d.%m.%Y")
                if input_date <= datetime.now():
                    date_to_save = input_date.strftime("%d.%m.%y")
                    is_date = True
                    desc_parts = rest[1:]
                else:
                    return None, None, "future", None
            except ValueError:
                # Не дата — всё в описание
                desc_parts = rest

    desc = " ".join(desc_parts).strip()
    return amount, is_inc, date_to_save, desc


@bot.message_handler(func=lambda m: m.text and any(w in m.text.lower() for w in ['расход', 'доход']))
def start_entry(message):
    amount, is_inc, date_to_save, desc = parse_message(message.text)

    if date_to_save == "future":
        bot.reply_to(message, "⚠️ Ошибка: дата ещё не наступила!")
        return

    if amount is None:
        bot.reply_to(
            message,
            "⚠️ Не понял. Пример: `500 расход обед` или `30000 доход`",
            parse_mode='Markdown'
        )
        return

    # Сохраняем во временное хранилище
    entry_id = make_entry_id()
    pending[entry_id] = {
        'amount': amount,
        'date': date_to_save,
        'is_inc': is_inc,
        'desc': desc or ''
    }

    cats = INCOME_CATS if is_inc else EXPENSE_CATS
    prefix = "inc" if is_inc else "exp"

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(c, callback_data=f"{prefix}|{entry_id}|{i}")
        for i, c in enumerate(cats)
    ]
    markup.add(*buttons)

    type_emoji = "💰" if is_inc else "💸"
    type_word = "Доход" if is_inc else "Расход"

    summary = f"{type_emoji} *{type_word}*\n💵 Сумма: {amount} ₽\n📅 Дата: {date_to_save}"
    if desc:
        summary += f"\n📝 Описание: _{desc}_"
    summary += "\n\nВыбери категорию:"

    bot.send_message(message.chat.id, summary, reply_markup=markup, parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        # Распаковываем: prefix|entry_id|cat_idx
        parts = call.data.split('|')
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "Устаревшая кнопка")
            return

        prefix, entry_id, cat_idx_str = parts
        cat_idx = int(cat_idx_str)

        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела, отправь заново")
            return

        cats = INCOME_CATS if prefix == "inc" else EXPENSE_CATS
        if cat_idx >= len(cats):
            bot.answer_callback_query(call.id, "Категория не найдена")
            return

        category = cats[cat_idx]
        entry_type = "Доход" if prefix == "inc" else "Расход"
        amount = entry['amount']
        date_val = entry['date']
        desc = entry['desc']

        # Записываем в таблицу: Дата | Сумма | Доход/Расход | Категория | Описание
        sheet.append_row([date_val, amount, entry_type, category, desc])

        type_emoji = "💰" if prefix == "inc" else "💸"
        confirm = (
            f"✅ Записано!\n\n"
            f"{type_emoji} {entry_type}\n"
            f"📅 {date_val}\n"
            f"📂 {category}\n"
            f"💵 {amount} ₽"
        )
        if desc:
            confirm += f"\n📝 {desc}"

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=confirm
        )

        # Чистим хранилище
        pending.pop(entry_id, None)

    except Exception as e:
        bot.reply_to(call.message, f"Ошибка записи: {e}")


# ═══════════════════════════════════════════════════════════
# 7. HEALTH CHECK (для Railway)
# ═══════════════════════════════════════════════════════════
# Railway проверяет что что-то слушает порт.
# Запускаем простой HTTP-сервер в фоне для health checks.
def start_health_server():
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK - bot running')

        def log_message(self, format, *args):
            pass  # тихо

    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Health server on port {port}")


# ═══════════════════════════════════════════════════════════
# 8. ЗАПУСК
# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    start_health_server()
    print("Polling Telegram...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
