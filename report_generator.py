
import pandas as pd
import datetime

OUTPUT_FILE = "Intraday_Trading_Plan.xlsx"

def generate_report(market_data, scanner_results, news_list):
    """
    Generates a multi-sheet Excel report.
    """
    try:
        writer = pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter')
        workbook = writer.book

        # Define Formats
        header_fmt = workbook.add_format({'bold': True, 'fg_color': '#D7E4BC', 'border': 1})
        buy_fmt = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        sell_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        
        # --- SHEET 1: Market Overview ---
        print("Generating Market Overview Sheet...")
        overview_data = []
        
        # Global Cues
        overview_data.append(["GLOBAL MARKETS SENTIMENT", market_data['Global_Sentiment']])
        overview_data.append(["", ""])
        for k, v in market_data['Global_Indices'].items():
            overview_data.append([k, f"{v['Last Price']} ({v['Change %']}%)"])
            
        overview_data.append(["", ""])
        overview_data.append(["DOMESTIC MARKET STATUS", ""])
        for k, v in market_data['Domestic_Status'].items():
            overview_data.append([k, f"{v['Previous Close']} ({v['Change %']}%) - Trend: {v['Trend']}"])
            
        df_overview = pd.DataFrame(overview_data, columns=["Metric", "Value"])
        df_overview.to_excel(writer, sheet_name='Market Overview', index=False)
        
        # --- SHEET 2, 3, 4: Scanned Stocks ---
        sheets = {
            "Support Zone Stocks": scanner_results.get("SUPPORT_ZONE", []),
            "Breakout Stocks": scanner_results.get("BREAKOUT", []),
            "Breakdown Stocks": scanner_results.get("BREAKDOWN", [])
        }
        
        for sheet_name, data in sheets.items():
            if data:
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                pd.DataFrame(["No Stocks Found"]).to_excel(writer, sheet_name=sheet_name, index=False)

        # --- SHEET 5: News Analysis ---
        if news_list:
            df_news = pd.DataFrame(news_list)
            df_news.to_excel(writer, sheet_name='News Impact', index=False)
        else:
            pd.DataFrame(["No News Fetched"]).to_excel(writer, sheet_name='News Impact', index=False)

        # --- SHEET 6: Final Trade Plan (Top 5) ---
        print("Generating Final Trade Plan...")
        all_trades = scanner_results.get("ALL_TRADES", [])
        # Simple Logic to pick top trades (e.g. highest target/risk or just first few)
        top_trades = all_trades[:5] 
        
        if top_trades:
            df_plan = pd.DataFrame(top_trades)
            # Reorder columns for clarity
            cols = ["Stock", "Signal", "Entry", "Stop Loss", "Target 1", "Target 2", "Reason"]
            # Ensure columns exist
            df_plan = df_plan[[c for c in cols if c in df_plan.columns]]
            df_plan.to_excel(writer, sheet_name='Final Trade Plan', index=False)
            
            # Formatting
            worksheet = writer.sheets['Final Trade Plan']
            worksheet.set_column('A:Z', 15) # Adjust width
            
        else:
            pd.DataFrame(["No High Probability Trades Found"]).to_excel(writer, sheet_name='Final Trade Plan', index=False)

        writer.close()
        print(f"Report generated successfully: {OUTPUT_FILE}")
        return OUTPUT_FILE
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return None
