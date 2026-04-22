import threading
import uuid
from typing import Dict, List, Optional, Any
from core.models import LogEntry, AnalysisResult

class SessionStore:
    """
    Thread-safe in-memory session store.
    Redis-compatible interface - swap backend later without changing callers.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = {
                "raw_text": [],
                "parsed_entries": [],
                "analysis": None,
                "bm25_index": None,
                "status": "created",
            }
        return session_id
    
    def session_exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions
        
    def append_raw_text(self,session_id: str, text: str) -> None:
        with self._lock:
            self._require(session_id)
            self._sessions[session_id]["raw_text"].append(text)

    def get_raw_text(self, session_id: str) -> str:
        with self._lock:
            session = self._sessions.get(session_id,{})
            return "\n".join(session.get("raw_text",[]))
        
    def set_parsed_entries(self,session_id: str, entries: List[LogEntry]) -> None:
        with self._lock:
            self._require(session_id)
            self._sessions[session_id]["parsed_entries"] = entries

    def get_parsed_entries(self,session_id: str) -> List[LogEntry]:
        with self._lock:
            return self._sessions.get(session_id, {}).get("parsed_entries",[])
        
    def set_analysis(self, session_id: str, result: AnalysisResult) -> None:
        with self._lock:
            self._require(session_id)
            self._sessions[session_id]["analysis"] = result
            self._sessions[session_id]["status"] = result.status

    def get_analysis(self, session_id: str) -> Optional[AnalysisResult]:
        with self._lock:
            session = self._sessions.get(session_id)
            return session.get("analysis") if session else None

    def set_status(self, session_id: str, status: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["status"] = status

    def get_status(self, session_id: str) -> Optional[str]:
        with self._lock:
            session = self._sessions.get(session_id)
            return session.get("status") if session else None
        
    def get_session(self, session_id: str)->Optional[Dict[str,Any]]:
        with self._lock:
            return self._sessions.get(session_id)
        
    def update_session(self, session_id: str, **kwargs) -> None:
        with self._lock:
            self._require(session_id)
            self._sessions[session_id].update(kwargs)

    def delete_session(self, session_id: str)-> None:
        with self._lock:
            self._sessions.pop(session_id,None)

    def list_sessions(self)->List[str]:
        with self._lock:
            return list(self._sessions.keys())
        
    def _require(self, session_id: str) -> None:
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        

# Global Singleton - imported by all modules
store = SessionStore()

        