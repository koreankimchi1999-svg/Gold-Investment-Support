import yfinance as yf
import pandas_datareader.data as web
import datetime
import requests
import os  # [추가] 환경변수를 쓰기 위해 필요함

# [수정] 아래 한 줄로 바꾸세요. 'gold'는 깃허브 시크릿 이름입니다.
WEBHOOK_URL = os.environ.get('gold') 

# (이후 기존 코드와 동일)

# [설정] 기준점 관리: 시장 상황이 변하면 이 숫자들만 수정하세요
CONFIG = {
    "REAL_YIELD_THRESHOLD": 1.5,
    "SPREAD_THRESHOLD": 5.0,
    "GS_RATIO_THRESHOLD": 80.0,
    "INFLATION_THRESHOLD": 2.0
}

def send_discord(msg):
    requests.post(WEBHOOK_URL, json={"content": msg})

def get_ma200(ticker_symbol):
    # 200일 이동평균선 계산
    data = yf.Ticker(ticker_symbol).history(period="300d")
    return data['Close'].rolling(window=200).mean().iloc[-1]

def get_fred_data(series_id):
    # FRED에서 경제 지표 가져오기
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=60)
    return web.DataReader(series_id, 'fred', start, end).iloc[-1].values[0]

def check_market():
    # 1. 데이터 수집
    dxy = yf.Ticker("DX-Y.NYB").history(period="1d")['Close'].iloc[-1]
    gold = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
    silver = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
    
    # 2. 이동평균 및 경제지표
    dxy_ma200 = get_ma200("DX-Y.NYB")
    gold_ma200 = get_ma200("GC=F")
    real_yield = get_fred_data("REAINTRATREARAT10Y")
    spread = get_fred_data("BAMLH0A0HYM2EY")
    breakeven = get_fred_data("T10YIE")
    
    # 3. YES/NO 판단 로직
    r1 = "YES" if dxy < dxy_ma200 else "NO"
    r2 = "YES" if gold > gold_ma200 else "NO"
    r3 = "YES" if real_yield < CONFIG["REAL_YIELD_THRESHOLD"] else "NO"
    r4 = "YES" if (gold/silver) < CONFIG["GS_RATIO_THRESHOLD"] else "NO"
    r5 = "YES" if spread > CONFIG["SPREAD_THRESHOLD"] else "NO"
    r6 = "YES" if breakeven > CONFIG["INFLATION_THRESHOLD"] else "NO"

    # 4. 리포트 생성
    msg = (
        f"📊 **금 투자 전략 대시보드 ({datetime.date.today()})**\n"
        f"------------------------------\n"
        f"• 달러 약세 (DXY < 200MA): **{r1}** ({dxy:.2f})\n"
        f"• 금 상승세 (Gold > 200MA): **{r2}** ({gold:.2f})\n"
        f"• 저금리 (RealYield < {CONFIG['REAL_YIELD_THRESHOLD']}%): **{r3}** ({real_yield:.2f}%)\n"
        f"• 저평가 (G/S Ratio < {CONFIG['GS_RATIO_THRESHOLD']}): **{r4}** ({gold/silver:.2f})\n"
        f"• 시장 위기 (Spread > {CONFIG['SPREAD_THRESHOLD']}%): **{r5}** ({spread:.2f}%)\n"
        f"• 물가 상승 (Inflation > {CONFIG['INFLATION_THRESHOLD']}%): **{r6}** ({breakeven:.2f}%)\n"
        f"------------------------------\n"
        f"💡 YES 개수: {sum([r1=='YES', r2=='YES', r3=='YES', r4=='YES', r5=='YES', r6=='YES'])}/6"
    )
    send_discord(msg)

if __name__ == "__main__":
    check_market()
