from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google
    web_client_id: str
    android_client_id: str
    client_secret: str

    # FastAPI
    api_url: str

    # Database
    database_url: str
    sqlalchemy_echo: bool = False

    # Miscellaneous
    groq_api_key: str
    jwt_secret_key: str

    model_config = {"env_file": ".env"}


settings = Settings()
