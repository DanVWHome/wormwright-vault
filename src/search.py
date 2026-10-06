"""SQLite LIKE semantics on decrypted metadata in memory; never persisted."""
from contextlib import closing
import sqlite3


def matching_ids(records, query):
    if not query:
        return {record['id'] for record in records}
    with closing(sqlite3.connect(':memory:')) as search:
        search.execute('CREATE TABLE metadata (id TEXT, description TEXT, link TEXT, notes TEXT)')
        search.executemany('INSERT INTO metadata VALUES (?,?,?,?)',
                           [(record['id'], record.get('description', ''), record.get('link', ''), record.get('notes', '')) for record in records])
        pattern = '%' + query + '%'
        return {row[0] for row in search.execute('SELECT id FROM metadata WHERE description LIKE ? OR link LIKE ? OR notes LIKE ?', (pattern, pattern, pattern))}
