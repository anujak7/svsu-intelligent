SVSU KNOWLEDGE BASE - UNIFIED HYBRID ARCHITECTURE
==================================================

As requested, all university data has been merged into a high-performance 
Relational and Vector database system.

Database Structure (The Brain):
------------------------------
1.  Database/svsu_knowledge.db
    - This is now the ONLY source of truth for the bot.
    - Contains ALL text from 'Text_Knowledge', 'Structured_Data' (including JSON), and 'PDFs'.
    - Optimized with SQLite FTS5 for 100% accurate keyword matching.

2.  Indexes/faiss_db/
    - High-speed Vector database for semantic (meaning-based) search.
    - Synchronized directly from the master SQLite database.

3.  Structured_Data/master_fact_sheet.json
    - High-precision cache for critical university facts.

Backup Folders:
---------------
The following folders are kept as human-readable backups:
- Text_Knowledge/ (Raw .txt files)
- Structured_Data/ (JSON & catalogs)
- PDFs/ (Original documents)

Performance:
------------
The bot now uses a 'Hybrid Triple-Retrieval' system:
1. SQL Lookup (For exact matches)
2. BM25 Search (For keyword relevance from DB)
3. FAISS Vector Search (For semantic understanding)

This ensures maximum accuracy and handling of high traffic.
