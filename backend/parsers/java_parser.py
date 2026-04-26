import re
from typing import List, Tuple

from core.models import LogEntry,LogFormat,LogLevel
from parsers.base import BaseParser,parse_timestamp,parse_level

# Java log4j/logback prefix: 2024-01-15 10:23:45,123 ERROR [thread] com.example.Service - msg
_LOG4J = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\s+'
    r'(?P<level>ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE|FATAL|CRITICAL)\s+'
    r'(?:\[(?P<thread>[^\]]+)\]\s+)?'
    r'(?P<logger>[\w.$]+(?:\.[\w.$]+)*)\s*[-:]\s*'
    r'(?P<msg>.+)$'
)

# Stack frame: at com.example.Service.method(Service.java:42)
_AT_LINE = re.compile(r'^\s*at\s+[\w.$<>]+\([\w.$]+\.(?:java|kt|groovy|scala):\d+\)')

# Caused by / Suppressed
_CAUSED_BY = re.compile(r'^(?:Caused by|Suppressed):\s*')

# Bare exception class on its own line: java.lang.NullPointerException:msg
_EXCEPTION = re.compile(
    r'^(?:java|javax|org|com|net|sun|io|kotlin)[\w.$]*(?:Exception|Error|Throwable)\b'
    r'|^\w+(?:Exception|Error):'
)

class JavaParser(BaseParser):
    def confidence(self, sample_lines: List[str]) -> float:
        score = 0.0
        total = 0
        for line in sample_lines[:30]:
            s = line.strip()
            if not s:
                continue
            total+=1
            if _AT_LINE.match(s):
                score+=1.0
            elif _CAUSED_BY.match(s):
                score+=0.9
            elif _LOG4J.match(s):
                score+=0.9
            elif _EXCEPTION.match(s):
                score+=0.7
            elif s.startswith("...") and "more" in s:
                score+=0.5
        return min(score/max(total,1),1.0)
    
    def parse(self, text: str, line_offset: int = 0) -> List[LogEntry]:
        entries: List[LogEntry] = []
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            if not lines[i].strip():
                i+=1
                continue
            try:
                entry, consumed = self._parse_block(lines,i,line_offset)
                entries.append(entry)
                i+=consumed
            except Exception:
                entries.append(self._fallback_entry(lines[i],line_offset+i))
                i+=1
        return entries
    
    def _parse_block(self,lines: List[str],start: int,offset: int)-> Tuple[LogEntry,int]:
        first = lines[start].strip()
        consumed = 1

        # Case 1: log4j/logback prefixed line
        m = _LOG4J.match(first)
        if m:
            g = m.groupdict()
            stack_lines, consumed = self._collect_stack(lines,start+1)
            consumed+=1
            return LogEntry(
                raw="\n".join(lines[start:start + consumed])[:5000],
                timestamp=parse_timestamp(g.get("ts") or ""),
                level=parse_level(g.get("level") or ""),
                service=(g.get("logger") or "").split(".")[-1] or None,
                message=(g.get("msg") or first)[:2000],
                stack_trace="\n".join(stack_lines) if stack_lines else None,
                format=LogFormat.JAVA,
                line_number=offset+start,
                extra={"thread": g.get("thread"), "logger": g.get("logger")},
            ),consumed
        
        # Case 2: bare exception block
        if _EXCEPTION.match(first) or _CAUSED_BY.match(first):
            stack_lines, extra = self._collect_stack(lines,start+1)
            consumed = 1+extra
            return LogEntry(
                raw="\n".join(lines[start:start + consumed])[:5000],
                level=LogLevel.ERROR,
                message=first[:2000],
                stack_trace="\n".join(stack_lines) if stack_lines else None,
                format=LogFormat.JAVA,
                line_number=offset+start,
            ),consumed
        
        # Fallback

        return LogEntry(
            raw=first,
            level=parse_level(first),
            message=first[:2000],
            format=LogFormat.JAVA,
            line_number=offset+start,
        ),1
    
    def _collect_stack(self,lines: List[str], start: int):
        """Collect contiguous stack frame lines. Returns (lines,count)."""
        stack, j = [],start
        while j <len(lines):
            s = lines[j].strip()
            if _AT_LINE.match(s) or _CAUSED_BY.match(s) or _EXCEPTION.match(s) or s.startswith("..."):
                stack.append(s)
                j+=1
            else:
                break
        return stack,j-start