import json
import os
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import asyncio
from pathlib import Path
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_json_dumps(obj):
    """
    Safely serialize objects to JSON, handling numpy/pandas types
    """
    def convert_types(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj) if np.isfinite(obj) else None
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (pd.Timestamp, pd.Timedelta)):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: convert_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(item) for item in obj]
        else:
            return obj
    
    return json.dumps(convert_types(obj))

class MemoryManager:
    """
    Manages conversation memory, file information, and dashboard plans
    """
    
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.conversations = {}  # In-memory cache
        self.file_info = {}     # File information storage
        self.dashboard_plans = {}  # Dashboard plans storage
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """
        Initialize SQLite database for persistent storage
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create conversations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        title TEXT,
                        status TEXT DEFAULT 'active'
                    )
                ''')
                
                # Create messages table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                ''')
                
                # Create file_info table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT,
                        file_paths TEXT NOT NULL,
                        analysis_data TEXT,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                ''')
                
                # Create conversation_files table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        original_name TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                ''')
                
                # Create dashboard_plans table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS dashboard_plans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT,
                        plan_data TEXT NOT NULL,
                        user_request TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active',
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            # Fall back to in-memory storage only
    
    def add_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Add a message to the conversation
        """
        try:
            # Add to in-memory cache
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = {
                    "id": conversation_id,
                    "messages": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "title": self._generate_conversation_title(content) if role == "user" else "New Conversation"
                }
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            self.conversations[conversation_id]["messages"].append(message)
            self.conversations[conversation_id]["updated_at"] = datetime.now().isoformat()
            
            # Persist to database
            self._persist_message(conversation_id, role, content, metadata)
            
            logger.info(f"Added {role} message to conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
    
    def get_conversation(self, conversation_id: str) -> Dict:
        """
        Get conversation history
        """
        try:
            # Try in-memory cache first
            if conversation_id in self.conversations:
                return self.conversations[conversation_id]
            
            # Load from database
            conversation = self._load_conversation_from_db(conversation_id)
            if conversation:
                # Cache in memory
                self.conversations[conversation_id] = conversation
                return conversation
            
            # Return empty conversation if not found
            return {
                "id": conversation_id,
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "title": "New Conversation"
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return {"id": conversation_id, "messages": [], "error": str(e)}
    
    def list_conversations(self) -> List[Dict]:
        """
        List all conversations
        """
        try:
            conversations = []
            
            # Get from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT c.id, c.title, c.created_at, c.updated_at, c.status,
                           COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.status = 'active'
                    GROUP BY c.id, c.title, c.created_at, c.updated_at, c.status
                    ORDER BY c.updated_at DESC
                ''')
                
                for row in cursor.fetchall():
                    conversations.append({
                        "id": row[0],
                        "title": row[1],
                        "created_at": row[2],
                        "updated_at": row[3],
                        "status": row[4],
                        "message_count": row[5]
                    })
            
            # Add in-memory conversations that might not be in DB yet
            for conv_id, conv_data in self.conversations.items():
                if not any(c["id"] == conv_id for c in conversations):
                    conversations.append({
                        "id": conv_id,
                        "title": conv_data.get("title", "New Conversation"),
                        "created_at": conv_data.get("created_at"),
                        "updated_at": conv_data.get("updated_at"),
                        "status": "active",
                        "message_count": len(conv_data.get("messages", []))
                    })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error listing conversations: {str(e)}")
            # Return in-memory conversations as fallback
            return [
                {
                    "id": conv_id,
                    "title": conv_data.get("title", "New Conversation"),
                    "created_at": conv_data.get("created_at"),
                    "updated_at": conv_data.get("updated_at"),
                    "status": "active",
                    "message_count": len(conv_data.get("messages", []))
                }
                for conv_id, conv_data in self.conversations.items()
            ]
    
    def delete_conversation(self, conversation_id: str):
        """
        Delete a conversation and all related data
        """
        try:
            # Remove from in-memory cache
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
            
            # Remove from file info cache
            if conversation_id in self.file_info:
                del self.file_info[conversation_id]
            
            # Remove from dashboard plans cache
            if conversation_id in self.dashboard_plans:
                del self.dashboard_plans[conversation_id]
            
            # Mark as deleted in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE conversations SET status = 'deleted' WHERE id = ?",
                    (conversation_id,)
                )
                conn.commit()
            
            logger.info(f"Deleted conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
    
    def add_file_info(self, conversation_id: str, file_paths: List[str], analysis_data: Dict):
        """
        Store file information for a conversation
        """
        try:
            file_info = {
                "file_paths": file_paths,
                "analysis_data": analysis_data,
                "uploaded_at": datetime.now().isoformat()
            }
            
            # Store in memory
            self.file_info[conversation_id] = file_info
            
            # Persist to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO file_info (conversation_id, file_paths, analysis_data)
                    VALUES (?, ?, ?)
                ''', (
                    conversation_id,
                    safe_json_dumps(file_paths),
                    safe_json_dumps(analysis_data)
                ))
                conn.commit()
            
            logger.info(f"Stored file info for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error storing file info: {str(e)}")
    
    def get_file_info(self, conversation_id: str) -> Optional[Dict]:
        """
        Get file information for a conversation
        """
        try:
            # Try in-memory cache first
            if conversation_id in self.file_info:
                return self.file_info[conversation_id]
            
            # Load from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT file_paths, analysis_data, uploaded_at
                    FROM file_info
                    WHERE conversation_id = ?
                    ORDER BY uploaded_at DESC
                    LIMIT 1
                ''', (conversation_id,))
                
                row = cursor.fetchone()
                if row:
                    file_info = {
                        "file_paths": json.loads(row[0]),
                        "analysis_data": json.loads(row[1]),
                        "uploaded_at": row[2]
                    }
                    
                    # Cache in memory
                    self.file_info[conversation_id] = file_info
                    return file_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None
    
    def store_dashboard_plan(self, conversation_id: str, plan_data: Dict, user_request: str):
        """
        Store a dashboard plan
        """
        try:
            plan_info = {
                "plan_data": plan_data,
                "user_request": user_request,
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }
            
            # Store in memory
            if conversation_id not in self.dashboard_plans:
                self.dashboard_plans[conversation_id] = []
            self.dashboard_plans[conversation_id].append(plan_info)
            
            # Persist to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO dashboard_plans (conversation_id, plan_data, user_request)
                    VALUES (?, ?, ?)
                ''', (
                    conversation_id,
                    safe_json_dumps(plan_data),
                    user_request
                ))
                conn.commit()
            
            logger.info(f"Stored dashboard plan for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error storing dashboard plan: {str(e)}")
    
    def get_latest_dashboard_plan(self, conversation_id: str) -> Optional[Dict]:
        """
        Get the latest dashboard plan for a conversation
        """
        try:
            # Try in-memory cache first
            if conversation_id in self.dashboard_plans and self.dashboard_plans[conversation_id]:
                return self.dashboard_plans[conversation_id][-1]
            
            # Load from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT plan_data, user_request, created_at, status
                    FROM dashboard_plans
                    WHERE conversation_id = ? AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (conversation_id,))
                
                row = cursor.fetchone()
                if row:
                    plan_info = {
                        "plan_data": json.loads(row[0]),
                        "user_request": row[1],
                        "created_at": row[2],
                        "status": row[3]
                    }
                    
                    # Cache in memory
                    if conversation_id not in self.dashboard_plans:
                        self.dashboard_plans[conversation_id] = []
                    self.dashboard_plans[conversation_id].append(plan_info)
                    
                    return plan_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting dashboard plan: {str(e)}")
            return None
    
    def get_conversation_summary(self, conversation_id: str) -> str:
        """
        Generate a summary of the conversation
        """
        try:
            conversation = self.get_conversation(conversation_id)
            messages = conversation.get("messages", [])
            
            if not messages:
                return "No messages in conversation"
            
            user_messages = [m["content"] for m in messages if m["role"] == "user"]
            
            if user_messages:
                # Create summary from user messages
                first_message = user_messages[0]
                
                # Look for dashboard-related keywords
                dashboard_keywords = ["dashboard", "chart", "visualization", "report", "analytics"]
                if any(keyword in first_message.lower() for keyword in dashboard_keywords):
                    return f"Dashboard creation: {first_message[:100]}..."
                else:
                    return f"General chat: {first_message[:100]}..."
            
            return "Empty conversation"
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {str(e)}")
            return "Error generating summary"
    
    def _persist_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict]):
        """
        Persist message to database
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Ensure conversation exists
                cursor.execute(
                    "INSERT OR IGNORE INTO conversations (id, title) VALUES (?, ?)",
                    (conversation_id, self._generate_conversation_title(content) if role == "user" else "New Conversation")
                )
                
                # Update conversation timestamp
                cursor.execute(
                    "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (conversation_id,)
                )
                
                # Insert message
                cursor.execute('''
                    INSERT INTO messages (conversation_id, role, content, metadata)
                    VALUES (?, ?, ?, ?)
                ''', (
                    conversation_id,
                    role,
                    content,
                    json.dumps(metadata) if metadata else None
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error persisting message: {str(e)}")
    
    def _load_conversation_from_db(self, conversation_id: str) -> Optional[Dict]:
        """
        Load conversation from database
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get conversation info
                cursor.execute(
                    "SELECT title, created_at, updated_at FROM conversations WHERE id = ? AND status = 'active'",
                    (conversation_id,)
                )
                conv_row = cursor.fetchone()
                
                if not conv_row:
                    return None
                
                # Get messages
                cursor.execute('''
                    SELECT role, content, timestamp, metadata
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY timestamp ASC
                ''', (conversation_id,))
                
                messages = []
                for row in cursor.fetchall():
                    message = {
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2],
                        "metadata": json.loads(row[3]) if row[3] else {}
                    }
                    messages.append(message)
                
                return {
                    "id": conversation_id,
                    "title": conv_row[0],
                    "created_at": conv_row[1],
                    "updated_at": conv_row[2],
                    "messages": messages
                }
                
        except Exception as e:
            logger.error(f"Error loading conversation from database: {str(e)}")
            return None
    
    def _generate_conversation_title(self, first_message: str) -> str:
        """
        Generate a title for the conversation based on the first message
        """
        try:
            # Clean and truncate the message
            title = first_message.strip()
            
            # Remove common prefixes
            prefixes_to_remove = ["create", "build", "make", "generate", "show me", "i want", "i need"]
            title_lower = title.lower()
            
            for prefix in prefixes_to_remove:
                if title_lower.startswith(prefix):
                    title = title[len(prefix):].strip()
                    break
            
            # Truncate and clean
            title = title[:50].strip()
            
            # Add ellipsis if truncated
            if len(first_message) > 50:
                title += "..."
            
            # Fallback if empty
            if not title:
                title = "New Conversation"
            
            return title
            
        except Exception as e:
            logger.error(f"Error generating conversation title: {str(e)}")
            return "New Conversation"
    
    def cleanup_old_conversations(self, days_old: int = 30):
        """
        Clean up old conversations
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE conversations 
                    SET status = 'archived' 
                    WHERE updated_at < ? AND status = 'active'
                ''', (cutoff_date.isoformat(),))
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                logger.info(f"Archived {affected_rows} old conversations")
                
        except Exception as e:
            logger.error(f"Error cleaning up conversations: {str(e)}")
    
    def get_statistics(self) -> Dict:
        """
        Get usage statistics
        """
        try:
            stats = {
                "total_conversations": 0,
                "active_conversations": 0,
                "total_messages": 0,
                "total_dashboards_created": 0,
                "total_files_processed": 0
            }
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count conversations
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE status = 'active'")
                stats["active_conversations"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM conversations")
                stats["total_conversations"] = cursor.fetchone()[0]
                
                # Count messages
                cursor.execute("SELECT COUNT(*) FROM messages")
                stats["total_messages"] = cursor.fetchone()[0]
                
                # Count dashboard plans
                cursor.execute("SELECT COUNT(*) FROM dashboard_plans WHERE status = 'active'")
                stats["total_dashboards_created"] = cursor.fetchone()[0]
                
                # Count file uploads
                cursor.execute("SELECT COUNT(*) FROM file_info")
                stats["total_files_processed"] = cursor.fetchone()[0]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {
                "total_conversations": len(self.conversations),
                "active_conversations": len(self.conversations),
                "total_messages": sum(len(conv.get("messages", [])) for conv in self.conversations.values()),
                "total_dashboards_created": len(self.dashboard_plans),
                "total_files_processed": len(self.file_info),
                "error": str(e)
            }
