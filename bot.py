import os
import telebot
import requests
import json
import urllib.parse
import uuid 
import re
import threading
from flask import Flask, request
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# 1. إعدادات البوت والبيانات الأساسية
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8987750439:AAGqJCL6nrqaxXLlo8a9MEnuQM-WqpcRtbU")
PROVIDER_TOKEN = os.environ.get("PROVIDER_TOKEN", "bk_01M1709WVE7KVBQ1YY9BVM4KNN") 
BASE_URL = "https://xprostore.store/api/v1"

ADMIN_ID = "1941469722"  # 👑 الـ ID الخاص بك
ADMIN_USERNAME = "@emadabdelhailm" 

PAYMENT_NUMBER = "01028835231"        # رقم فودافون كاش
ORANGE_NUMBER = "01285317443"        # رقم أورانج كاش
USDT_ADDRESS = "TYourUSDTWalletAddressTRC20Here" 

DOLLAR_PRICE_EGP = 50  
FIXED_PROFIT_EGP = 100 

CUSTOM_PRICES = {
    "13": 150,   
    "129": 200,  
    "130": 350
}

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

active_pending_payments = {}

# ==========================================
# 2. قاعدة البيانات
# ==========================================
DB_FILE = 'users_db.json'
user_payment_data = {} 

def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(db, f, indent=4, ensure_ascii=False)

def get_user(user_id, username=None):
    db = load_db()
    uid_str = str(user_id)
    clean_username = username.strip().replace('@', '') if username else ""
    
    if uid_str not in db: 
        db[uid_str] = {'balance': 0.0, 'lang': 'ar', 'username': clean_username}
        save_db(db)
    else:
        if clean_username and db[uid_str].get('username') != clean_username:
            db[uid_str]['username'] = clean_username
            save_db(db)
    return db[uid_str]

def set_lang(user_id, lang):
    db = load_db()
    db[str(user_id)]['lang'] = lang
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
# 3. نظام الترجمة
# ==========================================
translation_cache = {}

def translate_text(text, target_lang):
    if not text or target_lang == 'ar': return text
    cache_key = f"{target_lang}_{text}"
    if cache_key in translation_cache: return translation_cache[cache_key]
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
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
# 4. قاموس الواجهة الأساسية
# ==========================================
LANGS = {
    'ar': {
        'welcome': "أهلاً بك في متجرنا الرقمي! 🤖\nاستخدم القائمة بالأسفل للتنقل بحرية.",
        'keys': "مفاتيح API 🔑", 'orders': "طلباتي 📦", 'services': "الخدمات 🛍️",
        'support': "الدعم 💬", 'account': "حسابي 👤", 'language': "اللغة 🌐",
        'currency': "العملة 💱", 'referral': "الإحالات 🔒", 'add_balance': "إضافة رصيد 💳",
        'admin_panel_btn': "👑 لوحة التحكم",
        'choose_lang': "🌐 اختر لغتك:", 'lang_set': "✅ تم تغيير اللغة بنجاح!",
        'ask_amount': "💵 **أدخل المبلغ المراد شحنه (بالجنيه المصري):**\n\n⚠️ الحد الأدنى: 10 جنيه\n⚠️ الحد الأقصى: 1000 جنيه\n\n(اكتب 'إلغاء' للتراجع)",
        'invalid_amount': "⚠️ يرجى إدخال مبلغ صحيح بين 10 و 1000 جنيه.",
        'choose_payment': "💳 **اختر طريقة الدفع للمبلغ ({} جنيه):**",
        'ask_phone': "📱 **أرسل رقم هاتفك الذي ستُحول منه (مثلاً: 01012345678) لكي يقرأ النظام إشعار التحويل تلقائياً:**",
        'waiting_auto_pay': "⏳ **جارٍ انتظار قراءة إشعار التحويل (فودافون/أورانج/انستا باي)...**\n\nقم بالتحويل الآن بقيمة `{2} جنيه` إلى رقم **{0}** التالي:\n`{1}`\n\n📱 **رقم هاتفك المسجل:** `{3}`\n\n⚡ **ملاحظة:** بمجرد وصول رسالة التحويل لهاتفك، سيتم شحن رصيدك **فوراً تلقائياً**.",
        'cancel': "إلغاء ❌", 'insufficient': "⚠️ رصيدك غير كافٍ!", 
        'buy_btn': "💳 شراء الآن", 'back_btn': "🔙 رجوع",
        'account_info': "👤 **معلومات حسابك:**\n\n🆔 رقم الحساب: `{}`\n💰 الرصيد الحالي: **{} جنيه مصري**",
        'support_info': "💬 **للتواصل مع الدعم الفني:**\n\nتواصل معنا عبر الحساب: {}",
        'choose_cat': "🌟 **اختر القسم:**", 'available_serv': "📌 **الخدمات المتاحة:**",
        'details': "📌 **Service:** {}\n\n📝 **التفاصيل:**\n{}\n\n💰 **السعر:** {} جنيه\n🆔 **الكود:** {}"
    }
}
LANGS['en'] = {k: translate_text(v, 'en') for k, v in LANGS['ar'].items()}
LANGS['ru'] = {k: translate_text(v, 'ru') for k, v in LANGS['ar'].items()}
LANGS['en'].update({'keys': "API Keys 🔑", 'orders': "Orders 📦", 'services': "Services 🛍️", 'support': "Support 💬", 'account': "Account 👤", 'language': "Language 🌐", 'currency': "Currency 💱", 'referral': "Referrals 🔒", 'add_balance': "Add Balance 💳", 'admin_panel_btn': "👑 Admin Panel", 'cancel': "Cancel ❌", 'buy_btn': "💳 Buy Now", 'back_btn': "🔙 Back"})
LANGS['ru'].update({'keys': "API 🔑", 'orders': "Заказы 📦", 'services': "Услуги 🛍️", 'support': "Поддержка 💬", 'account': "Аккаунт 👤", 'language': "Язык 🌐", 'currency': "Валюта 💱", 'referral': "Рефералы 🔒", 'add_balance': "Пополнить 💳", 'admin_panel_btn': "👑 Админ-панель", 'cancel': "Отмена ❌", 'buy_btn': "💳 Купить", 'back_btn': "🔙 Назад"})

