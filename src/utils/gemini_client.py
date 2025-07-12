"""
Gemini API Client for AI Travel Planner

This module provides a client for interacting with Google's Gemini API directly.
"""

import logging
from typing import Dict, Any, List, Optional, Union
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import json
import asyncio
from datetime import datetime

from src.config.settings import settings


class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self):
        self.logger = logging.getLogger("gemini_client")
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client."""
        try:
            # Configure the API key
            genai.configure(api_key=settings.gemini_api_key)
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name=settings.gemini_model,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.gemini_temperature,
                    max_output_tokens=settings.gemini_max_tokens,
                    top_p=0.95,
                    top_k=40
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            
            self.logger.info("Gemini client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise
    
    async def generate_response(self, 
                              prompt: str, 
                              system_prompt: Optional[str] = None,
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a response from Gemini."""
        try:
            # Build the full prompt
            full_prompt = self._build_prompt(prompt, system_prompt, context)
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.model.generate_content, full_prompt
            )
            
            if response.text:
                return response.text.strip()
            else:
                self.logger.warning("Empty response from Gemini")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise
    
    async def generate_json_response(self, 
                                   prompt: str, 
                                   system_prompt: Optional[str] = None,
                                   context: Optional[Dict[str, Any]] = None,
                                   schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a JSON response from Gemini."""
        try:
            # Add JSON formatting instruction
            json_instruction = "\n\nPlease respond with valid JSON only. Do not include any other text or markdown formatting."
            if schema:
                json_instruction += f"\n\nThe JSON should follow this schema: {json.dumps(schema, indent=2)}"
            
            full_prompt = prompt + json_instruction
            
            # Generate response
            response_text = await self.generate_response(full_prompt, system_prompt, context)
            
            # Parse JSON
            try:
                # Clean up the response (remove markdown formatting if present)
                cleaned_response = response_text.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                return json.loads(cleaned_response)
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {str(e)}")
                self.logger.error(f"Raw response: {response_text}")
                # Return a structured error response
                return {
                    "error": "Failed to parse JSON response",
                    "raw_response": response_text,
                    "parse_error": str(e)
                }
                
        except Exception as e:
            self.logger.error(f"Error generating JSON response: {str(e)}")
            raise
    
    def _build_prompt(self, 
                     prompt: str, 
                     system_prompt: Optional[str] = None,
                     context: Optional[Dict[str, Any]] = None) -> str:
        """Build the full prompt with system instructions and context."""
        parts = []
        
        # Add system prompt
        if system_prompt:
            parts.append(f"System Instructions: {system_prompt}")
        
        # Add context
        if context:
            parts.append(f"Context: {json.dumps(context, indent=2)}")
        
        # Add main prompt
        parts.append(f"User Request: {prompt}")
        
        return "\n\n".join(parts)
    
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            system_prompt: Optional[str] = None) -> str:
        """Handle multi-turn conversation."""
        try:
            # Start a chat session
            chat = self.model.start_chat(history=[])
            
            # Add system prompt if provided
            if system_prompt:
                await asyncio.get_event_loop().run_in_executor(
                    None, chat.send_message, f"System: {system_prompt}"
                )
            
            # Process messages
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                
                if role == "user":
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, chat.send_message, content
                    )
                    
            # Return the last response
            return response.text.strip() if response.text else ""
            
        except Exception as e:
            self.logger.error(f"Error in chat completion: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model_name": settings.gemini_model,
            "temperature": settings.gemini_temperature,
            "max_tokens": settings.gemini_max_tokens,
            "api_configured": bool(settings.gemini_api_key)
        }


# Global client instance
gemini_client = GeminiClient() 