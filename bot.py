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
BOT_TOKEN = "8987750439:AAGqJCL6nrqaxXLlo8a9MEnuQM-WqpcRtbU"
API_KEY = "mgapi_EiLCO4JXGXJhugqzFS6KpGu6tZmLLxMzs4IBKHIdXoU"
BASE_URL = "https://tubular-sensually-stability.ngrok-free.dev/api/v1"

RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://your-bot-app.onrender.com")

ADMIN_ID = "1941469722"  # 👑 الـ ID الخاص بك
ADMIN_USERNAME = "@emadabdelhailm" 
MAIN_BOT_LINK = "https://t.me/MGStore_bot"

PAYMENT_NUMBER = "01028835231"
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

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

user_payment_data = {}
admin_temp_state = {}
ACTIVATION_DB = {}
recent_user_purchases = {}

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

def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_db(db):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(db, f, indent=4, ensure_ascii=False)
    except: pass

def get_user(user_id, username=None):
    db = load_db()
    uid_str = str(user_id)
    clean_username = username.strip().replace('@', '').lower() if username else ""
    
    if uid_str not in db: 
        db[uid_str] = {'balance': 0.0, 'lang': 'ar', 'currency': 'EGP', 'username': clean_username}
        save_db(db)
    else:
        if clean_username and db[uid_str].get('username') != clean_username:
            db[uid_str]['username'] = clean_username
            save_db(db)
    return db[uid_str]

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
# 3. صفحات التفعيل وأيقونات الذكاء الاصطناعي
# ==========================================
def generate_active_service_link(service_name):
    token = uuid.uuid4().hex
    ACTIVATION_DB[token] = {"service": service_name, "time": time.time()}
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
    if any(x in n for x in ['gemini', 'جيميناي']): return '✨'
    if any(x in n for x in ['gpt', 'chatgpt', 'openai']): return '🤖'
    if any(x in n for x in ['claude', 'كلود']): return '🧠'
    if any(x in n for x in ['midjourney', 'ميدجورني']): return '🌌'
    if any(x in n for x in ['ai', 'ذكاء', 'manus']): return '🪄'
    if any(x in n for x in ['capcut', 'كاب كات']): return '🎬'
    if any(x in n for x in ['creative', 'adobe', 'cloud', 'canva', 'تصميم']): return '🎨'
    if any(x in n for x in ['n8n', 'bot', 'automation']): return '⚡'
    if any(x in n for x in ['vpn', 'في بي إن', 'express']): return '🛡️'
    if any(x in n for x in ['netflix', 'نتفلكس']): return '🍿'
    if any(x in n for x in ['shahid', 'شاهد']): return '📺'
    if any(x in n for x in ['spotify', 'أنغامي']): return '🎵'
    if any(x in n for x in ['pubg', 'ببجي', 'game']): return '🎮'
    return '💠'

# ==========================================
# 4. قاموس واجهة البوت
# ==========================================
LANGS = {
    'ar': {
        'welcome': "🌟 **مرحباً بك في متجر الاشتراكات الرقمية!**\n\n👇 اختر ما تحتاجه من القائمة أدناه:",
        'services': "🛍️ المنتجات", 'orders': "📦 طلباتي", 
        'account': "👤 حسابي", 'add_balance': "💳 شحن الرصيد",
        'admin_panel_btn': "👑 لوحة التحكم",
        'ask_amount': "💵 **أدخل المبلغ المراد شحنه (بالجنيه المصري):**",
        'ask_phone': "📱 **أرسل رقم هاتفك الذي قمت بالتحويل منه:**",
        'pay_instructions': "💳 **تعليمات شحن الرصيد:**\n\nقم بتحويل مبلغ `{0} جنيه` إلى رقم المحفظة التالي (اضغط للنسخ):\n👉 `{1}`\n\n📱 **رقم الهاتف المحول منه:** `{2}`\n\n⏳ *سيتم مراجعة التحويل وإضافة الرصيد فوراً.*",
        'insufficient': "⚠️ **رصيدك الحالي غير كافٍ!**\n\n💰 المطلوب: `{0} جنيه`\n💳 رصيدك: `{1} جنيه`",
        'buy_btn': "💳 شراء فوري",
        'account_info': "👤 **حسابك الشخصي:**\n\n🆔 المعرف: `{}`\n💰 الرصيد: **{} EGP**",
        'details': "{} **{}**\n\n📝 **التفاصيل:**\n{}\n\n📦 **المخزون:** `{}`\n💎 **السعر:** **{} EGP**"
    }
}

