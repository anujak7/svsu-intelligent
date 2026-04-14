import hashlib
import os
import json
import sqlite3
from datetime import datetime

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))
ROOT_DIR = os.path.normpath(os.path.join(BACKEND_DIR, ".."))
BACKEND_DATA_DIR = os.path.join(BACKEND_DIR, "data")
ROOT_DIR = os.path.normpath(os.path.join(BACKEND_DIR, ".."))
KNOWLEDGE_BASE = os.path.join(ROOT_DIR, "SVSU_KNOWLEDGE")

# Organized Paths
KNOWLEDGE_DB_PATH = os.path.join(KNOWLEDGE_BASE, "Database", "svsu_knowledge.db")
BACKEND_KNOWLEDGE_DIR = os.path.join(KNOWLEDGE_BASE, "Text_Knowledge")
PDF_DIR = os.path.join(KNOWLEDGE_BASE, "PDFs")
STRUCTURED_DATA_DIR = os.path.join(KNOWLEDGE_BASE, "Structured_Data")

SOURCE_GROUP_PRIORITIES = {
    "CUSTOM_FACTS": 260,
    "CORE_FACTS": 230,
    "DEPARTMENTS": 210,
    "ABOUT": 190,
    "ACADEMICS": 185,
    "ADMINISTRATION": 190,
    "ADMISSION": 180,
    "EXAMINATION": 175,
    "FACILITIES": 170,
    "STUDENTS": 170,
    "LIBRARY": 165,
    "CONTACT": 165,
    "NOTICES": 155,
    "UPDATES": 155,
    "RESEARCH": 160,
    "SVSU_ALL_PROGRAMS_LIST": 165,
    "PDF": 120,
}

SOURCE_GROUP_ALIASES = {
    "EXAMINATIONS": "EXAMINATION",
    "RESULTS": "EXAMINATION",
    "RESULTS_DIRECTORY": "EXAMINATION",
    "NOTICE": "NOTICES",
    "UPDATES": "NOTICES",
    "PROGRAMS": "SVSU_ALL_PROGRAMS_LIST",
}


def _normalize_text(text: str) -> str:
    text = str(text or "").lower().replace("&", " and ")
    text = " ".join(text.split())
    return text


def _chunk_text(text: str, max_chars: int = 1400):
    chunks = []
    current_lines = []
    current_len = 0

    def flush():
        nonlocal current_lines, current_len
        block = "\n".join(current_lines).strip()
        if block:
            chunks.append(block)
        current_lines = []
        current_len = 0

    for raw_line in str(text or "").replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            if current_lines and current_lines[-1] != "":
                current_lines.append("")
            continue

        line_len = len(line) + 1
        is_heading = line.startswith("===") or line.startswith("---") or line.upper().startswith("DOCUMENT:")

        if is_heading and current_lines:
            flush()

        if current_len and current_len + line_len > max_chars:
            flush()

        current_lines.append(line)
        current_len += line_len

    flush()
    return chunks


def _source_group_from_filename(filename: str) -> str:
    name = os.path.basename(filename).lower()
    if name == "core_facts.txt":
        return "CORE_FACTS"
    if name == "custom_facts.txt":
        return "CUSTOM_FACTS"
    if name == "svsu_all_programs_list.txt":
        return "SVSU_ALL_PROGRAMS_LIST"
    if name == "pdf_knowledge.txt" or name.endswith(".pdf"):
        return "PDF"
    if name.endswith("_knowledge.txt"):
        return name.replace("_knowledge.txt", "").upper()
    if name.endswith("_data.txt"):
        source_group = name.replace("_data.txt", "").upper()
        return SOURCE_GROUP_ALIASES.get(source_group, source_group)
    if name == "results_directory.txt":
        return "EXAMINATION"
    source_group = os.path.splitext(name)[0].upper()
    return SOURCE_GROUP_ALIASES.get(source_group, source_group)


def _priority_for_source_group(source_group: str) -> int:
    return SOURCE_GROUP_PRIORITIES.get(source_group, 100)


