# Implementation Plan: Gemini "Hedge Fund Manager" Integration

## Goal
Transform the application from a quantitative tool into a "Thinking Analyst" by integrating Google Gemini. The AI will synthesize hard numbers (RSI, ML Scores) and soft data (News) to provide a reasoned trade verdict (Buy/Sell/Wait).

## User Review Required
> [!IMPORTANT]
> **API Key Expected**: This feature requires a valid Google Gemini API Key. You will need to enter this in the sidebar or save it in `.streamlit/secrets.toml`.

## Proposed Changes

### 1. New Module: `gemini_engine.py`
This file will handle the communication with Google's AI servers.
*   **Function**: `get_gemini_verdict(ticker, technical_dict, ml_score, news_list)`
*   **Prompt Strategy**: "Act as a Senior Hedge Fund Risk Manager. Review this technical and sentiment data. Provide a 3-sentence investment thesis and a final verdict (AGGRESSIVE BUY, ACCUMULATE, WAIT, SELL)."

### 2. Update: `institutional_dashboard.py`
Integrate the new engine into the existing dashboard.
*   **UI Change**: Add an "Ask Gemini Analyst 🧠" button (to avoid wasting API credits on every run).
*   **Display**: A new "Analyst Report" card that shows the AI's reasoning text.

## Step-by-Step Implementation

1.  **Install Library**: `pip install google-generativeai` (I will run this).
2.  **Create `gemini_engine.py`**: Implement the API logic.
3.  **Modify `institutional_dashboard.py`**:
    *   Import the new engine.
    *   Collect all analysis variables (RSI, VWAP status, ML Score).
    *   Pass them to Gemini when requested.
    *   Render the response.

## Verification Plan
*   **Manual Test**: Run the app, enter a dummy or real API key, and check if Gemini provides a relevant response for a stock like "RELIANCE".
*   **Latency Check**: Ensure the UI doesn't freeze while waiting for Gemini (use `st.spinner`).