# ==========================================
# 5. الأيقونات والقوائم
# ==========================================
def get_icon(name):
    n = name.lower()
    if any(x in n for x in ['gpt', 'جيميناي', 'ai']): return '🤖'
    if any(x in n for x in ['canva', 'adobe']): return '🎨'
    if any(x in n for x in ['netflix', 'hbo']): return '🎬'
    return '🛒'

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
# 6. الأوامر الأساسية ولوحة تحكم الأدمن
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    get_user(message.chat.id, message.from_user.username)
    lang = get_user(message.chat.id)['lang']
    bot.reply_to(message, LANGS[lang]['welcome'], reply_markup=main_menu(message.chat.id, lang))

@bot.message_handler(func=lambda msg: is_btn(msg, 'admin_panel_btn'))
def handle_admin_button(message):
    if str(message.chat.id) != str(ADMIN_ID):
        bot.reply_to(message, "⚠️ عذراً، هذا الزر مخصص للإدارة فقط.")
        return
    open_admin_panel(message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_panel_command(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    open_admin_panel(message.chat.id)

def open_admin_panel(chat_id):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("📋 جلب قائمة الخدمات (/prices)", callback_data="adm_prices"),
        InlineKeyboardButton("💼 فحص محفظة المتجر (/wallet)", callback_data="adm_wallet"),
        InlineKeyboardButton("💰 شحن رصيد لمستخدم (بـ Username)", callback_data="adm_add_balance"),
        InlineKeyboardButton("💸 إزالة رصيد من مستخدم (بـ Username)", callback_data="adm_remove_balance")
    )
    bot.send_message(chat_id, "👑 **أهلاً بك في لوحة تحكم الأدمن المحمية:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def admin_callbacks(call):
    if str(call.message.chat.id) != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "⚠️ غير مسموح لك!", show_alert=True)
        return
        
    action = call.data
    
    if action == 'adm_prices':
        bot.answer_callback_query(call.id)
        get_all_services_for_admin_call(call.message)
    elif action == 'adm_wallet':
        bot.answer_callback_query(call.id)
        check_provider_wallet_call(call.message)
    elif action == 'adm_add_balance':
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "👤 **أدخل يوزر المستخدم لإضافة الرصيد (مثلاً: @username):**\n\n(اكتب 'إلغاء' للتراجع)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, ask_username_for_balance)
    elif action == 'adm_remove_balance':
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "👤 **أدخل يوزر المستخدم لإزالة الرصيد منه (مثلاً: @username):**\n\n(اكتب 'إلغاء' للتراجع)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, ask_username_for_removal)

def ask_username_for_balance(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    if message.text.strip() == 'إلغاء':
        bot.send_message(message.chat.id, "❌ تم الإلغاء.")
        return
    
    username_input = message.text.strip().replace('@', '').lower()
    db = load_db()
    target_uid = None
    for uid, info in db.items():
        if info.get('username', '').strip().lower() == username_input:
            target_uid = uid
            break
            
    if not target_uid:
        bot.send_message(message.chat.id, f"⚠️ لم يتم العثور على مستخدم باليوزر `@{username_input}`.", parse_mode="Markdown")
        return
        
    msg = bot.send_message(message.chat.id, f"✅ تم العثور على المستخدم!\n🆔 الآي دي: `{target_uid}`\n\n💵 **أدخل المبلغ المراد إضافته (بالجنيه):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: execute_admin_balance_add(m, target_uid))

def execute_admin_balance_add(message, target_uid):
    if str(message.chat.id) != str(ADMIN_ID): return
    try:
        amount = float(message.text.strip())
        success = update_balance(target_uid, amount)
        if success:
            bot.send_message(ADMIN_ID, f"🎉 **تمت إضافة الرصيد بنجاح!**\nأُضيفت `{amount} جنيه` إلى حساب المستخدم (`{target_uid}`).", parse_mode="Markdown")
            try:
                bot.send_message(target_uid, f"🎁 **تم شحن رصيدك من قبل الإدارة!**\n💰 تمت إضافة **{amount} جنيه** إلى حسابك.", parse_mode="Markdown")
            except: pass
        else:
            bot.send_message(ADMIN_ID, "⚠️ حدث خطأ أثناء تحديث الرصيد.")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ يرجى إدخال رقم صحيح للمبلغ.")

def ask_username_for_removal(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    if message.text.strip() == 'إلغاء':
        bot.send_message(message.chat.id, "❌ تم الإلغاء.")
        return
    
    username_input = message.text.strip().replace('@', '').lower()
    db = load_db()
    target_uid = None
    for uid, info in db.items():
        if info.get('username', '').strip().lower() == username_input:
            target_uid = uid
            break
            
    if not target_uid:
        bot.send_message(message.chat.id, f"⚠️ لم يتم العثور على مستخدم باليوزر `@{username_input}`.", parse_mode="Markdown")
        return
        
    current_balance = db[target_uid].get('balance', 0.0)
    msg = bot.send_message(message.chat.id, f"✅ تم العثور على المستخدم!\n🆔 الآي دي: `{target_uid}`\n💰 رصيده الحالي: `{current_balance} جنيه`\n\n💵 **أدخل المبلغ المراد خصمه/إزالته (بالجنيه):**", parse_mode="Markdown")
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
        
        bot.send_message(ADMIN_ID, f"🗑️ **تمت خصم/إزالة الرصيد بنجاح!**\nتم خصم `{amount} جنيه` وأصبح رصيد المستخدم الحالي: `{new_balance} جنيه`.", parse_mode="Markdown")
        try:
            bot.send_message(target_uid, f"⚠️ **تم خصم مبلغ من رصيدك بواسطة الإدارة!**\n💰 المبلغ المخصوم: **{amount} جنيه**\n📌 رصيدك الحالي: **{new_balance} جنيه**", parse_mode="Markdown")
        except: pass
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ يرجى إدخال رقم صحيح للمبلغ.")

def get_all_services_for_admin_call(message):
    bot.send_message(message.chat.id, "جاري سحب الخدمات (`GET /services`)... ⏳")
    try:
        services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}).json().get('data', [])
        text = "📋 **قائمة الخدمات المتوفرة لتسعيرها:**\n\n"
        for s in services:
            s_id = s.get('id')
            s_name = s.get('name_ar', s.get('name_en', 'خدمة'))
            s_price = float(s.get('rate', s.get('price', 0)))
            text += f"▪️ **{s_name}**\nالكود: `{s_id}` | الأصلي: {s_price}$\n〰️\n"
            if len(text) > 3500:
                bot.send_message(message.chat.id, text, parse_mode="Markdown")
                text = ""
        if text: bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except Exception as e: bot.send_message(message.chat.id, f"حدث خطأ: {e}")

def check_provider_wallet_call(message):
    bot.send_message(message.chat.id, "جاري فحص المحفظة (`GET /me/wallet`)... ⏳")
    try:
        response = requests.get(f"{BASE_URL}/me/wallet", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10)
        balance = response.json().get('data', {}).get('balance', 'غير معروف')
        text = f"💼 **رصيد محفظتك الأساسية في (X Pro Store):**\n\n💰 الرصيد المتاح: **{balance} $**"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except Exception as e: bot.send_message(message.chat.id, f"⚠️ خطأ: {e}")

@bot.message_handler(commands=['prices'])
def get_all_services_for_admin(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    get_all_services_for_admin_call(message)

@bot.message_handler(commands=['wallet'])
def check_provider_wallet(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    check_provider_wallet_call(message)

# ==========================================
# 7. التغيير اللغوي والأزرار العامة
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'language'))
def choose_language(message):
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🇪🇬 العربية", callback_data="lang_ar"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
    )
    bot.send_message(message.chat.id, "🌐 اختر لغتك / Choose Language / Выберите язык:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    new_lang = call.data.split('_')[1]
    set_language(call.message.chat.id, new_lang)
    bot.answer_callback_query(call.id, "✅")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    lang = get_user(call.message.chat.id, call.from_user.username)['lang']
    bot.send_message(call.message.chat.id, LANGS[new_lang]['lang_set'], reply_markup=main_menu(call.message.chat.id, lang))

@bot.message_handler(func=lambda msg: is_btn(msg, 'account') or is_btn(msg, 'support') or is_btn(msg, 'orders'))
def basic_buttons(message):
    user = get_user(message.chat.id, message.from_user.username)
    lang = user['lang']
    if is_btn(message, 'account'):
        formatted_balance = int(user['balance']) if user['balance'].is_integer() else user['balance']
        bot.send_message(message.chat.id, LANGS[lang]['account_info'].format(message.chat.id, formatted_balance), parse_mode="Markdown")
    elif is_btn(message, 'support'):
        bot.send_message(message.chat.id, LANGS[lang]['support_info'].format(ADMIN_USERNAME), parse_mode="Markdown")
    elif is_btn(message, 'orders'):
        bot.send_message(message.chat.id, "📦 No orders yet." if lang != 'ar' else "📦 لا توجد طلبات سابقة.")

# ==========================================
# 8. نظام الشحن التلقائي وقراءة إشعارات (فودافون/أورانج/انستا باي)
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'add_balance'))
def ask_amount(message):
    get_user(message.chat.id, message.from_user.username)
    lang = get_user(message.chat.id)['lang']
    msg = bot.send_message(message.chat.id, LANGS[lang]['ask_amount'], parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_amount)