def _iter_source_files():
    yielded = set()
    if not os.path.exists(KNOWLEDGE_BASE):
        return

    # Skip these special folders
    skip_dirs = {"Database", "Indexes"}

    for root, dirs, files in os.walk(KNOWLEDGE_BASE):
        # Modify dirs in-place to skip specific folders
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext in {".txt", ".json", ".pdf", ".csv"}:
                path = os.path.join(root, filename)
                normalized = os.path.normpath(path)
                if normalized not in yielded:
                    yielded.add(normalized)
                    source_type = "pdf" if ext == ".pdf" else "text"
                    yield normalized, source_type


def _extract_pdf_text(pdf_path: str) -> str:
    if fitz is None:
        return ""

    extracted_pages = []
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text("text") or ""
                if page_text.strip():
                    extracted_pages.append(page_text.strip())
    except Exception:
        return ""

    return "\n\n".join(extracted_pages).strip()


def _read_file_bytes(path: str) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return b""


def _read_source_document(path: str, source_type: str):
    raw_bytes = _read_file_bytes(path)
    if source_type == "pdf":
        content = _extract_pdf_text(path)
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.endswith(".json"):
                    # For JSON, we might want to prettify it for better chunking
                    data = json.load(f)
                    content = json.dumps(data, indent=2)
                elif path.endswith(".csv"):
                    # For CSV, read as text but add a header hint
                    content = f"CSV DATA FROM {os.path.basename(path)}:\n" + f.read()
                else:
                    content = f.read()
        except Exception:
            content = ""

    if not str(content or "").strip():
        return None

    source_group = _source_group_from_filename(path)
    source_label = os.path.basename(path)
    source_key = hashlib.sha1(f"{source_group}|{os.path.normpath(path)}".encode("utf-8")).hexdigest()
    return {
        "source_key": source_key,
        "source_group": source_group,
        "source_type": source_type,
        "source_label": source_label,
        "origin_path": os.path.normpath(path),
        "priority": _priority_for_source_group(source_group),
        "content": content,
        "raw_bytes": raw_bytes,
    }


def collect_knowledge_documents():
    documents = []
    for path, source_type in _iter_source_files():
        doc = _read_source_document(path, source_type)
        if doc:
            documents.append(doc)
    return documents


def get_latest_source_mtime() -> float:
    latest = 0.0
    for path, _source_type in _iter_source_files():
        try:
            latest = max(latest, os.path.getmtime(path))
        except OSError:
            continue
    return latest


def get_knowledge_db_path() -> str:
    db_dir = os.path.join(KNOWLEDGE_BASE, "Database")
    os.makedirs(db_dir, exist_ok=True)
    return KNOWLEDGE_DB_PATH


