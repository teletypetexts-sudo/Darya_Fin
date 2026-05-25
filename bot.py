"""
Финансовый бот для Telegram с записью в Google Sheets.

Структура таблицы (точно по колонкам):
  A: Дата
  B: Доход/Расход
  C: Категория
  D: Описание
  E: Сумма
  F: Валюта        (бот оставляет пустой)
  G: Источник      (бот оставляет пустой)
  H: Теги          (через запятую)
  I: Подкатегория  (если есть)

Поток для расхода:
  1. Парсим сообщение → сумма, тип, дата, описание
  2. Выбор категории
  3. Если есть подкатегории — выбор подкатегории (или пропустить)
  4. Выбор тегов (мульти-выбор + свой)
  5. Сохранение

Команды:
  /start   — приветствие
  /balance — текущий баланс
  /tags    — список всех тегов
"""

import os
import json
import telebot
import gspread
from google.oauth2.service_account import Credentials
from telebot import types
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# 1. НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════
API_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1JwZWJbjORChtUmuJQiJisSZMrBr5TaBjKSxxuA1HdEU')
GOOGLE_CREDS_JSON = os.environ.get('GOOGLE_CREDS_JSON')

if not API_TOKEN:
    raise RuntimeError("Не задана переменная окружения TELEGRAM_TOKEN.")

# ═══════════════════════════════════════════════════════════
# 2. КАТЕГОРИИ С ПОДКАТЕГОРИЯМИ
# Чтобы добавить новую категорию или подкатегорию — просто
# отредактируй этот словарь. None значит подкатегорий нет.
# ═══════════════════════════════════════════════════════════
EXPENSE_TREE = {
    "🛒 Продукты":            None,
    "🍕 Кафе":                None,
    "👧 София":               ["Школа", "Секции", "Одежда", "Развлечения"],
    "🏥 Здоровье":            ["Обследование", "Лечение", "Аптека"],
    "🧘 ЗОЖ":                 ["Спорт", "БАДы", "Терапия"],
    "🚗 Авто":                ["Бензин", "Мойка", "ТО", "Ремонт"],
    "🚕 Такси/парковки":      None,
    "✈️ Путешествия":         None,
    "✨ Спа/Уход":            None,
    "👗 Одежда":              None,
    "🏠 Дом":                 ["Благоустройство", "Ремонт"],
    "🎬 Развлечения":         None,
    "📚 Обучение":            None,
    "📱 Связь/VPN":           None,
    "📰 Подписки":            None,
    "🚨 Штрафы":              None,
    "🧾 Налоги":              None,
    "💳 Кредиты":             None,
    "🎁 Подарки":             None,
    "🧩 Другое":              None,
}

INCOME_TREE = {
    "💳 Зарплата":            None,
    "🏢 Див: Тушино":         None,
    "🔑 Див: Николь":         None,
    "🩺 Див: Клиника":        None,
    "🔙 Возврат":             None,
    "📈 Инвест":              None,
    "🎲 Случайно":            None,
    "🎁 Подарки":             None,
}

# Чтобы быстро получить список категорий и понять есть ли подкат
EXPENSE_CATS = list(EXPENSE_TREE.keys())
INCOME_CATS = list(INCOME_TREE.keys())


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
pending = {}  # entry_id -> dict с данными
_counter = [0]


def make_entry_id():
    _counter[0] += 1
    return str(_counter[0] % 10000)


def find_active_text_input(chat_id):
    for eid, entry in pending.items():
        if entry.get('chat_id') == chat_id and entry.get('awaiting_text_tags'):
            return eid
    return None


# ═══════════════════════════════════════════════════════════
# 5. УТИЛИТЫ ДЛЯ ТЕГОВ
# ═══════════════════════════════════════════════════════════
def get_all_tags_with_counts():
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
    counts = get_all_tags_with_counts()
    items = sorted(counts.items(), key=lambda x: x[1][0], reverse=True)
    return [tag for tag, _ in items[:limit]]


def build_tags_keyboard(entry_id):
    entry = pending.get(entry_id)
    if not entry:
        return None

    available = entry.get('available_tags', [])
    selected = entry.get('selected_tags', set())

    markup = types.InlineKeyboardMarkup(row_width=2)
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

    markup.row(
        types.InlineKeyboardButton("➕ Свой тег", callback_data=f"tgnew|{entry_id}"),
        types.InlineKeyboardButton("⏭ Пропустить", callback_data=f"tgskip|{entry_id}")
    )
    markup.row(
        types.InlineKeyboardButton("✅ Готово", callback_data=f"tgdone|{entry_id}")
    )
    return markup


