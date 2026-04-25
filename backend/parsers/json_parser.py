import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models import LogEntry, LogFormat, LogLevel
from parsers.base import BaseParser, parse_timestamp, parse_level

# Field name aliases - handle different logging library conventions

_TS_KEYS = ["timestamp","ts","time","datetime","@timestamp","date","logged_at","t"]
_LVL_KEYS = ["level","severity","log_level","loglevel","lvl"]
_MSG_KEYS = ["message","msg","text","body","log","event","description"]
_SVC_KEYS = ["service","app","application","component","source","logger","name"]
_STK_KEYS = ["stack_trace","stacktrace","stack","exception","traceback"]

def _pick(obj: Dict[str, Any], keys: List[str])->Optional[Any]:
    for k in keys:
        if k in obj:
            return obj[k]
    # Case-insensitive fallback
    lower_map = {key.lower(): val for key, val in obj.items()}
    for k in keys:
        if k in lower_map:
            return lower_map[k]
    return None

class JsonParser(BaseParser):

    def confidence(self,sample_lines: List[str])-> float:
        lines = [l.strip() for l in sample_lines[:20] if l.strip()]
        if not lines:
            return 0.0
        valid = sum(1 for l in lines if self._is_json_obj(l))
        return valid/len(lines)
    
    def parse(self, text: str, line_offset: int = 0)->List[LogEntry]:
        entries: List[LogEntry] = []
        for i,raw in enumerate(text.splitlines()):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
                if isinstance(obj,dict):
                    entries.append(self._from_obj(obj, stripped, line_offset+i))
                else:
                    entries.append(self._fallback_entry(raw, line_offset+i))
            except json.JSONDecodeError as exc:
                entry = self._fallback_entry(raw,line_offset+i)
                entry.extra["json_error"] = str(exc)
                entries.append(entry)
            except Exception:
                entries.append(self._fallback_entry(raw,line_offset+i))
        return entries
    
    def _from_obj(self, obj: Dict[str,Any], raw: str, line_number: int)->LogEntry:
        # Timestamp
        ts_raw = _pick(obj, _TS_KEYS)
        timestamp = None
        if ts_raw:
            try:
                if isinstance(ts_raw, (int,float)):
                    # epoch ms vs epoch seconds
                    ts_raw = ts_raw/1000 if ts_raw>1e10 else ts_raw
                    timestamp = datetime.utcfromtimestamp(ts_raw)
                else:
                    timestamp = parse_timestamp(str(ts_raw))
            except Exception:
                pass

        # Level
        lvl_raw = _pick(obj, _LVL_KEYS)
        level = parse_level(str(lvl_raw)) if lvl_raw else LogLevel.UNKNOWN

        # Message
        msg_raw = _pick(obj,_MSG_KEYS)
        message = str(msg_raw).strip() if msg_raw else raw

        # Service
        svc_raw = _pick(obj, _SVC_KEYS)
        service = str(svc_raw) if svc_raw else None

        # Stack trace
        stk_raw = _pick(obj, _STK_KEYS)
        if isinstance(stk_raw, list):
            stk_raw = "\n".join(stk_raw)
        stack_trace = str(stk_raw) if stk_raw else None

        # Everything else goes to extra
        known = set(_TS_KEYS+_LVL_KEYS+_MSG_KEYS+_SVC_KEYS+_STK_KEYS)
        extra = {k: v for k, v in obj.items() if k not in known}

        return LogEntry(
            raw=raw[:5000],
            timestamp=timestamp,
            level=level,
            service=service,
            message=message[:2000],
            stack_trace=stack_trace,
            format=LogFormat.JSON,
            line_number=line_number,
            extra=extra,
        )
    
    @staticmethod
    def _is_json_obj(line : str) -> bool:
        try:
            return isinstance(json.loads(line),dict)
        except Exception:
            return False