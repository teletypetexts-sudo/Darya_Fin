"""
Финансовый бот для Telegram с записью в Google Sheets.

Структура таблицы (точно по колонкам):
  A: Дата
  B: Доход/Расход
  C: Категория
  D: Описание
  E: Сумма
  F: Валюта    (бот оставляет пустой)
  G: Источник  (бот оставляет пустой)
  H: Теги      (через запятую)

Формат ввода:
  500 расход                          → выбор категории → выбор тегов
  500 расход обед с Леной             → с описанием
  500 расход 12.05.25                 → с датой
  500 расход 12.05.25 обед с Леной    → всё вместе
  30000 доход клиент по контракту     → доход + описание

Команды:
  /balance — текущий баланс
  /tags    — список всех тегов с суммами
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
# 1. НАСТРОЙКИ из переменных окружения
# ═══════════════════════════════════════════════════════════
API_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1JwZWJbjORChtUmuJQiJisSZMrBr5TaBjKSxxuA1HdEU')
GOOGLE_CREDS_JSON = os.environ.get('GOOGLE_CREDS_JSON')

if not API_TOKEN:
    raise RuntimeError("Не задана переменная окружения TELEGRAM_TOKEN.")

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
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
else:
    creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)

client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

print("Бот запущен!")

# ═══════════════════════════════════════════════════════════
# 4. ВРЕМЕННОЕ ХРАНИЛИЩЕ
# ═══════════════════════════════════════════════════════════
# pending[entry_id] = {
#     'amount': str, 'date': str, 'is_inc': bool, 'desc': str,
#     'category': str, 'selected_tags': set, 'available_tags': list,
#     'awaiting_text_tags': bool, 'chat_id': int, 'message_id': int
# }
pending = {}
_counter = [0]


def make_entry_id():
    _counter[0] += 1
    return str(_counter[0] % 10000)


def find_active_text_input(chat_id):
    """Если в этом чате есть запись, ожидающая текстового ввода тегов — вернёт entry_id."""
    for eid, entry in pending.items():
        if entry.get('chat_id') == chat_id and entry.get('awaiting_text_tags'):
            return eid
    return None


# ═══════════════════════════════════════════════════════════
# 5. УТИЛИТЫ ДЛЯ ТЕГОВ
# ═══════════════════════════════════════════════════════════
def get_all_tags_with_counts():
    """Возвращает dict {тег: (количество, сумма)} из таблицы."""
    try:
        all_data = sheet.get_all_records()
    except Exception:
        return {}
    counts = {}
    for row in all_data:
        cell = str(row.get('Теги', '')).strip()
        if not cell:
            continue
        try:
            amount = float(str(row.get('Сумма', 0)).replace(',', '.').replace(' ', ''))
        except (ValueError, TypeError):
            amount = 0
        for tag in cell.split(','):
            tag = tag.strip()
            if not tag:
                continue
            if tag not in counts:
                counts[tag] = [0, 0.0]
            counts[tag][0] += 1
            counts[tag][1] += amount
    return counts


def get_top_tags(limit=10):
    """Топ тегов по частоте использования."""
    counts = get_all_tags_with_counts()
    items = sorted(counts.items(), key=lambda x: x[1][0], reverse=True)
    return [tag for tag, _ in items[:limit]]


def build_tags_keyboard(entry_id):
    """Строит inline-клавиатуру для выбора тегов."""
    entry = pending.get(entry_id)
    if not entry:
        return None

    available = entry.get('available_tags', [])
    selected = entry.get('selected_tags', set())

    markup = types.InlineKeyboardMarkup(row_width=2)
    # Кнопки существующих тегов (по 2 в ряд)
    row = []
    for i, tag in enumerate(available):
        mark = "✓ " if tag in selected else ""
        btn = types.InlineKeyboardButton(
            f"{mark}{tag}",
            callback_data=f"tg|{entry_id}|{i}"
        )
        row.append(btn)
        if len(row) == 2:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)

    # Управляющие кнопки
    markup.row(
        types.InlineKeyboardButton("➕ Свой тег", callback_data=f"tgnew|{entry_id}"),
        types.InlineKeyboardButton("⏭ Пропустить", callback_data=f"tgskip|{entry_id}")
    )
    markup.row(
        types.InlineKeyboardButton("✅ Готово", callback_data=f"tgdone|{entry_id}")
    )
    return markup


def format_tags_message(entry_id):
    """Сообщение со сводкой и выбранными тегами."""
    entry = pending.get(entry_id)
    if not entry:
        return ""

    type_emoji = "💰" if entry['is_inc'] else "💸"
    type_word = "Доход" if entry['is_inc'] else "Расход"
    text = (
        f"{type_emoji} *{type_word}* · {entry['amount']} ₽\n"
        f"📅 {entry['date']}\n"
        f"📂 {entry['category']}"
    )
    if entry.get('desc'):
        text += f"\n📝 _{entry['desc']}_"

    selected = entry.get('selected_tags', set())
    if selected:
        text += f"\n🏷 {', '.join(sorted(selected))}"

    text += "\n\nВыбери теги или нажми «Пропустить»:"
    return text


# ═══════════════════════════════════════════════════════════
# 6. КОМАНДЫ
# ═══════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(message):
    help_text = (
        "👋 Привет! Я твой финансовый бот.\n\n"
        "*Как записать расход или доход:*\n\n"
        "💸 `500 расход` — спросит категорию и теги\n"
        "💸 `500 расход обед с Леной` — с описанием\n"
        "💸 `500 расход 12.05.26` — с датой\n"
        "💸 `500 расход 12.05.26 обед с Леной` — всё вместе\n\n"
        "💰 `30000 доход` — доход\n"
        "💰 `30000 доход бонус от клиента` — с описанием\n\n"
        "*Команды:*\n"
        "/balance — текущий баланс\n"
        "/tags — список всех тегов с суммами"
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


@bot.message_handler(commands=['tags'])
def cmd_tags(message):
    try:
        counts = get_all_tags_with_counts()
        if not counts:
            bot.reply_to(message, "🏷 У тебя пока нет ни одного тега. Они появятся когда добавишь первую запись с тегом.")
            return
        # Сортируем по сумме (по убыванию)
        items = sorted(counts.items(), key=lambda x: x[1][1], reverse=True)
        lines = ["🏷 *Твои теги:*\n"]
        for tag, (cnt, amount) in items:
            lines.append(f"• `{tag}` — {amount:,.0f} ₽ ({cnt} оп.)".replace(',', ' '))
        bot.reply_to(message, '\n'.join(lines), parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")


# ═══════════════════════════════════════════════════════════
# 7. ПАРСИНГ И НАЧАЛО ВВОДА
# ═══════════════════════════════════════════════════════════
def parse_message(text):
    """Разбирает сообщение на: amount, is_inc, date, description."""
    parts = text.split()
    if len(parts) < 2:
        return None, None, None, None

    amount = "".join(filter(str.isdigit, parts[0]))
    if not amount:
        return None, None, None, None

    type_word = parts[1].lower()
    if 'доход' in type_word:
        is_inc = True
    elif 'расход' in type_word:
        is_inc = False
    else:
        return None, None, None, None

    rest = parts[2:]
    date_to_save = datetime.now().strftime("%d.%m.%y")
    desc_parts = []

    if rest:
        first = rest[0]
        try:
            input_date = datetime.strptime(first, "%d.%m.%y")
            if input_date <= datetime.now():
                date_to_save = first
                desc_parts = rest[1:]
            else:
                return None, None, "future", None
        except ValueError:
            try:
                input_date = datetime.strptime(first, "%d.%m.%Y")
                if input_date <= datetime.now():
                    date_to_save = input_date.strftime("%d.%m.%y")
                    desc_parts = rest[1:]
                else:
                    return None, None, "future", None
            except ValueError:
                desc_parts = rest

    desc = " ".join(desc_parts).strip()
    return amount, is_inc, date_to_save, desc


@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def handle_text(message):
    """Универсальный обработчик: либо новые теги, либо новая запись."""
    chat_id = message.chat.id

    # 1) Возможно мы ждём текстового ввода тегов?
    active_eid = find_active_text_input(chat_id)
    if active_eid:
        handle_text_tags(message, active_eid)
        return

    # 2) Иначе — это новая запись расхода/дохода
    if not any(w in message.text.lower() for w in ['расход', 'доход']):
        return  # игнорируем случайные сообщения

    start_entry(message)


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

    entry_id = make_entry_id()
    pending[entry_id] = {
        'amount': amount,
        'date': date_to_save,
        'is_inc': is_inc,
        'desc': desc or '',
        'category': None,
        'selected_tags': set(),
        'available_tags': [],
        'awaiting_text_tags': False,
        'chat_id': message.chat.id,
        'message_id': None,
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

    sent = bot.send_message(message.chat.id, summary, reply_markup=markup, parse_mode='Markdown')
    pending[entry_id]['message_id'] = sent.message_id


# ═══════════════════════════════════════════════════════════
# 8. CALLBACK: ВЫБОР КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data.startswith('exp|') or call.data.startswith('inc|'))
def callback_category(call):
    try:
        prefix, entry_id, cat_idx_str = call.data.split('|')
        cat_idx = int(cat_idx_str)

        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела, отправь заново")
            return

        cats = INCOME_CATS if prefix == "inc" else EXPENSE_CATS
        if cat_idx >= len(cats):
            bot.answer_callback_query(call.id, "Категория не найдена")
            return

        entry['category'] = cats[cat_idx]

        # Загружаем существующие теги
        entry['available_tags'] = get_top_tags(limit=10)

        # Показываем клавиатуру тегов
        markup = build_tags_keyboard(entry_id)
        text = format_tags_message(entry_id)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


# ═══════════════════════════════════════════════════════════
# 9. CALLBACK: РАБОТА С ТЕГАМИ
# ═══════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data.startswith('tg|'))
def callback_tag_toggle(call):
    """Переключить выбор тега."""
    try:
        _, entry_id, tag_idx_str = call.data.split('|')
        tag_idx = int(tag_idx_str)

        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела")
            return

        available = entry['available_tags']
        if tag_idx >= len(available):
            bot.answer_callback_query(call.id, "Тег не найден")
            return

        tag = available[tag_idx]
        if tag in entry['selected_tags']:
            entry['selected_tags'].discard(tag)
        else:
            entry['selected_tags'].add(tag)

        # Обновляем сообщение
        markup = build_tags_keyboard(entry_id)
        text = format_tags_message(entry_id)
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        except Exception:
            # Сообщение могло не измениться — игнорируем
            pass
        bot.answer_callback_query(call.id)

    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('tgnew|'))
def callback_tag_new(call):
    """Запрос на ввод нового тега текстом."""
    try:
        _, entry_id = call.data.split('|')
        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела")
            return

        entry['awaiting_text_tags'] = True
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "✏️ Напиши теги через запятую (без #):\n_например: отпуск, турция, безнал_",
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


def handle_text_tags(message, entry_id):
    """Обработка текстового ввода тегов."""
    entry = pending.get(entry_id)
    if not entry:
        return

    # Парсим теги (через запятую)
    new_tags = [t.strip() for t in message.text.split(',') if t.strip()]
    # Чистим от лишних # если пользователь всё-таки добавил
    new_tags = [t.lstrip('#').strip() for t in new_tags if t.lstrip('#').strip()]

    for t in new_tags:
        entry['selected_tags'].add(t)
        # Если такого тега ещё нет в available — добавим, чтобы был виден в клавиатуре
        if t not in entry['available_tags']:
            entry['available_tags'].append(t)

    entry['awaiting_text_tags'] = False

    # Показываем обновлённую клавиатуру (новым сообщением,
    # потому что редактировать старое уже неудобно)
    markup = build_tags_keyboard(entry_id)
    text = format_tags_message(entry_id)
    sent = bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    entry['message_id'] = sent.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith('tgskip|') or call.data.startswith('tgdone|'))
def callback_tag_finish(call):
    """Завершаем выбор тегов и сохраняем запись."""
    try:
        action, entry_id = call.data.split('|')
        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела")
            return

        # При "Пропустить" — теги пустые
        if action == 'tgskip':
            tags_to_save = []
        else:
            tags_to_save = sorted(entry['selected_tags'])

        tags_str = ', '.join(tags_to_save)

        entry_type = "Доход" if entry['is_inc'] else "Расход"
        amount = entry['amount']
        date_val = entry['date']
        category = entry['category']
        desc = entry['desc']

        # Правильный порядок колонок:
        # A: Дата | B: Доход/Расход | C: Категория | D: Описание
        # E: Сумма | F: Валюта (пусто) | G: Источник (пусто) | H: Теги
        sheet.append_row([
            date_val,
            entry_type,
            category,
            desc,
            amount,
            '',         # Валюта
            '',         # Источник
            tags_str    # Теги
        ])

        type_emoji = "💰" if entry['is_inc'] else "💸"
        confirm = (
            f"✅ Записано!\n\n"
            f"{type_emoji} {entry_type}\n"
            f"📅 {date_val}\n"
            f"📂 {category}\n"
            f"💵 {amount} ₽"
        )
        if desc:
            confirm += f"\n📝 {desc}"
        if tags_str:
            confirm += f"\n🏷 {tags_str}"

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=confirm
        )
        bot.answer_callback_query(call.id, "Готово!")

        pending.pop(entry_id, None)

    except Exception as e:
        bot.reply_to(call.message, f"Ошибка записи: {e}")


# ═══════════════════════════════════════════════════════════
# 10. HEALTH CHECK (для Railway)
# ═══════════════════════════════════════════════════════════
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
            pass

    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Health server on port {port}")


# ═══════════════════════════════════════════════════════════
# 11. ЗАПУСК
# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    start_health_server()
    print("Polling Telegram...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
