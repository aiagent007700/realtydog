"""Environment-driven settings. See .env.example for the full list."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    database_url: str = "postgresql+psycopg2://localhost:5432/realtydog"
    environment: str = "dev"

    # Telegram
    telegram_bot_token: str = ""
    telegram_group_chat_id: str = ""
    allowed_telegram_ids: str = ""

    # External APIs
    google_maps_api_key: str = ""
    openrouter_api_key: str = ""
    llm_model: str = "openai/gpt-4o-mini"

    # Object storage
    s3_endpoint_url: str = ""
    s3_bucket: str = "realtydog-photos"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "us-east-1"

    # Email
    sendgrid_api_key: str = ""
    email_from: str = ""
    email_to: str = ""

    # Optional / later
    skiptrace_api_key: str = ""

    # JOB-002b: local path (or URL) to TAD's fixed-length PropertyData roll for land-use
    tarrant_roll_path: str = ""
    tarrant_roll_url: str = ""

    # Selection defaults (Layer-1 buy box)
    buybox_counties: str = "Dallas,Tarrant"  # primary counties (expand as more are ingested)
    buybox_min_acres: float = 5
    buybox_max_acres: float = 50  # cap out venue-sized parcels (0 disables); tunable
    buybox_min_sf: int = 15000
    buybox_max_purchase: int = 4_000_000
    buybox_max_all_in: int = 5_000_000
    # Affordability ceiling on assessed value — drops big-box / large operating commercial
    # that could never be a <=$4M buy. Tunable proxy; 0 disables.
    buybox_max_assessed: int = 6_000_000

    # Notification thresholds (motivation score buckets)
    motivation_hot: int = 60
    motivation_warm: int = 30

    @property
    def counties(self) -> list[str]:
        return [c.strip() for c in self.buybox_counties.split(",") if c.strip()]

    @property
    def allowed_ids(self) -> set[int]:
        return {int(x) for x in self.allowed_telegram_ids.split(",") if x.strip().isdigit()}


settings = Settings()
