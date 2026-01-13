
import datetime
from data_engine import fetch_global_sentiment, get_market_status
from news_engine import fetch_market_news
from scanner import scan_stocks, analyze_single_stock
from report_generator import generate_report

def main():
    print("==========================================")
    print(f"   INTRADAY TRADING AI AGENT (PRO) - {datetime.datetime.now().strftime('%Y-%m-%d')}")
    print("==========================================\n")
    
    # 1. Market Overview
    print(">>> Phase 1: Analyzing Market Sentiment...")
    sentiment, global_data = fetch_global_sentiment()
    domestic_status = get_market_status()
    print(f"Global Sentiment: {sentiment}")
    
    market_data = {
        "Global_Sentiment": sentiment,
        "Global_Indices": global_data,
        "Domestic_Status": domestic_status
    }
    
    # 2. News Analysis
    print("\n>>> Phase 2: Fetching Today's Market News...")
    news_list = fetch_market_news()
    print(f"Fetched {len(news_list)} recent news items.")
    
    # 3. Mode Selection
    print("\n------------------------------------------")
    print("SELECT MODE:")
    print("1. Scan Full Market (Nifty 500)")
    print("2. Analyze Specific Stock")
    print("------------------------------------------")
    mode = input("Enter Choice (1 or 2): ").strip()
    
    scanner_results = {}
    
    if mode == "1":
        print("\n>>> Phase 3: Scanning Nifty 500...")
        scanner_results = scan_stocks()
        
        print("\n>>> Phase 4: Generating Report...")
        file_path = generate_report(market_data, scanner_results, news_list)
        if file_path:
             print(f"SUCCESS! Full Market Report saved at: {file_path}")

    elif mode == "2":
        stock_input = input("ENTER STOCK NAME (e.g. RELIANCE): ").strip().upper()
        if stock_input:
            ticker = stock_input if stock_input.endswith(".NS") else f"{stock_input}.NS"
            print(f"\n>>> Analyzing {ticker}...")
            
            # Use the single stock analyzer from scanner
            # Note: We need to import the simple version or modify the threaded one. 
            # The threaded one calls analyze_single_stock which returns None if no setup.
            # But for specific stock, user wants details regardless.
            # We will use a quick direct call logic here or modify analyze_single_stock to be flexible.
            # For now, let's call analyze_single_stock and if None, means no data or no Setup. 
            # If no setup, we might want to force a return. 
            # Lets just use the function as is, if it returns None (due to no setup), we might want to manually fetch to show 'Neutral'.
            
            # Force return data for single stock analysis
            result = analyze_single_stock(ticker, return_any_data=True)
            
            if result:
                print("\n" + "="*40)
                print(f" ANALYSIS REPORT: {result['Stock']}")
                print("="*40)
                print(f" CMP      : {result['CMP']}")
                print(f" SIGNAL   : {result['Signal']}")
                print(f" SETUP    : {result['Setup']}")
                print(f" REASON   : {result['Reason']}")
                if result['Signal'] != "NEUTRAL":
                    print(f" ENTRY    : {result['Entry']}")
                    print(f" STOP LOSS: {result['Stop Loss']}")
                    print(f" TARGET 1 : {result['Target 1']}")
                    print(f" TARGET 2 : {result['Target 2']}")
                print("="*40)
            else:
                print("No clear trade setup found (or invalid data) for this stock.")
                
            # Still generate report for consistency if user wants
            # ...
    
    else:
        print("Invalid Choice.")

if __name__ == "__main__":
    main()
