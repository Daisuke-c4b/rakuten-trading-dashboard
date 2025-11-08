# Overview

This is a stock chart analysis application built with Streamlit that leverages Google's Gemini 2.5 Flash AI model to perform technical analysis on stock price charts. The application accepts chart images and provides detailed technical analysis based on multiple moving averages (SMA), RSI indicators, and volume data. The system is designed to act as an experienced technical analyst, interpreting chart patterns and providing insights on trends, support/resistance levels, and trading signals.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit - A Python-based web application framework chosen for its simplicity in creating data-driven applications with minimal frontend code
- **Image Processing**: PIL (Python Imaging Library) - Handles image upload and preprocessing before sending to the AI model
- **Rationale**: Streamlit provides rapid prototyping capabilities and built-in components for file uploads, making it ideal for an AI-powered analysis tool

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

## Technical Indicators Analyzed
The system is designed to analyze charts containing:
1. **Moving Averages** (5 different periods: 5, 20, 60, 100, 200) - Multi-timeframe trend identification
2. **RSI (Relative Strength Index)** - Overbought/oversold conditions
3. **Volume Data** - Trading activity confirmation

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
- **os**: Environment variable access for configuration management

## Platform Dependencies
- **Replit AI Integrations**: Provides managed API access and credential storage for Gemini API, eliminating need for direct Google Cloud setup