def main_menu(user_id, lang='ar'):
    l = LANGS.get(lang, LANGS['ar'])
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(KeyboardButton(l['services']), KeyboardButton(l['account']))
    markup.row(KeyboardButton(l['add_balance']), KeyboardButton(l['orders']))
    if str(user_id) == str(ADMIN_ID):
        markup.row(KeyboardButton(l['admin_panel_btn']))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.chat.id
        get_user(user_id, message.from_user.username)
        bot.reply_to(message, LANGS['ar']['welcome'], reply_markup=main_menu(user_id), parse_mode="Markdown")
    except Exception as e:
        print(f"Error: {e}")

# ==========================================
# 5. لوحة تحكم الأدمن الشاملة (تعديل الأسعار والأرصدة)
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'admin_panel_btn'))
def handle_admin_button(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    open_admin_panel(message.chat.id)

def open_admin_panel(chat_id):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("💼 فحص رصيد المزود الأساسي", callback_data="adm_wallet"),
        InlineKeyboardButton("👥 عرض المستخدمين والأرصدة", callback_data="adm_users_list"),
        InlineKeyboardButton("💰 شحن رصيد لمستخدم", callback_data="adm_add_balance"),
        InlineKeyboardButton("💸 خصم رصيد من مستخدم", callback_data="adm_remove_balance"),
        InlineKeyboardButton("✏️ تعديل أسعار الخدمات", callback_data="adm_edit_prices")
    )
    bot.send_message(chat_id, "👑 **لوحة تحكم الأدمن المتكاملة:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def admin_callbacks(call):
    if str(call.message.chat.id) != str(ADMIN_ID): return
    action = call.data
    
    if action == 'adm_wallet':
        bot.answer_callback_query(call.id)
        try:
            res = requests.get(f"{BASE_URL}/balance", headers=get_api_headers(), timeout=10).json()
            balance = res.get('balance', res.get('data', {}).get('balance', 'غير متوفر'))
            bot.send_message(call.message.chat.id, f"💼 رصيد محفظتك الأساسية لدى المزود: **{balance} EGP**", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"⚠️ خطأ: {e}")
            
    elif action == 'adm_users_list':
        bot.answer_callback_query(call.id)
        db = load_db()
        text = "👥 **قائمة المستخدمين والأرصدة:**\n\n"
        for uid, info in db.items():
            uname = info.get('username', 'بدون يوزر')
            bal = info.get('balance', 0.0)
            text += f"▪️ `{uid}` | @{uname} | **{bal} جنيه**\n"
        if len(text) > 4000: text = text[:4000] + "\n...(تم الاختصار)"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif action == 'adm_add_balance':
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "👤 **أدخل يوزر المستخدم لإضافة الرصيد (مثلاً: @username):**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, ask_username_for_balance)
        
    elif action == 'adm_remove_balance':
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "👤 **أدخل يوزر المستخدم لخصم الرصيد:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, ask_username_for_removal)

    elif action == 'adm_edit_prices':
        bot.answer_callback_query(call.id)
        try:
            res = requests.get(f"{BASE_URL}/products?lang=ar", headers=get_api_headers(), timeout=10).json()
            services = res if isinstance(res, list) else res.get('products', res.get('data', res.get('items', [])))
            markup = InlineKeyboardMarkup(row_width=1)
            for s in services:
                s_id = s.get('id') or s.get('product_id')
                s_name = s.get('name') or s.get('title') or 'خدمة'
                markup.add(InlineKeyboardButton(f" تعديل سعر: {s_name}", callback_data=f"price_edit_{s_id}"))
            bot.send_message(call.message.chat.id, "✏️ **اختر الخدمة المراد تعديل سعرها:**", reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"⚠️ خطأ في جلب الخدمات: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('price_edit_'))
def price_edit_callback(call):
    if str(call.message.chat.id) != str(ADMIN_ID): return
    service_id = call.data.split('_')[2]
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💵 **أدخل السعر الجديد بالجنيه (EGP):**", parse_mode="Markdown")
    admin_temp_state[call.message.chat.id] = {'edit_price_id': service_id}
    bot.register_next_step_handler(msg, save_new_service_price)

def save_new_service_price(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    state = admin_temp_state.get(message.chat.id)
    if not state: return
    try:
        new_price = float(message.text.strip())
        s_id = state['edit_price_id']
        CUSTOM_PRICES[str(s_id)] = new_price
        save_custom_prices(CUSTOM_PRICES)
        bot.send_message(message.chat.id, f"✅ تم تحديث سعر الخدمة (كود: {s_id}) إلى `{new_price} EGP` بنجاح.", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "⚠️ قيمة غير صالحة.")

def ask_username_for_balance(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    u_input = message.text.strip().replace('@', '').lower()
    db = load_db()
    target_uid = next((uid for uid, info in db.items() if info.get('username', '').strip().lower() == u_input), None)
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
        bot.send_message(ADMIN_ID, f"✅ تمت إضافة `{amount} جنيه` بنجاح.", parse_mode="Markdown")
        bot.send_message(int(target_uid), f"🎁 تم شحن رصيدك بمبلغ **{amount} جنيه** بواسطة الإدارة.", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "⚠️ قيمة غير صالحة.")

def ask_username_for_removal(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    u_input = message.text.strip().replace('@', '').lower()
    db = load_db()
    target_uid = next((uid for uid, info in db.items() if info.get('username', '').strip().lower() == u_input), None)
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
        db[target_uid]['balance'] = round(max(0.0, current_balance - amount), 2)
        save_db(db)
        bot.send_message(ADMIN_ID, f"✅ تم خصم `{amount} جنيه` بنجاح.", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "⚠️ قيمة غير صالحة.")

# ==========================================
# 6. شحن الرصيد والتفاعل السريع
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'add_balance'))
def ask_amount(message):
    msg_reply = bot.send_message(message.chat.id, LANGS['ar']['ask_amount'], parse_mode="Markdown")
    bot.register_next_step_handler(msg_reply, process_amount_step)

def process_amount_step(message):
    try:
        amount = float(message.text.strip())
        if amount <= 0: raise ValueError
        user_payment_data[message.chat.id] = {'amount': amount}
        msg = bot.send_message(message.chat.id, LANGS['ar']['ask_phone'], parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_phone_step)
    except:
        bot.send_message(message.chat.id, "⚠️ يرجى إدخال مبلغ صحيح.")

def process_phone_step(message):
    user_id = message.chat.id
    phone = message.text.strip()
    if user_id not in user_payment_data: return
    amount = user_payment_data[user_id]['amount']
    
    text = LANGS['ar']['pay_instructions'].format(amount, PAYMENT_NUMBER, phone)
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ تم التحويل", callback_data="pay_done"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == 'pay_done')
def pay_done_callback(call):
    bot.answer_callback_query(call.id, "✅ تم إرسال طلب الشحن للإدارة.")
    bot.edit_message_text("✅ **تم تسجيل طلب الشحن وفي انتظار المراجعة.**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: is_btn(msg, 'account') or is_btn(msg, 'orders'))
def basic_buttons(message):
    user = get_user(message.chat.id, message.from_user.username)
    if is_btn(message, 'account'):
        bot.send_message(message.chat.id, LANGS['ar']['account_info'].format(message.chat.id, user['balance']), parse_mode="Markdown")
    elif is_btn(message, 'orders'):
        bot.send_message(message.chat.id, "📦 لا توجد طلبات سابقة مسجلة.", parse_mode="Markdown")

# ==========================================
# 7. عرض الخدمات والمنتجات المخصصة
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'services'))
def list_categories(message):
    try:
        res = requests.get(f"{BASE_URL}/products?lang=ar", headers=get_api_headers(), timeout=10).json()
        services = res if isinstance(res, list) else res.get('products', res.get('data', res.get('items', [])))
        
        if not services:
            bot.send_message(message.chat.id, "⚠️ لا توجد منتجات متاحة حالياً.")
            return

        seen = set()
        unique_services = []
        for s in services:
            name = (s.get('name') or s.get('title') or '').strip().lower()
            s_id = str(s.get('id') or s.get('product_id'))
            price = CUSTOM_PRICES.get(s_id, s.get('price') or s.get('rate') or 0)
            ident = f"{name}_{price}"
            if ident not in seen:
                seen.add(ident)
                unique_services.append(s)

        markup = InlineKeyboardMarkup(row_width=1)
        for s in unique_services:
            s_id = str(s.get('id') or s.get('product_id'))
            s_name = s.get('name') or s.get('title') or 'خدمة'
            s_price = CUSTOM_PRICES.get(s_id, s.get('price') or s.get('rate') or 0)
            raw_stock = s.get('stock') if s.get('stock') is not None else s.get('quantity')
            stock = raw_stock if raw_stock is not None else '∞'
            
            icon = get_service_icon(s_name)
            btn_text = f"{icon} {s_name} | {s_price} EGP | 🎁 {stock}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=f"srv_{s_id}"))
            
        bot.send_message(message.chat.id, "🛍️ **اختر الخدمة المطلوبة:**", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطأ في الاتصال: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('srv_'))
def show_details(call):
    service_id = call.data.split('_')[1]
    try:
        res = requests.get(f"{BASE_URL}/products?lang=ar", headers=get_api_headers(), timeout=10).json()
        services = res if isinstance(res, list) else res.get('products', res.get('data', res.get('items', [])))
        selected = next((s for s in services if str(s.get('id') or s.get('product_id')) == str(service_id)), None)
        
        if selected:
            s_name = selected.get('name') or selected.get('title') or 'خدمة'
            s_price = CUSTOM_PRICES.get(str(service_id), selected.get('price') or selected.get('rate') or 0)
            s_desc = selected.get('description') or selected.get('desc') or 'لا يوجد وصف.'
            icon = get_service_icon(s_name)
            raw_stock = selected.get('stock') if selected.get('stock') is not None else selected.get('quantity')
            stock = raw_stock if raw_stock is not None else 'متاح'
            
            text = LANGS['ar']['details'].format(icon, s_name, s_desc, stock, s_price)
            
            markup = InlineKeyboardMarkup(row_width=1)
            if raw_stock is not None and str(raw_stock) == '0':
                markup.add(InlineKeyboardButton("❌ الكمية نفذت", callback_data="out_of_stock"))
            else:
                markup.add(InlineKeyboardButton(LANGS['ar']['buy_btn'], callback_data=f"buy_{service_id}_{s_price}"))
            
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.answer_callback_query(call.id, f"⚠️ خطأ: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'out_of_stock')
def handle_out_of_stock(call):
    bot.answer_callback_query(call.id, "⚠️ عذراً، الكمية نفذت.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_purchase(call):
    try:
        parts = call.data.split('_')
        if len(parts) < 3: return
        service_id, price_str = parts[1], parts[2]
        price_egp, user_id = float(price_str), call.message.chat.id
        
        current_time = time.time()
        if user_id in recent_user_purchases and current_time - recent_user_purchases[user_id] < 4:
            bot.answer_callback_query(call.id, "⚠️ جاري معالجة طلبك...", show_alert=True)
            return
        recent_user_purchases[user_id] = current_time

        user = get_user(user_id, call.from_user.username)
        
        if user['balance'] >= price_egp:
            bot.answer_callback_query(call.id, "⏳ جاري تنفيذ الطلب...")
            
            unique_request_id = f"ord-{user_id}-{service_id}-{uuid.uuid4().hex[:12]}"
            payload = {"product_id": int(service_id), "quantity": 1, "request_id": unique_request_id}
            
            response = requests.post(f"{BASE_URL}/order", headers=get_api_headers(), json=payload, timeout=20)
            api_data = response.json()
            
            if response.status_code in [200, 201]:
                update_balance(user_id, -price_egp)
                activation_link = generate_active_service_link(service_id)
                
                success_text = f"🎉 **تم الطلب بنجاح!**\n💰 تم خصم: {int(price_egp)} EGP\n\n🔗 **رابط التفعيل الفوري:**\n`{activation_link}`"
                markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 فتح صفحة التفعيل", url=activation_link))
                bot.send_message(user_id, success_text, reply_markup=markup, parse_mode="Markdown")
            else:
                err = api_data.get('message', 'خطأ غير معروف')
                bot.send_message(user_id, f"⚠️ فشل الطلب: `{err}`", parse_mode="Markdown")
        else:
            insufficient_msg = LANGS['ar']['insufficient'].format(int(price_egp), user['balance'])
            bot.answer_callback_query(call.id, "⚠️ رصيدك غير كافٍ!", show_alert=True)
            bot.send_message(user_id, insufficient_msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error: {e}")

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.remove_webhook()
    while True:
        try: bot.infinity_polling(none_stop=True, interval=0, timeout=20)
        except: pass
