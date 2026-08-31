import os
import telebot
import requests
import json
import urllib.parse
import uuid 
import re
import threading
import time
from flask import Flask, request
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# 1. إعدادات البوت والبيانات الأساسية
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8987750439:AAGqJCL6nrqaxXLlo8a9MEnuQM-WqpcRtbU")
PROVIDER_TOKEN = os.environ.get("PROVIDER_TOKEN", "bk_01M1709WVE7KVBQ1YY9BVM4KNN") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 
BASE_URL = "https://xprostore.store/api/v1"

ADMIN_ID = "1941469722"  # 👑 الـ ID الخاص بك
ADMIN_USERNAME = "@emadabdelhailm" 

PAYMENT_NUMBER = "01028835231"        # رقم المحفظة / إنستا باي

DOLLAR_PRICE_EGP = 50  
FIXED_PROFIT_EGP = 100 

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

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

active_pending_payments = {}
recent_incoming_receipts = []

# ==========================================
# 2. قاعدة البيانات الآمنة
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
# 3. مساعدات الذكاء الاصطناعي عبر Requests مباشرة
# ==========================================
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

def get_ai_service_image(service_name):
    n = service_name.lower()
    if 'netflix' in n:
        return "https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?q=80&w=800&auto=format&fit=crop"
    elif 'chatgpt' in n or 'gpt' in n or 'openai' in n:
        return "https://images.unsplash.com/photo-1677442136019-21780efad99a?q=80&w=800&auto=format&fit=crop"
    elif 'gemini' in n or 'جيميناي' in n or 'ai' in n:
        return "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=800&auto=format&fit=crop"
    elif 'canva' in n or 'تصميم' in n:
        return "https://images.unsplash.com/photo-1626785774573-4b799315345d?q=80&w=800&auto=format&fit=crop"
    elif 'shahid' in n or 'شاهد' in n or 'tv' in n:
        return "https://images.unsplash.com/photo-1593784991095-a205069470b6?q=80&w=800&auto=format&fit=crop"
    elif 'vpn' in n or 'حماية' in n:
        return "https://images.unsplash.com/photo-1563986768609-322da13575f3?q=80&w=800&auto=format&fit=crop"
    else:
        return "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop"

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

def ai_generate_offer_banner(service_name, old_price, new_price):
    if not GEMINI_API_KEY:
        return f"🔥 **عرض خاص لفترة محدودة!**\n\n🎯 الخدمة: {service_name}\n❌ السعر القديم: {old_price} جنيه\n💎 السعر الحالي: **{new_price} جنيه**"
    try:
        prompt = f"Design an attractive, professional promotional banner and description in Arabic with rich emojis for a special limited-time offer on '{service_name}'. Old price: {old_price} EGP, New promo price: {new_price} EGP."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        pass
    return f"🔥 **عرض خاص حصري!**\n\n🎯 الخدمة: {service_name}\n💎 السعر الجديد: **{new_price} جنيه**"

