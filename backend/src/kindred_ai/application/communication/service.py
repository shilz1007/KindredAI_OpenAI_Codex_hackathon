"""Communication MCP use cases; messages and calls are local prototype queues."""
import os, sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

DEFAULT = Path(__file__).resolve().parents[4] / "data" / "communication.sqlite3"

class CommunicationService:
    def __init__(self, path: Path): self.path = path
    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as c:
            c.executescript("""CREATE TABLE IF NOT EXISTS family_contacts (id TEXT PRIMARY KEY, name TEXT NOT NULL, relationship TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS communication_messages (id TEXT PRIMARY KEY, contact_id TEXT NOT NULL REFERENCES family_contacts(id), content TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
            INSERT OR IGNORE INTO family_contacts VALUES ('daughter','Sara','daughter');
            INSERT OR IGNORE INTO family_contacts VALUES ('son','Rahim','son');
            CREATE TABLE IF NOT EXISTS phone_book_contacts (
                id TEXT PRIMARY KEY REFERENCES family_contacts(id),
                display_name TEXT NOT NULL,
                relationship TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                approved_for_calls INTEGER NOT NULL CHECK (approved_for_calls IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS call_requests (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL REFERENCES phone_book_contacts(id),
                status TEXT NOT NULL CHECK (status IN ('requested', 'cancelled', 'completed')),
                created_at TEXT NOT NULL
            );
            INSERT OR IGNORE INTO phone_book_contacts VALUES ('daughter', 'Sara', 'daughter', '+4712345678', 1);
            INSERT OR IGNORE INTO phone_book_contacts VALUES ('son', 'Rahim', 'son', '+4787654321', 1);""")
    def list_contacts(self):
        with closing(sqlite3.connect(self.path)) as c:
            return [{"id": r[0], "name": r[1], "relationship": r[2]} for r in c.execute("SELECT id,name,relationship FROM family_contacts ORDER BY name")]

    def list_phone_book(self):
        """Return the prototype user's approved family phone book."""
        with closing(sqlite3.connect(self.path)) as c:
            rows = c.execute(
                "SELECT id, display_name, relationship, phone_number, approved_for_calls FROM phone_book_contacts ORDER BY display_name"
            )
            return [
                {"id": row[0], "display_name": row[1], "relationship": row[2], "phone_number": row[3], "approved_for_calls": bool(row[4])}
                for row in rows
            ]

    def request_family_call(self, contact_query: str):
        """Record a requested call. TODO: integrate an approved telephony provider."""
        clean_query = contact_query.strip()
        if not clean_query:
            raise ValueError("A family contact name or relationship is required.")
        with closing(sqlite3.connect(self.path)) as c:
            matches = c.execute(
                "SELECT id, display_name, relationship, phone_number FROM phone_book_contacts "
                "WHERE lower(display_name) = lower(?) OR lower(relationship) = lower(?)",
                (clean_query, clean_query),
            ).fetchall()
            if not matches:
                raise ValueError("Phone book contact was not found.")
            if len(matches) > 1:
                raise ValueError("More than one phone book contact matches; please use a specific name.")
            contact = matches[0]
            request = {"id": str(uuid4()), "contact_id": contact[0], "status": "requested", "created_at": datetime.now(UTC).isoformat()}
            c.execute("INSERT INTO call_requests VALUES (:id, :contact_id, :status, :created_at)", request)
        return {**request, "display_name": contact[1], "relationship": contact[2], "phone_number": contact[3]}
    def send_family_message(self, contact_id: str, content: str, approved: bool):
        if not approved: raise ValueError("Explicit user approval is required before sending a family message.")
        if not content.strip(): raise ValueError("Message content cannot be empty.")
        with closing(sqlite3.connect(self.path)) as c:
            if not c.execute("SELECT 1 FROM family_contacts WHERE id=?", (contact_id,)).fetchone(): raise ValueError("Family contact was not found.")
            result={"id":str(uuid4()),"contact_id":contact_id,"content":content.strip(),"status":"queued","created_at":datetime.now(UTC).isoformat()}
            c.execute("INSERT INTO communication_messages VALUES (:id,:contact_id,:content,:status,:created_at)",result)
        return result

_service=None
def get_communication_service():
    global _service
    if _service is None:
        _service=CommunicationService(Path(os.getenv("KINDRED_COMMUNICATION_DB_PATH", DEFAULT))); _service.initialize()
    return _service
