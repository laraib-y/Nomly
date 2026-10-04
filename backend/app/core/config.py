from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from the environment.

    Secrets stay on the server. The frontend only receives NEXT_PUBLIC_API_URL,
    which is not read here.
    """

    database_url: str = ""
    gemini_api_key: str = ""
    geoapify_api_key: str = ""
    embedding_model: str = "gemini-embedding-001"
    elevenlabs_api_key: str = ""
    elevenlabs_stt_model: str = "scribe_v2"
    elevenlabs_tts_model: str = "eleven_flash_v2_5"
    elevenlabs_tts_voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    frontend_url: str = ""
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    auth_cookie_name: str = "nomly_session"
    auth_session_days: int = 30
    # Keep "lax" when the site and API share a registrable domain. A cross-site
    # deployment needs "none", which browsers only accept together with Secure.
    auth_cookie_samesite: str = "lax"
    auth_cookie_secure: bool = False

    model_config = SettingsConfigDict(
        # Later files win. The file next to the process overrides the repo-root file,
        # so a blank GEOAPIFY_API_KEY in ../.env does not erase one set in backend/.env.
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cookie_samesite(self) -> str:
        value = self.auth_cookie_samesite.strip().lower()
        return value if value in {"lax", "strict", "none"} else "lax"

    @property
    def cookie_secure(self) -> bool:
        return self.auth_cookie_secure or self.cookie_samesite == "none"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        frontend = self.frontend_url.strip()
        if frontend and frontend not in origins:
            origins.append(frontend)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
