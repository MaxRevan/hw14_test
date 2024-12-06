from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    database_test_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    verification_token_expire_hours: int
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int
    mail_server: str
    redis_url: str
    cloudinary_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()