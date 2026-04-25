import re
from typing import List

from core.models import LogEntry, LogFormat, LogLevel
from parsers.base import BaseParser, parse_timestamp, parse_level

# Ordered from most-specific to least-specific
_PATTERNS = [
    # [2024-01-15 10:23:45] ERROR service - message
    re.compile(
        r'^\[?(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?)\]?\s+'
        r'(?P<level>CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\s+'
        r'(?:(?P<service>[\w.\-]+)\s+[-:]\s+)?(?P<msg>.+)$',
        re.IGNORECASE,
    ),

    # 2024-01-15T10:23:45 [ERROR] [service] message
    re.compile(
        r'^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?)\s+'
        r'\[(?P<level>CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\]\s*'
        r'(?:\[(?P<service>[\w.\-]+)\]\s*)?(?P<msg>.+)$',
        re.IGNORECASE,
    ),

    # ERROR 2024-01-15 10:23:45 service message (level first)
    re.compile(
        r'^(?P<level>CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\s+'
        r'(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?)\s+'
        r'(?:(?P<service>[\w.\-]+)\s+)?(?P<msg>.+)$',
        re.IGNORECASE,
    ),

    # Jan 15 10:23:45 hostname service[pid]: message  (syslog)
    re.compile(
        r'^(?P<ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<service>[\w.\-]+)(?:\[\d+\])?\s*:\s*(?P<msg>.+)$',
    ),
    # ERROR: message  (no timestamp)
    re.compile(
        r'^(?P<level>CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\s*:\s*(?P<msg>.+)$',
        re.IGNORECASE,
    ),
]

class PlaintextParser(BaseParser):

    def confidence(self, sample_lines: List[str]) -> float:
        lines = [l.strip() for l in sample_lines[:20] if l.strip()]
        if not lines:
            return 0.0
        hits = sum(1 for l in lines if any(p.match(l) for p in _PATTERNS))
        # Plain text is the catch-all - give it a small base score
        return max(0.15,hits/len(lines))
    
    def parse(self, text: str, line_offset: int = 0)-> List[LogEntry]:
        entries: List[LogEntry] = []
        for i, raw in enumerate(text.splitlines()):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                entries.append(self._parse_line(stripped, line_offset+i))
            except Exception:
                entries.append(self._fallback_entry(raw,line_offset+i))
        return entries
    
    def _parse_line(self,raw: str,line_number: int) -> LogEntry:
        for pattern in _PATTERNS:
            m = pattern.match(raw)
            if not m:
                continue
            g = m.groupdict()
            return LogEntry(
                raw=raw,
                timestamp=parse_timestamp(g.get("ts") or ""),
                level=parse_level(g.get("level") or ""),
                service=g.get("service") or None,
                message=(g.get("msg") or raw).strip()[:2000],
                format=LogFormat.PLAINTEXT,
                line_number=line_number,
            )
        #   No pattern matched - best-effort, keep the line
        return LogEntry(
            raw=raw,
            timestamp=parse_timestamp(raw),
            level=parse_level(raw),
            message=raw[:2000],
            format=LogFormat.PLAINTEXT,
            line_number=line_number
        )