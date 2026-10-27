import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from ..config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        # 1. Users table (synthetic user personas)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            workspace_access TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Conversations table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)

        # 3. Messages table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            citations TEXT DEFAULT '[]',
            agent_trace TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
        );
        """)

        # 4. User Memories table (Strict User Isolation)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            provenance TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            correction_history TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)

        # 5. Memory Audit Logs table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_audit (
            audit_id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 6. Evaluation Runs table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS eval_runs (
            run_id TEXT PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cases_total INTEGER NOT NULL,
            cases_passed INTEGER NOT NULL,
            cases_failed INTEGER NOT NULL,
            metrics TEXT NOT NULL,
            details TEXT NOT NULL
        );
        """)

        # Seed Synthetic Users if empty
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM users;")
        if cursor.fetchone()["cnt"] == 0:
            synthetic_users = [
                ("user_alice", "Alice Chen", "alice.chen@asterline.internal", "Senior DevOps Engineer", "us-prod, eu-prod"),
                ("user_bob", "Bob Miller", "bob.miller@asterline.internal", "Data Platform Engineer", "us-prod"),
                ("user_carol", "Carol Davis", "carol.davis@asterline.internal", "Product Operations Lead", "us-prod, eu-prod")
            ]
            conn.executemany("""
                INSERT INTO users (user_id, name, email, role, workspace_access)
                VALUES (?, ?, ?, ?, ?);
            """, synthetic_users)
            
    conn.close()

# User Helpers
def get_users() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY name ASC;").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# Conversation Helpers
def create_conversation(user_id: str, title: str = "New Research Session") -> Dict[str, Any]:
    cid = f"conv_{uuid.uuid4().hex[:10]}"
    conn = get_db_connection()
    with conn:
        conn.execute("""
            INSERT INTO conversations (conversation_id, user_id, title)
            VALUES (?, ?, ?);
        """, (cid, user_id, title))
    conn.close()
    return {"conversation_id": cid, "user_id": user_id, "title": title}

