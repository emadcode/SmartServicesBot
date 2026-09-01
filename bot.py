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

PAYMENT_NUMBER = "01028835231"        # رقم المحفظة / إنستا باي

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

active_pending_payments = {}
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
    if any(x in n for x in ['capcut', 'كاب كات']): return '🎬'
    if any(x in n for x in ['vpn', 'في بي إن']): return '🛡️'
    if any(x in n for x in ['manus', 'ai']): return '✨'
    if any(x in n for x in ['creative', 'adobe', 'cloud']): return '🎨'
    if any(x in n for x in ['n8n', 'bot', 'automation']): return '⚡'
    if any(x in n for x in ['netflix', 'نتفلكس']): return '🍿'
    if any(x in n for x in ['shahid', 'شاهد']): return '📺'
    if any(x in n for x in ['gpt', 'chatgpt', 'openai']): return '🤖'
    return '🎁'

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
        'insufficient': "⚠️ **رصيدك الحالي غير كافٍ لإتمام عملية الشراء!**\n\n💰 السعر المطلوب: `{0} جنيه`\n💳 رصيدك الحالي: `{1} جنيه`",
        'buy_btn': "💳 شراء الاشتراك فوراً",
        'account_info': "👤 **معلومات حسابك الشخصي:**\n\n🆔 رقم الحساب: `{}`\n💰 الرصيد المتاح: **{} {}**",
        'support_info': "💬 **للتواصل مع الدعم الفني:**\n\nالمسؤول: {}",
        'details': "{} **{}**\n\n📝 **التفاصيل:**\n{}\n\n💎 **السعر النهائي:** **{} EGP**\n🆔 **كود الاشتراك:** `{}`"
    }
}
LANGS['en'] = LANGS['ar']
LANGS['ru'] = LANGS['ar']

def main_menu(user_id, lang='ar'):
    l = LANGS.get(lang, LANGS['ar'])
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(KeyboardButton(l['services']), KeyboardButton(l['orders']))
    markup.row(KeyboardButton(l['account']), KeyboardButton(l['referral']))
    markup.row(KeyboardButton(l['support']), KeyboardButton(l['add_balance']))
    if str(user_id) == str(ADMIN_ID):
        markup.row(KeyboardButton(l['admin_panel_btn']))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        get_user(message.chat.id, message.from_user.username)
        bot.reply_to(message, LANGS['ar']['welcome'], reply_markup=main_menu(message.chat.id), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in start: {e}")

@bot.message_handler(func=lambda msg: is_btn(msg, 'admin_panel_btn'))
def handle_admin_button(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    res = requests.get(f"{BASE_URL}/balance", headers=get_api_headers(), timeout=10).json()
    balance = res.get('balance', res.get('data', {}).get('balance', 'غير متوفر'))
    bot.send_message(message.chat.id, f"👑 **لوحة الأدمن:**\n💼 رصيد محفظتك الأساسية: **{balance} EGP**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: is_btn(msg, 'account') or is_btn(msg, 'support') or is_btn(msg, 'orders') or is_btn(msg, 'referral') or is_btn(msg, 'add_balance'))
def basic_buttons(message):
    user = get_user(message.chat.id, message.from_user.username)
    bal = user['balance']
    if is_btn(message, 'account'):
        bot.send_message(message.chat.id, LANGS['ar']['account_info'].format(message.chat.id, bal, 'EGP'), parse_mode="Markdown")
    elif is_btn(message, 'support'):
        bot.send_message(message.chat.id, LANGS['ar']['support_info'].format(ADMIN_USERNAME), parse_mode="Markdown")
    elif is_btn(message, 'orders'):
        bot.send_message(message.chat.id, "📦 لا توجد طلبات سابقة مسجلة حالياً.")
    elif is_btn(message, 'referral'):
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user.get('username', 'user')}"
        bot.send_message(message.chat.id, f"🎁 **نظام الإحالات:**\nشارك رابط الإحالة واحصل على مكافأة:\n`{ref_link}`", parse_mode="Markdown")
    elif is_btn(message, 'add_balance'):
        bot.send_message(message.chat.id, "💵 **لشحن الرصيد:**\nقم بتحويل المبلغ إلى فودافون كاش أو إنستا باي على الرقم:\n👉 `01028835231`\nثم ارسل إيصال التحويل للإدارة.", parse_mode="Markdown")

# ==========================================
# 5. عرض الخدمات بشكل طولي ومنظم (بدون تكرار)
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg, 'services'))
def list_categories(message):
    try:
        res = requests.get(f"{BASE_URL}/products?lang=ar", headers=get_api_headers(), timeout=10).json()
        services = []
        if isinstance(res, list): services = res
        elif isinstance(res, dict): services = res.get('products', res.get('data', res.get('items', [])))
        
        if not services:
            bot.send_message(message.chat.id, "⚠️ لا توجد خدمات متاحة حالياً.")
            return

        # فلترة وإزالة الخدمات المتكررة بناءً على اسم الخدمة والسعر
        seen_services = set()
        unique_services = []
        for s in services:
            name = (s.get('name') or s.get('title') or '').strip().lower()
            price = s.get('price') or s.get('rate') or 0
            identifier = f"{name}_{price}"
            if identifier not in seen_services:
                seen_services.add(identifier)
                unique_services.append(s)

        # إنشاء الأزرار بشكل عمودي طولي (زر واحد في كل صف) مطابق تماماً لشكل الصورة المطلوبة
        markup = InlineKeyboardMarkup(row_width=1)
        for s in unique_services:
            s_id = s.get('id') or s.get('product_id')
            s_name = s.get('name') or s.get('title') or 'خدمة'
            s_price = s.get('price') or s.get('rate') or 0
            stock = s.get('stock') or s.get('quantity') or 10
            
            icon = get_service_icon(s_name)
            # تنسيق النص تماماً مثل الصورة: الأيقونة | اسم الخدمة | السعر | الكمية
            btn_text = f"{icon}  {s_name} | {s_price} EGP | 🎁 {stock}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=f"srv_{s_id}"))
            
        bot.send_message(message.chat.id, "🛍️ **المنتجات المتاحة في المتجر:**", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطأ في جلب المنتجات: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('srv_'))
