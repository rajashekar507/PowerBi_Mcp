from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.callbacks.base import BaseCallbackHandler
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .ai_client import AIClient
from .data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardCreationCallback(BaseCallbackHandler):
    """Custom callback to track dashboard creation progress"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.steps = []
        
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Called when a tool starts"""
        self.steps.append({
            "step": serialized.get("name", "unknown"),
            "input": input_str,
            "timestamp": datetime.now().isoformat(),
            "status": "started"
        })
        logger.info(f"Starting tool: {serialized.get('name', 'unknown')}")
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool ends"""
        if self.steps:
            self.steps[-1]["status"] = "completed"
            self.steps[-1]["output"] = output[:200]  # Truncate long outputs
        logger.info(f"Tool completed: {output[:100]}")

class DashboardController:
    """
    LangChain-powered controller for orchestrating dashboard creation
    """
    
    def __init__(self):
        self.ai_client = AIClient()
        self.data_processor = DataProcessor()
        self.memories = {}  # Store conversation memories by ID
        
    def get_memory(self, conversation_id: str) -> ConversationBufferMemory:
        """Get or create memory for a conversation"""
        if conversation_id not in self.memories:
            self.memories[conversation_id] = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
        return self.memories[conversation_id]
    
    async def create_dashboard_plan(self, user_request: str, file_paths: List[str], conversation_id: str) -> Dict:
        """
        Create a comprehensive dashboard plan using AI analysis
        """
        try:
            logger.info(f"Creating dashboard plan for conversation {conversation_id}")
            
            # Step 1: Analyze uploaded data
            data_analysis = await self.data_processor.analyze_files(file_paths)
            
            # Step 2: Get AI analysis of the request and data
            dashboard_plan = await self.ai_client.analyze_dashboard_request(
                user_request, 
                data_analysis
            )
            
            # Step 3: Enhance plan with LangChain memory context
            memory = self.get_memory(conversation_id)
            conversation_context = self._get_conversation_context(memory)
            
            # Step 4: Refine plan based on conversation context
            if conversation_context:
                enhanced_plan = await self._enhance_plan_with_context(
                    dashboard_plan, 
                    conversation_context, 
                    user_request
                )
                dashboard_plan.update(enhanced_plan)
            
            # Step 5: Generate DAX formulas for calculated measures
            dax_formulas = await self.ai_client.generate_dax_formulas(
                dashboard_plan, 
                data_analysis.get("schema", {})
            )
            dashboard_plan["dax_formulas"] = dax_formulas
            
            # Step 6: Store plan in memory for future reference
            self._store_plan_in_memory(conversation_id, dashboard_plan, user_request)
            
            logger.info("Dashboard plan created successfully")
            return dashboard_plan
            
        except Exception as e:
            logger.error(f"Error creating dashboard plan: {str(e)}")
            # Return a fallback plan
            return self._create_fallback_plan(user_request, file_paths)
    
    async def modify_dashboard_plan(self, conversation_id: str, modification_request: str) -> Dict:
        """
        Modify an existing dashboard plan based on user feedback
        """
        try:
            memory = self.get_memory(conversation_id)
            
            # Get the last dashboard plan from memory
            current_plan = self._get_last_plan_from_memory(conversation_id)
            if not current_plan:
                raise ValueError("No existing dashboard plan found")
            
            # Use AI to understand modification request
            modification_prompt = f"""
            Current dashboard plan: {json.dumps(current_plan, indent=2)}
            
            User wants to modify: {modification_request}
            
            Return the updated dashboard plan in the same JSON format, incorporating the requested changes.
            Only modify the specific parts mentioned by the user, keep everything else the same.
            """
            
            # Get AI response for modifications
            if self.ai_client.openai_client or self.ai_client.anthropic_client:
                response = await self.ai_client.get_response(modification_prompt, conversation_id)
                
                # Try to parse JSON response
                try:
                    modified_plan = json.loads(response)
                except json.JSONDecodeError:
                    # Extract JSON from response
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start >= 0 and end > start:
                        modified_plan = json.loads(response[start:end])
                    else:
                        raise ValueError("Could not parse modification response")
            else:
                # Fallback: basic modification logic
                modified_plan = self._apply_basic_modifications(current_plan, modification_request)
            
            # Store modified plan in memory
            self._store_plan_in_memory(conversation_id, modified_plan, modification_request)
            
            return modified_plan
            
        except Exception as e:
            logger.error(f"Error modifying dashboard plan: {str(e)}")
            raise e
    
    async def execute_dashboard_workflow(self, dashboard_plan: Dict, data_paths: List[str], conversation_id: str) -> Dict:
        """
        Execute the complete dashboard creation workflow
        """
        workflow_steps = [
            {"name": "validate_plan", "description": "Validate dashboard plan"},
            {"name": "process_data", "description": "Process and clean data"},
            {"name": "create_measures", "description": "Create DAX measures"},
            {"name": "build_visuals", "description": "Build visualizations"},
            {"name": "apply_formatting", "description": "Apply themes and formatting"},
            {"name": "finalize_dashboard", "description": "Finalize and publish dashboard"}
        ]
        
        results = {}
        
        for i, step in enumerate(workflow_steps):
            try:
                logger.info(f"Executing step {i+1}/{len(workflow_steps)}: {step['description']}")
                
                # Execute each step
                step_result = await self._execute_workflow_step(
                    step["name"], 
                    dashboard_plan, 
                    data_paths, 
                    conversation_id,
                    results
                )
                
                results[step["name"]] = step_result
                
                # Add to memory
                memory = self.get_memory(conversation_id)
                memory.chat_memory.add_ai_message(f"✅ Completed: {step['description']}")
                
            except Exception as e:
                logger.error(f"Error in workflow step {step['name']}: {str(e)}")
                results[step["name"]] = {"error": str(e)}
                
                # Try to recover or skip step
                if step["name"] in ["create_measures", "apply_formatting"]:
                    # These are optional steps, continue workflow
                    continue
                else:
                    # Critical step failed, abort workflow
                    raise e
        
        return results
    
    async def _execute_workflow_step(self, step_name: str, dashboard_plan: Dict, data_paths: List[str], conversation_id: str, previous_results: Dict) -> Dict:
        """
        Execute a single workflow step
        """
        if step_name == "validate_plan":
            return await self._validate_plan(dashboard_plan)
        
        elif step_name == "process_data":
            return await self.data_processor.process_for_powerbi(data_paths, dashboard_plan)
        
        elif step_name == "create_measures":
            return await self._create_dax_measures(dashboard_plan)
        
        elif step_name == "build_visuals":
            return await self._build_visualizations(dashboard_plan, previous_results.get("process_data", {}))
        
        elif step_name == "apply_formatting":
            return await self._apply_formatting(dashboard_plan)
        
        elif step_name == "finalize_dashboard":
            return await self._finalize_dashboard(dashboard_plan, previous_results)
        
        else:
            raise ValueError(f"Unknown workflow step: {step_name}")
    
    async def _validate_plan(self, dashboard_plan: Dict) -> Dict:
        """Validate the dashboard plan"""
        required_fields = ["title", "visualizations"]
        missing_fields = [field for field in required_fields if field not in dashboard_plan]
        
        if missing_fields:
            raise ValueError(f"Dashboard plan missing required fields: {missing_fields}")
        
        return {
            "status": "valid",
            "visualizations_count": len(dashboard_plan.get("visualizations", [])),
            "kpis_count": len(dashboard_plan.get("kpis", []))
        }
    
    async def _create_dax_measures(self, dashboard_plan: Dict) -> Dict:
        """Create DAX measures for the dashboard"""
        dax_formulas = dashboard_plan.get("dax_formulas", {})
        measures = dax_formulas.get("measures", [])
        
        # Validate DAX syntax (basic validation)
        valid_measures = []
        invalid_measures = []
        
        for measure in measures:
            if self._validate_dax_syntax(measure.get("dax", "")):
                valid_measures.append(measure)
            else:
                invalid_measures.append(measure)
        
        return {
            "valid_measures": valid_measures,
            "invalid_measures": invalid_measures,
            "total_measures": len(measures)
        }
    
    async def _build_visualizations(self, dashboard_plan: Dict, processed_data: Dict) -> Dict:
        """Build visualization specifications"""
        visualizations = dashboard_plan.get("visualizations", [])
        built_visuals = []
        
        for viz in visualizations:
            try:
                # Create visualization specification
                viz_spec = {
                    "type": viz.get("type", "bar"),
                    "title": viz.get("title", "Untitled Chart"),
                    "data_fields": viz.get("data_fields", []),
                    "position": viz.get("position", {"row": 1, "column": 1, "width": 6, "height": 4}),
                    "config": self._get_visualization_config(viz.get("type", "bar"))
                }
                built_visuals.append(viz_spec)
                
            except Exception as e:
                logger.warning(f"Failed to build visualization: {str(e)}")
        
        return {
            "visualizations": built_visuals,
            "total_count": len(built_visuals)
        }
    
    async def _apply_formatting(self, dashboard_plan: Dict) -> Dict:
        """Apply theme and formatting"""
        theme = dashboard_plan.get("color_theme", "professional")
        
        theme_config = {
            "professional": {"primary": "#1f77b4", "secondary": "#ff7f0e", "background": "#ffffff"},
            "blue": {"primary": "#0078d4", "secondary": "#40e0d0", "background": "#f8f9fa"},
            "green": {"primary": "#107c10", "secondary": "#00cc6a", "background": "#f8f9fa"},
            "red": {"primary": "#d13438", "secondary": "#ff4b4b", "background": "#f8f9fa"}
        }
        
        return {
            "theme": theme,
            "colors": theme_config.get(theme, theme_config["professional"]),
            "fonts": {"title": "Segoe UI Semibold", "body": "Segoe UI"},
            "layout": dashboard_plan.get("layout", "single_page")
        }
    
    async def _finalize_dashboard(self, dashboard_plan: Dict, workflow_results: Dict) -> Dict:
        """Finalize dashboard creation"""
        return {
            "title": dashboard_plan.get("title", "Custom Dashboard"),
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "workflow_results": workflow_results,
            "features": dashboard_plan.get("features", [])
        }
    
    def _get_conversation_context(self, memory: ConversationBufferMemory) -> str:
        """Extract relevant context from conversation memory"""
        try:
            messages = memory.chat_memory.messages
            if not messages:
                return ""
            
            # Get last few messages for context
            recent_messages = messages[-6:] if len(messages) > 6 else messages
            context_parts = []
            
            for msg in recent_messages:
                if isinstance(msg, HumanMessage):
                    context_parts.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage):
                    context_parts.append(f"Assistant: {msg.content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.warning(f"Error getting conversation context: {str(e)}")
            return ""
    
    async def _enhance_plan_with_context(self, dashboard_plan: Dict, context: str, current_request: str) -> Dict:
        """Enhance dashboard plan with conversation context"""
        # Simple enhancement based on context keywords
        enhancements = {}
        
        context_lower = context.lower()
        
        # Enhance based on mentioned preferences
        if "monthly" in context_lower or "month" in context_lower:
            enhancements["time_granularity"] = "monthly"
        elif "weekly" in context_lower or "week" in context_lower:
            enhancements["time_granularity"] = "weekly"
        elif "daily" in context_lower or "day" in context_lower:
            enhancements["time_granularity"] = "daily"
        
        # Color preferences
        if "blue" in context_lower:
            enhancements["color_theme"] = "blue"
        elif "green" in context_lower:
            enhancements["color_theme"] = "green"
        elif "red" in context_lower:
            enhancements["color_theme"] = "red"
        
        return enhancements
    
    def _store_plan_in_memory(self, conversation_id: str, dashboard_plan: Dict, user_request: str):
        """Store dashboard plan in conversation memory"""
        memory = self.get_memory(conversation_id)
        
        plan_summary = f"Created dashboard plan: {dashboard_plan.get('title', 'Custom Dashboard')} with {len(dashboard_plan.get('visualizations', []))} visualizations"
        
        memory.chat_memory.add_user_message(user_request)
        memory.chat_memory.add_ai_message(plan_summary)
    
    def _get_last_plan_from_memory(self, conversation_id: str) -> Optional[Dict]:
        """Get the last dashboard plan from memory"""
        # This would typically query a database
        # For now, return None to indicate no stored plan
        return None
    
    def _apply_basic_modifications(self, current_plan: Dict, modification_request: str) -> Dict:
        """Apply basic modifications to dashboard plan"""
        modified_plan = current_plan.copy()
        
        request_lower = modification_request.lower()
        
        # Basic color changes
        if "blue" in request_lower:
            modified_plan["color_theme"] = "blue"
        elif "green" in request_lower:
            modified_plan["color_theme"] = "green"
        elif "red" in request_lower:
            modified_plan["color_theme"] = "red"
        
        # Basic layout changes
        if "title" in request_lower and "change" in request_lower:
            # Extract potential new title (basic extraction)
            words = modification_request.split()
            if "to" in words:
                title_index = words.index("to") + 1
                if title_index < len(words):
                    new_title = " ".join(words[title_index:])
                    modified_plan["title"] = new_title.strip('"\'')
        
        return modified_plan
    
    def _validate_dax_syntax(self, dax_formula: str) -> bool:
        """Basic DAX syntax validation"""
        if not dax_formula or not isinstance(dax_formula, str):
            return False
        
        # Basic checks
        forbidden_patterns = ["--", "/*", "*/", "xp_cmdshell", "exec"]
        for pattern in forbidden_patterns:
            if pattern in dax_formula.lower():
                return False
        
        # Must contain at least one DAX function
        dax_functions = ["SUM", "AVERAGE", "COUNT", "MAX", "MIN", "CALCULATE", "FILTER"]
        has_dax_function = any(func in dax_formula.upper() for func in dax_functions)
        
        return has_dax_function
    
    def _get_visualization_config(self, viz_type: str) -> Dict:
        """Get configuration for visualization type"""
        configs = {
            "bar": {"orientation": "vertical", "show_values": True},
            "line": {"smooth": True, "show_markers": True},
            "pie": {"show_percentages": True, "show_legend": True},
            "table": {"show_grid": True, "sortable": True},
            "card": {"font_size": "large", "show_trend": False}
        }
        
        return configs.get(viz_type, {})
    
    def _create_fallback_plan(self, user_request: str, file_paths: List[str]) -> Dict:
        """Create a basic fallback plan when AI is unavailable"""
        return {
            "title": "Basic Dashboard",
            "description": "Auto-generated dashboard from your data",
            "dashboard_type": "general",
            "visualizations": [
                {
                    "type": "bar",
                    "title": "Data Overview",
                    "data_fields": ["auto_detected"],
                    "purpose": "Show data overview",
                    "position": {"row": 1, "column": 1, "width": 12, "height": 6}
                }
            ],
            "kpis": [],
            "filters": [],
            "color_theme": "professional",
            "layout": "single_page",
            "features": ["Basic data visualization"],
            "dax_formulas": {"measures": [], "calculated_columns": []}
        }
