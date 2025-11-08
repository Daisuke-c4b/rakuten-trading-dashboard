import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from google import genai
from google.genai import types
from PIL import Image
from io import StringIO

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


def load_realized_pl_csv(uploaded_file, encoding='shift-jis'):
    """
    実現損益CSVファイルを読み込む
    
    Args:
        uploaded_file: Streamlitのアップロードファイル
        encoding: ファイルのエンコーディング（デフォルト: shift-jis）
    
    Returns:
        pandas DataFrame
    """
    try:
        content = uploaded_file.getvalue().decode(encoding)
        df = pd.read_csv(StringIO(content))
        
        if '約定日' in df.columns:
            df['約定日'] = pd.to_datetime(df['約定日'], format='%Y/%m/%d', errors='coerce')
        if '受渡日' in df.columns:
            df['受渡日'] = pd.to_datetime(df['受渡日'], format='%Y/%m/%d', errors='coerce')
        if '決済日' in df.columns:
            df['決済日'] = pd.to_datetime(df['決済日'], format='%Y/%m/%d', errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"CSVファイルの読み込みに失敗しました: {str(e)}")
        return None


def create_cumulative_pl_chart(df, currency_label):
    """
    累積実現損益のグラフを作成
    
    Args:
        df: 実現損益データフレーム
        currency_label: 通貨ラベル（円ベース/ドルベース）
    
    Returns:
        Plotly figure
    """
    pl_col = None
    for col in df.columns:
        if '実現損益' in col or '損益' in col:
            pl_col = col
            break
    
    if pl_col is None:
        return None
    
    df_sorted = df.sort_values('約定日').copy()
    
    df_sorted[pl_col] = pd.to_numeric(df_sorted[pl_col].astype(str).str.replace(',', ''), errors='coerce')
    
    df_sorted['累積損益'] = df_sorted[pl_col].cumsum()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_sorted['約定日'],
        y=df_sorted['累積損益'],
        mode='lines+markers',
        name='累積実現損益',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.2)'
    ))
    
    fig.update_layout(
        title=f'累積実現損益の推移 ({currency_label})',
        xaxis_title='約定日',
        yaxis_title=f'累積損益 ({currency_label})',
        hovermode='x unified',
        height=500,
        template='plotly_white'
    )
    
    return fig


