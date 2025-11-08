import os
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

# Gemini AI Integrations setup (using Replit AI Integrations)
AI_INTEGRATIONS_GEMINI_API_KEY = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY")
AI_INTEGRATIONS_GEMINI_BASE_URL = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")

client = genai.Client(
    api_key=AI_INTEGRATIONS_GEMINI_API_KEY,
    http_options={
        'api_version': '',
        'base_url': AI_INTEGRATIONS_GEMINI_BASE_URL   
    }
)


def analyze_chart_image(image_bytes: bytes, timeframe: str, mime_type: str = "image/png") -> str:
    """
    Gemini 2.5 Flashを使用して株価チャート画像を分析
    
    Args:
        image_bytes: 画像のバイトデータ
        timeframe: チャートの時間軸（日足、週足、月足）
        mime_type: 画像のMIMEタイプ（image/png, image/jpegなど）
    
    Returns:
        分析結果のテキスト
    """
    prompt = f"""
あなたは経験豊富なテクニカルアナリストです。以下の{timeframe}チャート画像を詳細に分析してください。

チャートには以下の要素が含まれています：
- 5本の移動平均線（SMA）:
  * 赤線: 5期間SMA（短期トレンド）
  * 緑線: 20期間SMA（短中期トレンド）
  * 青線: 60期間SMA（中期トレンド）
  * 紫線: 100期間SMA（中長期トレンド）
  * 黄線: 200期間SMA（長期トレンド）
- RSI（相対力指数）: 買われすぎ・売られすぎの判定
- 出来高: ボリュームの動向

以下の点について詳しく分析してください：

## 1. 現在のトレンド分析
- 価格と各移動平均線の位置関係
- 移動平均線同士の配置（ゴールデンクロス/デッドクロスの有無）
- トレンドの強さと方向性

## 2. 移動平均線の分析
- 短期（5期間）と中期（20期間）の関係
- 中期（60期間）と長期（200期間）の関係
- サポート・レジスタンスとしての機能

## 3. RSI分析
- 現在のRSI水準（30以下で売られすぎ、70以上で買われすぎ）
- ダイバージェンスの有無
- トレンドとの整合性

## 4. 出来高分析
- 直近の出来高の推移
- 価格変動と出来高の関係
- 高値圏・安値圏での出来高の特徴

## 5. 総合判断
- 現在の相場環境（強気・弱気・レンジ）
- 注目すべき価格水準
- リスクとチャンスポイント
- 今後の見通しと戦略

わかりやすく、具体的に説明してください。
"""
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part(
                    inline_data=types.Blob(
                        mime_type=mime_type,
                        data=image_bytes
                    )
                )
            ]
        )
        return response.text or "分析結果を取得できませんでした。"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"


def main():
    st.set_page_config(
        page_title="株価チャート テクニカル分析",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 株価チャート テクニカル分析アプリ")
    st.markdown("""
    このアプリは、アップロードされた株価チャート画像をAIが分析し、テクニカル指標に基づいた詳細なレポートを提供します。
    
    **チャート要件:**
    - 移動平均線（SMA）: 赤:5、緑:20、青:60、紫:100、黄:200
    - RSI（相対力指数）
    - 出来高
    """)
    
    st.divider()
    
    # 3つの時間軸用のタブを作成
    tab1, tab2, tab3 = st.tabs(["📊 日足チャート", "📊 週足チャート", "📊 月足チャート"])
    
    # 日足チャート
    with tab1:
        st.header("日足チャート分析")
        st.markdown("**短期的なトレンドと売買タイミングの把握に適しています**")
        
        daily_image = st.file_uploader(
            "日足チャート画像をアップロード",
            type=["png", "jpg", "jpeg"],
            key="daily_chart",
            help="日足チャートの画像ファイルを選択してください"
        )
        
        if daily_image is not None:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("アップロードされたチャート")
                image = Image.open(daily_image)
                st.image(image, use_container_width=True)
            
            with col2:
                st.subheader("AI分析中...")
                with st.spinner("日足チャートを分析しています..."):
                    image_bytes = daily_image.getvalue()
                    mime_type = daily_image.type
                    analysis = analyze_chart_image(image_bytes, "日足", mime_type)
                
                st.success("分析完了！")
            
            st.divider()
            st.subheader("📋 日足チャート分析結果")
            st.markdown(analysis)
    
    # 週足チャート
    with tab2:
        st.header("週足チャート分析")
        st.markdown("**中期的なトレンドとスイングトレードの戦略立案に適しています**")
        
        weekly_image = st.file_uploader(
            "週足チャート画像をアップロード",
            type=["png", "jpg", "jpeg"],
            key="weekly_chart",
            help="週足チャートの画像ファイルを選択してください"
        )
        
        if weekly_image is not None:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("アップロードされたチャート")
                image = Image.open(weekly_image)
                st.image(image, use_container_width=True)
            
            with col2:
                st.subheader("AI分析中...")
                with st.spinner("週足チャートを分析しています..."):
                    image_bytes = weekly_image.getvalue()
                    mime_type = weekly_image.type
                    analysis = analyze_chart_image(image_bytes, "週足", mime_type)
                
                st.success("分析完了！")
            
            st.divider()
            st.subheader("📋 週足チャート分析結果")
            st.markdown(analysis)
    
    # 月足チャート
    with tab3:
        st.header("月足チャート分析")
        st.markdown("**長期的なトレンドと投資戦略の判断に適しています**")
        
        monthly_image = st.file_uploader(
            "月足チャート画像をアップロード",
            type=["png", "jpg", "jpeg"],
            key="monthly_chart",
            help="月足チャートの画像ファイルを選択してください"
        )
        
        if monthly_image is not None:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("アップロードされたチャート")
                image = Image.open(monthly_image)
                st.image(image, use_container_width=True)
            
            with col2:
                st.subheader("AI分析中...")
                with st.spinner("月足チャートを分析しています..."):
                    image_bytes = monthly_image.getvalue()
                    mime_type = monthly_image.type
                    analysis = analyze_chart_image(image_bytes, "月足", mime_type)
                
                st.success("分析完了！")
            
            st.divider()
            st.subheader("📋 月足チャート分析結果")
            st.markdown(analysis)
    
    # サイドバーに使い方を表示
    with st.sidebar:
        st.header("📖 使い方")
        st.markdown("""
        1. **チャート画像を準備**  
           日足、週足、月足のいずれかのチャート画像を用意
        
        2. **該当するタブを選択**  
           分析したい時間軸のタブをクリック
        
        3. **画像をアップロード**  
           ファイルアップローダーからチャート画像を選択
        
        4. **分析結果を確認**  
           AIによる詳細なテクニカル分析を確認
        """)
        
        st.divider()
        
        st.header("📊 分析内容")
        st.markdown("""
        - **トレンド分析**: 現在の市場動向
        - **移動平均線**: 5本のSMAの位置関係
        - **RSI**: 買われすぎ/売られすぎ判定
        - **出来高**: ボリューム動向分析
        - **総合判断**: 戦略的アドバイス
        """)
        
        st.divider()
        
        st.info("💡 **ヒント**: 複数の時間軸を組み合わせて分析すると、より精度の高い判断ができます。")


if __name__ == "__main__":
    main()
