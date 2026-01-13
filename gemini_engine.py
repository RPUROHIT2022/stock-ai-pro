
import google.generativeai as genai
import streamlit as st
import json

def get_available_models(api_key):
    """Lists available models for debugging."""
    try:
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return models
    except:
        return ["Could not fetch models"]

def get_gemini_verdict(ticker, tech_data, ml_score, news_list, api_key):
    """
    Sends stock data to Gemini. Tries updated models, falls back to reporting available ones.
    """
    if not api_key:
        return "⚠️ Please enter your Google Gemini API Key in the Sidebar to unlock this feature."
        
    try:
        genai.configure(api_key=api_key)
        
        # Try the most standard model name first
        model_name = 'gemini-2.5-flash' 
        model = genai.GenerativeModel(model_name)
        
        # 1. Prepare Prompt Data
        news_text = "\n".join([f"- {n['Headline']} (Source: {n['Score']})" for n in news_list[:5]])
        
        prompt = f"""
        You are a Senior Risk Manager at a top Wall Street Hedge Fund. I am a Junior Analyst pitching a trade on {ticker}.
        
        Review the following data and give me your BRUTALLY HONEST verdict.
        
        ### 1. TECHNICALS
        - Price: {tech_data.get('CMP')}
        - Trend: {tech_data.get('Trend')}
        - RSI: {tech_data.get('RSI')} ({'Overbought' if tech_data.get('RSI')>70 else 'Oversold' if tech_data.get('RSI')<30 else 'Neutral'})
        - VWAP Status: {tech_data.get('VWAP_Status')}
        
        ### 2. AI MODEL CONFIDENCE
        - Our Internal ML Model Score: {ml_score}/100
        - Pattern Detected: {tech_data.get('Pattern')}
        
        ### 3. RECENT NEWS HEADLINES
        {news_text}
        
        ### YOUR TASK:
        Provide a response in this exact format:
        
        **VERDICT**: [AGGRESSIVE BUY | ACCUMULATE | WAIT | SELL]
        
        **THESIS**: (2-3 sentences explaining WHY, focusing on risks vs reward. Be skeptical.)
        
        **WATCH OUT FOR**: (1 sentence on the biggest risk factor).
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        # Debugging: List available models if the specific one failed
        available = get_available_models(api_key)
        valid_models = ", ".join([m.replace("models/", "") for m in available])
        return f"""❌ **Model Error**: {str(e)}
        
        ℹ️ **Valid Models for your Key**: 
        {valid_models}
        
        (I attempted to use '{model_name}')"""
