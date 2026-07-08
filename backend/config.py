from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    #  App
    app_name: str = "Trading Simulation Platform"
    debug: bool = True

    #  Database 
    # SQLite for local development and testing.
    # To switch to PostgreSQL later, change this URL
    database_url: str = "sqlite+aiosqlite:///./trading_sim.db"

    #  JWT Authentication 
    secret_key: str = "change-this-to-a-long-random-string-before-deployment"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    #  New User Account 
    initial_balance: float = 1_000_00.0  # every new user starts with ₹1 lakh

    # Market Data
    historical_data_dir: str = "./data"  # folder for storing CSV files 

    # Simulation
    simulation_tick_interval: float = 1.0  # seconds between each price update

    # Reads values from a .env file if it exists
    # So to override any setting without touching this file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Global configuration instance
settings = Settings()
