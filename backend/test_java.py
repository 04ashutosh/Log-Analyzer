from parsers.java_parser import JavaParser

log = """2024-01-15 10:23:44,123 ERROR com.example.UserService - Failed to fetch user
\tat com.example.UserService.fetch(UserService.java:145)
\tat com.example.Controller.get(Controller.java:67)
java.lang.NullPointerException: Cannot invoke getEmail()
\tat com.example.Service.handle(Service.java:90)
Caused by: java.io.IOException: stream closed
\tat java.io.StreamClose.close(StreamClose.java:10)"""

p = JavaParser()
entries = p.parse(log)
print(f"Entries parsed: {len(entries)}")
for e in entries:
    print(f"  level={e.level.value}  service={e.service}  stack={'yes' if e.stack_trace else 'no'}")
print("java_parser OK!")