def format_summary(entry, prompt_text=""):
    """Общий шаблон сводки текущей записи."""
    type_emoji = "💰" if entry['is_inc'] else "💸"
    type_word = "Доход" if entry['is_inc'] else "Расход"
    text = (
        f"{type_emoji} *{type_word}* · {entry['amount']} ₽\n"
        f"📅 {entry['date']}"
    )
    if entry.get('category'):
        text += f"\n📂 {entry['category']}"
    if entry.get('subcategory'):
        text += f" → {entry['subcategory']}"
    if entry.get('desc'):
        text += f"\n📝 _{entry['desc']}_"
    selected = entry.get('selected_tags', set())
    if selected:
        text += f"\n🏷 {', '.join(sorted(selected))}"
    if prompt_text:
        text += f"\n\n{prompt_text}"
    return text


# ═══════════════════════════════════════════════════════════
# 6. КОМАНДЫ
# ═══════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(message):
    help_text = (
        "👋 Привет! Я твой финансовый бот.\n\n"
        "*Как записать:*\n\n"
        "💸 `500 расход` — спросит категорию\n"
        "💸 `500 расход обед` — с описанием\n"
        "💸 `500 расход 12.05.26` — с датой\n"
        "💸 `500 расход 12.05.26 обед` — всё вместе\n\n"
        "💰 `30000 доход бонус`\n\n"
        "*Команды:*\n"
        "/balance — баланс\n"
        "/tags — все теги с суммами"
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
        bot.reply_to(message, f"Ошибка: {e}")


@bot.message_handler(commands=['tags'])
def cmd_tags(message):
    try:
        counts = get_all_tags_with_counts()
        if not counts:
            bot.reply_to(message, "🏷 Пока нет ни одного тега.")
            return
        items = sorted(counts.items(), key=lambda x: x[1][1], reverse=True)
        lines = ["🏷 *Твои теги:*\n"]
        for tag, (cnt, amount) in items:
            lines.append(f"• `{tag}` — {amount:,.0f} ₽ ({cnt} оп.)".replace(',', ' '))
        bot.reply_to(message, '\n'.join(lines), parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")


# ═══════════════════════════════════════════════════════════
# 7. ПАРСИНГ И НАЧАЛО
# ═══════════════════════════════════════════════════════════
def parse_message(text):
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
    chat_id = message.chat.id

    # Если ждём текстового ввода тегов
    active_eid = find_active_text_input(chat_id)
    if active_eid:
        handle_text_tags(message, active_eid)
        return

    if not any(w in message.text.lower() for w in ['расход', 'доход']):
        return

    start_entry(message)


def start_entry(message):
    amount, is_inc, date_to_save, desc = parse_message(message.text)

    if date_to_save == "future":
        bot.reply_to(message, "⚠️ Ошибка: дата ещё не наступила!")
        return

    if amount is None:
        bot.reply_to(
            message,
            "⚠️ Не понял. Пример: `500 расход обед`",
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
        'subcategory': '',
        'selected_tags': set(),
        'available_tags': [],
        'awaiting_text_tags': False,
        'chat_id': message.chat.id,
        'message_id': None,
    }

    show_category_picker(message.chat.id, entry_id)


def show_category_picker(chat_id, entry_id):
    """Показывает клавиатуру с категориями."""
    entry = pending[entry_id]
    cats = INCOME_CATS if entry['is_inc'] else EXPENSE_CATS
    prefix = "inc" if entry['is_inc'] else "exp"

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(c, callback_data=f"{prefix}|{entry_id}|{i}")
        for i, c in enumerate(cats)
    ]
    markup.add(*buttons)

    text = format_summary(entry, "Выбери категорию:")

    if entry.get('message_id'):
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=entry['message_id'],
                text=text,
                reply_markup=markup,
                parse_mode='Markdown'
            )
            return
        except Exception:
            pass

    sent = bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')
    entry['message_id'] = sent.message_id


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
            bot.answer_callback_query(call.id, "Запись устарела")
            return

        cats = INCOME_CATS if prefix == "inc" else EXPENSE_CATS
        tree = INCOME_TREE if prefix == "inc" else EXPENSE_TREE

        if cat_idx >= len(cats):
            bot.answer_callback_query(call.id, "Категория не найдена")
            return

        category = cats[cat_idx]
        entry['category'] = category
        bot.answer_callback_query(call.id)

        subcats = tree.get(category)
        if subcats:
            # Показать выбор подкатегории
            show_subcategory_picker(call.message.chat.id, entry_id, subcats)
        else:
            # Сразу к тегам
            show_tags_picker(call.message.chat.id, entry_id)

    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


