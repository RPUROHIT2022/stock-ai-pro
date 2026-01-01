
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def prepare_features(df):
    """
    Creates ML-ready features from technical indicators.
    """
    df = df.copy()
    
    # 1. Feature Engineering
    # Trend
    df['EMA_Diff'] = (df['EMA_20'] - df['EMA_200']) / df['EMA_200']
    df['Close_Above_EMA200'] = (df['Close'] > df['EMA_200']).astype(int)
    
    # Momentum
    df['RSI'] = df['RSI'] / 100.0 # Normalize
    df['Stoch_K'] = df['StochRSI_K'] / 100.0
    
    # Strength
    df['ADX_Norm'] = df['ADX'] / 50.0  # Normalize roughly
    
    # Volatility Squeeze
    df['BB_Width'] = df['BB_Width']
    
    # Lagged Returns (What happened before?)
    df['Ret_1'] = df['Close'].pct_change(1)
    df['Ret_5'] = df['Close'].pct_change(5)
    
    # Volume
    df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    
    # Target Construction (The "Answer")
    # We want to predict if price goes UP by 0.5% in next 4 candles (1 hour)
    # 1 = Buy Signal, 0 = Hold/Sell
    future_returns = df['Close'].shift(-4) / df['Close'] - 1
    df['Target'] = (future_returns > 0.005).astype(int) 
    
    # Clean NaNs
    df.dropna(inplace=True)
    
    feature_cols = [
        'EMA_Diff', 'Close_Above_EMA200', 'RSI', 'Stoch_K', 
        'ADX_Norm', 'BB_Width', 'Ret_1', 'Ret_5', 'Vol_Ratio'
    ]
    
    return df, feature_cols

def train_and_predict(df, ticker):
    """
    Trains a Random Forest on the fly and returns probability.
    """
    try:
        if len(df) < 200: 
            return 50 # Not enough data
            
        data, features = prepare_features(df)
        
        # Split Train/Test (Last 10 rows are "Use Case", rest is training)
        # We simulate "Live" by training on past, predicting on current.
        
        X = data[features]
        y = data['Target']
        
        # Train on EVERYTHING except the very last candle (which we want to predict for?)
        # Actually, for target generation, we lose the last 4 rows (Target is NaN).
        # So we train on 0 to N-5.
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        # Model
        clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        clf.fit(X_train, y_train)
        
        # Validate (Optional log)
        # acc = accuracy_score(y_test, clf.predict(X_test))
        # print(f"Model Accuracy for {ticker}: {acc:.2f}")
        
        # PREDICT LIVE (The most recent candle)
        # We need the FEATURES for the current candle (latest row in original df)
        current_features = df.iloc[[-1]].copy()
        
        # Re-calc features for single row is hard without history.
        # Easier: Just take the last row of the PREPARED X
        # Note: 'Target' is NaN for last row in prepare_features usually due to shift(-4).
        # So we have to care about that.
        # Let's re-run prepare_features on full DF, then take last row.
        
        live_data, _ = prepare_features(df) # This drops last 4 rows... wait.
        # Logic fix: prepare_features drops NaNs. The last 4 rows have NaN Target.
        # So X does NOT contain the current candle.
        
        # We need X for current candle.
        # Let's create X separately.
        
        # 1. Train on historical valid targets
        valid_data = data  # This has dropped NaNs, so it's only old data.
        clf.fit(valid_data[features], valid_data['Target'])
        
        # 2. Predict on LATEST candle (which was dropped from valid_data)
        # We need to manually construct features for df.iloc[-1]
        latest_row = df.iloc[[-1]].copy()
        
        # We need previous candles for Rolling/PctChange features.
        # Let's just pass the WHOLE df to feature calc, but don't drop NaNs on Target
        # just to get X.
        
        return get_prediction_prob(clf, df, features)

    except Exception as e:
        print(f"ML Error: {e}")
        return 50 # Default Neutral

def get_prediction_prob(model, full_df, feature_cols):
    # Recalculate features for the whole dataframe WITHOUT dropping based on Target
    df = full_df.copy()
    
    df['EMA_Diff'] = (df['EMA_20'] - df['EMA_200']) / df['EMA_200']
    df['Close_Above_EMA200'] = (df['Close'] > df['EMA_200']).astype(int)
    df['RSI'] = df['RSI'] / 100.0
    df['Stoch_K'] = df['StochRSI_K'] / 100.0
    df['ADX_Norm'] = df['ADX'] / 50.0 
    df['BB_Width'] = df['BB_Width']
    df['Ret_1'] = df['Close'].pct_change(1)
    df['Ret_5'] = df['Close'].pct_change(5)
    df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    
    # Last row is the one we want to predict
    last_x = df[feature_cols].iloc[[-1]]
    
    # Fill any NaNs in inputs (e.g. if new stock)
    last_x.fillna(0, inplace=True)
    
    # Probability of Class 1 (Buy)
    prob_buy = model.predict_proba(last_x)[0][1] # [prob_0, prob_1]
    
    return int(prob_buy * 100)