def _connect():
    db_path = get_knowledge_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_knowledge_store():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_sources (
                source_key TEXT PRIMARY KEY,
                source_group TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_label TEXT NOT NULL,
                origin_path TEXT NOT NULL,
                priority INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                source_key TEXT PRIMARY KEY,
                source_group TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_label TEXT NOT NULL,
                origin_path TEXT NOT NULL,
                priority INTEGER NOT NULL,
                full_text TEXT NOT NULL,
                normalized_full_text TEXT NOT NULL,
                raw_blob BLOB,
                raw_size_bytes INTEGER NOT NULL,
                content_sha1 TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                chunk_id TEXT PRIMARY KEY,
                source_key TEXT NOT NULL,
                source_group TEXT NOT NULL,
                source_label TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                normalized_content TEXT NOT NULL,
                priority INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(source_key) REFERENCES knowledge_sources(source_key) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts
            USING fts5(
                chunk_id UNINDEXED,
                source_group UNINDEXED,
                source_label UNINDEXED,
                title,
                content
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_group ON knowledge_documents(source_group)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_priority ON knowledge_documents(priority DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source_group ON knowledge_chunks(source_group)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_priority ON knowledge_chunks(priority DESC)")
        conn.commit()


def rebuild_knowledge_store(force: bool = False):
    db_path = get_knowledge_db_path()
    latest_source_mtime = get_latest_source_mtime()
    if not force and os.path.exists(db_path) and os.path.getmtime(db_path) >= latest_source_mtime:
        return {
            "status": "unchanged",
            "db_path": db_path,
            "sources": count_knowledge_sources(),
            "chunks": count_knowledge_chunks(),
        }

    init_knowledge_store()
    documents = collect_knowledge_documents()
    timestamp = datetime.now().isoformat(timespec="seconds")

    unique_chunk_signatures = set()
    source_rows = []
    document_rows = []
    chunk_rows = []

    for doc in documents:
        source_rows.append(
            (
                doc["source_key"],
                doc["source_group"],
                doc["source_type"],
                doc["source_label"],
                doc["origin_path"],
                doc["priority"],
                timestamp,
            )
        )
        document_rows.append(
            (
                doc["source_key"],
                doc["source_group"],
                doc["source_type"],
                doc["source_label"],
                doc["origin_path"],
                doc["priority"],
                doc["content"],
                _normalize_text(doc["content"]),
                sqlite3.Binary(doc["raw_bytes"]) if doc["raw_bytes"] else None,
                len(doc["raw_bytes"]),
                hashlib.sha1(doc["raw_bytes"] if doc["raw_bytes"] else doc["content"].encode("utf-8")).hexdigest(),
                timestamp,
            )
        )

        for chunk_index, chunk_text in enumerate(_chunk_text(doc["content"])):
            normalized_content = _normalize_text(chunk_text)
            if not normalized_content:
                continue

            title = next((line.strip() for line in chunk_text.splitlines() if line.strip()), "")[:180]
            signature = hashlib.sha1(f"{doc['source_group']}|{normalized_content[:500]}".encode("utf-8")).hexdigest()
            if signature in unique_chunk_signatures:
                continue
            unique_chunk_signatures.add(signature)

            chunk_id = hashlib.sha1(f"{doc['source_key']}|{chunk_index}|{normalized_content[:500]}".encode("utf-8")).hexdigest()
            chunk_rows.append(
                (
                    chunk_id,
                    doc["source_key"],
                    doc["source_group"],
                    doc["source_label"],
                    chunk_index,
                    title,
                    chunk_text,
                    normalized_content,
                    doc["priority"],
                    timestamp,
                )
            )

    with _connect() as conn:
        conn.execute("DELETE FROM knowledge_chunks_fts")
        conn.execute("DELETE FROM knowledge_chunks")
        conn.execute("DELETE FROM knowledge_documents")
        conn.execute("DELETE FROM knowledge_sources")
        conn.executemany(
            """
            INSERT INTO knowledge_sources (
                source_key, source_group, source_type, source_label, origin_path, priority, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            source_rows,
        )
        conn.executemany(
            """
            INSERT INTO knowledge_documents (
                source_key, source_group, source_type, source_label, origin_path, priority,
                full_text, normalized_full_text, raw_blob, raw_size_bytes, content_sha1, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            document_rows,
        )
        conn.executemany(
            """
            INSERT INTO knowledge_chunks (
                chunk_id, source_key, source_group, source_label, chunk_index, title,
                content, normalized_content, priority, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            chunk_rows,
        )
        conn.executemany(
            """
            INSERT INTO knowledge_chunks_fts (chunk_id, source_group, source_label, title, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(row[0], row[2], row[3], row[5], row[6]) for row in chunk_rows],
        )
        conn.commit()

    return {
        "status": "rebuilt",
        "db_path": db_path,
        "sources": len(source_rows),
        "documents": len(document_rows),
        "chunks": len(chunk_rows),
    }


def ensure_knowledge_store_ready(force: bool = False):
    return rebuild_knowledge_store(force=force)


def count_knowledge_sources() -> int:
    db_path = get_knowledge_db_path()
    if not os.path.exists(db_path):
        return 0
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM knowledge_sources").fetchone()
        return int(row["count"]) if row else 0


def count_knowledge_chunks() -> int:
    db_path = get_knowledge_db_path()
    if not os.path.exists(db_path):
        return 0
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM knowledge_chunks").fetchone()
        return int(row["count"]) if row else 0


def count_knowledge_documents() -> int:
    db_path = get_knowledge_db_path()
    if not os.path.exists(db_path):
        return 0
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM knowledge_documents").fetchone()
        return int(row["count"]) if row else 0


def load_runtime_knowledge_chunks():
    db_path = get_knowledge_db_path()
    if not os.path.exists(db_path):
        return []

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT chunk_id, source_group, source_label, title, content, normalized_content, priority
            FROM knowledge_chunks
            ORDER BY priority DESC, source_group ASC, chunk_index ASC
            """
        ).fetchall()

    runtime_chunks = []
    for row in rows:
        runtime_chunks.append(
            {
                "chunk_id": row["chunk_id"],
                "text": row["content"],
                "source": row["source_group"],
                "source_label": row["source_label"],
                "lower": row["normalized_content"],
                "title": row["title"] or row["source_label"],
                "title_lower": _normalize_text(row["title"] or row["source_label"]),
                "priority": int(row["priority"]),
            }
        )
    return runtime_chunks


def get_custom_facts_text() -> str:
    db_path = get_knowledge_db_path()
    if not os.path.exists(db_path):
        return ""

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT content
            FROM knowledge_chunks
            WHERE source_group = 'CUSTOM_FACTS'
            ORDER BY chunk_index ASC
            """
        ).fetchall()

    return "\n\n".join(row["content"] for row in rows).strip()


def upsert_custom_facts(facts: str):
    normalized_facts = str(facts or "").strip()
    timestamp = datetime.now().isoformat(timespec="seconds")
    source_key = hashlib.sha1("CUSTOM_FACTS|custom_facts.txt".encode("utf-8")).hexdigest()

    init_knowledge_store()
    with _connect() as conn:
        conn.execute("DELETE FROM knowledge_chunks_fts WHERE chunk_id IN (SELECT chunk_id FROM knowledge_chunks WHERE source_group = 'CUSTOM_FACTS')")
        conn.execute("DELETE FROM knowledge_chunks WHERE source_group = 'CUSTOM_FACTS'")
        conn.execute("DELETE FROM knowledge_documents WHERE source_group = 'CUSTOM_FACTS'")
        conn.execute("DELETE FROM knowledge_sources WHERE source_group = 'CUSTOM_FACTS'")

        if normalized_facts:
            conn.execute(
                """
                INSERT INTO knowledge_sources (
                    source_key, source_group, source_type, source_label, origin_path, priority, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_key,
                    "CUSTOM_FACTS",
                    "manual",
                    "custom_facts.txt",
                    os.path.join(BACKEND_KNOWLEDGE_DIR, "custom_facts.txt"),
                    SOURCE_GROUP_PRIORITIES["CUSTOM_FACTS"],
                    timestamp,
                ),
            )
            conn.execute(
                """
                INSERT INTO knowledge_documents (
                    source_key, source_group, source_type, source_label, origin_path, priority,
                    full_text, normalized_full_text, raw_blob, raw_size_bytes, content_sha1, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_key,
                    "CUSTOM_FACTS",
                    "manual",
                    "custom_facts.txt",
                    os.path.join(BACKEND_KNOWLEDGE_DIR, "custom_facts.txt"),
                    SOURCE_GROUP_PRIORITIES["CUSTOM_FACTS"],
                    normalized_facts,
                    _normalize_text(normalized_facts),
                    sqlite3.Binary(normalized_facts.encode("utf-8")),
                    len(normalized_facts.encode("utf-8")),
                    hashlib.sha1(normalized_facts.encode("utf-8")).hexdigest(),
                    timestamp,
                ),
            )

            chunk_rows = []
            for chunk_index, chunk_text in enumerate(_chunk_text(normalized_facts)):
                normalized_content = _normalize_text(chunk_text)
                if not normalized_content:
                    continue
                title = next((line.strip() for line in chunk_text.splitlines() if line.strip()), "")[:180]
                chunk_id = hashlib.sha1(f"{source_key}|{chunk_index}|{normalized_content[:500]}".encode("utf-8")).hexdigest()
                chunk_rows.append(
                    (
                        chunk_id,
                        source_key,
                        "CUSTOM_FACTS",
                        "custom_facts.txt",
                        chunk_index,
                        title,
                        chunk_text,
                        normalized_content,
                        SOURCE_GROUP_PRIORITIES["CUSTOM_FACTS"],
                        timestamp,
                    )
                )

            conn.executemany(
                """
                INSERT INTO knowledge_chunks (
                    chunk_id, source_key, source_group, source_label, chunk_index, title,
                    content, normalized_content, priority, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                chunk_rows,
            )
            conn.executemany(
                """
                INSERT INTO knowledge_chunks_fts (chunk_id, source_group, source_label, title, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(row[0], row[2], row[3], row[5], row[6]) for row in chunk_rows],
            )

        conn.commit()


def get_knowledge_store_overview():
    db_path = get_knowledge_db_path()
    if not os.path.exists(db_path):
        return {
            "db_path": db_path,
            "sources": 0,
            "documents": 0,
            "chunks": 0,
            "groups": [],
            "largest_documents": [],
        }

    with _connect() as conn:
        groups = [
            dict(row)
            for row in conn.execute(
                """
                SELECT source_group, COUNT(*) AS document_count, MAX(priority) AS priority
                FROM knowledge_documents
                GROUP BY source_group
                ORDER BY priority DESC, source_group ASC
                """
            ).fetchall()
        ]
        largest_documents = [
            dict(row)
            for row in conn.execute(
                """
                SELECT source_group, source_label, raw_size_bytes, substr(origin_path, 1, 500) AS origin_path
                FROM knowledge_documents
                ORDER BY raw_size_bytes DESC, source_label ASC
                LIMIT 12
                """
            ).fetchall()
        ]

    return {
        "db_path": db_path,
        "sources": count_knowledge_sources(),
        "documents": count_knowledge_documents(),
        "chunks": count_knowledge_chunks(),
        "groups": groups,
        "largest_documents": largest_documents,
    }


def search_knowledge_store(query: str, limit: int = 20):
    cleaned_query = str(query or "").strip()
    if not cleaned_query:
        return []

    db_path = get_knowledge_db_path()
    if not os.path.exists(db_path):
        return []

    limit = max(1, min(int(limit or 20), 50))
    match_query = " OR ".join(token for token in cleaned_query.split() if token.strip())

    with _connect() as conn:
        try:
            rows = conn.execute(
                """
                SELECT f.chunk_id, f.source_group, f.source_label, k.title,
                       snippet(knowledge_chunks_fts, 3, '<mark>', '</mark>', ' ... ', 18) AS snippet,
                       bm25(knowledge_chunks_fts) AS rank_score
                FROM knowledge_chunks_fts f
                JOIN knowledge_chunks k ON k.chunk_id = f.chunk_id
                WHERE knowledge_chunks_fts MATCH ?
                ORDER BY rank_score ASC, k.priority DESC
                LIMIT ?
                """,
                (match_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute(
                """
                SELECT chunk_id, source_group, source_label, title,
                       substr(content, 1, 500) AS snippet
                FROM knowledge_chunks
                WHERE normalized_content LIKE ?
                ORDER BY priority DESC
                LIMIT ?
                """,
                (f"%{_normalize_text(cleaned_query)}%", limit),
            ).fetchall()

    return [dict(row) for row in rows]


def get_knowledge_document_details(source_key: str):
    source_key = str(source_key or "").strip()
    if not source_key:
        return None

    db_path = get_knowledge_db_path()
    if not os.path.exists(db_path):
        return None

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT source_key, source_group, source_type, source_label, origin_path,
                   priority, raw_size_bytes, content_sha1, updated_at, full_text
            FROM knowledge_documents
            WHERE source_key = ?
            """,
            (source_key,),
        ).fetchone()

    if not row:
        return None

    data = dict(row)
    data["preview"] = data["full_text"][:5000]
    data["full_text_length"] = len(data["full_text"])
    del data["full_text"]
    return data
