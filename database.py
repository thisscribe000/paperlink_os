import sqlite3
import mimetypes
import json


class Database:
    def __init__(self, db_file='paperlink.db'):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._setup_tables()
        print("Connected to PaperLink Database.")

    def _setup_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT,
                slug TEXT UNIQUE,
                owner_id INTEGER
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_files (
                id INTEGER PRIMARY KEY,
                project_id INTEGER,
                file_path TEXT,
                content BLOB,
                content_type TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_slug TEXT,
                telegram_handle TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_slug TEXT NOT NULL UNIQUE,
                template_type TEXT NOT NULL,
                config_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def create_project(self, name, owner_id, files_dict):
        slug = name.lower().replace(" ", "-").strip()

        try:
            self.cursor.execute("SELECT id FROM projects WHERE slug = ?", (slug,))
            existing = self.cursor.fetchone()

            if existing:
                p_id = existing['id']
                self.cursor.execute("DELETE FROM project_files WHERE project_id = ?", (p_id,))
            else:
                self.cursor.execute(
                    "INSERT INTO projects (name, slug, owner_id) VALUES (?, ?, ?)",
                    (name, slug, owner_id)
                )
                p_id = self.cursor.lastrowid

            for path, content in files_dict.items():
                ctype, _ = mimetypes.guess_type(path)
                self.cursor.execute(
                    "INSERT INTO project_files (project_id, file_path, content, content_type) VALUES (?, ?, ?, ?)",
                    (p_id, path, content, ctype or 'text/plain')
                )

            self.conn.commit()
            return slug

        except Exception as e:
            print(f"Database Error: {e}")
            self.conn.rollback()
            return None

    def save_project_config(self, project_slug, template_type, config_data):
        config_json = json.dumps(config_data)

        self.cursor.execute("SELECT id FROM project_configs WHERE project_slug = ?", (project_slug,))
        existing = self.cursor.fetchone()

        if existing:
            self.cursor.execute("""
                UPDATE project_configs
                SET template_type = ?, config_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE project_slug = ?
            """, (template_type, config_json, project_slug))
        else:
            self.cursor.execute("""
                INSERT INTO project_configs (project_slug, template_type, config_json)
                VALUES (?, ?, ?)
            """, (project_slug, template_type, config_json))

        self.conn.commit()

    def get_project_config(self, project_slug):
        self.cursor.execute("""
            SELECT template_type, config_json
            FROM project_configs
            WHERE project_slug = ?
        """, (project_slug,))
        row = self.cursor.fetchone()

        if not row:
            return None

        return {
            "template_type": row["template_type"],
            "config": json.loads(row["config_json"])
        }

    def get_project_file(self, slug, file_path):
        self.cursor.execute("""
            SELECT pf.content, pf.content_type
            FROM project_files pf
            JOIN projects p ON pf.project_id = p.id
            WHERE p.slug = ? AND pf.file_path = ?
        """, (slug, file_path))
        return self.cursor.fetchone()

    def delete_project(self, slug):
        self.cursor.execute("SELECT id FROM projects WHERE slug = ?", (slug,))
        p = self.cursor.fetchone()

        if p:
            self.cursor.execute("DELETE FROM project_files WHERE project_id = ?", (p['id'],))
            self.cursor.execute("DELETE FROM projects WHERE id = ?", (p['id'],))
            self.cursor.execute("DELETE FROM project_configs WHERE project_slug = ?", (slug,))
            self.conn.commit()
            return True

        return False

    def close(self):
        self.conn.close()