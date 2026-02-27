import sqlite3

def setup_database():
    """
    Creates the database file and the necessary tables for PaperLink Core.
    """
    conn = sqlite3.connect('paperlink.db')
    cursor = conn.cursor()

    # --- TABLE 1: File Transfer Layer (Phase 1) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            telegram_file_id TEXT NOT NULL,
            shareable_link TEXT NOT NULL UNIQUE,
            owner_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            version INTEGER NOT NULL DEFAULT 1
        );
    ''')

    # --- TABLE 2: Projects (Phase 2 - The 'Container') ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE, 
            owner_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # --- TABLE 3: Project Files (Phase 2 - The 'Content') ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            content BLOB NOT NULL,
            content_type TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        );
    ''')

    conn.commit()
    conn.close()
    print("Database 'paperlink.db' successfully initialized with Infrastructure & Hosting tables.")

if __name__ == '__main__':
    setup_database()