def create_ticker_pl_chart(df, currency_label):
    """
    銘柄別実現損益のグラフを作成
    
    Args:
        df: 実現損益データフレーム
        currency_label: 通貨ラベル（円ベース/ドルベース）
    
    Returns:
        Plotly figure
    """
    pl_col = None
    for col in df.columns:
        if '実現損益' in col or '損益' in col:
            pl_col = col
            break
    
    if pl_col is None or 'ティッカー' not in df.columns:
        return None
    
    df[pl_col] = pd.to_numeric(df[pl_col].astype(str).str.replace(',', ''), errors='coerce')
    
    ticker_pl = df.groupby('ティッカー')[pl_col].sum().sort_values()
    
    colors = ['red' if x < 0 else 'green' for x in ticker_pl.values]
    
    fig = go.Figure(go.Bar(
        x=ticker_pl.values,
        y=ticker_pl.index,
        orientation='h',
        marker=dict(color=colors),
        text=ticker_pl.values,
        texttemplate='%{text:,.0f}',
        textposition='outside'
    ))
    
    fig.update_layout(
        title=f'銘柄別実現損益 ({currency_label})',
        xaxis_title=f'実現損益 ({currency_label})',
        yaxis_title='ティッカー',
        height=max(400, len(ticker_pl) * 30),
        template='plotly_white',
        showlegend=False
    )
    
    return fig


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
    
    # 4つのタブを作成（3つの時間軸 + 実現損益）
    tab1, tab2, tab3, tab4 = st.tabs(["📊 日足チャート", "📊 週足チャート", "📊 月足チャート", "💰 実現損益分析"])
    
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
    
    # 実現損益分析
    with tab4:
        st.header("💰 実現損益分析")
        st.markdown("**取引の実現損益を可視化して、パフォーマンスを把握します**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("円ベースデータ")
            yen_csv = st.file_uploader(
                "円ベースCSVファイルをアップロード",
                type=["csv"],
                key="yen_csv",
                help="円建ての実現損益CSVファイルを選択"
            )
        
        with col2:
            st.subheader("ドルベースデータ")
            dollar_csv = st.file_uploader(
                "ドルベースCSVファイルをアップロード",
                type=["csv"],
                key="dollar_csv",
                help="ドル建ての実現損益CSVファイルを選択"
            )
        
        st.divider()
        
        if yen_csv is not None:
            st.subheader("📊 円ベース実現損益分析")
            
            yen_df = load_realized_pl_csv(yen_csv)
            
            if yen_df is not None:
                pl_col = None
                for col in yen_df.columns:
                    if '実現損益' in col or '損益' in col:
                        pl_col = col
                        break
                
                if pl_col:
                    yen_df[pl_col] = pd.to_numeric(yen_df[pl_col].astype(str).str.replace(',', ''), errors='coerce')
                    total_pl = yen_df[pl_col].sum()
                    avg_pl = yen_df[pl_col].mean()
                    win_count = (yen_df[pl_col] > 0).sum()
                    lose_count = (yen_df[pl_col] < 0).sum()
                    win_rate = (win_count / (win_count + lose_count) * 100) if (win_count + lose_count) > 0 else 0
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("総実現損益", f"¥{total_pl:,.0f}")
                    with col2:
                        st.metric("平均損益", f"¥{avg_pl:,.0f}")
                    with col3:
                        st.metric("勝率", f"{win_rate:.1f}%")
                    with col4:
                        st.metric("取引回数", f"{len(yen_df)}回")
                    
                    st.plotly_chart(create_cumulative_pl_chart(yen_df, "円"), use_container_width=True)
                    
                    st.plotly_chart(create_ticker_pl_chart(yen_df, "円"), use_container_width=True)
                    
                    with st.expander("📋 データテーブル"):
                        st.dataframe(yen_df, use_container_width=True)
        
        if dollar_csv is not None:
            st.subheader("📊 ドルベース実現損益分析")
            
            dollar_df = load_realized_pl_csv(dollar_csv)
            
            if dollar_df is not None:
                pl_col = None
                for col in dollar_df.columns:
                    if '実現損益' in col or '損益' in col:
                        pl_col = col
                        break
                
                if pl_col:
                    dollar_df[pl_col] = pd.to_numeric(dollar_df[pl_col].astype(str).str.replace(',', ''), errors='coerce')
                    total_pl = dollar_df[pl_col].sum()
                    avg_pl = dollar_df[pl_col].mean()
                    win_count = (dollar_df[pl_col] > 0).sum()
                    lose_count = (dollar_df[pl_col] < 0).sum()
                    win_rate = (win_count / (win_count + lose_count) * 100) if (win_count + lose_count) > 0 else 0
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("総実現損益", f"${total_pl:,.2f}")
                    with col2:
                        st.metric("平均損益", f"${avg_pl:,.2f}")
                    with col3:
                        st.metric("勝率", f"{win_rate:.1f}%")
                    with col4:
                        st.metric("取引回数", f"{len(dollar_df)}回")
                    
                    st.plotly_chart(create_cumulative_pl_chart(dollar_df, "USD"), use_container_width=True)
                    
                    st.plotly_chart(create_ticker_pl_chart(dollar_df, "USD"), use_container_width=True)
                    
                    with st.expander("📋 データテーブル"):
                        st.dataframe(dollar_df, use_container_width=True)
        
        if yen_csv is None and dollar_csv is None:
            st.info("💡 円ベースまたはドルベースのCSVファイルをアップロードして、実現損益を分析してください。")
    
    # サイドバーに使い方を表示
    with st.sidebar:
        st.header("📖 使い方")
        
        st.subheader("チャート分析")
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
        
        st.subheader("実現損益分析")
        st.markdown("""
        1. **CSVファイルを準備**  
           円ベース・ドルベースの実現損益CSV
        
        2. **実現損益分析タブを選択**  
           💰実現損益分析タブをクリック
        
        3. **CSVファイルをアップロード**  
           円ベース・ドルベースそれぞれアップロード
        
        4. **可視化結果を確認**  
           累積損益、銘柄別損益、統計データを確認
        """)
        
        st.divider()
        
        st.header("📊 分析内容")
        st.markdown("""
        **チャート分析:**
        - トレンド分析: 現在の市場動向
        - 移動平均線: 5本のSMAの位置関係
        - RSI: 買われすぎ/売られすぎ判定
        - 出来高: ボリューム動向分析
        - 総合判断: 戦略的アドバイス
        
        **実現損益分析:**
        - 累積損益推移グラフ
        - 銘柄別損益分析
        - 勝率・平均損益などの統計
        """)
        
        st.divider()
        
        st.info("💡 **ヒント**: 複数の時間軸を組み合わせて分析すると、より精度の高い判断ができます。")


if __name__ == "__main__":
    main()
