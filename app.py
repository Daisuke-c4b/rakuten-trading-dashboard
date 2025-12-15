import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
from google import genai
from google.genai import types
from PIL import Image
from io import StringIO

# Gemini API setup
# 優先順位: 1. 環境変数 2. Streamlit secrets


def get_api_key():
    """APIキーを取得（環境変数優先、フォールバックでst.secrets）"""
    # 1. 環境変数から取得を試みる
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your-gemini-api-key-here":
        return api_key
    
    # 2. Streamlit secretsから取得を試みる
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", None)
        if api_key and api_key != "your-gemini-api-key-here":
            return api_key
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    
    # 3. 辞書形式でのアクセスを試みる
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        if api_key and api_key != "your-gemini-api-key-here":
            return api_key
    except (KeyError, FileNotFoundError):
        pass
    
    return None


def get_gemini_client():
    """Gemini APIクライアントを取得"""
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Gemini APIクライアントの初期化に失敗: {str(e)}")
        return None


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


def create_cumulative_pl_chart(df, currency_label, grouping='daily'):
    """
    累積実現損益のグラフを作成
    
    Args:
        df: 実現損益データフレーム
        currency_label: 通貨ラベル（円ベース/ドルベース）
        grouping: グループ化の単位（'daily', 'monthly', 'yearly'）
    
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
    
    # グループ化の処理
    if grouping == 'monthly':
        # 月次グループ化
        df_sorted['期間'] = pd.to_datetime(df_sorted['約定日']).dt.to_period('M')
        grouped = df_sorted.groupby('期間')[pl_col].sum().reset_index()
        grouped['約定日'] = grouped['期間'].dt.to_timestamp()
        grouped['累積損益'] = grouped[pl_col].cumsum()
        x_data = grouped['約定日']
        y_data = grouped['累積損益']
        x_title = '年月'
    elif grouping == 'yearly':
        # 年次グループ化
        df_sorted['期間'] = pd.to_datetime(df_sorted['約定日']).dt.to_period('Y')
        grouped = df_sorted.groupby('期間')[pl_col].sum().reset_index()
        grouped['約定日'] = grouped['期間'].dt.to_timestamp()
        grouped['累積損益'] = grouped[pl_col].cumsum()
        x_data = grouped['約定日']
        y_data = grouped['累積損益']
        x_title = '年'
    else:  # daily
        # 日次（デフォルト）
        df_sorted['累積損益'] = df_sorted[pl_col].cumsum()
        x_data = df_sorted['約定日']
        y_data = df_sorted['累積損益']
        x_title = '約定日'
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode='lines+markers',
        name='累積実現損益',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.2)'
    ))
    
    grouping_label = {'daily': '日次', 'monthly': '月次', 'yearly': '年次'}[grouping]
    
    fig.update_layout(
        title=f'累積実現損益の推移 ({currency_label}) - {grouping_label}',
        xaxis_title=x_title,
        yaxis_title=f'累積損益 ({currency_label})',
        hovermode='x unified',
        height=500,
        template='plotly_white'
    )
    
    return fig


def display_ticker_details(df, currency_symbol, is_yen_base=True):
    """
    ティッカーごとの詳細情報を表示
    
    Args:
        df: 実現損益データフレーム
        currency_symbol: 通貨記号（¥ or $）
        is_yen_base: 円ベースかどうか
    """
    ticker_col = None
    for col in df.columns:
        if 'ティッカー' in col:
            ticker_col = col
            break
    
    if ticker_col is None:
        st.warning("⚠️ ティッカー列が見つかりません。")
        return
    
    # ティッカーごとにグループ化
    tickers = df[ticker_col].unique()
    
    st.subheader("📈 個別株詳細分析")
    
    for ticker in tickers:
        ticker_data = df[df[ticker_col] == ticker].copy()
        
        # ticker_dataが空の場合はスキップ
        if ticker_data.empty:
            continue
        
        # 銘柄名を取得
        stock_name = ticker_data['銘柄名'].iloc[0] if '銘柄名' in ticker_data.columns and len(ticker_data) > 0 else ticker
        
        with st.expander(f"**{ticker}** - {stock_name}"):
            # 数値列の変換
            for col in ticker_data.columns:
                if any(keyword in col for keyword in ['単価', '額', '損益', '数量', '価額']):
                    ticker_data[col] = pd.to_numeric(ticker_data[col].astype(str).str.replace(',', ''), errors='coerce')
            
            # 数量を取得
            total_quantity = ticker_data['数量[株]'].sum() if '数量[株]' in ticker_data.columns else 0
            
            # 通貨固有の列を選択
            if is_yen_base:
                # 円ベースの場合
                acq_price_col = [col for col in ticker_data.columns if '平均取得価額' in col and '円' in col]
                sell_amount_col = [col for col in ticker_data.columns if '売却' in col and '額' in col and '円' in col]
                pl_col = [col for col in ticker_data.columns if '実現損益' in col and '円' in col]
            else:
                # ドルベースの場合
                acq_price_col = [col for col in ticker_data.columns if '平均取得価額' in col and 'USドル' in col]
                sell_amount_col = [col for col in ticker_data.columns if '売却' in col and '額' in col and 'USドル' in col]
                pl_col = [col for col in ticker_data.columns if '実現損益' in col and 'USドル' in col]
            
            # フォールバック：通貨指定がない場合は最初の一致する列を使用
            if not acq_price_col:
                acq_price_col = [col for col in ticker_data.columns if '平均取得価額' in col]
            if not sell_amount_col:
                sell_amount_col = [col for col in ticker_data.columns if '売却' in col and '額' in col]
            if not pl_col:
                pl_col = [col for col in ticker_data.columns if '実現損益' in col]
            
            # 売却単価（USD）列を取得
            sell_price_usd_col = [col for col in ticker_data.columns if '売却' in col and 'USドル' in col and '単価' in col]
            
            # ドルベース売却額列を取得（為替レート推定用）
            sell_amount_usd_col = [col for col in ticker_data.columns if '売却' in col and '額' in col and 'USドル' in col]
            
            # 数量加重平均で取得価格を計算
            # CSVの「平均取得価額」は各行で既に加重平均されているが、複数行がある場合は数量加重平均が必要
            if acq_price_col and '数量[株]' in ticker_data.columns:
                quantities = ticker_data['数量[株]']
                acq_prices = ticker_data[acq_price_col[0]]
                # 取得総額 = Σ(平均取得価額 × 数量) を計算してから総数量で割る
                total_acq_amount = (acq_prices * quantities).sum()
                weighted_acq_price = total_acq_amount / quantities.sum() if quantities.sum() > 0 else 0
            else:
                weighted_acq_price = 0
                total_acq_amount = 0
            
            # 数量加重平均で売却単価（USD）を計算
            if sell_price_usd_col and '数量[株]' in ticker_data.columns:
                quantities = ticker_data['数量[株]']
                prices = ticker_data[sell_price_usd_col[0]]
                weighted_sell_price_usd = (prices * quantities).sum() / quantities.sum() if quantities.sum() > 0 else 0
            else:
                weighted_sell_price_usd = 0
            
            # 取得総額を計算
            total_acquisition = weighted_acq_price * total_quantity
            
            # 受渡金額（売却額の合計）
            total_sell_amount = ticker_data[sell_amount_col[0]].sum() if sell_amount_col else 0
            
            # ドルベース売却額の合計（為替レート推定用）
            total_sell_amount_usd = ticker_data[sell_amount_usd_col[0]].sum() if sell_amount_usd_col else 0
            
            # 実現損益
            total_pl = ticker_data[pl_col[0]].sum() if pl_col else 0
            
            # 損益率を計算
            pl_rate = (total_pl / total_acquisition * 100) if total_acquisition != 0 else 0
            
            # 為替レートを推定（円ベースの場合）
            has_usd_data = False
            estimated_exchange_rate = 0
            if is_yen_base:
                # 円ベース売却額（円）÷ ドルベース売却額（USD）で為替レートを推定
                if total_sell_amount_usd > 0:
                    estimated_exchange_rate = total_sell_amount / total_sell_amount_usd
                    has_usd_data = True
                elif sell_price_usd_col:
                    # 売却単価からも為替レートを推定可能
                    # 売却額（円）= 売却単価（USD）× 数量 × 為替レート
                    # → 為替レート = 売却額（円）÷（売却単価（USD）× 数量）
                    if weighted_sell_price_usd > 0 and total_quantity > 0:
                        estimated_exchange_rate = total_sell_amount / (weighted_sell_price_usd * total_quantity)
                        has_usd_data = True
                    else:
                        estimated_exchange_rate = 0
                else:
                    # USDデータが全くない場合
                    estimated_exchange_rate = 0
                
                # USD取得単価を計算（為替レートが推定できた場合のみ）
                if has_usd_data and estimated_exchange_rate > 0:
                    acq_price_usd = weighted_acq_price / estimated_exchange_rate
                else:
                    acq_price_usd = 0
                
                # 円での売却単価を計算
                sell_price_yen = total_sell_amount / total_quantity if total_quantity > 0 else 0
                
                # USD売却単価が取得できなかった場合は為替レートから推定
                if weighted_sell_price_usd == 0 and sell_price_yen > 0 and estimated_exchange_rate > 0:
                    weighted_sell_price_usd = sell_price_yen / estimated_exchange_rate
            else:
                # ドルベースの場合
                acq_price_usd = weighted_acq_price
                sell_price_yen = 0
                has_usd_data = True  # ドルベースは常にUSDデータがある
            
            # 3列レイアウト
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**📊 購入時**")
                if is_yen_base:
                    st.metric("¥取得単価", f"¥{weighted_acq_price:,.2f}")
                else:
                    st.metric("$取得単価", f"${weighted_acq_price:,.2f}")
                st.metric("購入株数", f"{total_quantity:,.0f}株")
            
            with col2:
                st.markdown("**📉 売却時**")
                if is_yen_base:
                    st.metric("¥売却単価", f"¥{sell_price_yen:,.2f}")
                else:
                    # ドルベースの場合は売却単価を計算
                    sell_price_base = total_sell_amount / total_quantity if total_quantity > 0 else 0
                    st.metric("$売却単価", f"${sell_price_base:,.2f}")
                st.metric("売却株数", f"{total_quantity:,.0f}株")
            
            with col3:
                st.markdown("**💰 投資結果**")
                st.metric("損益", f"{currency_symbol}{total_pl:,.2f}", delta=f"{pl_rate:,.2f}%")
                st.metric("取得総額", f"{currency_symbol}{total_acquisition:,.2f}")
                st.metric("受渡金額", f"{currency_symbol}{total_sell_amount:,.2f}")
                st.metric("損益率", f"{pl_rate:,.2f}%")
            
            # 約定日別サマリー
            execution_date_col = None
            for col in ticker_data.columns:
                if '約定日' in col:
                    execution_date_col = col
                    break
            
            if execution_date_col and execution_date_col in ticker_data.columns:
                st.markdown("**📅 約定日別サマリー**")
                
                # 約定日でグループ化（NaT や空の値は除外）
                date_groups = ticker_data[ticker_data[execution_date_col].notna()].groupby(execution_date_col)
                
                # 各約定日ごとに表示
                for exec_date, date_data in date_groups:
                    with st.expander(f"📆 {exec_date}"):
                        # 数量を計算
                        date_quantity = date_data['数量[株]'].sum() if '数量[株]' in date_data.columns else 0
                        
                        # 取得価格（数量加重平均）
                        if acq_price_col and '数量[株]' in date_data.columns:
                            date_quantities = date_data['数量[株]']
                            date_acq_prices = date_data[acq_price_col[0]]
                            date_weighted_acq = (date_acq_prices * date_quantities).sum() / date_quantities.sum() if date_quantities.sum() > 0 else 0
                        else:
                            date_weighted_acq = 0
                        
                        # 売却単価（数量加重平均）
                        if sell_price_usd_col and '数量[株]' in date_data.columns:
                            date_quantities = date_data['数量[株]']
                            date_sell_prices = date_data[sell_price_usd_col[0]]
                            date_weighted_sell = (date_sell_prices * date_quantities).sum() / date_quantities.sum() if date_quantities.sum() > 0 else 0
                        else:
                            date_weighted_sell = 0
                        
                        # 取得総額
                        date_acq_total = date_weighted_acq * date_quantity
                        
                        # 売却額
                        date_sell_amount = date_data[sell_amount_col[0]].sum() if sell_amount_col else 0
                        
                        # 損益
                        date_pl = date_data[pl_col[0]].sum() if pl_col else 0
                        
                        # 損益率
                        date_pl_rate = (date_pl / date_acq_total * 100) if date_acq_total != 0 else 0
                        
                        # 為替レート推定（円ベースの場合）
                        # ティッカー全体の為替レートを使用
                        if is_yen_base:
                            date_sell_yen = date_sell_amount / date_quantity if date_quantity > 0 else 0
                            
                            # ティッカー全体の為替レートを使用
                            if estimated_exchange_rate > 0:
                                date_acq_usd = date_weighted_acq / estimated_exchange_rate
                                date_has_usd = True
                                
                                # USD売却単価を計算
                                if date_weighted_sell == 0 and date_sell_yen > 0:
                                    date_weighted_sell = date_sell_yen / estimated_exchange_rate
                            else:
                                date_acq_usd = 0
                                date_has_usd = False
                        else:
                            date_acq_usd = date_weighted_acq
                            date_sell_yen = 0
                            date_has_usd = True
                        
                        # 3列レイアウトで表示
                        d_col1, d_col2, d_col3 = st.columns(3)
                        
                        with d_col1:
                            st.markdown("**📊 購入時**")
                            if is_yen_base:
                                st.metric("¥取得単価", f"¥{date_weighted_acq:,.2f}")
                            else:
                                st.metric("$取得単価", f"${date_weighted_acq:,.2f}")
                            st.metric("購入株数", f"{date_quantity:,.0f}株")
                        
                        with d_col2:
                            st.markdown("**📉 売却時**")
                            if is_yen_base:
                                st.metric("¥売却単価", f"¥{date_sell_yen:,.2f}")
                            else:
                                date_sell_price_base = date_sell_amount / date_quantity if date_quantity > 0 else 0
                                st.metric("$売却単価", f"${date_sell_price_base:,.2f}")
                            st.metric("売却株数", f"{date_quantity:,.0f}株")
                        
                        with d_col3:
                            st.markdown("**💰 投資結果**")
                            st.metric("損益", f"{currency_symbol}{date_pl:,.2f}", delta=f"{date_pl_rate:,.2f}%")
                            st.metric("取得総額", f"{currency_symbol}{date_acq_total:,.2f}")
                            st.metric("受渡金額", f"{currency_symbol}{date_sell_amount:,.2f}")
                            st.metric("損益率", f"{date_pl_rate:,.2f}%")
            
            # 取引履歴テーブル
            st.markdown("**📋 取引履歴**")
            display_cols = ['約定日', '受渡日', '数量[株]', '売却/決済単価[USドル]']
            display_cols = [col for col in display_cols if col in ticker_data.columns]
            
            if pl_col:
                display_cols.append(pl_col[0])
            if sell_amount_col:
                display_cols.append(sell_amount_col[0])
            if acq_price_col:
                display_cols.append(acq_price_col[0])
            
            st.dataframe(ticker_data[display_cols], use_container_width=True, hide_index=True)


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
    
    ticker_col = None
    for col in df.columns:
        if 'ティッカー' in col:
            ticker_col = col
            break
    
    if pl_col is None or ticker_col is None:
        return None
    
    df_copy = df.copy()
    df_copy[pl_col] = pd.to_numeric(df_copy[pl_col].astype(str).str.replace(',', ''), errors='coerce')
    
    ticker_pl = df_copy.groupby(ticker_col)[pl_col].sum().sort_values()
    
    colors = ['red' if x < 0 else 'green' for x in ticker_pl.values]
    
    # USDの場合は小数点以下2桁、円の場合は整数で表示
    text_format = '%{text:,.2f}' if currency_label == 'USD' else '%{text:,.0f}'
    
    fig = go.Figure(go.Bar(
        x=ticker_pl.values,
        y=ticker_pl.index,
        orientation='h',
        marker=dict(color=colors),
        text=ticker_pl.values,
        texttemplate=text_format,
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
    client = get_gemini_client()
    if client is None:
        return "❌ Gemini APIクライアントが初期化されていません。Streamlit Cloudのシークレット設定で GEMINI_API_KEY を設定してください。"
    
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
            model="gemini-2.5-flash-lite",
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
        
        # タブで円ベース・ドルベースを切り替え
        yen_tab, dollar_tab = st.tabs(["円ベース", "ドルベース"])
        
        with yen_tab:
            if yen_csv is not None:
                yen_df = load_realized_pl_csv(yen_csv)
                
                if yen_df is not None:
                    # 最終行は合計行なので除外
                    yen_df_data = yen_df.iloc[:-1].copy() if len(yen_df) > 1 else yen_df.copy()
                    
                    pl_col = None
                    for col in yen_df.columns:
                        if '実現損益' in col and '円' in col:
                            pl_col = col
                            break
                    
                    if pl_col:
                        # K列の最終行（合計行）から総実現損益を取得
                        total_pl_str = str(yen_df[pl_col].iloc[-1])
                        total_pl = pd.to_numeric(total_pl_str.replace(',', ''), errors='coerce')
                        if pd.isna(total_pl):
                            total_pl = 0
                        
                        # 取引回数：ティッカー × 約定日のユニークな組み合わせ数（最終行を除く）
                        ticker_col = None
                        for col in yen_df_data.columns:
                            if 'ティッカー' in col:
                                ticker_col = col
                                break
                        
                        execution_date_col = None
                        for col in yen_df_data.columns:
                            if '約定日' in col:
                                execution_date_col = col
                                break
                        
                        if ticker_col and execution_date_col:
                            # ティッカー × 約定日でユニークにカウント（最終行除外）
                            trade_count = yen_df_data[[ticker_col, execution_date_col]].drop_duplicates().shape[0]
                        else:
                            # フォールバック：全行数（最終行除外）
                            trade_count = len(yen_df_data)
                        
                        # 平均損益 = 総実現損益 ÷ 取引回数
                        avg_pl = total_pl / trade_count if trade_count > 0 else 0
                        
                        # 勝率計算（最終行を除くデータで計算）
                        yen_df_data_calc = yen_df_data.copy()
                        yen_df_data_calc[pl_col] = pd.to_numeric(yen_df_data_calc[pl_col].astype(str).str.replace(',', ''), errors='coerce')
                        pl_values = yen_df_data_calc[pl_col].dropna()
                        win_count = (pl_values > 0).sum()
                        lose_count = (pl_values < 0).sum()
                        win_rate = (win_count / (win_count + lose_count) * 100) if (win_count + lose_count) > 0 else 0
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("総実現損益", f"¥{total_pl:,.0f}")
                        with col2:
                            st.metric("平均損益", f"¥{avg_pl:,.0f}")
                        with col3:
                            st.metric("勝率", f"{win_rate:.1f}%")
                        with col4:
                            st.metric("取引回数", f"{trade_count}回")
                        
                        # 累積損益グラフのグループ化選択
                        st.subheader("📊 累積実現損益の推移")
                        grouping_yen = st.radio(
                            "表示単位を選択",
                            options=['daily', 'monthly', 'yearly'],
                            format_func=lambda x: {'daily': '日次', 'monthly': '月次', 'yearly': '年次'}[x],
                            key='grouping_yen',
                            horizontal=True
                        )
                        
                        cumulative_chart = create_cumulative_pl_chart(yen_df_data, "円", grouping=grouping_yen)
                        if cumulative_chart is not None:
                            st.plotly_chart(cumulative_chart, use_container_width=True)
                        else:
                            st.warning("⚠️ 累積損益グラフを作成できませんでした。CSVファイルに「約定日」列が含まれているか確認してください。")
                        
                        ticker_chart = create_ticker_pl_chart(yen_df_data, "円")
                        if ticker_chart is not None:
                            st.plotly_chart(ticker_chart, use_container_width=True)
                        else:
                            st.warning("⚠️ 銘柄別損益グラフを作成できませんでした。CSVファイルに「ティッカー」または「ティッカーコード」列が含まれているか確認してください。")
                        
                        # 個別株詳細分析（最終行を除いたデータを使用）
                        display_ticker_details(yen_df_data, "¥", is_yen_base=True)
                        
                        with st.expander("📋 全データテーブル"):
                            st.dataframe(yen_df, use_container_width=True)
            else:
                st.info("💡 円ベースのCSVファイルをアップロードして、実現損益を分析してください。")
        
        with dollar_tab:
            if dollar_csv is not None:
                dollar_df = load_realized_pl_csv(dollar_csv)
                
                if dollar_df is not None:
                    pl_col = None
                    for col in dollar_df.columns:
                        if '実現損益' in col or '損益' in col:
                            pl_col = col
                            break
                    
                    if pl_col:
                        # 数値変換を一時的なコピーで行う
                        dollar_df_calc = dollar_df.copy()
                        dollar_df_calc[pl_col] = pd.to_numeric(dollar_df_calc[pl_col].astype(str).str.replace(',', ''), errors='coerce')
                        
                        # 総実現損益：K列の最終行から取得
                        total_pl = dollar_df_calc[pl_col].iloc[-1] if len(dollar_df_calc) > 0 else 0
                        
                        # 最終行を除いたデータで各種計算を行う
                        dollar_df_data = dollar_df.iloc[:-1].copy()
                        dollar_df_data_calc = dollar_df_calc.iloc[:-1].copy()
                        
                        # 取引回数：ティッカー × 約定日のユニークな組み合わせ数（最終行除く）
                        ticker_col = None
                        for col in dollar_df.columns:
                            if 'ティッカー' in col:
                                ticker_col = col
                                break
                        
                        execution_date_col = None
                        for col in dollar_df.columns:
                            if '約定日' in col:
                                execution_date_col = col
                                break
                        
                        if ticker_col and execution_date_col:
                            # ティッカー × 約定日でユニークにカウント（最終行を除く）
                            trade_count = dollar_df_data[[ticker_col, execution_date_col]].drop_duplicates().shape[0]
                        else:
                            # フォールバック：全行数（最終行を除く）
                            trade_count = len(dollar_df_data)
                        
                        # 平均損益 = 総実現損益 ÷ 取引回数
                        avg_pl = total_pl / trade_count if trade_count > 0 else 0
                        
                        # 勝率計算（最終行を除いたデータで計算）
                        pl_values = dollar_df_data_calc[pl_col].dropna()
                        win_count = (pl_values > 0).sum()
                        lose_count = (pl_values < 0).sum()
                        win_rate = (win_count / (win_count + lose_count) * 100) if (win_count + lose_count) > 0 else 0
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("総実現損益", f"${total_pl:,.2f}")
                        with col2:
                            st.metric("平均損益", f"${avg_pl:,.2f}")
                        with col3:
                            st.metric("勝率", f"{win_rate:.1f}%")
                        with col4:
                            st.metric("取引回数", f"{trade_count}回")
                        
                        # 累積損益グラフのグループ化選択
                        st.subheader("📊 累積実現損益の推移")
                        grouping_dollar = st.radio(
                            "表示単位を選択",
                            options=['daily', 'monthly', 'yearly'],
                            format_func=lambda x: {'daily': '日次', 'monthly': '月次', 'yearly': '年次'}[x],
                            key='grouping_dollar',
                            horizontal=True
                        )
                        
                        cumulative_chart = create_cumulative_pl_chart(dollar_df_data, "USD", grouping=grouping_dollar)
                        if cumulative_chart is not None:
                            st.plotly_chart(cumulative_chart, use_container_width=True)
                        else:
                            st.warning("⚠️ 累積損益グラフを作成できませんでした。CSVファイルに「約定日」列が含まれているか確認してください。")
                        
                        ticker_chart = create_ticker_pl_chart(dollar_df_data, "USD")
                        if ticker_chart is not None:
                            st.plotly_chart(ticker_chart, use_container_width=True)
                        else:
                            st.warning("⚠️ 銘柄別損益グラフを作成できませんでした。CSVファイルに「ティッカー」または「ティッカーコード」列が含まれているか確認してください。")
                        
                        # 個別株詳細分析（最終行を除いたデータを使用）
                        display_ticker_details(dollar_df_data, "$", is_yen_base=False)
                        
                        with st.expander("📋 全データテーブル"):
                            st.dataframe(dollar_df, use_container_width=True)
            else:
                st.info("💡 ドルベースのCSVファイルをアップロードして、実現損益を分析してください。")
    
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