def ai_analyze_payment_receipt(message_text):
    phone_match = re.search(r'(01[0125]\d{8})', message_text)
    amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(جنيه|جـ|EGP|LE)?', message_text)
    
    extracted_amount = float(amount_match.group(1)) if amount_match else 0.0
    extracted_phone = phone_match.group(1) if phone_match else ""

    if not GEMINI_API_KEY:
        return {"valid": extracted_amount > 0, "amount": extracted_amount, "phone": extracted_phone}

    try:
        prompt = f"Analyze this incoming message text thoroughly. Extract strictly a JSON object with keys: valid (true/false if financial transfer), amount (float number), phone (string phone number). Text: {message_text}"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            ai_reply = response.json()['candidates'][0]['content']['parts'][0]['text']
            clean_reply = ai_reply.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_reply)
            if data.get('amount', 0) > 0:
                return data
    except:
        pass
    return {"valid": extracted_amount > 0, "amount": extracted_amount, "phone": extracted_phone}

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
        'welcome': "🌟 **مرحباً بك في متجرنا الرقمي الذكي المتكامل!**\n\n💎 استمتع بتجربة تسوق فريدة وخدمات رقمية فورية وآمنة 100%.\n\n👇 اختر ما يناسبك من القائمة أدناه:",
        'keys': "مفاتيح API 🔑", 'orders': "طلباتي 📦", 'services': "الخدمات والعروض الفورية 🛍️",
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
        'buy_btn': "💳 شراء فوري عبر API", 'back_btn': "🔙 رجوع للخلف",
        'account_info': "👤 **معلومات حسابك الشخصي:**\n\n🆔 رقم الحساب: `{}`\n💰 الرصيد المتاح: **{} {}**",
        'support_info': "💬 **للتواصل مع الدعم الفني:**\n\nالمسؤول: {}",
        'choose_cat': "🎨 **اختر القسم المطلوب استعراضه:**", 'available_serv': "✨ **اختر الخدمة المطلوبة:**",
        'details': "🎯 **الخدمة:** {}\n\n📝 **التفاصيل:**\n{}\n\n💎 **السعر النهائي:** **{} {}**\n🆔 **كود الخدمة:** `{}`"
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
        InlineKeyboardButton("⚙️ تعديل أسعار الخدمات المحلية", callback_data="adm_edit_prices_menu"),
        InlineKeyboardButton("🏷️ إنشاء وعرض خصم لخدمة (عبر AI)", callback_data="adm_create_offer"),
        InlineKeyboardButton("👥 المستخدمين والأرصدة الحالية", callback_data="adm_users_list"),
        InlineKeyboardButton("💼 فحص محفظة المتجر الأساسية (/wallet)", callback_data="adm_wallet"),
        InlineKeyboardButton("💰 شحن رصيد لمستخدم", callback_data="adm_add_balance"),
        InlineKeyboardButton("💸 إزالة رصيد من مستخدم", callback_data="adm_remove_balance")
    )
    bot.send_message(chat_id, "👑 **لوحة تحكم الأدمن الذكية:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def admin_callbacks(call):
    if str(call.message.chat.id) != str(ADMIN_ID): return
    action = call.data
    if action == 'adm_edit_prices_menu':
        bot.answer_callback_query(call.id)
        try:
            services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10).json().get('data', [])
            markup = InlineKeyboardMarkup(row_width=1)
            for s in services[:20]:
                s_id = str(s.get('id'))
                s_name = s.get('name_ar', s.get('name', 'خدمة'))
                current_p = CUSTOM_PRICES.get(s_id, int(float(s.get('rate', s.get('price', 0))) * DOLLAR_PRICE_EGP) + FIXED_PROFIT_EGP)
                markup.add(InlineKeyboardButton(f"✏️ {s_name} [{current_p} ج]", callback_data=f"edit_p_{s_id}"))
            bot.send_message(call.message.chat.id, "📌 **اختر الخدمة لتعديل سعرها محلياً:**", reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(call.message.chat.id, "⚠️ تعذر جلب الخدمات.")
    elif action == 'adm_create_offer':
        bot.answer_callback_query(call.id)
        try:
            services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10).json().get('data', [])
            markup = InlineKeyboardMarkup(row_width=1)
            for s in services[:15]:
                s_id = s.get('id')
                s_name = s.get('name_ar', s.get('name', 'خدمة'))
                markup.add(InlineKeyboardButton(f"🏷️ {s_name}", callback_data=f"offer_srv_{s_id}"))
            bot.send_message(call.message.chat.id, "📌 **اختر الخدمة لعمل عرض وتوقيت خاص لها:**", reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(call.message.chat.id, "⚠️ تعذر جلب الخدمات.")
    elif action == 'adm_users_list':
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_p_'))
def edit_price_selected(call):
    service_id = call.data.split('_')[2]
    msg = bot.send_message(call.message.chat.id, "💵 **أدخل السعر الجديد المخصص لهذه الخدمة (بالجنيه المصري):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: save_new_custom_price(m, service_id))

def save_new_custom_price(message, service_id):
    try:
        new_price = float(message.text.strip())
        CUSTOM_PRICES[str(service_id)] = new_price
        save_custom_prices(CUSTOM_PRICES)
        bot.send_message(ADMIN_ID, f"✅ **تم تحديث سعر الخدمة محلياً بنجاح إلى: {new_price} جنيه**", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "⚠️ قيمة غير صالحة.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('offer_srv_'))
def offer_service_selected(call):
    service_id = call.data.split('_')[2]
    msg = bot.send_message(call.message.chat.id, "💵 **أدخل السعر الجديد للعرض (بالجنيه):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: get_offer_price_step(m, service_id))

def get_offer_price_step(message, service_id):
    try:
        new_price = float(message.text.strip())
        msg = bot.send_message(message.chat.id, "⏱️ **أدخل مدة العرض بالساعات (مثلاً: 2):**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: finalize_offer_creation(m, service_id, new_price))
    except:
        bot.send_message(message.chat.id, "⚠️ قيمة غير صالحة.")

def finalize_offer_creation(message, service_id, new_price):
    try:
        hours = float(message.text.strip())
        expiry_timestamp = time.time() + (hours * 3600)
        
        active_offers[str(service_id)] = {
            "price": new_price,
            "expiry": expiry_timestamp
        }
        
        services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10).json().get('data', [])
        selected = next((s for s in services if str(s.get('id')) == str(service_id)), None)
        s_name = selected.get('name_ar', selected.get('name', 'خدمة')) if selected else "خدمة رقمية"
        old_price = CUSTOM_PRICES.get(str(service_id), 150)
        
        banner = ai_generate_offer_banner(s_name, old_price, new_price)
        final_announcement = f"{banner}\n\n⏳ **ينتهي العرض خلال:** {hours} ساعات!\n🛒 متوفر الآن في قسم الخدمات."
        
        db = load_db()
        for uid in db.keys():
            try:
                bot.send_message(int(uid), final_announcement, parse_mode="Markdown")
            except: pass
            
        bot.send_message(ADMIN_ID, "✅ **تم تفعيل العرض وتوليد واجهته وإرساله لكافة المستخدمين بنجاح!**", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "⚠️ خطأ في تحديد المدة الزمنية.")

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

def check_provider_wallet_call(message):
    try:
        res = requests.get(f"{BASE_URL}/me/wallet", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10).json()
        balance = res.get('data', {}).get('balance', '0')
        bot.send_message(message.chat.id, f"💼 رصيد محفظتك الأساسية لدى المزود: **{balance} $**", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ: {e}")

# ==========================================
# 6. العملة والإحالات والشحن
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'currency'))
def choose_currency_menu(message):
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🇪🇬 جنيه مصري (EGP)", callback_data="curr_EGP"),
        InlineKeyboardButton("🇺🇸 دولار أمريكي (USD)", callback_data="curr_USD")
    )
    bot.send_message(message.chat.id, "💱 **اختر العملة المفضلة:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('curr_'))
def set_currency_callback(call):
    curr = call.data.split('_')[1]
    set_user_currency(call.message.chat.id, curr)
    bot.answer_callback_query(call.id, f"✅ تم تغيير العملة إلى {curr}")
    bot.edit_message_text(f"✅ تم ضبط العملة بنجاح إلى: **{curr}**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

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
    curr = user.get('currency', 'EGP')
    bal = user['balance']
    if curr == 'USD':
        bal = round(bal / DOLLAR_PRICE_EGP, 2)

    if is_btn(message, 'account'):
        bot.send_message(message.chat.id, LANGS[lang]['account_info'].format(message.chat.id, bal, curr), parse_mode="Markdown")
    elif is_btn(message, 'support'):
        bot.send_message(message.chat.id, LANGS[lang]['support_info'].format(ADMIN_USERNAME), parse_mode="Markdown")
    elif is_btn(message, 'orders'):
        bot.send_message(message.chat.id, "📦 لا توجد طلبات سابقة مسجلة في حسابك عبر API.")
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
    expiry_time = time.time() + 300  # 5 دقائق مهلة
    
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

    text = f"⏳ **جاري انتظار وتأكيد التحويل...**\n\nقم بالتحويل الآن بقيمة `{data['amount']} جنيه` إلى الرقم الأزرق التالي:\n👉 **[01028835231](tel:01028835231)**\n\n📱 *رقم هاتفك المسجل:* `{sender_phone}`\n⏱️ *ملاحظة:* صالحة لمدة **5 دقائق فقط**."
    bot.send_message(user_id, text, parse_mode="Markdown")

@app.route('/w/6oo6rETS2B4Ws1KG7oXl', methods=['POST', 'GET'])
def payment_webhook():
    try:
        incoming_data = request.json if request.is_json else (request.form if request.form else {})
        message_text = " ".join([str(v) for v in incoming_data.values() if v]) if isinstance(incoming_data, dict) else str(incoming_data)
        
        ai_result = ai_analyze_payment_receipt(message_text)
        
        if ai_result.get('valid') == True:
            paid_amount = float(ai_result.get('amount', 0))
            sender_phone = str(ai_result.get('phone', ''))
            
            recent_incoming_receipts.append({"amount": paid_amount, "phone": sender_phone, "text": message_text})
            if len(recent_incoming_receipts) > 20: recent_incoming_receipts.pop(0)

            target_user_id = None
            current_time = time.time()
            
            for p_key, info in list(active_pending_payments.items()):
                if current_time > info['expiry']:
                    del active_pending_payments[p_key]
                    continue
                    
                amount_matched = abs(info['amount'] - paid_amount) < 1.0
                phone_matched = (sender_phone and info['phone'] in sender_phone) or (sender_phone == "")
                
                if amount_matched and phone_matched:
                    target_user_id = info['user_id']
                    del active_pending_payments[p_key]
                    break
            
            if target_user_id:
                update_balance(target_user_id, paid_amount)
                bot.send_message(target_user_id, f"🎉 **لقد استلمنا مبلغ {paid_amount} جنيه، وتمت إضافتها إلى رصيدك فوراً عبر API!**", parse_mode="Markdown")
                return {"status": "success"}, 200
                
        return {"status": "received_and_logged"}, 200
    except Exception as e:
        return {"status": "error"}, 200

# ==========================================
# 7. الأقسام والخدمات (تصميم شبكي مزدوج row_width=2 مريح للعين مع صور AI)
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'services'))
def list_categories(message):
    try:
        lang = get_user(message.chat.id)['lang']
        services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10).json().get('data', [])
        categories = {}
        for s in services:
            cat = s.get('category', {})
            cid = cat.get('id')
            if cid and cid not in categories: 
                c_name = get_name(cat, lang)
                categories[cid] = (c_name, get_service_icon(c_name))
        
        markup = InlineKeyboardMarkup(row_width=2)
        buttons = [InlineKeyboardButton(f"📁 {icon} {name}", callback_data=f"cat_{cid}") for cid, (name, icon) in categories.items()]
        markup.add(*buttons)
        
        bot.send_message(message.chat.id, "🎨 **اختر القسم المناسب لتصفح الخدمات:**", reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "⚠️ تعذر جلب الخدمات من API الأساسي حالياً.")

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_cats')
def back_to_categories(call):
    lang = get_user(call.message.chat.id)['lang']
    services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10).json().get('data', [])
    categories = {}
    for s in services:
        cat = s.get('category', {})
        cid = cat.get('id')
        if cid and cid not in categories:
            c_name = get_name(cat, lang)
            categories[cid] = (c_name, get_service_icon(c_name))
            
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(f"📁 {icon} {name}", callback_data=f"cat_{cid}") for cid, (name, icon) in categories.items()]
    markup.add(*buttons)
    
    bot.edit_message_text("🎨 **اختر القسم المناسب لتصفح الخدمات:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def show_services(call):
    cat_id, user_info = call.data.split('_')[1], get_user(call.message.chat.id)
    lang, curr = user_info['lang'], user_info.get('currency', 'EGP')
    services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10).json().get('data', [])
    
    markup = InlineKeyboardMarkup(row_width=2)
    service_buttons = []
    
    for s in services:
        if str(s.get('category', {}).get('id')) == str(cat_id):
            s_name = get_name(s, lang)
            s_id = str(s.get('id'))
            
            price_egp = CUSTOM_PRICES.get(s_id, int(float(s.get('rate', s.get('price', 0))) * DOLLAR_PRICE_EGP) + FIXED_PROFIT_EGP)
            if s_id in active_offers and time.time() < active_offers[s_id]['expiry']:
                price_egp = active_offers[s_id]['price']
                
            disp_price = price_egp if curr == 'EGP' else round(price_egp / DOLLAR_PRICE_EGP, 2)
            disp_curr = "جنية" if curr == 'EGP' else "$"
            
            icon = get_service_icon(s_name)
            if s_id in active_offers and time.time() < active_offers[s_id]['expiry']:
                icon = "🔥 " + icon

            btn_text = f"{icon} {s_name} | {disp_price} {disp_curr}"
            service_buttons.append(InlineKeyboardButton(btn_text, callback_data=f"srv_{s_id}"))
            
    markup.add(*service_buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_cats"))
    
    bot.edit_message_text("✨ **الخدمات المتاحة داخل هذا القسم (اختر خدمتك المفضلة):**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('srv_'))
def show_details(call):
    service_id, user_info = call.data.split('_')[1], get_user(call.message.chat.id)
    lang, curr = user_info['lang'], user_info.get('currency', 'EGP')
    services = requests.get(f"{BASE_URL}/services", headers={"Authorization": f"Bearer {PROVIDER_TOKEN}"}, timeout=10).json().get('data', [])
    selected = next((s for s in services if str(s.get('id')) == str(service_id)), None)
    
    if selected:
        price_egp = CUSTOM_PRICES.get(str(service_id), int(float(selected.get('rate', selected.get('price', 0))) * DOLLAR_PRICE_EGP) + FIXED_PROFIT_EGP)
        
        if str(service_id) in active_offers:
            if time.time() < active_offers[str(service_id)]['expiry']:
                price_egp = active_offers[str(service_id)]['price']
            else:
                del active_offers[str(service_id)]

        display_price = price_egp
        display_curr = "جنيه"
        if curr == 'USD':
            display_price = round(price_egp / DOLLAR_PRICE_EGP, 2)
            display_curr = "دولار"

        s_name = get_name(selected, lang)
        text = LANGS[lang]['details'].format(s_name, get_desc(selected, lang), display_price, display_curr, service_id)
        markup = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton(LANGS[lang]['buy_btn'], callback_data=f"buy_{service_id}_{price_egp}"),
            InlineKeyboardButton(LANGS[lang]['back_btn'], callback_data=f"cat_{selected.get('category', {}).get('id', '')}")
        )
        
        img_url = get_ai_service_image(s_name)
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        
        bot.send_photo(call.message.chat.id, img_url, caption=text, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 8. الشراء الفعلي عبر API
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_purchase(call):
    try:
        _, service_id, price_str = call.data.split('_')
        price_egp, user_id = float(price_str), call.message.chat.id
        user = get_user(user_id, call.from_user.username)
        
        if user['balance'] >= price_egp:
            bot.answer_callback_query(call.id, "⏳ جاري تنفيذ الطلب عبر API المزود...")
            
            headers = {
                "Authorization": f"Bearer {PROVIDER_TOKEN}", 
                "Content-Type": "application/json", 
                "Idempotency-Key": str(uuid.uuid4())
            }
            payload = {
                "service_id": str(service_id), 
                "quantity": 1
            }
            
            response = requests.post(f"{BASE_URL}/orders", headers=headers, json=payload, timeout=20)
            api_data = response.json()
            
            if response.status_code in [200, 201] or api_data.get('status') in [True, 'success']:
                update_balance(user_id, -price_egp)
                order_details = api_data.get('data', api_data)
                formatted_result = json.dumps(order_details, ensure_ascii=False, indent=2).replace('{', '').replace('}', '').replace('"', '')
                
                bot.send_message(user_id, f"🎉 **تم إتمام الطلب بنجاح عبر API الأساسي!**\n💰 خصم: {int(price_egp)} جنيه من رصيدك.\n\n📦 **تفاصيل التنفيذ:**\n`{formatted_result}`", parse_mode="Markdown")
            else:
                bot.send_message(user_id, "⚠️ عذراً، الخدمة غير متاحة حالياً من المزود، ولم يتم خصم أي مبلغ.")
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