def show_details(call):
    service_id = call.data.split('_')[1]
    try:
        res = requests.get(f"{BASE_URL}/products?lang=ar", headers=get_api_headers(), timeout=10).json()
        services = []
        if isinstance(res, list): services = res
        elif isinstance(res, dict): services = res.get('products', res.get('data', res.get('items', [])))
            
        selected = next((s for s in services if str(s.get('id') or s.get('product_id')) == str(service_id)), None)
        
        if selected:
            s_name = selected.get('name') or selected.get('title') or 'خدمة'
            s_price = selected.get('price') or selected.get('rate') or 0
            s_desc = selected.get('description') or selected.get('desc') or 'لا يوجد وصف متاح.'
            icon = get_service_icon(s_name)
            
            text = LANGS['ar']['details'].format(icon, s_name, s_desc, s_price, service_id)
            markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton(LANGS['ar']['buy_btn'], callback_data=f"buy_{service_id}_{s_price}")
            )
            
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.answer_callback_query(call.id, f"⚠️ خطأ: {e}", show_alert=True)

# ==========================================
# 6. الشراء الفعلي ومنع التكرار وسحب الخدمة
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_purchase(call):
    try:
        parts = call.data.split('_')
        if len(parts) < 3: return
        service_id, price_str = parts[1], parts[2]
        price_egp, user_id = float(price_str), call.message.chat.id
        
        current_time = time.time()
        if user_id in recent_user_purchases and current_time - recent_user_purchases[user_id] < 5:
            bot.answer_callback_query(call.id, "⚠️ جاري معالجة طلبك السابق، يرجى الانتظار قليلاً.", show_alert=True)
            return
        recent_user_purchases[user_id] = current_time

        user = get_user(user_id, call.from_user.username)
        
        if user['balance'] >= price_egp:
            bot.answer_callback_query(call.id, "⏳ جاري تنفيذ الطلب وسحب الخدمة...")
            
            unique_request_id = f"ord-{user_id}-{service_id}-{uuid.uuid4().hex[:12]}"
            payload = {"product_id": int(service_id), "quantity": 1, "request_id": unique_request_id}
            
            response = requests.post(f"{BASE_URL}/order", headers=get_api_headers(), json=payload, timeout=20)
            api_data = response.json()
            
            if response.status_code in [200, 201]:
                update_balance(user_id, -price_egp)
                activation_link = generate_active_service_link(service_id)
                
                success_text = f"🎉 **تم إتمام الطلب بنجاح وسحب الخدمة من حسابك الأساسي!**\n💰 خصم: {int(price_egp)} EGP من رصيد العميل.\n\n🔗 **رابط التفعيل الفعال للعميل:**\n`{activation_link}`"
                markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 فتح صفحة التفعيل", url=activation_link))
                bot.send_message(user_id, success_text, reply_markup=markup, parse_mode="Markdown")
            else:
                bot.send_message(user_id, f"⚠️ عذراً، فشل تنفيذ الطلب من المزود: {api_data.get('message', 'خطأ غير معروف')}")
        else:
            insufficient_msg = LANGS['ar']['insufficient'].format(int(price_egp), user['balance'])
            bot.answer_callback_query(call.id, "⚠️ رصيدك غير كافٍ!", show_alert=True)
            bot.send_message(user_id, insufficient_msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in purchase: {e}")

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.remove_webhook()
    while True:
        try: bot.infinity_polling(none_stop=True, interval=0, timeout=20)
        except: pass