def get_conversations(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC;
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_conversation(conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("""
        SELECT * FROM conversations WHERE conversation_id = ? AND user_id = ?;
    """, (conversation_id, user_id)).fetchone()
    conn.close()
    return dict(row) if row else None

# Message Helpers
def add_message(
    conversation_id: str,
    sender: str,
    content: str,
    citations: Optional[List[Dict[str, Any]]] = None,
    agent_trace: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    mid = f"msg_{uuid.uuid4().hex[:10]}"
    cit_json = json.dumps(citations or [])
    trace_json = json.dumps(agent_trace or [])
    
    conn = get_db_connection()
    with conn:
        conn.execute("""
            INSERT INTO messages (message_id, conversation_id, sender, content, citations, agent_trace)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (mid, conversation_id, sender, content, cit_json, trace_json))
        conn.execute("""
            UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?;
        """, (conversation_id,))
    conn.close()
    return {
        "message_id": mid,
        "conversation_id": conversation_id,
        "sender": sender,
        "content": content,
        "citations": citations or [],
        "agent_trace": agent_trace or []
    }

def get_messages(conversation_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC;
    """, (conversation_id,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["citations"] = json.loads(d.get("citations") or "[]")
        except Exception:
            d["citations"] = []
        try:
            d["agent_trace"] = json.loads(d.get("agent_trace") or "[]")
        except Exception:
            d["agent_trace"] = []
        result.append(d)
    return result

# Strict User-Isolated Memory Helpers
def get_memories(user_id: str, status: str = "active") -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM memories WHERE user_id = ? AND status = ? ORDER BY updated_at DESC;
    """, (user_id, status)).fetchall()
    conn.close()
    
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["correction_history"] = json.loads(item.get("correction_history") or "[]")
        except Exception:
            item["correction_history"] = []
        out.append(item)
    return out

def save_memory(
    user_id: str,
    category: str,
    content: str,
    provenance: str,
    memory_id: Optional[str] = None
) -> Dict[str, Any]:
    mid = memory_id or f"mem_{uuid.uuid4().hex[:10]}"
    conn = get_db_connection()
    with conn:
        conn.execute("""
            INSERT INTO memories (memory_id, user_id, category, content, provenance, status)
            VALUES (?, ?, ?, ?, ?, 'active');
        """, (mid, user_id, category, content, provenance))
        
        # Audit log
        conn.execute("""
            INSERT INTO memory_audit (audit_id, memory_id, user_id, action, new_value, reason)
            VALUES (?, ?, ?, 'create', ?, ?);
        """, (f"aud_{uuid.uuid4().hex[:10]}", mid, user_id, content, f"Extracted from {provenance}"))
    conn.close()
    return {"memory_id": mid, "user_id": user_id, "category": category, "content": content, "status": "active"}

def correct_memory(
    memory_id: str,
    user_id: str,
    new_content: str,
    reason: str = "User correction"
) -> bool:
    conn = get_db_connection()
    row = conn.execute("""
        SELECT * FROM memories WHERE memory_id = ? AND user_id = ?;
    """, (memory_id, user_id)).fetchone()
    
    if not row:
        conn.close()
        return False
        
    old_content = row["content"]
    try:
        history = json.loads(row["correction_history"] or "[]")
    except Exception:
        history = []
        
    history.append({
        "timestamp": datetime.utcnow().isoformat(),
        "old_content": old_content,
        "new_content": new_content,
        "reason": reason
    })
    
    with conn:
        conn.execute("""
            UPDATE memories
            SET content = ?, correction_history = ?, updated_at = CURRENT_TIMESTAMP
            WHERE memory_id = ? AND user_id = ?;
        """, (new_content, json.dumps(history), memory_id, user_id))
        
        # Audit log
        conn.execute("""
            INSERT INTO memory_audit (audit_id, memory_id, user_id, action, old_value, new_value, reason)
            VALUES (?, ?, ?, 'update', ?, ?, ?);
        """, (f"aud_{uuid.uuid4().hex[:10]}", memory_id, user_id, old_content, new_content, reason))
        
    conn.close()
    return True

def forget_memory(
    memory_id: str,
    user_id: str,
    hard_delete: bool = False
) -> bool:
    conn = get_db_connection()
    row = conn.execute("""
        SELECT * FROM memories WHERE memory_id = ? AND user_id = ?;
    """, (memory_id, user_id)).fetchone()
    
    if not row:
        conn.close()
        return False
        
    with conn:
        if hard_delete:
            conn.execute("""
                DELETE FROM memories WHERE memory_id = ? AND user_id = ?;
            """, (memory_id, user_id))
            action = "hard_delete"
        else:
            conn.execute("""
                UPDATE memories SET status = 'forgotten', updated_at = CURRENT_TIMESTAMP
                WHERE memory_id = ? AND user_id = ?;
            """, (memory_id, user_id))
            action = "soft_delete"
            
        conn.execute("""
            INSERT INTO memory_audit (audit_id, memory_id, user_id, action, old_value, reason)
            VALUES (?, ?, ?, ?, ?, 'Requested by user');
        """, (f"aud_{uuid.uuid4().hex[:10]}", memory_id, user_id, action, row["content"]))
        
    conn.close()
    return True

def get_memory_audit_logs(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM memory_audit WHERE user_id = ? ORDER BY timestamp DESC;
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Eval Runs
def save_eval_run(run_id: str, cases_total: int, cases_passed: int, cases_failed: int, metrics: Dict[str, Any], details: List[Dict[str, Any]]):
    conn = get_db_connection()
    with conn:
        conn.execute("""
            INSERT INTO eval_runs (run_id, cases_total, cases_passed, cases_failed, metrics, details)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (run_id, cases_total, cases_passed, cases_failed, json.dumps(metrics), json.dumps(details)))
    conn.close()

def get_latest_eval_run() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM eval_runs ORDER BY timestamp DESC LIMIT 1;").fetchone()
    conn.close()
    if not row:
        return None
    res = dict(row)
    res["metrics"] = json.loads(res["metrics"])
    res["details"] = json.loads(res["details"])
    return res
