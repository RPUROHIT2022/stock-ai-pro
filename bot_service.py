
import os
import time
import requests
import pandas as pd
from scanner import scan_stocks

# --- CONFIGURATION ---
# Users must replace these with their own details
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" 
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# Check if environment variables exist (for Cloud deployment security)
if os.environ.get("TG_TOKEN"):
    TELEGRAM_BOT_TOKEN = os.environ.get("TG_TOKEN")
if os.environ.get("TG_CHAT_ID"):
    TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram_message(message):
    """
    Sends a message to the configured Telegram chat.
    """
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Telegram Token not set. Skipping alert.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            print("✅ Telegram Alert Sent!")
        else:
            print(f"⚠️ Failed to send Telegram: {resp.text}")
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")

def run_bot_service():
    """
    Main loop for the background worker.
    """
    print("🤖 Telegram Bot Service Started...")
    send_telegram_message("🤖 **Trading Bot Started!** Monitoring markets...")
    
    while True:
        try:
            print(f"⏳ Scanning Market at {time.strftime('%H:%M:%S')}...")
            
            # 1. Run Scan
            results = scan_stocks()
            trades = results.get('ALL_TRADES', [])
            
            if trades:
                # 2. Filter for High Quality Trades
                message = f"🚨 **TRADING ALERTS ({len(trades)})** 🚨\n\n"
                
                count = 0
                for t in trades:
                    # Only alert if Signal is Strong (or at least valid)
                    if t['Signal'] != "NEUTRAL":
                        emoji = "🟢" if "BUY" in t['Signal'] else "🔴"
                        msg_chunk = (
                            f"{emoji} **{t['Stock']}**\n"
                            f"Signal: {t['Signal']}\n"
                            f"Price: {t['CMP']}\n"
                            f"Strategy: {t['Strategy']}\n"
                            f"Link: [Chart](https://in.tradingview.com/chart/?symbol=NSE:{t['Stock']})\n"
                            f"-------------------\n"
                        )
                        message += msg_chunk
                        count += 1
                        
                        # Split messages if too long
                        if len(message) > 3500:
                            send_telegram_message(message)
                            message = ""

                if count > 0 and message:
                    send_telegram_message(message)
            else:
                 print("😴 No trades found this cycle.")

            # 3. Sleep
            # Scan every 15 minutes to avoid spam and api limits
            time.sleep(900) 
            
        except Exception as e:
            print(f"❌ Error in Bot Loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot_service()
