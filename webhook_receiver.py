from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
CHAT_ID = os.getenv('CHAT_ID', '')

def calculate_targets(entry, sl, direction):
    try:
        entry = float(entry)
        sl = float(sl)
        sl_distance = abs(entry - sl)
        if direction == "BUY":
            tp1 = entry + (sl_distance * 2)
            tp2 = entry + (sl_distance * 3)
            tp3 = entry + (sl_distance * 4)
        else:
            tp1 = entry - (sl_distance * 2)
            tp2 = entry - (sl_distance * 3)
            tp3 = entry - (sl_distance * 4)
        return tp1, tp2, tp3, sl_distance
    except:
        return None, None, None, None

def format_signal(data):
    case_emoji = {"CASE 1": "⚡", "CASE 2": "⭐", "CASE 3": "🔥", "CASE 4": "💎"}
    case = data.get('case', 'CASE 1')
    emoji = case_emoji.get(case.split(' - ')[0], "📊")
    entry = data.get('entry', 'N/A')
    sl = data.get('sl', 'N/A')
    direction = data.get('direction', 'BUY')
    tp1, tp2, tp3, sl_dist = calculate_targets(entry, sl, direction)
    if tp1:
        tp1_str = f"{tp1:.5f}"
        tp2_str = f"{tp2:.5f}"
        tp3_str = f"{tp3:.5f}"
        sl_dist_str = f"{sl_dist * 10000:.1f}"
    else:
        tp1_str = tp2_str = tp3_str = "Calculate manually"
        sl_dist_str = "N/A"
    confluences = data.get('confluences', 2)
    if confluences == 2:
        risk_msg = "• Recommended risk: 0.5-1% of account"
    elif confluences == 3:
        risk_msg = "• Recommended risk: 1-1.5% of account"
    elif confluences == 4:
        risk_msg = "• Recommended risk: 1.5% of account ⭐ HIGH PROBABILITY"
    else:
        risk_msg = "• Recommended risk: 1.5-2% of account 🔥 PREMIUM SETUP"
    message = f"""
{emoji} **MOHAMED BDJ STRATEGY SIGNAL** {emoji}

**{case}**
Confluences: {confluences}

━━━━━━━━━━━━━━━━━━━━━━
**INSTRUMENT:** {data.get('pair', 'N/A')}
**TIMEFRAME:** {data.get('timeframe', 'M15')}
**DIRECTION:** {direction} {'🟢' if direction == 'BUY' else '🔴'}

━━━━━━━━━━━━━━━━━━━━━━
**ENTRY ZONE:** {entry}
**STOP LOSS:** {sl} ({sl_dist_str} pips)

**TARGETS:**
📍 TP1: {tp1_str} (1:2) - PARTIAL EXIT
📍 TP2: {tp2_str} (1:3) - MAIN EXIT
📍 TP3: {tp3_str} (1:4) - EXTENDED

━━━━━━━━━━━━━━━━━━━━━━
**COMPONENTS ALIGNED:**
{' + '.join(data.get('components', ['LQ', 'BOS']))}

**SESSION:** {data.get('session', 'KILL ZONE')} ⏰
**TIME:** {data.get('time', datetime.now().strftime('%H:%M:%S'))}

━━━━━━━━━━━━━━━━━━━━━━
**RISK MANAGEMENT:**
{risk_msg}

{data.get('note', '')}

━━━━━━━━━━━━━━━━━━━━━━
📊 Based on Mohamed BDJ's framework
    """
    return message

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        print(f"Received: {data}")
        message = format_signal(data)
        result = send_telegram(message)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Mohamed BDJ Bot Running'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
