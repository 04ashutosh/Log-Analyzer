import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List,Optional

from core.models import LogEntry, LogFormat, LogLevel

# --Timestamp patterns (most specific first)
_TS_PATTERNS = [
    (r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?',
     ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]),
    (r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}',
     ["%d/%b/%Y:%H:%M:%S"]),
    (r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',
     ["%b %d %H:%M:%S", "%b  %d %H:%M:%S"]),
]

def parse_timestamp(text: str)->Optional[datetime]:
    for pattern, formats in _TS_PATTERNS:
        m = re.search(pattern, text)
        if not m:
            continue

        raw_str = m.group(0).rstrip("Z")
        # strip tz offset
        raw_str = re.sub(r'[+-]\d{2}:?\d{2}$','',raw_str).strip()
        for fmt in formats:
            try:
                return datetime.strptime(raw_str,fmt)
            except ValueError:
                continue
    return None

def parse_level(text: str) -> LogLevel:
    upper = text.upper()
    if "CRITICAL" in upper or "FATAL" in upper:
        return LogLevel.CRITICAL
    if "ERROR" in upper:
        return LogLevel.ERROR
    if "WARN" in upper:
        return LogLevel.WARN
    if "INFO" in upper:
        return LogLevel.INFO
    if "DEBUG" in upper or "TRACE" in upper:
        return LogLevel.DEBUG
    return LogLevel.UNKNOWN
    
class BaseParser(ABC):
    """All parsers implement this contract."""

    @abstractmethod
    def confidence(self,sample_lines: List[str])->float:
        """Return 0.0-1.0 confidence that this parser handles the format."""

    @abstractmethod
    def parse(self, text: str, line_offset: int=0)-> List[LogEntry]:
        """Parse text into LogEntry list. Must never raise - catch everything."""

    @property
    def name(self) -> str:
        return self.__class__.__name__.replace("Parser", "").lower()
    
    def _fallback_entry(self, raw: str, line_number: int) -> LogEntry:
        """Last-resort entry for lines that can't be parsed at all."""
        return LogEntry(
            raw=raw[:5000],
            line_number=line_number,
            message=raw.strip()[:2000],
            level=parse_level(raw),
            format=LogFormat.UNKNOWN,
            is_malformed=True,
        )