def show_subcategory_picker(chat_id, entry_id, subcats):
    """Клавиатура с подкатегориями."""
    entry = pending[entry_id]

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(sc, callback_data=f"sub|{entry_id}|{i}")
        for i, sc in enumerate(subcats)
    ]
    markup.add(*buttons)
    # Управляющие
    markup.row(
        types.InlineKeyboardButton("⏭ Без подкатегории", callback_data=f"subskip|{entry_id}"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data=f"subback|{entry_id}")
    )

    text = format_summary(entry, "Выбери подкатегорию:")

    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=entry['message_id'],
            text=text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception:
        sent = bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')
        entry['message_id'] = sent.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith('sub|'))
def callback_subcategory(call):
    try:
        _, entry_id, sub_idx_str = call.data.split('|')
        sub_idx = int(sub_idx_str)

        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела")
            return

        tree = INCOME_TREE if entry['is_inc'] else EXPENSE_TREE
        subcats = tree.get(entry['category']) or []
        if sub_idx >= len(subcats):
            bot.answer_callback_query(call.id, "Не найдено")
            return

        entry['subcategory'] = subcats[sub_idx]
        bot.answer_callback_query(call.id)
        show_tags_picker(call.message.chat.id, entry_id)

    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('subskip|'))
def callback_sub_skip(call):
    try:
        _, entry_id = call.data.split('|')
        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела")
            return
        entry['subcategory'] = ''
        bot.answer_callback_query(call.id)
        show_tags_picker(call.message.chat.id, entry_id)
    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('subback|'))
def callback_sub_back(call):
    """Назад к выбору категории."""
    try:
        _, entry_id = call.data.split('|')
        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела")
            return
        entry['category'] = None
        entry['subcategory'] = ''
        bot.answer_callback_query(call.id)
        show_category_picker(call.message.chat.id, entry_id)
    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


# ═══════════════════════════════════════════════════════════
# 9. CALLBACK: РАБОТА С ТЕГАМИ
# ═══════════════════════════════════════════════════════════
def show_tags_picker(chat_id, entry_id):
    entry = pending[entry_id]
    entry['available_tags'] = get_top_tags(limit=10)

    markup = build_tags_keyboard(entry_id)
    text = format_summary(entry, "Выбери теги или нажми «Пропустить»:")

    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=entry['message_id'],
            text=text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception:
        sent = bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')
        entry['message_id'] = sent.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith('tg|'))
def callback_tag_toggle(call):
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

        markup = build_tags_keyboard(entry_id)
        text = format_summary(entry, "Выбери теги или нажми «Пропустить»:")
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('tgnew|'))
def callback_tag_new(call):
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
            "✏️ Напиши теги через запятую (без #):\n_отпуск, турция, безнал_",
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.reply_to(call.message, f"Ошибка: {e}")


def handle_text_tags(message, entry_id):
    entry = pending.get(entry_id)
    if not entry:
        return

    new_tags = [t.strip() for t in message.text.split(',') if t.strip()]
    new_tags = [t.lstrip('#').strip() for t in new_tags if t.lstrip('#').strip()]

    for t in new_tags:
        entry['selected_tags'].add(t)
        if t not in entry['available_tags']:
            entry['available_tags'].append(t)

    entry['awaiting_text_tags'] = False

    markup = build_tags_keyboard(entry_id)
    text = format_summary(entry, "Выбери теги или нажми «Готово»:")
    sent = bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    entry['message_id'] = sent.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith('tgskip|') or call.data.startswith('tgdone|'))
def callback_tag_finish(call):
    try:
        action, entry_id = call.data.split('|')
        entry = pending.get(entry_id)
        if not entry:
            bot.answer_callback_query(call.id, "Запись устарела")
            return

        if action == 'tgskip':
            tags_to_save = []
        else:
            tags_to_save = sorted(entry['selected_tags'])
        tags_str = ', '.join(tags_to_save)

        entry_type = "Доход" if entry['is_inc'] else "Расход"
        amount = entry['amount']
        date_val = entry['date']
        category = entry['category']
        subcategory = entry.get('subcategory', '')
        desc = entry['desc']

        # A:Дата | B:Тип | C:Категория | D:Описание | E:Сумма
        # F:Валюта | G:Источник | H:Теги | I:Подкатегория
        sheet.append_row([
            date_val,
            entry_type,
            category,
            desc,
            amount,
            '',          # Валюта
            '',          # Источник
            tags_str,    # Теги
            subcategory  # Подкатегория
        ])

        type_emoji = "💰" if entry['is_inc'] else "💸"
        confirm = (
            f"✅ Записано!\n\n"
            f"{type_emoji} {entry_type}\n"
            f"📅 {date_val}\n"
            f"📂 {category}"
        )
        if subcategory:
            confirm += f" → {subcategory}"
        confirm += f"\n💵 {amount} ₽"
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
# 10. HEALTH CHECK
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
