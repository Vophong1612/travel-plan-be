import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv
load_dotenv()


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
    mongodb_port: int = Field(default=32768, env="MONGODB_PORT")
    mongodb_database: str = Field(default="travel_planner", env="MONGODB_DATABASE")
    mongodb_username: Optional[str] = Field(default="root", env="MONGODB_USERNAME")
    mongodb_password: Optional[str] = Field(default="password12345", env="MONGODB_PASSWORD")
    mongodb_auth_database: Optional[str] = Field(None, env="MONGODB_AUTH_DATABASE")
    mongodb_uri: Optional[str] = Field(default="mongodb://root:password12345@localhost:32768/?directConnection=true", env="MONGODB_URI")
    
    # Database selection
    use_mongodb: bool = Field(default=True, env="USE_MONGODB")
    
    # AI Model Configuration
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-pro", env="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.1, env="GEMINI_TEMPERATURE")
    gemini_max_tokens: int = Field(default=4096, env="GEMINI_MAX_TOKENS")
    
    # Google Maps
    google_maps_api_key: str = Field(..., env="GOOGLE_MAPS_API_KEY")

settings = Settings() 