def process_amount(message):
    lang = get_user(message.chat.id)['lang']
    if is_btn(message, 'cancel') or any(is_btn(message, k) for k in LANGS[lang].keys()):
        bot.send_message(message.chat.id, LANGS[lang]['cancel'], reply_markup=main_menu(message.chat.id, lang))
        return
    try:
        amount_egp = float(message.text)
        if not (10 <= amount_egp <= 1000): raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, LANGS[lang]['invalid_amount'])
        return

    user_payment_data[message.chat.id] = {'amount': amount_egp}
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Vodafone Cash 🔴", callback_data="pay_vf"),
        InlineKeyboardButton("Orange Cash 🟠", callback_data="pay_orange"),
        InlineKeyboardButton("InstaPay 🏦", callback_data="pay_insta")
    )
    bot.send_message(message.chat.id, LANGS[lang]['choose_payment'].format(amount_egp), reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def select_payment_method(call):
    method, user_id = call.data.split('_')[1], call.message.chat.id
    lang, data = get_user(user_id, call.from_user.username)['lang'], user_payment_data.get(user_id)
    if not data: return
    data['method'] = method

    msg = bot.edit_message_text(LANGS[lang]['ask_phone'], call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.register_next_step_handler(msg, wait_for_auto_payment)

def wait_for_auto_payment(message):
    user_id, lang = message.chat.id, get_user(message.chat.id, message.from_user.username)['lang']
    data = user_payment_data.get(user_id)
    if not data: return

    sender_phone = message.text.strip()
    data['phone'] = sender_phone

    active_pending_payments[sender_phone] = {
        "user_id": user_id,
        "amount": data['amount']
    }

    chosen_method = data.get('method', 'vf')
    if chosen_method == 'orange':
        wallet_name, target_wallet_num = "Orange Cash", ORANGE_NUMBER
    elif chosen_method == 'vf':
        wallet_name, target_wallet_num = "Vodafone Cash", PAYMENT_NUMBER
    else:
        wallet_name, target_wallet_num = "InstaPay", PAYMENT_NUMBER

    text = LANGS[lang]['waiting_auto_pay'].format(wallet_name, target_wallet_num, data['amount'], sender_phone)
    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=main_menu(user_id, lang))

@app.route('/w/6oo6rETS2B4Ws1KG7oXl', methods=['POST', 'GET'])
def payment_webhook():
    try:
        incoming_data = request.json if request.is_json else request.form
        message_text = incoming_data.get('message', '') or incoming_data.get('text', '') or str(incoming_data)
        
        if not message_text and request.data:
            message_text = request.data.decode('utf-8')

        # 🔍 استخراج رقم الهاتف والمبلغ من نص الإشعار الوارد بغض النظر عن طريقة صياغته
        phone_match = re.search(r'(01[0125]\d{8})', message_text)
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(جنيه|جـ|EGP|LE)?', message_text)

        if phone_match and amount_match:
            sender_phone = phone_match.group(1)
            paid_amount = float(amount_match.group(1))

            target_user_id = None
            for uid, info in active_pending_payments.items():
                # التحقق من تطابق رقم الهاتف أو قيمة المبلغ المعلق
                if info['amount'] == paid_amount or info.get('phone') == sender_phone:
                    target_user_id = info['user_id']
                    break

            if target_user_id:
                update_balance(target_user_id, paid_amount)
                lang = get_user(target_user_id)['lang']
                
                success_text = f"🎉 **تم قراءة إشعار التحويل بنجاح!**\n💰 تمت إضافة **{paid_amount} جنيه** إلى رصيدك فوراً."
                bot.send_message(target_user_id, success_text, parse_mode="Markdown")
                
                if sender_phone in active_pending_payments:
                    del active_pending_payments[sender_phone]
                    
                return {"status": "success", "message": "Balance updated via notification script"}, 200

        return {"status": "ignored", "message": "No matching payment pattern found"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# ==========================================
# 9. عرض الأقسام والخدمات
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'services'))
def list_categories(message):
    get_user(message.chat.id, message.from_user.username)
    lang = get_user(message.chat.id)['lang']
    msg_wait = bot.send_message(message.chat.id, "⏳ ...")
    try:
        markup = get_categories_markup(lang)
        bot.delete_message(message.chat.id, msg_wait.message_id)
        bot.send_message(message.chat.id, LANGS[lang]['choose_cat'], parse_mode="Markdown", reply_markup=markup)
    except: pass

