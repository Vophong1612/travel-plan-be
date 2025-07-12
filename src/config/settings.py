import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = Field(default="AI Travel Planner", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Database Configuration
    # Option 1: Firestore (Google Cloud)
    firestore_project_id: Optional[str] = Field(None, env="FIRESTORE_PROJECT_ID")
    firestore_credentials_path: Optional[str] = Field(None, env="FIRESTORE_CREDENTIALS_PATH")
    
    # Option 2: MongoDB (On-premise alternative)
    mongodb_host: str = Field(default="localhost", env="MONGODB_HOST")
    mongodb_port: int = Field(default=27017, env="MONGODB_PORT")
    mongodb_database: str = Field(default="travel_planner", env="MONGODB_DATABASE")
    mongodb_username: Optional[str] = Field(None, env="MONGODB_USERNAME")
    mongodb_password: Optional[str] = Field(None, env="MONGODB_PASSWORD")
    mongodb_auth_database: Optional[str] = Field(None, env="MONGODB_AUTH_DATABASE")
    
    # Database selection
    use_mongodb: bool = Field(default=False, env="USE_MONGODB")
    
    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    
    # AI Model Configuration
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-pro", env="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.1, env="GEMINI_TEMPERATURE")
    gemini_max_tokens: int = Field(default=4096, env="GEMINI_MAX_TOKENS")
    
    # Google Cloud (Optional - only needed for Firestore)
    google_cloud_project: Optional[str] = Field(None, env="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")
    
    # External APIs
    google_maps_api_key: str = Field(..., env="GOOGLE_MAPS_API_KEY")
    openweather_api_key: Optional[str] = Field(None, env="OPENWEATHER_API_KEY")
    amadeus_api_key: Optional[str] = Field(None, env="AMADEUS_API_KEY")
    amadeus_api_secret: Optional[str] = Field(None, env="AMADEUS_API_SECRET")
    
    # MCP Configuration
    mcp_server_host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    mcp_server_port: int = Field(default=8080, env="MCP_SERVER_PORT")
    
    # Authentication
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Agent Configuration
    max_agent_iterations: int = Field(default=10, env="MAX_AGENT_ITERATIONS")
    agent_timeout_seconds: int = Field(default=120, env="AGENT_TIMEOUT_SECONDS")
    
    # Trip Planning
    max_trip_days: int = Field(default=30, env="MAX_TRIP_DAYS")
    max_activities_per_day: int = Field(default=8, env="MAX_ACTIVITIES_PER_DAY")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 