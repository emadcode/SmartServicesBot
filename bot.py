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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 
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
    if str(user_id) in db:
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
# 3. نظام الترجمة والذكاء الاصطناعي الآمن 100%
# ==========================================
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

def ai_analyze_payment_receipt(message_text):
    phone_match = re.search(r'(01[0125]\d{8})', message_text)
    amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(جنيه|جـ|EGP|LE)?', message_text)
    
    extracted_amount = float(amount_match.group(1)) if amount_match else 0.0
    extracted_phone = phone_match.group(1) if phone_match else ""

    if not GEMINI_API_KEY:
        return {"valid": extracted_amount > 0, "amount": extracted_amount, "phone": extracted_phone}

    try:
        prompt = f"Analyze the following financial receipt/SMS notification text from Vodafone Cash, Orange Cash, or InstaPay. Extract the transaction details and return strictly a JSON object with keys: 'valid' (true/false), 'amount' (float number), 'phone' (string phone number if found). Text to analyze: {message_text}"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        response = requests.post(url, headers=headers, json=payload, timeout=4)
        if response.status_code == 200:
            result_json = response.json()
            ai_reply = result_json['candidates'][0]['content']['parts'][0]['text']
            clean_json_str = re.sub(r'```json|
