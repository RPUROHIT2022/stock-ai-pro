
import pandas as pd
import os
from datetime import datetime

EXCEL_FILE = "e:/stock news/Intraday_Trading_Plan.xlsx"

def log_trade_to_excel(trade_data):
    """
    Appends a trade dictionary to the Excel journal.
    trade_data expected format:
    {
        "Stock": "RELIANCE",
        "Signal": "BUY",
        "Entry": 2500,
        "Stop Loss": 2480,
        "Target 1": 2540,
        "Strategy": "Trend Following",
        "Reason": "ADX > 25..."
    }
    """
    try:
        # Prepare Row Data
        new_row = {
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Ticker": trade_data.get("Stock", "Unknown"),
            "Signal": trade_data.get("Signal", "NEUTRAL"),
            "Entry": trade_data.get("Entry", 0),
            "Stop Loss": trade_data.get("Stop Loss", 0),
            "Target": trade_data.get("Target 1", 0),
            "Strategy": trade_data.get("Strategy", "Manual"),
            "Status": "OPEN",  # Default status
            "Notes": trade_data.get("Reason", "")
        }
        
        df_new = pd.DataFrame([new_row])

        # Check if file exists
        if os.path.exists(EXCEL_FILE):
            try:
                # Try reading existing
                existing_df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
                # Append
                updated_df = pd.concat([existing_df, df_new], ignore_index=True)
            except Exception as e:
                print(f"Error reading Excel (might be corrupted/locked): {e}")
                # If reading fails, we might want to start fresh or backup?
                # For now, let's try to overwrite if it's just a schema issue, 
                # but if locked, we can't do anything.
                return False
        else:
            updated_df = df_new

        # Write back
        updated_df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        return True

    except Exception as e:
        print(f"Failed to log trade: {e}")
        return False