def get_categories_markup(lang):
    services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}).json().get('data', [])
    categories = {}
    for s in services:
        cat = s.get('category', {})
        cid = cat.get('id')
        if cid and cid not in categories: categories[cid] = get_name(cat, lang)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(*[InlineKeyboardButton(f"{get_icon(v)} {v}", callback_data=f"cat_{k}") for k, v in categories.items()])
    return markup

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_cats')
def back_to_categories(call):
    lang = get_user(call.message.chat.id, call.from_user.username)['lang']
    try: bot.edit_message_text(LANGS[lang]['choose_cat'], call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=get_categories_markup(lang))
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def show_services(call):
    cat_id, lang = call.data.split('_')[1], get_user(call.message.chat.id, call.from_user.username)['lang']
    try:
        services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}).json().get('data', [])
        markup = InlineKeyboardMarkup(row_width=1)
        for s in services:
            if str(s.get('category', {}).get('id')) == str(cat_id):
                markup.add(InlineKeyboardButton(f"🛒 {get_name(s, lang)}", callback_data=f"srv_{s.get('id')}"))
        markup.add(InlineKeyboardButton(LANGS[lang]['back_btn'], callback_data="back_to_cats"))
        bot.edit_message_text(LANGS[lang]['available_serv'], call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('srv_'))
