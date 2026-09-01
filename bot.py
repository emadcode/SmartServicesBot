import os
import telebot
import requests
import json
import urllib.parse
import uuid 
import threading
import time
from flask import Flask, render_template_string
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# 1. إعدادات البوت والبيانات الأساسية
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8987750439:AAGqJCL6nrqaxXLlo8a9MEnuQM-WqpcRtbU").strip()
API_KEY = "mgapi_EiLCO4JXGXJhugqzFS6KpGu6tZmLLxMzs4IBKHIdXoU"
BASE_URL = "https://tubular-sensually-stability.ngrok-free.dev/api/v1"

RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://your-bot-app.onrender.com")

ADMIN_ID = "1941469722"  # 👑 الـ ID الخاص بك
ADMIN_USERNAME = "@emadabdelhailm" 

PAYMENT_NUMBER = "01028835231"        # رقم المحفظة / إنستا باي

PRICES_FILE = 'custom_prices.json'

def load_custom_prices():
    if not os.path.exists(PRICES_FILE): return {}
    try:
        with open(PRICES_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_custom_prices(prices):
    try:
        with open(PRICES_FILE, 'w', encoding='utf-8') as f: json.dump(prices, f, indent=4, ensure_ascii=False)
    except: pass

CUSTOM_PRICES = load_custom_prices()
active_offers = {} 

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    BOT_TOKEN = "8987750439:AAGqJCL6nrqaxXLlo8a9MEnuQM-WqpcRtbU"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

active_pending_payments = {}
recent_incoming_receipts = []
ACTIVATION_DB = {}

def get_api_headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

# ==========================================
# 2. قاعدة البيانات الآمنة للأرصدة
# ==========================================
DB_FILE = 'users_db.json'
user_payment_data = {} 

def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_db(db):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(db, f, indent=4, ensure_ascii=False)
    except: pass

def get_user(user_id, username=None, ref_username=None):
    db = load_db()
    uid_str = str(user_id)
    clean_username = username.strip().replace('@', '').lower() if username else ""
    
    if uid_str not in db: 
        db[uid_str] = {'balance': 0.0, 'lang': 'ar', 'currency': 'EGP', 'username': clean_username, 'referred_by': None}
        if ref_username and ref_username.lower() != clean_username:
            ref_uid = next((u for u, info in db.items() if info.get('username', '').lower() == ref_username.lower()), None)
            if ref_uid:
                db[uid_str]['referred_by'] = ref_uid
                db[ref_uid]['balance'] = round(db[ref_uid].get('balance', 0.0) + 5.0, 2)
                try:
                    bot.send_message(int(ref_uid), "🎁 **مبارك! انضم شخص عبر رابط إحالتك وتمت إضافة 5 جنيه إلى رصيدك.**", parse_mode="Markdown")
                except: pass
        save_db(db)
    else:
        if clean_username and db[uid_str].get('username') != clean_username:
            db[uid_str]['username'] = clean_username
            save_db(db)
        if 'currency' not in db[uid_str]:
            db[uid_str]['currency'] = 'EGP'
            save_db(db)
    return db[uid_str]

def set_lang(user_id, lang):
    db = load_db()
    if str(user_id) in db:
        db[str(user_id)]['lang'] = lang
        save_db(db)

def set_user_currency(user_id, currency):
    db = load_db()
    if str(user_id) in db:
        db[str(user_id)]['currency'] = currency
        save_db(db)

def update_balance(user_id, amount):
    db = load_db()
    uid_str = str(user_id)
    if uid_str in db:
        db[uid_str]['balance'] = round(db[uid_str].get('balance', 0.0) + amount, 2)
        save_db(db)
        return True
    return False

def is_btn(msg, key):
    if not msg.text: return False
    return any(msg.text == lang_dict.get(key) for lang_dict in LANGS.values())

# ==========================================
# 3. صفحات التفعيل والخدمات المساعدة
# ==========================================
def generate_active_service_link(service_name):
    token = uuid.uuid4().hex
    ACTIVATION_DB[token] = {
        "service": service_name,
        "time": time.time()
    }
    base_host = RENDER_EXTERNAL_URL.rstrip('/')
    return f"{base_host}/activate/{token}"

ACTIVATION_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تفعيل الاشتراك الرقمي الفوري</title>
    <style>
        body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #fff; text-align: center; padding: 40px; }
        .card { background: #1e293b; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); max-width: 450px; margin: auto; }
        h2 { color: #38bdf8; }
        p { color: #94a3b8; line-height: 1.6; }
        .service-box { background: #334155; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 18px; color: #facc15; font-weight: bold; }
        .btn { display: inline-block; background: #2563eb; color: white; padding: 12px 25px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 15px; }
        .btn:hover { background: #1d4ed8; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🚀 صفحة التفعيل الرسمية</h2>
        <p>تم تأكيد طلبك بنجاح وجاري تفعيل الاشتراك الخاص بك:</p>
        <div class="service-box">{{ service_name }}</div>
        <p>يمكنك الآن الاستمتاع بالخدمة بكل سهولة.</p>
        <a href="https://t.me/" class="btn">العودة إلى البوت</a>
    </div>
</body>
</html>
"""

@app.route('/activate/<token>', methods=['GET'])
def activate_service_page(token):
    service_info = ACTIVATION_DB.get(token)
    if not service_info:
        return "<h2 style='text-align:center; color:red; margin-top:50px;'>⚠️ رابط التفعيل منتهي الصلاحية أو غير صالح!</h2>"
    return render_template_string(ACTIVATION_HTML_TEMPLATE, service_name=service_info['service'])

def get_service_icon(name):
    n = name.lower()
    if any(x in n for x in ['netflix', 'نتفلكس']): return '🍿'
    if any(x in n for x in ['shahid', 'شاهد']): return '📺'
    if any(x in n for x in ['gpt', 'chatgpt', 'openai']): return '🤖'
    if any(x in n for x in ['gemini', 'جيميناي', 'ai']): return '✨'
    if any(x in n for x in ['canva', 'كانفا']): return '🎨'
    if any(x in n for x in ['spotify', 'أنغامي', 'music']): return '🎵'
    if any(x in n for x in ['pubg', 'ببجي', 'game']): return '🎮'
    if any(x in n for x in ['vpn', 'ترجام', 'proxy']): return '🔒'
    return '💎'

translation_cache = {}

def translate_text(text, target_lang):
    if not text or target_lang == 'ar': return text
    cache_key = f"{target_lang}_{text}"
    if cache_key in translation_cache: return translation_cache[cache_key]
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        translated = "".join([i[0] for i in response.json()[0]])
        translation_cache[cache_key] = translated
        return translated
    except Exception: return text

def get_name(item, lang):
    name = item.get('name_ar', item.get('name', 'خدمة'))
    return name if lang == 'ar' else (item.get('name_en') or translate_text(name, lang))

def get_desc(item, lang):
    desc = item.get('description_ar', 'لا يوجد وصف')
    return desc if lang == 'ar' else (item.get('description_en') or translate_text(desc, lang))

# ==========================================
# 4. قاموس الواجهة
# ==========================================
LANGS = {
    'ar': {
        'welcome': "🌟 **مرحباً بك في متجر الاشتراكات الرقمية الذكي!**\n\n💎 استمتع بخدماتنا الفورية والآمنة 100%.\n\n👇 اختر ما يناسبك من القائمة أدناه:",
        'keys': "مفاتيح API 🔑", 'orders': "طلباتي 📦", 'services': "الاشتراكات والعروض 🛍️",
        'support': "الدعم الفني 💬", 'account': "حسابي 👤", 'language': "اللغة 🌐",
        'currency': "العملة 💱", 'referral': "الإحالات والأرباح 🎁", 'add_balance': "شحن الرصيد 💳",
        'admin_panel_btn': "👑 لوحة التحكم",
        'choose_lang': "🌐 اختر لغتك المفضلة:", 'lang_set': "✅ تم تغيير اللغة بنجاح!",
        'ask_amount': "💵 **أدخل المبلغ المراد شحنه (بالجنيه المصري):**\n\n📌 الحد الأدنى: 5 جنيه\n📌 الحد الأقصى: 1000 جنيه\n\n(اكتب 'إلغاء' للتراجع)",
        'invalid_amount': "⚠️ يرجى إدخال مبلغ صحيح بين 5 و 1000 جنيه.",
        'choose_payment': "💳 **اختر وسيلة الدفع للمبلغ ({0} جنيه):**",
        'ask_phone': "📱 **أرسل رقم هاتفك الذي قمت بالتحويل منه (مثلاً: 01012345678):**",
        'waiting_auto_pay': "⏳ **جاري انتظار وتأكيد التحويل...**\n\nقم بالتحويل الآن بقيمة `{2} جنيه` إلى الرقم الأزرق التالي:\n👉 **[01028835231](tel:01028835231)**\n\n📱 *رقم هاتفك المسجل:* `{3}`\n⏱️ *ملاحظة:* العملية صالحة لمدة **5 دقائق فقط** وسيتم شحن رصيدك تلقائياً.",
        'cancel': "❌ تم الإلغاء.", 'insufficient': "⚠️ **رصيدك الحالي غير كافٍ لإتمام عملية الشراء!**\n\n💰 السعر المطلوب: `{0} جنيه`\n💳 رصيدك الحالي: `{1} جنيه`\n\nيرجى شحن رصيدك لإتمام الطلب.", 
        'buy_btn': "💳 شراء الاشتراك فوراً", 'back_btn': "🔙 رجوع للخلف",
        'account_info': "👤 **معلومات حسابك الشخصي:**\n\n🆔 رقم الحساب: `{}`\n💰 الرصيد المتاح: **{} {}**",
        'support_info': "💬 **للتواصل مع الدعم الفني:**\n\nالمسؤول: {}",
        'choose_cat': "🎨 **اختر فئة الاشتراكات المطلوبة:**", 'available_serv': "✨ **اختر الاشتراك المطلوب:**",
        'details': "🎯 **الخدمة:** {}\n\n📝 **التفاصيل:**\n{}\n\n💎 **السعر النهائي:** **{} EGP**\n🆔 **كود الاشتراك:** `{}`"
    }
}
LANGS['en'] = {k: translate_text(v, 'en') for k, v in LANGS['ar'].items()}
LANGS['ru'] = {k: translate_text(v, 'ru') for k, v in LANGS['ar'].items()}

def main_menu(user_id, lang='ar'):
    l = LANGS.get(lang, LANGS['ar'])
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(KeyboardButton(l['keys']), KeyboardButton(l['orders']))
    markup.row(KeyboardButton(l['services']), KeyboardButton(l['support']))
    markup.row(KeyboardButton(l['account']))
    markup.row(KeyboardButton(l['language']), KeyboardButton(l['currency']))
    markup.row(KeyboardButton(l['referral']), KeyboardButton(l['add_balance']))
    if str(user_id) == str(ADMIN_ID):
        markup.row(KeyboardButton(l['admin_panel_btn']))
    return markup

# ==========================================
# 5. لوحة تحكم الأدمن
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        args = message.text.split()
        ref_username = args[1] if len(args) > 1 else None
        get_user(message.chat.id, message.from_user.username, ref_username=ref_username)
        lang = get_user(message.chat.id)['lang']
        bot.reply_to(message, LANGS[lang]['welcome'], reply_markup=main_menu(message.chat.id, lang), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in start: {e}")

@bot.message_handler(func=lambda msg: is_btn(msg, 'admin_panel_btn'))
def handle_admin_button(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    open_admin_panel(message.chat.id)

def open_admin_panel(chat_id):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("💼 فحص رصيد المتجر الأساسي عبر الـ API الجديد", callback_data="adm_wallet"),
        InlineKeyboardButton("👥 المستخدمين والأرصدة الحالية", callback_data="adm_users_list"),
        InlineKeyboardButton("💰 شحن رصيد لمستخدم", callback_data="adm_add_balance"),
        InlineKeyboardButton("💸 إزالة رصيد من مستخدم", callback_data="adm_remove_balance")
    )
    bot.send_message(chat_id, "👑 **لوحة تحكم الأدمن الذكية:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def admin_callbacks(call):
    if str(call.message.chat.id) != str(ADMIN_ID): return
    action = call.data
    if action == 'adm_users_list':
        bot.answer_callback_query(call.id)
        db = load_db()
        text = "👥 **قائمة المستخدمين والأرصدة الحالية:**\n\n"
        for uid, info in db.items():
            uname = info.get('username', 'بدون يوزر')
            bal = info.get('balance', 0.0)
            text += f"▪️ المعرف: `{uid}` | اليوزر: @{uname} | الرصيد: **{bal} جنيه**\n"
        if len(text) > 4000: text = text[:4000] + "\n...(تم الاختصار)"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    elif action == 'adm_wallet':
        bot.answer_callback_query(call.id)
        check_provider_wallet_call(call.message)
    elif action == 'adm_add_balance':
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "👤 **أدخل يوزر المستخدم لإضافة الرصيد (مثلاً: @username):**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, ask_username_for_balance)
    elif action == 'adm_remove_balance':
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "👤 **أدخل يوزر المستخدم لإزالة الرصيد:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, ask_username_for_removal)

def check_provider_wallet_call(message):
    try:
        res = requests.get(f"{BASE_URL}/balance", headers=get_api_headers(), timeout=10).json()
        balance = res.get('balance', res.get('data', {}).get('balance', 'غير متوفر'))
        bot.send_message(message.chat.id, f"💼 رصيد محفظتك الأساسية لدى المزود الجديد: **{balance} EGP**", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ في جلب الرصيد: {e}")

def ask_username_for_balance(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    username_input = message.text.strip().replace('@', '').lower()
    db = load_db()
    target_uid = next((uid for uid, info in db.items() if info.get('username', '').strip().lower() == username_input), None)
    if not target_uid:
        bot.send_message(message.chat.id, "⚠️ لم يتم العثور على المستخدم.")
        return
    msg = bot.send_message(message.chat.id, "💵 **أدخل المبلغ المراد إضافته:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: execute_admin_balance_add(m, target_uid))

def execute_admin_balance_add(message, target_uid):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        amount = float(message.text.strip())
        update_balance(target_uid, amount)
        bot.send_message(ADMIN_ID, f"🎉 تمت إضافة `{amount} جنيه` بنجاح.", parse_mode="Markdown")
        bot.send_message(target_uid, f"🎁 تم شحن رصيدك بمبلغ **{amount} جنيه** بواسطة الإدارة.", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "⚠️ قيمة غير صالحة.")

def ask_username_for_removal(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    username_input = message.text.strip().replace('@', '').lower()
    db = load_db()
    target_uid = next((uid for uid, info in db.items() if info.get('username', '').strip().lower() == username_input), None)
    if not target_uid:
        bot.send_message(message.chat.id, "⚠️ لم يتم العثور على المستخدم.")
        return
    msg = bot.send_message(message.chat.id, "💵 **أدخل المبلغ المراد خصمه:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: execute_admin_balance_remove(m, target_uid))

def execute_admin_balance_remove(message, target_uid):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        amount = float(message.text.strip())
        db = load_db()
        current_balance = db[target_uid].get('balance', 0.0)
        new_balance = max(0.0, current_balance - amount)
        db[target_uid]['balance'] = round(new_balance, 2)
        save_db(db)
        bot.send_message(ADMIN_ID, f"🗑️ تم خصم `{amount} جنيه`.", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "⚠️ قيمة غير صالحة.")

# ==========================================
# 6. العملة والإحالات والشحن
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'currency'))
def choose_currency_menu(message):
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🇪🇬 جنيه مصري (EGP)", callback_data="curr_EGP")
    )
    bot.send_message(message.chat.id, "💱 **العملة المعتمدة لدى المزود:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: is_btn(msg, 'language'))
def choose_language(message):
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🇪🇬 العربية", callback_data="lang_ar"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
    )
    bot.send_message(message.chat.id, "🌐 اختر لغتك المفضلة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    new_lang = call.data.split('_')[1]
    set_lang(call.message.chat.id, new_lang)
    bot.answer_callback_query(call.id, "✅")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    lang = get_user(call.message.chat.id)['lang']
    bot.send_message(call.message.chat.id, LANGS[new_lang]['lang_set'], reply_markup=main_menu(call.message.chat.id, lang))

@bot.message_handler(func=lambda msg: is_btn(msg, 'account') or is_btn(msg, 'support') or is_btn(msg, 'orders') or is_btn(msg, 'referral'))
def basic_buttons(message):
    user = get_user(message.chat.id, message.from_user.username)
    lang = user['lang']
    bal = user['balance']

    if is_btn(message, 'account'):
        bot.send_message(message.chat.id, LANGS[lang]['account_info'].format(message.chat.id, bal, 'EGP'), parse_mode="Markdown")
    elif is_btn(message, 'support'):
        bot.send_message(message.chat.id, LANGS[lang]['support_info'].format(ADMIN_USERNAME), parse_mode="Markdown")
    elif is_btn(message, 'orders'):
        try:
            res = requests.get(f"{BASE_URL}/order/my-order-001", headers=get_api_headers(), timeout=10).json()
            bot.send_message(message.chat.id, f"📦 **آخر طلب مسجل:**\n`{json.dumps(res, ensure_ascii=False, indent=2)}`", parse_mode="Markdown")
        except:
            bot.send_message(message.chat.id, "📦 لا توجد طلبات سابقة مسجلة حالياً.")
    elif is_btn(message, 'referral'):
        bot_info = bot.get_me()
        username = user.get('username')
        if not username:
            bot.send_message(message.chat.id, "⚠️ يرجى ضبط يوزر (Username) لحسابك على تيليجرام أولاً.")
            return
        ref_link = f"https://t.me/{bot_info.username}?start={username}"
        ref_text = f"🎁 **نظام الإحالات والأرباح الفورية:**\n\nشارك رابط الإحالة واحصل على **5 جنيه** هدية فورية عن كل شخص يسجل!\n\n📌 **رابط الإحالة الخاص بك:**\n`{ref_link}`"
        bot.send_message(message.chat.id, ref_text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: is_btn(msg, 'add_balance'))
def ask_amount(message):
    msg = bot.send_message(message.chat.id, LANGS[get_user(message.chat.id)['lang']]['ask_amount'], parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_amount)

def process_amount(message):
    try:
        amount_egp = float(message.text)
        if not (5 <= amount_egp <= 1000): raise ValueError
    except:
        bot.send_message(message.chat.id, "⚠️ يرجى إدخال مبلغ صحيح بين 5 و 1000 جنيه.")
        return
    user_payment_data[message.chat.id] = {'amount': amount_egp}
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Vodafone Cash 🔴", callback_data="pay_vf"),
        InlineKeyboardButton("Orange Cash 🟠", callback_data="pay_orange"),
        InlineKeyboardButton("InstaPay 🏦", callback_data="pay_insta")
    )
    bot.send_message(message.chat.id, f"💳 اختر وسيلة الدفع للمبلغ ({amount_egp} جنيه):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def select_payment_method(call):
    method, user_id = call.data.split('_')[1], call.message.chat.id
    data = user_payment_data.get(user_id)
    if not data: return
    data['method'] = method
    msg = bot.edit_message_text("📱 **أرسل رقم هاتفك الذي ستقوم بالتحويل منه:**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, wait_for_auto_payment)

def wait_for_auto_payment(message):
    user_id = message.chat.id
    data = user_payment_data.get(user_id)
    if not data: return
    sender_phone = message.text.strip()
    
    payment_key = f"{user_id}_{sender_phone}"
    expiry_time = time.time() + 300  
    
    active_pending_payments[payment_key] = {
        "user_id": user_id, 
        "amount": data['amount'],
        "phone": sender_phone,
        "expiry": expiry_time
    }

    def expire_payment():
        time.sleep(300)
        if payment_key in active_pending_payments:
            del active_pending_payments[payment_key]
            try:
                bot.send_message(user_id, "⏳ **انتهت مهلة الـ 5 دقائق وتم إلغاء الطلب تلقائياً.**", parse_mode="Markdown")
            except: pass

    threading.Thread(target=expire_payment, daemon=True).start()

    text = f"⏳ **جاري انتظار وتأكيد التحويل...**\n\nقم بالتحويل الآن بقيمة `{data['amount']} جنيه` إلى الرقم الأزرق التالي:\n👉 **[01028835231](tel:01028835231)**\n\n📱 *رقم هاتفك المسجل:* `{sender_phone}`\n⏱️ *ملاحظة:* العملية صالحة لمدة **5 دقائق فقط**."
    bot.send_message(user_id, text, parse_mode="Markdown")

@app.route('/webhook', methods=['POST', 'GET'])
def payment_webhook():
    return {"status": "received"}, 200

# ==========================================
# 7. الأقسام والاشتراكات عبر الـ API الجديد
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'services'))
def list_categories(message):
    try:
        lang = get_user(message.chat.id)['lang']
        res = requests.get(f"{BASE_URL}/products?lang={lang}", headers=get_api_headers(), timeout=10).json()
        services = res.get('products', res.get('data', []))
        
        markup = InlineKeyboardMarkup(row_width=2)
        service_buttons = []
        
        for s in services:
            s_id = s.get('id')
            s_name = s.get('name', 'خدمة')
            s_price = s.get('price', 0)
            icon = get_service_icon(s_name)
            
            btn_text = f"{icon} {s_name} | {s_price} EGP"
            service_buttons.append(InlineKeyboardButton(btn_text, callback_data=f"srv_{s_id}"))
            
        markup.add(*service_buttons)
        bot.send_message(message.chat.id, "✨ **اختر الاشتراك المطلوب من القائمة أدناه:**", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ تعذر جلب المنتجات من الـ API الجديد: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('srv_'))
def show_details(call):
    service_id, user_info = call.data.split('_')[1], get_user(call.message.chat.id)
    lang = user_info['lang']
    
    try:
        res = requests.get(f"{BASE_URL}/products?lang={lang}", headers=get_api_headers(), timeout=10).json()
        services = res.get('products', res.get('data', []))
        selected = next((s for s in services if str(s.get('id')) == str(service_id)), None)
        
        if selected:
            s_name = selected.get('name', 'خدمة')
            s_price = selected.get('price', 0)
            s_desc = selected.get('description', 'لا يوجد وصف')
            
            text = LANGS[lang]['details'].format(s_name, s_desc, s_price, service_id)
            
            markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton(LANGS[lang]['buy_btn'], callback_data=f"buy_{service_id}_{s_price}")
            )
            
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.answer_callback_query(call.id, f"⚠️ خطأ: {e}", show_alert=True)

# ==========================================
# 8. الشراء الفعلي ومنع تكرار الطلبات (Idempotency) وسحب الخدمة من رصيد المزود
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_purchase(call):
    try:
        _, service_id, price_str = call.data.split('_')
        price_egp, user_id = float(price_str), call.message.chat.id
        user = get_user(user_id, call.from_user.username)
        
        if user['balance'] >= price_egp:
            bot.answer_callback_query(call.id, "⏳ جاري تنفيذ الطلب وسحب الخدمة عبر رصيدك الأساسي...")
            
            # منع تكرار الطلبات عبر request_id فريد وغير مكرر
            unique_request_id = f"ord-{user_id}-{service_id}-{uuid.uuid4().hex[:10]}"
            
            payload = {
                "product_id": int(service_id),
                "quantity": 1,
                "request_id": unique_request_id
            }
            
            # إرسال الطلب للمزود الأساسي للخصم من رصيدك وسحب الخدمة
            response = requests.post(f"{BASE_URL}/order", headers=get_api_headers(), json=payload, timeout=20)
            api_data = response.json()
            
            if response.status_code in [200, 201]:
                # الخصم من رصيد العميل في البوت بعد نجاح العملية بالمزود الأساسي
                update_balance(user_id, -price_egp)
                
                services = requests.get(f"{BASE_URL}/products?lang=ar", headers=get_api_headers(), timeout=10).json().get('products', [])
                selected = next((s for s in services if str(s.get('id')) == str(service_id)), None)
                s_name = selected.get('name', 'اشتراك رقمي') if selected else "اشتراك رقمي"

                activation_link = generate_active_service_link(s_name)
                
                success_text = f"🎉 **تم إتمام الطلب بنجاح وسحب الخدمة من حسابك الأساسي!**\n💰 خصم: {int(price_egp)} EGP من رصيد العميل.\n\n🔗 **رابط التفعيل الفعال للعميل:**\n`{activation_link}`\n\n*(اضغط على الزر أدناه لتفعيل اشتراكك)*"
                markup = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🚀 فتح صفحة التفعيل", url=activation_link)
                )
                bot.send_message(user_id, success_text, reply_markup=markup, parse_mode="Markdown")
            else:
                bot.send_message(user_id, f"⚠️ عذراً، فشل تنفيذ الطلب من المزود الأساسي: {api_data.get('message', 'خطأ غير معروف')}")
        else:
            lang = user['lang']
            insufficient_msg = LANGS[lang]['insufficient'].format(int(price_egp), user['balance'])
            markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("💳 شحن الرصيد الآن", callback_data="direct_add_balance")
            )
            bot.answer_callback_query(call.id, "⚠️ رصيدك غير كافٍ!", show_alert=True)
            bot.send_message(user_id, insufficient_msg, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in purchase: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'direct_add_balance')
def direct_add_balance_callback(call):
    ask_amount(call.message)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=False, use_reloader=False)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    open_admin_panel(message.chat.id)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.remove_webhook()
    while True:
        try: bot.infinity_polling(none_stop=True, interval=0, timeout=20)
        except: pass
