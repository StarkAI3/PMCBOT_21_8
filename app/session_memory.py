from collections import defaultdict

# Structure: {session_id: [{"role": "user", "content": ...}, {"role": "assistant", "content": ...}]}
session_memory = defaultdict(list)

def add_to_history(session_id: str, role: str, content: str):
    session_memory[session_id].append({"role": role, "content": content})

def get_history(session_id: str):
    return session_memory.get(session_id, [])