def show_details(call):
    service_id, lang = call.data.split('_')[1], get_user(call.message.chat.id, call.from_user.username)['lang']
    try:
        services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}).json().get('data', [])
        selected = next((s for s in services if str(s.get('id')) == str(service_id)), None)
        if selected:
            if str(service_id) in CUSTOM_PRICES:
                price_egp = CUSTOM_PRICES[str(service_id)]
            else:
                price_egp = int(float(selected.get('rate', selected.get('price', 0))) * DOLLAR_PRICE_EGP) + FIXED_PROFIT_EGP 
            
            text = LANGS[lang]['details'].format(get_name(selected, lang), get_desc(selected, lang), price_egp, service_id)
            markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton(LANGS[lang]['buy_btn'], callback_data=f"buy_{service_id}_{price_egp}"))
            
            cat_id = selected.get('category', {}).get('id', '')
            markup.add(InlineKeyboardButton(LANGS[lang]['back_btn'], callback_data=f"cat_{cat_id}" if cat_id else "back_to_cats"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except: pass

# ==========================================
# 10. الشراء الآلي الفوري
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_purchase(call):
    _, service_id, price_str = call.data.split('_')
    price_egp, user_id = float(price_str), call.message.chat.id
    user = get_user(user_id, call.from_user.username)
    lang = user['lang']
    
    if user['balance'] >= price_egp:
        bot.answer_callback_query(call.id, "⏳ جاري تنفيذ الطلب...")
        bot.edit_message_text("⏳ جاري التواصل مع الخادم... يرجى الانتظار.", call.message.chat.id, call.message.message_id)
        
        headers = {
            "Authorization": f"Bearer {PROVIDER_TOKEN}",
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid.uuid4())
        }
        payload = {
            "service_id": str(service_id),
            "quantity": 1
        }
        
        try:
            response = requests.post(f"{BASE_URL}/orders", headers=headers, json=payload, timeout=20)
            api_data = response.json()
            
            if response.status_code in [200, 201] or api_data.get('status') in [True, 'success']:
                update_balance(user_id, -price_egp) 
                
                order_details = api_data.get('data', api_data)
                formatted_result = json.dumps(order_details, ensure_ascii=False, indent=2).replace('{', '').replace('}', '').replace('"', '')
                
                msg_lang = "🎉 **تم إتمام الشراء بنجاح!**" if lang == 'ar' else "🎉 **Purchase Completed!**"
                bot.send_message(user_id, f"{msg_lang}\n💰 -{int(price_egp)} جنيه\n\n📦 **تفاصيل المنتج / Product Details:**\n`{formatted_result}`", parse_mode="Markdown")
            else:
                error_msg = api_data.get('message', 'خطأ في السيرفر الأساسي')
                err_lang = "⚠️ عذراً، الخدمة غير متاحة من المصدر." if lang == 'ar' else "⚠️ Service unavailable at source."
                bot.send_message(user_id, err_lang)
        except Exception as e:
            bot.send_message(user_id, "⚠️ حدث خطأ أثناء الاتصال بالسيرفر.")
    else:
        bot.answer_callback_query(call.id, LANGS[lang]['insufficient'], show_alert=True)

# ==========================================
# تشغيل السيرفر والبوت معاً
# ==========================================
def run_flask():
    port = int(os.environ.get("PORT", 8787))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    print("🚀 البوت يعمل الآن بكامل الميزات وبنظام قراءة سكريبت إشعارات المحافظ (فودافون/أورانج/انستا باي)...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    bot.remove_webhook()
    bot.infinity_polling()
