# Overview

This is a comprehensive stock trading analysis application built with Streamlit that combines:
1. **AI-powered chart analysis** using Google's Gemini 2.5 Flash to perform technical analysis on stock price charts with multiple moving averages (SMA), RSI indicators, and volume data
2. **Realized profit/loss visualization** that processes trading data from CSV files to display cumulative performance, ticker-wise analysis, and statistical insights

The system serves as both a technical analyst for chart interpretation and a performance tracker for realized trading results.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit - A Python-based web application framework chosen for its simplicity in creating data-driven applications with minimal frontend code
- **Image Processing**: PIL (Python Imaging Library) - Handles image upload and preprocessing before sending to the AI model
- **Data Visualization**: Plotly - Interactive charting library for realized profit/loss graphs and ticker analysis
- **Data Processing**: Pandas - DataFrame manipulation for CSV data analysis with Shift-JIS encoding support
- **Rationale**: Streamlit provides rapid prototyping capabilities and built-in components for file uploads, making it ideal for an AI-powered analysis tool combined with financial data visualization

## Backend Architecture
- **Language**: Python - Selected for its strong ecosystem in data analysis, AI/ML integration, and financial applications
- **AI Model Integration**: Google Gemini 2.5 Flash via the `google-genai` SDK
- **Architecture Pattern**: Direct API integration with minimal abstraction layers, prioritizing simplicity and quick response times
- **Analysis Function**: `analyze_chart_image()` - Core function that accepts image bytes, timeframe parameters, and MIME type, then constructs a detailed prompt for technical analysis

## AI Integration Design
- **Problem**: Need to analyze complex stock charts with multiple technical indicators
- **Solution**: Leverage Gemini's multimodal capabilities to process both image and text prompts simultaneously
- **Prompt Engineering**: Structured prompt that explicitly defines chart elements (5 SMA lines with different periods, RSI, volume) and requests specific analysis categories including trend analysis, crossover patterns, and momentum indicators
- **Alternatives Considered**: Could use specialized financial analysis APIs, but Gemini's vision capabilities offer more flexible, natural language analysis
- **Pros**: Natural language output, ability to interpret visual patterns, flexible analysis depth
- **Cons**: Requires API calls (cost/latency), dependent on external service availability

## Configuration Management
- **Environment Variables**: Uses Replit AI Integrations environment variables for secure API key and base URL storage
  - `AI_INTEGRATIONS_GEMINI_API_KEY`: Authentication credential
  - `AI_INTEGRATIONS_GEMINI_BASE_URL`: Custom endpoint configuration for Replit's AI integration proxy
- **Custom HTTP Options**: Configured with empty `api_version` and custom `base_url` to work with Replit's integration layer

## Application Features

### Chart Analysis (Tabs 1-3: Daily, Weekly, Monthly)
The system analyzes charts containing:
1. **Moving Averages** (5 different periods: 5, 20, 60, 100, 200) - Multi-timeframe trend identification
2. **RSI (Relative Strength Index)** - Overbought/oversold conditions
3. **Volume Data** - Trading activity confirmation

### Realized Profit/Loss Analysis (Tab 4)
Added November 2025 - Visualizes trading performance from CSV data:
1. **Data Import**: 
   - Supports both yen-based (円ベース) and dollar-based (ドルベース) CSV files
   - Handles Shift-JIS encoding common in Japanese financial exports
   - Automatic date parsing and numeric conversion with comma handling
   - Robust NaN handling for accurate calculations
2. **Visualizations**:
   - **Cumulative P/L Chart**: Time-series line graph showing cumulative realized profit/loss progression
   - **Ticker P/L Analysis**: Horizontal bar chart displaying profit/loss by individual ticker symbol (color-coded: green for profits, red for losses)
3. **Statistical Metrics**:
   - Total realized P/L (with NaN exclusion for accuracy)
   - Average P/L per trade
   - Win rate (percentage of profitable trades)
   - Total number of trades
4. **Individual Stock Detail Analysis**:
   - Expandable sections for each ticker showing:
     - **Purchase Information**: USD/JPY acquisition price, purchase quantity
     - **Sale Information**: USD/JPY sale price, sale quantity
     - **Investment Results**: P/L, total acquisition cost, settlement amount, P/L rate
   - **Per-Execution-Date Breakdown** (Added November 2025):
     - Within each ticker, displays metrics grouped by execution date (約定日)
     - Shows purchase/sale/investment results for each trading date
     - Quantity-weighted averages calculated per date
     - Handles both yen-based and dollar-based data with proper currency column selection
     - Graceful fallback when USD data is missing
   - Transaction history table per ticker
   - Automated calculation of performance metrics per stock
   - Empty DataFrame handling to prevent IndexError
5. **Data Functions**:
   - `load_realized_pl_csv()`: Loads and parses CSV with Shift-JIS encoding, handles date columns
   - `create_cumulative_pl_chart()`: Generates interactive cumulative P/L visualization
   - `create_ticker_pl_chart()`: Creates ticker-wise P/L comparison chart
   - `display_ticker_details()`: Displays detailed per-ticker analysis with purchase/sale/results metrics
     - Includes per-execution-date breakdown with expandable sections
     - Quantity-weighted average calculations for multi-transaction tickers
     - Exchange rate estimation from yen/USD sale amount data
     - Robust handling of missing USD columns with "データなし" display
     - Empty DataFrame validation to prevent IndexError

# External Dependencies

## AI Services
- **Google Gemini API** (via Replit AI Integrations)
  - Model: Gemini 2.5 Flash
  - Purpose: Multimodal AI analysis of chart images combined with technical analysis expertise
  - Integration: Custom base URL routing through Replit's AI integration proxy
  - Authentication: API key-based

## Python Libraries
- **streamlit**: Web application framework for the user interface
- **google-genai**: Official Google SDK for Gemini API integration
- **Pillow (PIL)**: Image processing and manipulation
- **pandas**: Data manipulation and CSV processing with encoding support
- **plotly**: Interactive charting for realized P/L visualizations
- **os**: Environment variable access for configuration management

## Platform Dependencies
- **Replit AI Integrations**: Provides managed API access and credential storage for Gemini API, eliminating need for direct Google Cloud setup