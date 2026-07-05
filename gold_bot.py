import yfinance as yf
import pandas_datareader.data as web
import pandas as pd
import datetime
import requests
import os

# GitHub Secrets에 'gold'라는 이름으로 웹훅 URL이 저장되어 있어야 합니다.
WEBHOOK_URL = os.environ.get('gold')

def get_data():
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=365)
    
    tickers = ["GC=F", "SI=F", "DX-Y.NYB"]
    df_price = yf.download(tickers, start=start, end=end)['Close']
    fred_data = web.DataReader(['BAMLH0A0HYM2EY', 'T10YIE'], 'fred', start, end)
    
    df = df_price.join(fred_data, how='outer').ffill().dropna()
    return df

def run_bot():
    df = get_data()
    
    # 1. 지표 계산
    df['Gold_MA200'] = df['GC=F'].rolling(window=200).mean()
    
    # 2. 5-Factor 로직
    cond_trend = (df['GC=F'] > df['Gold_MA200']).astype(int)
    cond_value = ((df['GC=F'] / df['SI=F']) < 90).astype(int)
    cond_fear = (df['BAMLH0A0HYM2EY'] > 5.0).astype(int)
    cond_infl = (df['T10YIE'] > df['T10YIE'].rolling(60).mean()).astype(int)
    cond_dxy = (df['DX-Y.NYB'] < df['DX-Y.NYB'].rolling(200).mean()).astype(int)
    
    # 3. 점수 및 신호 계산
    df['Score'] = cond_value + cond_fear + cond_infl + cond_dxy
    df['Signal'] = ((cond_trend == 1) & (df['Score'] >= 2)).astype(int)
    
    # 4. 노이즈 제거 (3일 확정 필터)
    is_confirmed = df['Signal'].iloc[-3:].sum() == 3
    final_signal = "YES" if is_confirmed else "NO"
    
    # 5. 상세 상태 표시용 아이콘 매핑
    def status_icon(val): return "✅" if val.iloc[-1] == 1 else "❌"
    
    # 6. 알림 메시지 구성 (상세 내역 추가)
    msg = (f"🚀 **금투자 5-Factor 봇 ({datetime.date.today().strftime('%Y-%m-%d')})**\n"
           f"• 최종 신호: **{final_signal}** (3일 확인)\n"
           f"• 금 시세: ${df['GC=F'].iloc[-1]:.2f}\n\n"
           f"--- [팩터별 상세] ---\n"
           f"{status_icon(cond_trend)} 추세 (Gold > MA200)\n"
           f"{status_icon(cond_value)} 가치 (GS Ratio < 90)\n"
           f"{status_icon(cond_fear)} 위기 (Spread > 5.0)\n"
           f"{status_icon(cond_infl)} 물가 (Inflation Momentum)\n"
           f"{status_icon(cond_dxy)} 달러 (DXY Weakness)\n"
           f"---------------------\n"
           f"• 총 점수: {df['Score'].iloc[-1]}/4 (Trend 제외)\n"
           f"• 상태: {'진입/보유 중' if is_confirmed else '관망/현금'}")
    
    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={"content": msg})
    print(msg)

if __name__ == "__main__":
    run_bot()
