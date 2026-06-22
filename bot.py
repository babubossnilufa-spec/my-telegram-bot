import os
import telebot
from telebot import types
import requests
import threading
import time
from urllib.parse import urlparse

# --- 1. CONFIGURATION ---
BOT_TOKEN = os.getenv('BOT_TOKEN', '8889798531:AAGi9QpH4PNaUZB5Jmo-qfQAbax3VK5XfXo') 
ADMIN_ID = int(os.getenv('ADMIN_ID', 7224420111))  

DATABASE_URL = os.getenv('DATABASE_URL')

# Checker Settings
CHECKER_URL = "http://ag-checker-api.site:8080/check/"
CHECKER_AUTH = os.getenv('CHECKER_AUTH', 'user6543')  
CHECKER_API_KEY = os.getenv('CHECKER_API_KEY', 'rR9vZsvYxfEenVUt')  

BASE_URL = 'https://api.durianrcs.com/out/ext_api'
TELEGRAM_PID = 257

bot = telebot.TeleBot(BOT_TOKEN)

user_hunting_state = {}
active_numbers_threads = {}
admin_states = {}
final_checker_states = {}  

def get_db_connection():
    if DATABASE_URL:
        import pg8000
        parsed = urlparse(DATABASE_URL)
        return pg8000.connect(
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:]
        )
    else:
        import sqlite3
        return sqlite3.connect('bot_users.db')

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                api_key TEXT
            )
        ''')
        
        cursor.execute('DELETE FROM users WHERE telegram_id = %s', (8726449159,))
        
        cursor.execute('SELECT telegram_id FROM users WHERE telegram_id = %s', (ADMIN_ID,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (telegram_id, username, api_key)
                VALUES (%s, %s, %s)
            ''', (ADMIN_ID, 'shuyaib890', 'TGhzcGtiWUVJbzA2R1QyY09sSGpTUT09'))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database Init Error: {e}")

init_db()

def get_user_credentials(tg_id):
    if int(tg_id) == int(ADMIN_ID):
        return {'username': 'tarek890', 'api_key': 'S0w5cjU3aGFUSzVROHlVcWVmd1FLUT09'}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, api_key FROM users WHERE telegram_id = %s', (tg_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return {'username': row[0], 'api_key': row[1]}
    except: pass
    return None

# --- 3. RAILWAY BYPASS NUMBER CHECKER ---
def check_number_status(phone_number):
    formatted_num = f"+{phone_number.replace('+', '').strip()}"
    payload = {
        "auth": CHECKER_AUTH,
        "api_key": CHECKER_API_KEY,
        "phone_numbers": [formatted_num]
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "close"  # Prevent thread hanging
    }
    
    try:
        # Tight timeout (2s) to prevent bot freeze in case Railway drops packet
        with requests.Session() as session:
            response = session.post(CHECKER_URL, json=payload, headers=headers, timeout=2).json()
            result_obj = response.get('result_obj', {})
            status = str(result_obj.get(formatted_num, result_obj.get(phone_number, 'unknown'))).upper().strip()
            
            if 'UNOCCUPIED' in status: return "✅"
            elif 'OCCUPIED' in status: return "🔐"
            elif 'BANNED' in status: return "🚫"
            else: return "⏳"
    except Exception as e:
        print(f"Railway Checker Blocked/Timeout: {e}")
        return "⏳"

def background_checker_updater(chat_id, clean_num, msg_id, cuy_flag, cuy_code):
    time.sleep(0.3)  
    check_status = check_number_status(clean_num)
    final_checker_states[clean_num] = check_status  
    try:
        interface_text = (
            f"**Rc Dhurian receiver**\n"
            f"🌍 Country: {cuy_flag} {cuy_code.upper()}\n"
            f"🚀 Number: `+{clean_num}`\n"
            f"🔎 Check: {check_status}\n"
            f"⏰ Status: `Waiting ⏳` (5:00)"
        )
        bot.edit_message_text(interface_text, chat_id, msg_id, parse_mode="Markdown", reply_markup=number_action_keyboard(clean_num))
    except: pass

