import openai
import asyncio
import json
import os
import re
import requests
import base64
from typing import Dict, List, Optional
from anthropic import Anthropic
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        """
        Initialize AI client with OpenAI and Claude (Anthropic) support
        """
        # Load API keys from environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Initialize clients
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
            self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
            logger.info("OpenAI client initialized")
        else:
            self.openai_client = None
            logger.warning("OpenAI API key not found")
            
        if self.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)
            logger.info("Anthropic client initialized")
        else:
            self.anthropic_client = None
            logger.warning("Anthropic API key not found")
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 for AI processing
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {str(e)}")
            return ""
    
    def _is_image_file(self, file_path: str) -> bool:
        """
        Check if file is an image
        """
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        return any(file_path.lower().endswith(ext) for ext in image_extensions)
    
    def _get_image_files_from_context(self, context: Optional[Dict] = None) -> List[str]:
        """
        Extract image file paths from context
        """
        if not context:
            return []
        
        # Check if there are uploaded files in context
        uploaded_files = context.get('uploaded_files', [])
        image_files = []
        
        for file_path in uploaded_files:
            if self._is_image_file(file_path):
                image_files.append(file_path)
        
        return image_files
    
    def _needs_current_info(self, message: str) -> bool:
        """
        Determine if the message requires current/recent information
        """
        current_info_keywords = [
            'latest', 'recent', 'current', 'new', 'update', 'updates', 'newest',
            '2024', '2025', 'this year', 'recently', 'now', 'today',
            'what\'s new', 'latest version', 'recent changes', 'current version'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in current_info_keywords)
    
    async def _search_web(self, query: str) -> str:
        """
        Search the web for current information
        """
        try:
            # Use DuckDuckGo Instant Answer API (free, no API key required)
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant information
                result = ""
                if data.get('Abstract'):
                    result += f"Current Information: {data['Abstract']}\n"
                if data.get('AbstractText'):
                    result += f"{data['AbstractText']}\n"
                if data.get('Definition'):
                    result += f"Definition: {data['Definition']}\n"
                
                # Add related topics if available
                if data.get('RelatedTopics'):
                    topics = data['RelatedTopics'][:3]  # Limit to 3 topics
                    for topic in topics:
                        if isinstance(topic, dict) and topic.get('Text'):
                            result += f"Related: {topic['Text']}\n"
                
                if result.strip():
                    return result.strip()
            
            # Fallback: Simple web scraping approach for Power BI specific queries
            if 'power bi' in query.lower():
                return self._get_powerbi_updates()
            
            return ""
            
        except Exception as e:
            logger.warning(f"Web search failed: {str(e)}")
            return ""
    
    def _get_powerbi_updates(self) -> str:
        """
        Get current Power BI information from Microsoft's official sources
        """
        try:
            # This would ideally scrape Microsoft's Power BI blog or documentation
            # For now, we'll provide a template that encourages checking official sources
            current_year = datetime.now().year
            current_month = datetime.now().strftime("%B")
            
            return f"""
Current Power BI Information (as of {current_month} {current_year}):

Microsoft regularly updates Power BI with new features and improvements. Recent updates typically include:

• Enhanced AI capabilities and Copilot integration
• New visualization types and custom visuals
• Improved data connectivity options
• Performance optimizations
• Security and governance enhancements
• Mobile app improvements

For the most current and detailed information about Power BI updates:
1. Visit the official Microsoft Power BI Blog: https://powerbi.microsoft.com/blog/
2. Check Power BI Documentation: https://docs.microsoft.com/power-bi/
3. Review the Power BI Release Notes: https://docs.microsoft.com/power-bi/fundamentals/desktop-latest-update

Note: Power BI receives monthly updates with new features, and the service is continuously improved with cloud updates.
"""
        except Exception as e:
            logger.warning(f"Failed to get Power BI updates: {str(e)}")
            return ""
    
    async def get_response(self, message: str, conversation_id: str, context: Optional[Dict] = None) -> str:
        """
        Get AI response using the best available model with current information when needed
        """
        try:
            # Check if the message needs current information
            current_info = ""
            if self._needs_current_info(message):
                logger.info("Message requires current information, searching web...")
                current_info = await self._search_web(message)
            
            # Add current information to context if found
            enhanced_context = context or {}
            if current_info:
                enhanced_context['current_info'] = current_info
                enhanced_context['search_timestamp'] = datetime.now().isoformat()
            
            # Try OpenAI first (GPT-4)
            if self.openai_client:
                try:
                    return await self._get_openai_response(message, conversation_id, enhanced_context)
                except Exception as openai_error:
                    logger.warning(f"OpenAI failed: {str(openai_error)}")
                    if self.anthropic_client:
                        logger.info("Falling back to Anthropic Claude...")
                        return await self._get_anthropic_response(message, conversation_id, enhanced_context)
                    else:
                        raise openai_error
            
            # Use Anthropic if OpenAI not available
            elif self.anthropic_client:
                return await self._get_anthropic_response(message, conversation_id, enhanced_context)
            
            else:
                raise ValueError("No AI API keys configured. Please add OPENAI_API_KEY or ANTHROPIC_API_KEY to your .env file.")
                
        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            raise e
    
    async def analyze_dashboard_request(self, user_request: str, data_info: Dict) -> Dict:
        """
        Analyze user request and data to create a detailed dashboard plan
        """
        analysis_prompt = f"""
You are an expert Power BI dashboard designer. Analyze this request and data to create a detailed dashboard plan.

USER REQUEST: {user_request}

DATA INFORMATION:
{json.dumps(data_info, indent=2)}

Create a comprehensive dashboard plan in JSON format with these components:

{{
    "title": "Dashboard Title",
    "description": "What this dashboard shows",
    "dashboard_type": "sales/financial/operational/executive/etc",
    "visualizations": [
        {{
            "type": "chart_type (bar, line, pie, table, card, etc)",
            "title": "Chart Title",
            "data_fields": ["field1", "field2"],
            "purpose": "What this chart shows",
            "position": {{
                "row": 1,
                "column": 1,
                "width": 6,
                "height": 4
            }}
        }}
    ],
    "kpis": [
        {{
            "name": "KPI Name",
            "calculation": "SUM/AVERAGE/COUNT/etc",
            "field": "data_field",
            "format": "currency/percentage/number"
        }}
    ],
    "filters": [
        {{
            "field": "field_name",
            "type": "slicer/dropdown",
            "position": "top/side"
        }}
    ],
    "color_theme": "blue/green/red/professional",
    "layout": "single_page/multi_page",
    "features": ["List of key features this dashboard provides"]
}}

Make sure the plan uses the actual field names from the data and creates a professional, useful dashboard.
"""
        
        try:
            if self.openai_client:
                response = await self._get_openai_response(analysis_prompt, "dashboard_analysis")
            elif self.anthropic_client:
                response = await self._get_anthropic_response(analysis_prompt, "dashboard_analysis")
            else:
                raise ValueError("No AI API keys configured. Cannot analyze dashboard request without AI integration.")
            
            # Try to parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Extract JSON from response if it's wrapped in text
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    return json.loads(response[start:end])
                else:
                    raise ValueError("Could not parse AI response for dashboard analysis")
                    
        except Exception as e:
            logger.error(f"Error analyzing dashboard request: {str(e)}")
            raise e
    
    async def generate_dax_formulas(self, dashboard_plan: Dict, data_schema: Dict) -> Dict:
        """
        Generate DAX formulas for calculated measures
        """
        dax_prompt = f"""
You are a Power BI DAX expert. Generate DAX formulas for this dashboard.

DASHBOARD PLAN:
{json.dumps(dashboard_plan, indent=2)}

DATA SCHEMA:
{json.dumps(data_schema, indent=2)}

Create DAX formulas in JSON format:

{{
    "measures": [
        {{
            "name": "Measure Name",
            "dax": "DAX Formula",
            "description": "What this measure calculates"
        }}
    ],
    "calculated_columns": [
        {{
            "name": "Column Name",
            "dax": "DAX Formula",
            "table": "Table Name"
        }}
    ]
}}

Generate proper DAX syntax using the actual table and column names from the schema.
"""
        
        try:
            if self.openai_client:
                response = await self._get_openai_response(dax_prompt, "dax_generation")
            elif self.anthropic_client:
                response = await self._get_anthropic_response(dax_prompt, "dax_generation")
            else:
                raise ValueError("No AI API keys configured. Cannot generate DAX formulas without AI integration.")
            
            # Parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    return json.loads(response[start:end])
                else:
                    raise ValueError("Could not parse AI response for DAX generation")
                    
        except Exception as e:
            logger.error(f"Error generating DAX formulas: {str(e)}")
            raise e
    
    async def _get_openai_response(self, message: str, conversation_id: str, context: Optional[Dict] = None) -> str:
        """
        Get response from OpenAI GPT-4 with image support
        """
        try:
            # Build system message with current information if available
            system_content = """You are an expert Power BI dashboard designer and data analyst. 
You help users create professional dashboards by understanding their needs and providing detailed plans.
Always provide helpful, accurate, and actionable responses.
When analyzing images, describe what you see in detail and explain how it relates to data visualization or dashboard creation."""
            
            # Add current information to system message if available
            if context and context.get('current_info'):
                system_content += f"""

CURRENT INFORMATION (as of {context.get('search_timestamp', 'now')}):
{context['current_info']}

Use this current information to provide up-to-date responses. Do not mention knowledge cutoff dates."""
            
            messages = [
                {
                    "role": "system",
                    "content": system_content
                }
            ]
            
            # Check for images in context
            image_files = self._get_image_files_from_context(context)
            
            if image_files:
                # Create user message with images
                user_content = [{"type": "text", "text": message}]
                
                for image_path in image_files:
                    base64_image = self._encode_image(image_path)
                    if base64_image:
                        # Determine image type
                        image_type = "jpeg"
                        if image_path.lower().endswith('.png'):
                            image_type = "png"
                        elif image_path.lower().endswith('.gif'):
                            image_type = "gif"
                        elif image_path.lower().endswith('.webp'):
                            image_type = "webp"
                        
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_type};base64,{base64_image}",
                                "detail": "high"
                            }
                        })
                
                messages.append({
                    "role": "user",
                    "content": user_content
                })
            else:
                # Regular text message
                messages.append({
                    "role": "user",
                    "content": message
                })
            
            # Use vision model if images are present
            model = "gpt-4o" if image_files else "gpt-4o"
            
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error with OpenAI: {str(e)}")
            raise e
    
    async def _get_anthropic_response(self, message: str, conversation_id: str, context: Optional[Dict] = None) -> str:
        """
        Get response from Anthropic Claude
        """
        try:
            # Check for images in context
            image_files = self._get_image_files_from_context(context)
            
            # Build system message
            system_content = """You are an expert Power BI dashboard designer and data analyst. 
You help users create professional dashboards by understanding their needs and providing detailed plans.
Always provide helpful, accurate, and actionable responses.
When analyzing images, describe what you see in detail and explain how it relates to data visualization or dashboard creation."""
            
            # Add current information if available
            if context and context.get('current_info'):
                system_content += f"""

CURRENT INFORMATION (as of {context.get('search_timestamp', 'now')}):
{context['current_info']}

Use this current information to provide up-to-date responses. Do not mention knowledge cutoff dates."""
            
            # Build user content with images if present
            if image_files:
                user_content = [{"type": "text", "text": message}]
                
                for image_path in image_files:
                    base64_image = self._encode_image(image_path)
                    if base64_image:
                        # Determine media type
                        media_type = "image/jpeg"
                        if image_path.lower().endswith('.png'):
                            media_type = "image/png"
                        elif image_path.lower().endswith('.gif'):
                            media_type = "image/gif"
                        elif image_path.lower().endswith('.webp'):
                            media_type = "image/webp"
                        
                        user_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        })
            else:
                user_content = message
            
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                system=system_content,
                messages=[
                    {
                        "role": "user",
                        "content": user_content
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error with Anthropic: {str(e)}")
            raise e
    

    

