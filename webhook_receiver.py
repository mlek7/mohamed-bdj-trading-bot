from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
import re
import json

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
SUBSCRIBERS_FILE = 'subscribers.json'

# Load subscribers from file
def load_subscribers():
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

# Save subscribers to file  
def save_subscribers(subscribers):
    try:
        with open(SUBSCRIBERS_FILE, 'w') as f:
            json.dump(subscribers, f)
    except Exception as e:
        print(f"Error saving subscribers: {e}")

# Add subscriber
def add_subscriber(chat_id):
    subscribers = load_subscribers()
    if chat_id not in subscribers:
        subscribers.append(chat_id)
        save_subscribers(subscribers)
        return True
    return False

# Remove subscriber
def remove_subscriber(chat_id):
    subscribers = load_subscribers()
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        save_subscribers(subscribers)
        return True
    return False

def get_pip_value(pair):
    if 'JPY' in pair:
        return 0.01
    elif 'XAU' in pair or 'GOLD' in pair:
        return 0.1
    elif 'BTC' in pair:
        return 1.0
    else:
        return 0.0001

def calculate_targets_smc(entry, sl, direction, pair):
    try:
        entry_price = float(entry)
        sl_price = float(sl)
        pip_value = get_pip_value(pair)
        sl_distance = abs(entry_price - sl_price)
        sl_pips = sl_distance / pip_value
        entry_zone_range = sl_distance * 0.2
        entry_zone_low = entry_price - entry_zone_range
        entry_zone_high = entry_price + entry_zone_range
        if direction == "BUY":
            tp1 = entry_price + (sl_distance * 2)
            tp2 = entry_price + (sl_distance * 3)
            tp3 = entry_price + (sl_distance * 4)
        else:
            tp1 = entry_price - (sl_distance * 2)
            tp2 = entry_price - (sl_distance * 3)
            tp3 = entry_price - (sl_distance * 4)
        if 'JPY' in pair:
            decimals = 2
        elif 'XAU' in pair or 'GOLD' in pair:
            decimals = 1
        elif 'BTC' in pair:
            decimals = 0
        else:
            decimals = 5
        return {
            'entry_zone_low': round(entry_zone_low, decimals),
            'entry_zone_high': round(entry_zone_high, decimals),
            'entry': round(entry_price, decimals),
            'sl': round(sl_price, decimals),
            'tp1': round(tp1, decimals),
            'tp2': round(tp2, decimals),
            'tp3': round(tp3, decimals),
            'sl_pips': round(sl_pips, 1),
            'tp1_pips': round(sl_pips * 2, 1),
            'tp2_pips': round(sl_pips * 3, 1),
            'tp3_pips': round(sl_pips * 4, 1)
        }
    except:
        return None

def extract_signal_data(message):
    data = {}
    pair_match = re.search(r'Pair[:\s]+([A-Z0-9]+)', message, re.IGNORECASE)
    if pair_match:
        data['pair'] = pair_match.group(1)
    price_match = re.search(r'Price[:\s]+([0-9.,]+)', message, re.IGNORECASE)
    if price_match:
        data['price'] = price_match.group(1).replace(',', '')
    tf_match = re.search(r'Timeframe[:\s]+(\d+)', message, re.IGNORECASE)
    if tf_match:
        data['timeframe'] = tf_match.group(1)
    time_match = re.search(r'Time[:\s]+([\d\-:\s]+)', message, re.IGNORECASE)
    if time_match:
        data['time'] = time_match.group(1)
    if 'BULLISH' in message.upper() or 'BUY' in message.upper():
        data['direction'] = 'BUY'
        data['emoji'] = '🟢'
    else:
        data['direction'] = 'SELL'
        data['emoji'] = '🔴'
    if 'BOS' in message:
        data['signal_type'] = 'Break of Structure (BOS)'
    elif 'CHOCH' in message:
        data['signal_type'] = 'Change of Character (CHoCH)'
    elif 'OB' in message or 'ORDER BLOCK' in message.upper():
        data['signal_type'] = 'Order Block'
    elif 'FVG' in message or 'FAIR VALUE GAP' in message.upper():
        data['signal_type'] = 'Fair Value Gap'
    else:
        data['signal_type'] = 'SMC Signal'
    return data

def format_enhanced_signal(data, targets):
    if not targets:
        return "⚠️ Error calculating trade levels"
    pair = data.get('pair', 'Unknown')
    direction = data.get('direction', 'BUY')
    emoji = data.get('emoji', '🟢')
    signal_type = data.get('signal_type', 'SMC Signal')
    timeframe = data.get('timeframe', '15')
    time = data.get('time', datetime.now().strftime('%Y-%m-%d %H:%M'))
    return f"""🚨 **TRADING SIGNALS GR STRATEGY** 🚨\n{emoji} **{direction}** {pair}\n━━━━━━━━━━━━━━━\n📊 {signal_type}\n⏰ {timeframe}m | {time}\n💎 SMC ANALYSIS:\n✓ LuxAlgo SMC | ✓ ICT Killzone\n✓ Market Structure | ✓ Liquidity Sweep\n━━━━━━━━━━━━━━━\n🎯 ENTRY ZONE: {targets['entry_zone_low']}-{targets['entry_zone_high']}\n🔸 ENTRY: {targets['entry']}\n🛑 STOP LOSS: {targets['sl']} ({targets['sl_pips']} pips)\n📈 TARGETS:\n📍 TP1: {targets['tp1']} (1:2) PARTIAL\n📍 TP2: {targets['tp2']} (1:3) MAIN\n📍 TP3: {targets['tp3']} (1:4) EXTENDED\n━━━━━━━━━━━━━━━\n⚠️ RISK: 1-2% | 50% at TP1\nMove SL to BE after TP1 | Trail after TP2\n#TradingSignalsGR #SMC #ICT"""

def send_telegram_message(message, chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=5)
        return response.json()
    except Exception as e:
        print(f"Error sending to {chat_id}: {e}")
        return None

def broadcast_message(message):
    subscribers = load_subscribers()
    success_count = 0
    for chat_id in subscribers:
        if send_telegram_message(message, chat_id):
            success_count += 1
    return success_count
    return success_count

@app.route('/')
def home():
    return f"TRADING SIGNALS GR Bot Running! Subscribers: {len(load_subscribers())}"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if request.is_json:
            message = str(request.get_json())
        else:
            message = request.data.decode('utf-8')
        signal_data = extract_signal_data(message)
        pair = signal_data.get('pair', 'EURUSD')
        price = signal_data.get('price', '1.18000')
        direction = signal_data.get('direction', 'BUY')
        pip_value = get_pip_value(pair)
        sl_distance = 20 * pip_value
        if direction == 'BUY':
            entry = float(price)
            sl = entry - sl_distance
        else:
            entry = float(price)
            sl = entry + sl_distance
        targets = calculate_targets_smc(entry, sl, direction, pair)
        formatted_message = format_enhanced_signal(signal_data, targets)
        sent_count = broadcast_message(formatted_message)
        return jsonify({'status': 'success', 'sent_to': sent_count}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            text = update['message'].get('text', '')
            if text == '/start':
                add_subscriber(chat_id)
                send_telegram_message("✅ Welcome! You'll receive TRADING SIGNALS GR trading signals. Send /stop to unsubscribe.", chat_id)
            elif text == '/stop':
                remove_subscriber(chat_id)
                send_telegram_message("Unsubscribed. Send /start to resubscribe.", chat_id)
        return jsonify({'ok': True}), 200
    except:
        return jsonify({'ok': False}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