def get_country_info(input_name):
    q = str(input_name).lower().strip().replace(' ', '')
    CMAP = {
        'argentinas': 'ar', 'argentina': 'ar', 'ar': 'ar', 'australia': 'au', 'au': 'au',
        'austria': 'at', 'at': 'at', 'bahrain': 'bh', 'bh': 'bh', 'brazil': 'br', 'br': 'br',
        'chile': 'cl', 'cl': 'cl', 'colombia': 'co', 'co': 'co', 'czechrepublic': 'cz', 'cz': 'cz',
        'ecuador': 'ec', 'ec': 'ec', 'finland': 'fi', 'fi': 'fi', 'france': 'fr', 'fr': 'fr',
        'germany': 'de', 'de': 'de', 'ghana': 'gh', 'gh': 'gh', 'hungary': 'hu', 'hu': 'hu',
        'india': 'in', 'in': 'in', 'indonesia': 'id', 'id': 'id', 'ireland': 'ie', 'ie': 'ie',
        'japan': 'jp', 'jp': 'jp', 'jordan': 'jo', 'jo': 'jo', 'kenya': 'ke', 'ke': 'ke',
        'luxembourg': 'lu', 'lu': 'lu', 'malaysia': 'my', 'my': 'my', 'mexico': 'mx', 'mx': 'mx',
        'netherlands': 'nl', 'nl': 'nl', 'nigeria': 'ng', 'ng': 'ng', 'norway': 'no', 'no': 'no',
        'panama': 'pa', 'pa': 'pa', 'philippines': 'ph', 'ph': 'ph', 'poland': 'pl', 'pl': 'pl',
        'portugal': 'pt', 'pt': 'pt', 'romania': 'ro', 'ro': 'ro', 'saudiarabia': 'sa', 'sa': 'sa',
        'singapore': 'sg', 'sg': 'sg', 'vietnam': 'vn', 'vietnam': 'vn', 'vn': 'vn', 'slovenia': 'si',
        'si': 'si', 'southafrica': 'za', 'za': 'za', 'spain': 'es', 'es': 'es', 'switzerland': 'ch',
        'ch': 'ch', 'thailand': 'th', 'th': 'th', 'unitedarabemirates': 'ae', 'uae': 'ae', 'ae': 'ae',
        'macedonia': 'mk', 'mk': 'mk', 'egypt': 'eg', 'eg': 'eg', 'unitedstates': 'us', 'usa': 'us',
        'us': 'us', 'elsalvador': 'sv', 'sv': 'sv', 'bolivia': 'bo', 'bo': 'bo', 'canada': 'ca',
        'ca': 'ca', 'myanmar': 'mm', 'mm': 'mm', 'bangladesh': 'bd', 'bd': 'bd', 'pakistan': 'pk',
        'pk': 'pk', 'russia': 'ru', 'ru': 'ru', 'honduras': 'hn', 'hn': 'hn', 'uk': 'gb', 'gb': 'gb'
    }
    FLAGS = {
        'ar': '🇦🇷', 'au': '🇦🇺', 'at': '🇦🇹', 'bh': '🇧🇭', 'br': '🇧🇷', 'cl': '🇨🇱', 'co': '🇨🇴',
        'cz': '🇨🇿', 'ec': '🇪🇨', 'fi': '🇫🇮', 'fr': '🇫🇷', 'de': '🇩🇪', 'gh': '🇬🇭', 'hu': '🇭🇺',
        'in': '🇮🇳', 'id': '🇮🇩', 'ie': '🇮🇪', 'jp': '🇯🇵', 'jo': '🇯🇴', 'ke': '🇰🇪', 'lu': '🇱🇺',
        'my': '🇲🇾', 'mx': '🇲🇽', 'nl': '🇳🇱', 'ng': '🇳🇬', 'no': '🇳🇴', 'pa': '🇵🇦', 'ph': '🇵🇭',
        'pl': '🇵🇱', 'pt': '🇵🇹', 'ro': '🇷🇴', 'sa': '🇸🇦', 'sg': '🇸🇬', 'vn': '🇻🇳', 'si': '🇸🇮',
        'za': '🇿🇦', 'es': '🇪🇸', 'ch': '🇨🇭', 'th': '🇹🇭', 'ae': '🇦🇪', 'mk': '🇲🇰', 'eg': '🇪🇬',
        'us': '🇺🇸', 'sv': '🇸🇻', 'bo': '🇧🇴', 'ca': '🇨🇦', 'mm': '🇲🇲', 'bd': '🇧🇩', 'pk': '🇵🇰',
        'ru': '🇷🇺', 'hn': '🇭🇳', 'gb': '🇬🇧'
    }
    if q in CMAP: code = CMAP[q]
    else: code = q[:2]
    flag = FLAGS.get(code, '🏳️‍🌈')
    return code, flag

