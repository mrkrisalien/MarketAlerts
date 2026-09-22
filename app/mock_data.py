from __future__ import annotations

from app.models import Quote
from app.timeutil import now_ist, spark


def _q(**kwargs) -> Quote:
    ts = now_ist()
    kwargs.setdefault("as_of", ts)
    kwargs.setdefault("retrieved_at", ts)
    if "sparkline" not in kwargs:
        kwargs["sparkline"] = spark(kwargs["ltp"])
    if "prev_close" not in kwargs:
        kwargs["prev_close"] = round(kwargs["ltp"] / (1 + kwargs["change_pct"] / 100), 4)
    if "change_abs" not in kwargs:
        kwargs["change_abs"] = round(kwargs["ltp"] - kwargs["prev_close"], 4)
    return Quote(**kwargs)


def mock_quotes() -> list[Quote]:
    src = "mock"
    st = "mock"
    return [
        _q(symbol="BTC", canonical="CRYPTO:BTC", name="Bitcoin", market="crypto", ltp=79486, change_pct=-1.24, currency="USD", high=81245, low=77932, volume=2.84e10, source="CoinGecko (cached mock)", source_type=st, source_url="https://www.coingecko.com"),
        _q(symbol="ETH", canonical="CRYPTO:ETH", name="Ethereum", market="crypto", ltp=3245, change_pct=0.82, currency="USD", high=3310, low=3188, volume=1.2e10, source="CoinGecko (cached mock)", source_type=st, source_url="https://www.coingecko.com"),
        _q(symbol="SOL", canonical="CRYPTO:SOL", name="Solana", market="crypto", ltp=187.36, change_pct=0.91, currency="USD", source="CoinGecko (cached mock)", source_type=st),
        _q(symbol="XRP", canonical="CRYPTO:XRP", name="XRP", market="crypto", ltp=0.592, change_pct=1.36, currency="USD", source="CoinGecko (cached mock)", source_type=st),
        _q(symbol="BNB", canonical="CRYPTO:BNB", name="BNB", market="crypto", ltp=588.21, change_pct=-0.65, currency="USD", source="CoinGecko (cached mock)", source_type=st),
        _q(symbol="NIFTY 50", canonical="NSE:NIFTY50", name="NIFTY 50", market="nse", ltp=24612, change_pct=-0.36, currency="INR", high=24732, low=24510, volume=3.284e8, oi=None, source="NSE snapshot (mock until broker/NSE feed)", source_type=st, source_url="https://www.nseindia.com"),
        _q(symbol="BANKNIFTY", canonical="NSE:BANKNIFTY", name="BANKNIFTY", market="nse", ltp=52341, change_pct=-0.78, currency="INR", source="NSE snapshot (mock)", source_type=st, source_url="https://www.nseindia.com"),
        _q(symbol="SENSEX", canonical="BSE:SENSEX", name="SENSEX", market="nse", ltp=80437, change_pct=-0.41, currency="INR", source="BSE/NSE snapshot (mock)", source_type=st),
        _q(symbol="FINNIFTY", canonical="NSE:FINNIFTY", name="FINNIFTY", market="nse", ltp=23840, change_pct=-0.52, currency="INR", source="NSE snapshot (mock)", source_type=st),
        _q(symbol="MIDCAP", canonical="NSE:NIFTYMIDCAP", name="NIFTY MIDCAP", market="nse", ltp=13210, change_pct=0.18, currency="INR", source="NSE snapshot (mock)", source_type=st),
        _q(symbol="INDIA VIX", canonical="NSE:INDIAVIX", name="INDIA VIX", market="nse", ltp=13.84, change_pct=8.4, currency="INR", source="NSE snapshot (mock)", source_type=st, volatility="elevated"),
        _q(symbol="GOLD", canonical="MCX:GOLD", name="Gold (MCX)", market="mcx", ltp=73658, change_pct=1.12, currency="INR", high=73812, low=72621, volume=182100, oi=415300, source="MCX market watch (mock until broker/MCX)", source_type=st, source_url="https://www.mcxindia.com/market-data/market-watch"),
        _q(symbol="SILVER", canonical="MCX:SILVER", name="Silver", market="mcx", ltp=88321, change_pct=1.98, currency="INR", source="MCX (mock)", source_type=st),
        _q(symbol="CRUDE", canonical="MCX:CRUDE", name="Crude Oil", market="mcx", ltp=5842, change_pct=0.64, currency="INR", source="MCX (mock)", source_type=st),
        _q(symbol="NATGAS", canonical="MCX:NATGAS", name="Natural Gas", market="mcx", ltp=245.60, change_pct=-1.23, currency="INR", source="MCX (mock)", source_type=st),
        _q(symbol="COPPER", canonical="MCX:COPPER", name="Copper", market="mcx", ltp=785.40, change_pct=0.41, currency="INR", source="MCX (mock)", source_type=st),
        _q(symbol="ALUMINIUM", canonical="MCX:ALUMINIUM", name="Aluminium", market="mcx", ltp=228.40, change_pct=0.18, currency="INR", source="MCX (mock)", source_type=st),
        _q(symbol="ZINC", canonical="MCX:ZINC", name="Zinc", market="mcx", ltp=268.50, change_pct=0.22, currency="INR", source="MCX (mock)", source_type=st),
        _q(symbol="DXY", canonical="FX:DXY", name="DXY", market="fx", ltp=103.27, change_pct=-0.21, currency="USD", source="Yahoo Finance (mock fallback)", source_type=st),
        _q(symbol="US 10Y", canonical="RATES:US10Y", name="US 10Y", market="rates", ltp=4.32, change_pct=0.03, change_abs=0.01, currency="%", source="Treasury/Yahoo (mock fallback)", source_type=st),
        _q(symbol="S&P 500", canonical="US:SPX", name="S&P 500", market="global", ltp=4502.10, change_pct=0.48, currency="USD", source="Yahoo Finance (mock)", source_type=st),
        _q(symbol="NASDAQ", canonical="US:NDX", name="NASDAQ", market="global", ltp=15730.20, change_pct=0.62, currency="USD", source="Yahoo Finance (mock)", source_type=st),
        _q(symbol="DOW JONES", canonical="US:DJI", name="DOW JONES", market="global", ltp=34618.90, change_pct=0.31, currency="USD", source="Yahoo Finance (mock)", source_type=st),
        _q(symbol="FTSE 100", canonical="UK:FTSE", name="FTSE 100", market="global", ltp=7632.40, change_pct=-0.28, currency="GBP", source="Yahoo Finance (mock)", source_type=st),
        _q(symbol="DAX", canonical="DE:DAX", name="DAX", market="global", ltp=18412.60, change_pct=-0.11, currency="EUR", source="Yahoo Finance (mock)", source_type=st),
        _q(symbol="NIKKEI 225", canonical="JP:N225", name="NIKKEI 225", market="global", ltp=32678.10, change_pct=1.04, currency="JPY", source="Yahoo Finance (mock)", source_type=st),
        _q(symbol="HANG SENG", canonical="HK:HSI", name="Hang Seng", market="global", ltp=17892.30, change_pct=0.42, currency="HKD", source="Yahoo Finance (mock)", source_type=st),
        _q(symbol="RELIANCE", canonical="NSE:RELIANCE", name="RELIANCE", market="nse", ltp=2612.45, change_pct=0.62, currency="INR", source="Broker/NSE (mock)", source_type=st),
        _q(symbol="HDFCBANK", canonical="NSE:HDFCBANK", name="HDFCBANK", market="nse", ltp=1634.20, change_pct=-0.38, currency="INR", source="Broker/NSE (mock)", source_type=st),
        _q(symbol="TCS", canonical="NSE:TCS", name="TCS", market="nse", ltp=3872.10, change_pct=0.21, currency="INR", source="Broker/NSE (mock)", source_type=st),
        _q(symbol="INFY", canonical="NSE:INFY", name="INFY", market="nse", ltp=1518.90, change_pct=-0.45, currency="INR", source="Broker/NSE (mock)", source_type=st),
        _q(symbol="ICICIBANK", canonical="NSE:ICICIBANK", name="ICICIBANK", market="nse", ltp=1239.80, change_pct=0.11, currency="INR", source="Broker/NSE (mock)", source_type=st),
        _q(symbol="SBIN", canonical="NSE:SBIN", name="SBIN", market="nse", ltp=812.30, change_pct=-0.63, currency="INR", source="Broker/NSE (mock)", source_type=st),
        _q(symbol="BHARTIARTL", canonical="NSE:BHARTIARTL", name="BHARTIARTL", market="nse", ltp=1542.00, change_pct=0.35, currency="INR", source="Broker/NSE (mock)", source_type=st),
        _q(symbol="LT", canonical="NSE:LT", name="LT", market="nse", ltp=3621.50, change_pct=0.18, currency="INR", source="Broker/NSE (mock)", source_type=st),
    ]
