from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Sirf types define karein, values .env se aayengi
    PROJECT_NAME: str
    API_V1_STR: str
    JWT_SECRET: str
    ALGORITHM: str

    # Database
    MONGODB_URL: str
    DATABASE_NAME: str

    # Email Settings
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool

    # Google Auth
    GOOGLE_CLIENT_ID: str
    #Gemini KEY
    GEMINI_API_KEY: str
    #DEEP_SEEK KEY
    DEEP_SEEK_KEY: str
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    # Yeh line Pydantic ko kehti hai ke .env file ko read karo
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()