def main_menu_keyboard(tg_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("💰 Balance"), types.KeyboardButton("🎯 Target"))
    markup.add(types.KeyboardButton("🌐 Country Stock"))
    if int(tg_id) == int(ADMIN_ID):
        markup.add(types.KeyboardButton("🛠 Admin Panel"))
    return markup

def admin_actions_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Add User", callback_data="admin_add"),
               types.InlineKeyboardButton("➖ Remove User", callback_data="admin_remove"))
    markup.add(types.InlineKeyboardButton("📋 View All Users", callback_data="admin_view"))
    return markup

def cancel_inline_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_admin_action"))
    return markup

def control_keyboard(is_paused=False):
    markup = types.InlineKeyboardMarkup()
    btn_toggle = types.InlineKeyboardButton("▶️ Resume" if is_paused else "⏸️ Pause", callback_data="resume_hunting") if is_paused else types.InlineKeyboardButton("⏸️ Pause", callback_data="pause_hunting")
    btn_stop = types.InlineKeyboardButton("⏹️ Stop", callback_data="stop_hunting")
    markup.add(btn_toggle, btn_stop)
    return markup

def number_action_keyboard(phone_number):
    clean_number = str(phone_number).replace("+", "").replace(" ", "").strip()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🔄 Release", callback_data=f"release_{clean_number}"),
               types.InlineKeyboardButton("🚫 Block", callback_data=f"block_{clean_number}"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    user_data = get_user_credentials(uid)
    if not user_data and uid != ADMIN_ID:
        bot.reply_to(message, "❌ Access Denied!")
        return
    bot.send_message(message.chat.id, "👋 Welcome! **Rc_Dhurian_receiver** session verified successfully.", parse_mode="Markdown", reply_markup=main_menu_keyboard(uid))

@bot.message_handler(func=lambda message: message.from_user.id in admin_states)
def admin_input_processor(message):
    uid = message.from_user.id
    step = admin_states[uid]['step']
    last_msg_id = admin_states[uid].get('msg_id')
    
    if step == 'add_id':
        try:
            target_id = int(message.text)
            admin_states[uid].update({'temp_id': target_id, 'step': 'add_username'})
            if last_msg_id:
                try: bot.delete_message(message.chat.id, last_msg_id)
                except: pass
            sent = bot.send_message(message.chat.id, "Step 2: Enter Durian Site `Username`:", parse_mode="Markdown", reply_markup=cancel_inline_keyboard())
            admin_states[uid]['msg_id'] = sent.message_id
        except: 
            bot.send_message(message.chat.id, "❌ Please enter a valid numerical Telegram ID.")
            
    elif step == 'add_username':
        admin_states[uid].update({'temp_user': message.text.strip(), 'step': 'add_key'})
        if last_msg_id:
            try: bot.delete_message(message.chat.id, last_msg_id)
            except: pass
        sent = bot.send_message(message.chat.id, "Step 3: Enter Durian Site `API Key`:", parse_mode="Markdown", reply_markup=cancel_inline_keyboard())
        admin_states[uid]['msg_id'] = sent.message_id
        
    elif step == 'add_key':
        if last_msg_id:
            try: bot.delete_message(message.chat.id, last_msg_id)
            except: pass
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (telegram_id, username, api_key) VALUES (%s, %s, %s)
            ''', (admin_states[uid]['temp_id'], admin_states[uid]['temp_user'], message.text.strip()))
            conn.commit(); cursor.close(); conn.close()
            bot.send_message(message.chat.id, "✅ User successfully added to the Cloud Database!")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Database Error: {e}")
        del admin_states[uid]
        
    elif step == 'remove_id':
        if last_msg_id:
            try: bot.delete_message(message.chat.id, last_msg_id)
            except: pass
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE telegram_id = %s', (int(message.text),))
            conn.commit(); cursor.close(); conn.close()
            bot.send_message(message.chat.id, "✅ User successfully removed from database.")
            del admin_states[uid]
        except: 
            bot.send_message(message.chat.id, "❌ Please enter a valid ID.")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    uid = message.from_user.id
    user_data = get_user_credentials(uid)
    
    if not user_data and uid != ADMIN_ID:
        bot.reply_to(message, "❌ Access Denied!")
        return

    if message.text == "🛠 Admin Panel" and uid == ADMIN_ID:
        bot.send_message(chat_id, "🔧 **Admin Panel:**", reply_markup=admin_actions_keyboard(), parse_mode="Markdown")
        
    elif message.text == "💰 Balance":
        target_url = f"{BASE_URL}/getUserInfo"
        credits = "Loading..."
        live_params = {'name': user_data['username'], 'ApiKey': user_data['api_key'], '_t': int(time.time())}
        try:
            response = requests.get(target_url, params=live_params, timeout=15).json()
            if str(response.get('code')) in ['200', '0']:
                res_data = response.get('data')
                credits = res_data.get('balance', res_data.get('money', res_data.get('score', 'Error'))) if isinstance(res_data, dict) else str(res_data)
            else: credits = f"Error ({response.get('msg', 'Bad Req')})"
        except: credits = "API Error"
        bot.send_message(chat_id, f"📊 **Overview**\n👤 User: {user_data['username']}\n💰 Bal: `{credits} credits`\n🏆 VIP Level: VIP2", parse_mode="Markdown")
        
    elif message.text == "🌐 Country Stock":
        bot.send_message(chat_id, "⏳ Loading Live Stock data...")
        try:
            res = requests.get(f"{BASE_URL}/getCountryPhoneNum", params={'name': user_data['username'], 'ApiKey': user_data['api_key'], 'pid': TELEGRAM_PID, 'vip': 'null'}, timeout=15).json()
            if str(res.get('code')) in ['200', '0']:
                stock_text = "🌐 **Live Country Stock**\n━━━━━━━━━━━━━━━━━━━━━\n"
                for c, count in res.get('data', {}).items():
                    c_code, c_flag = get_country_info(c)
                    stock_text += f"{c_flag} {c.upper()} (`{c_code}`): `{count} pcs`\n"
                bot.send_message(chat_id, stock_text, parse_mode="Markdown")
        except: bot.send_message(chat_id, "⚠️ API Response Timeout! Server is running slow.")

    elif message.text == "🎯 Target":
        if chat_id in user_hunting_state and user_hunting_state[chat_id].get("running"):
            bot.send_message(chat_id, "⚠️ **A target is already running!**\n\nClick **⏹️ Stop** below to terminate the previous one first.", parse_mode="Markdown")
            return
            
        user_hunting_state[chat_id] = {"waiting_for_country": True, "running": False, "paused": False}
        bot.send_message(chat_id, "🎯 Enter country codes separated by comma (e.g., sv,bo):")

    elif user_hunting_state.get(chat_id, {}).get("waiting_for_country"):
        input_text = message.text.strip()
        countries = [c.strip() for c in input_text.split(",") if c.strip()]
        
        session_token = str(time.time())
        user_hunting_state[chat_id].update({
            "waiting_for_country": False, "running": True, "paused": False, 
            "countries": countries, "req_count": 0, "got_count": 0, "session_token": session_token
        })
        
        display_countries = ""
        for c in countries:
            _, c_flag = get_country_info(c)
            display_countries += f"{c_flag} {c.upper()} "
            
        status_text = f"🎯 **Target Running (Multi)**\n🌍 {display_countries}\n📊 Req: 0 | Got: 0"
        control_msg = bot.send_message(chat_id, status_text, reply_markup=control_keyboard(is_paused=False))
        user_hunting_state[chat_id]["control_msg_id"] = control_msg.message_id
        
        threading.Thread(target=continuous_number_hunter, args=(chat_id, countries, user_data, session_token)).start()

def continuous_number_hunter(chat_id, countries, user_data, session_token):
    target_url = f"{BASE_URL}/getMobile"
    
    display_countries = ""
    for c in countries:
        _, c_flag = get_country_info(c)
        display_countries += f"{c_flag} {c.upper()} "
        
    last_update_time = 0  
        
    while chat_id in user_hunting_state:
        state = user_hunting_state[chat_id]
        if state.get("session_token") != session_token or not state.get("running"):
            break
        while state.get("paused"):
            if state.get("session_token") != session_token or not state.get("running"): break
            time.sleep(0.5)
            
        state["req_count"] += 1
        
        current_time = time.time()
        if current_time - last_update_time >= 3.0:
            try:
                bot.edit_message_text(f"🎯 **Target Running (Multi)**\n🌍 {display_countries}\n📊 Req: {state['req_count']} | Got: {state['got_count']}", chat_id, state["control_msg_id"], reply_markup=control_keyboard(is_paused=state.get("paused", False)))
                last_update_time = current_time
            except: pass

        for target_country in countries:
            if not state.get("running") or state.get("paused"):
                break
                
            cuy_code, cuy_flag = get_country_info(target_country)
            params = {'name': user_data['username'], 'ApiKey': user_data['api_key'], 'cuy': cuy_code, 'pid': TELEGRAM_PID, 'num': 1, 'noblack': 0, 'serial': 2}
            
            try:
                res = requests.get(target_url, params=params, timeout=3).json()
                if str(res.get('code')) in ['200', '0']:
                    state["got_count"] += 1
                    clean_num = str(res.get('data')).replace("+", "").replace(" ", "").strip()
                    
                    interface_text = (
                        f"**Rc Dhurian receiver**\n"
                        f"🌍 Country: {cuy_flag} {cuy_code.upper()}\n"
                        f"🚀 Number: `+{clean_num}`\n"
                        f"🔎 Check: ⏳\n"
                        f"⏰ Status: `Waiting ⏳` (5:00)"
                    )
                    sent_msg = bot.send_message(chat_id, interface_text, parse_mode="Markdown", reply_markup=number_action_keyboard(clean_num))
                    active_numbers_threads[clean_num] = True
                    final_checker_states[clean_num] = "⏳" 
                    
                    threading.Thread(target=background_checker_updater, args=(chat_id, clean_num, sent_msg.message_id, cuy_flag, cuy_code)).start()
                    threading.Thread(target=dedicated_otp_tab_thread, args=(chat_id, clean_num, target_country, sent_msg.message_id, user_data)).start()
            except: pass
            
            time.sleep(0.2)

def dedicated_otp_tab_thread(chat_id, phone_number, country_name, msg_id, user_data):
    sms_url, status_url = f"{BASE_URL}/getMsg", f"{BASE_URL}/getStatus"
    cuy_code, cuy_flag = get_country_info(country_name)
    common = {'name': user_data['username'], 'ApiKey': user_data['api_key'], 'pn': f"+{phone_number}", 'pid': TELEGRAM_PID}
    start_time = time.time()
    
    is_released_or_timeout = False
    
    while time.time() - start_time < 300 and active_numbers_threads.get(phone_number):
        rem = 300 - int(time.time() - start_time)
        chk_emoji = final_checker_states.get(phone_number, "⏳")

        try:
            status = str(requests.get(status_url, params=common, timeout=3).json().get('data', '')).lower()
            if "expire" in status or "timeout" in status:
                expired_text = (
                    f"**Rc Dhurian receiver**\n"
                    f"🌍 Country: {cuy_flag} {cuy_code.upper()}\n"
                    f"🔴 Number: `+{phone_number}`\n"
                    f"🔎 Check: {chk_emoji}\n"
                    f"⏰ Status: `Expired ⏰`"
                )
                bot.edit_message_text(expired_text, chat_id, msg_id, parse_mode="Markdown")
                is_released_or_timeout = True
                break
            elif "block" in status:
                blocked_text = (
                    f"**Rc Dhurian receiver**\n"
                    f"🌍 Country: {cuy_flag} {cuy_code.upper()}\n"
                    f"🚫 Number: `+{phone_number}`\n"
                    f"🔎 Check: {chk_emoji}\n"
                    f"⏰ Status: `Blocked 🚫`"
                )
                bot.edit_message_text(blocked_text, chat_id, msg_id, parse_mode="Markdown")
                is_released_or_timeout = True
                break
            
            res = requests.get(sms_url, params={'name': user_data['username'], 'ApiKey': user_data['api_key'], 'pn': f"+{phone_number}", 'pid': TELEGRAM_PID, 'serial': 2}, timeout=3).json()
            if str(res.get('code')) in ['200', '0']:
                success_text = (
                    f"**Rc Dhurian receiver**\n"
                    f"🌍 Country: {cuy_flag} {cuy_code.upper()}\n"
                    f"🟢 Number: `+{phone_number}`\n"
                    f"🔎 Check: {chk_emoji}\n"
                    f"📩 **OTP SMS:** `{res.get('data')}` ✨"
                )
                bot.edit_message_text(success_text, chat_id, msg_id, parse_mode="Markdown")
                is_released_or_timeout = True
                break
            else:
                waiting_text = (
                    f"**Rc Dhurian receiver**\n"
                    f"🌍 Country: {cuy_flag} {cuy_code.upper()}\n"
                    f"🚀 Number: `+{phone_number}`\n"
                    f"🔎 Check: {chk_emoji}\n"
                    f"⏰ Status: `Waiting ⏳` ({rem // 60}:{rem % 60:02d})"
                )
                bot.edit_message_text(waiting_text, chat_id, msg_id, parse_mode="Markdown", reply_markup=number_action_keyboard(phone_number))
        except: pass
        time.sleep(6)

    if not is_released_or_timeout and active_numbers_threads.get(phone_number):
        active_numbers_threads[phone_number] = False
        try: requests.get(f"{BASE_URL}/passMobile", params={'name': user_data['username'], 'ApiKey': user_data['api_key'], 'pn': f"+{phone_number}", 'pid': TELEGRAM_PID, 'serial': 2}, timeout=3)
        except: pass
        try:
            auto_release_text = (
                f"**Rc Dhurian receiver**\n"
                f"🌍 Country: {cuy_flag} {cuy_code.upper()}\n"
                f"⏰ Number: `+{phone_number}`\n"
                f"🔎 Check: ⏳\n"
                f"📊 Status: `Auto Released ⏳ (Timeout)`"
            )
            bot.edit_message_text(auto_release_text, chat_id, msg_id, parse_mode="Markdown")
        except: pass
    
    if phone_number in final_checker_states: del final_checker_states[phone_number]

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    uid = call.from_user.id
    user_data = get_user_credentials(uid)
    try: bot.answer_callback_query(call.id)
    except: pass

    if call.data == "admin_add" and uid == ADMIN_ID:
        sent = bot.send_message(chat_id, "Step 1: Enter the new user's `Telegram ID`:", parse_mode="Markdown", reply_markup=cancel_inline_keyboard())
        admin_states[uid] = {'step': 'add_id', 'msg_id': sent.message_id}
        
    elif call.data == "admin_remove" and uid == ADMIN_ID:
        sent = bot.send_message(chat_id, "Enter `Telegram ID` to remove:", parse_mode="Markdown", reply_markup=cancel_inline_keyboard())
        admin_states[uid] = {'step': 'remove_id', 'msg_id': sent.message_id}
        
    elif call.data == "cancel_admin_action" and uid == ADMIN_ID:
        if uid in admin_states: del admin_states[uid]
        try: bot.edit_message_text("🛑 User management process cancelled.", chat_id, call.message.message_id)
        except: pass

    elif call.data == "admin_view" and uid == ADMIN_ID:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id, username FROM users')
            users = cursor.fetchall()
            cursor.close(); conn.close()
            text = "📋 **User List:**\n" + "\n".join([f"ID: `{u[0]}` | User: `{u[1]}`" for u in users])
            bot.send_message(chat_id, text, parse_mode="Markdown")
        except: bot.send_message(chat_id, "❌ Error reading the database.")
        
    elif call.data == "stop_hunting":
        if chat_id in user_hunting_state:
            user_hunting_state[chat_id]["running"] = False
        try: bot.edit_message_text("🛑 Target Stopped Successfully.", chat_id, call.message.message_id)
        except: pass
        
    elif call.data == "pause_hunting":
        if chat_id in user_hunting_state:
            user_hunting_state[chat_id]["paused"] = True
        try: bot.edit_message_text("⏸️ Target Paused.", chat_id, call.message.message_id, reply_markup=control_keyboard(is_paused=True))
        except: pass
        
    elif call.data == "resume_hunting":
        if chat_id in user_hunting_state:
            user_hunting_state[chat_id]["paused"] = False
        try: bot.edit_message_text("🎯 Resuming Target...", chat_id, call.message.message_id, reply_markup=control_keyboard(is_paused=False))
        except: pass
        
    elif call.data.startswith("release_") and user_data:
        pn = call.data.split("_")[1]
        active_numbers_threads[pn] = False
        try: requests.get(f"{BASE_URL}/passMobile", params={'name': user_data['username'], 'ApiKey': user_data['api_key'], 'pn': f"+{pn}", 'pid': TELEGRAM_PID, 'serial': 2}, timeout=3)
        except: pass
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
    elif call.data.startswith("block_") and user_data:
        pn = call.data.split("_")[1]
        active_numbers_threads[pn] = False
        try: requests.get(f"{BASE_URL}/addBlack", params={'name': user_data['username'], 'ApiKey': user_data['api_key'], 'pn': f"+{pn}", 'pid': TELEGRAM_PID}, timeout=3)
        except: pass
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass

print("🔒 Premium Stable Bot with Fresh DB Setup is Live...")
bot.infinity_polling()
