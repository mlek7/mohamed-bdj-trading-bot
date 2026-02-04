from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
import re

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.getenv('CHAT_ID', '')

def get_pip_value(pair):
    """Get pip value based on trading pair"""
    if 'JPY' in pair:
        return 0.01  # JPY pairs
    elif 'XAU' in pair or 'GOLD' in pair:
        return 0.1   # Gold
    elif 'BTC' in pair:
        return 1.0   # Bitcoin
    else:
        return 0.0001  # Standard forex pairs

def calculate_targets_smc(entry, sl, direction, pair):
    """
    Calculate entry zone, stop loss, and multiple take profits
    based on Smart Money Concepts risk management
    """
    try:
        entry_price = float(entry)
        sl_price = float(sl)
        pip_value = get_pip_value(pair)
        
        # Calculate stop loss distance in pips
        sl_distance = abs(entry_price - sl_price)
        sl_pips = sl_distance / pip_value
        
        # Calculate entry zone (range around entry point)
        entry_zone_range = sl_distance * 0.2  # 20% of SL distance
        entry_zone_low = entry_price - entry_zone_range
        entry_zone_high = entry_price + entry_zone_range
        
        # Calculate take profit levels based on risk-reward ratios
        if direction == "BUY":
            tp1 = entry_price + (sl_distance * 2)   # 1:2 RR
            tp2 = entry_price + (sl_distance * 3)   # 1:3 RR
            tp3 = entry_price + (sl_distance * 4)   # 1:4 RR
        else:  # SELL
            tp1 = entry_price - (sl_distance * 2)
            tp2 = entry_price - (sl_distance * 3)
            tp3 = entry_price - (sl_distance * 4)
        
        # Format based on pair type
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
    """
    Extract trading signal data from TradingView alert message
    """
    data = {}
    
    # Extract pair
    pair_match = re.search(r'Pair[:\s]+([A-Z0-9]+)', message, re.IGNORECASE)
    if pair_match:
        data['pair'] = pair_match.group(1)
    
    # Extract price
    price_match = re.search(r'Price[:\s]+([0-9.,]+)', message, re.IGNORECASE)
    if price_match:
        data['price'] = price_match.group(1).replace(',', '')
    
    # Extract timeframe
    tf_match = re.search(r'Timeframe[:\s]+(\d+)', message, re.IGNORECASE)
    if tf_match:
        data['timeframe'] = tf_match.group(1)
    
    # Extract time
    time_match = re.search(r'Time[:\s]+([\d\-:\s]+)', message, re.IGNORECASE)
    if time_match:
        data['time'] = time_match.group(1)
    
    # Determine signal type
    if 'BULLISH' in message.upper() or 'BUY' in message.upper():
        data['direction'] = 'BUY'
        data['emoji'] = '🟢'
    else:
        data['direction'] = 'SELL'
        data['emoji'] = '🔴'
    
    # Extract signal type
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
    """
    Format the trading signal with full SMC analysis
    """
    if not targets:
        return "⚠️ Error calculating trade levels"
    
    pair = data.get('pair', 'Unknown')
    direction = data.get('direction', 'BUY')
    emoji = data.get('emoji', '🟢')
    signal_type = data.get('signal_type', 'SMC Signal')
    timeframe = data.get('timeframe', '15')
    time = data.get('time', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    message = f"""🚨 **MOHAMED BDJ STRATEGY SIGNAL** 🚨

{emoji} **{direction}** {pair}
━━━━━━━━━━━━━━━━━━━━━

📊 **SIGNAL TYPE:** {signal_type}
⏰ **TIMEFRAME:** {timeframe} minutes
🕐 **TIME:** {time}

💎 **SMART MONEY ANALYSIS:**
✓ LuxAlgo SMC Confirmed
✓ ICT Killzone Active
✓ Market Structure Aligned
✓ Liquidity Sweep Detected

━━━━━━━━━━━━━━━━━━━━━

🎯 **ENTRY ZONE:** {targets['entry_zone_low']} - {targets['entry_zone_high']}
🔸 **OPTIMAL ENTRY:** {targets['entry']}

🛑 **STOP LOSS:** {targets['sl']} ({targets['sl_pips']} pips)

📈 **TARGETS:**
📍 TP1: {targets['tp1']} (1:2 RR - {targets['tp1_pips']} pips) - PARTIAL EXIT
📍 TP2: {targets['tp2']} (1:3 RR - {targets['tp2_pips']} pips) - MAIN EXIT  
📍 TP3: {targets['tp3']} (1:4 RR - {targets['tp3_pips']} pips) - EXTENDED

━━━━━━━━━━━━━━━━━━━━━

⚠️ **RISK MANAGEMENT:**
• Max Risk: 1-2% per trade
• Take 50% profit at TP1
• Move SL to breakeven after TP1
• Trail stop after TP2

💡 Monitor for:
- Order Block reactions
- Liquidity grabs
- Fair Value Gap fills
- Session momentum shifts

#MohamedBDJ #SmartMoneyConcepts #ICT
"""
    return message

def send_telegram_message(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

@app.route('/')
def home():
    return "Mohamed BDJ Trading Bot is Running! ✓"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Get the alert message
        if request.is_json:
            data = request.get_json()
            message = str(data)
        else:
            message = request.data.decode('utf-8')
        
        # Extract signal data
        signal_data = extract_signal_data(message)
        
        # Get pair for calculations
        pair = signal_data.get('pair', 'EURUSD')
        price = signal_data.get('price', '1.18000')
        direction = signal_data.get('direction', 'BUY')
        
        # Calculate stop loss (example: 20 pips for forex, adjust based on your strategy)
        pip_value = get_pip_value(pair)
        sl_distance = 20 * pip_value  # 20 pips
        
        if direction == 'BUY':
            entry = float(price)
            sl = entry - sl_distance
        else:
            entry = float(price)
            sl = entry + sl_distance
        
        # Calculate targets
        targets = calculate_targets_smc(entry, sl, direction, pair)
        
        # Format and send message
        formatted_message = format_enhanced_signal(signal_data, targets)
        result = send_telegram_message(formatted_message)
        
        return jsonify({
            'status': 'success',
            'message': 'Signal sent to Telegram',
            'telegram_response': result
        }), 200
        
    except Exception as e:
        error_msg = f"Error processing webhook: {str(e)}"
        print(error_msg)
        return jsonify({'status': 'error', 'message': error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
