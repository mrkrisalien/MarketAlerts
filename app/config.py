from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MarketCommand"
    timezone: str = "Asia/Kolkata"
    enable_live_crypto: bool = True
    enable_live_yahoo: bool = True
    coingecko_api_key: str = ""
    refresh_seconds: int = 3
    enable_live_binance: bool = True
    broker_api_key: str = ""
    broker_api_secret: str = ""
    board_password: str = ""


settings = Settings()
