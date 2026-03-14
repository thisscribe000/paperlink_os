import sqlite3
import json

class Database:
    def __init__(self):
        # check_same_thread=False allows the Bot and Server to use the same connection
        self.conn = sqlite3.connect("paperlink.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._ensure_tables()
        print("Connected to PaperLink Database.")

    def _ensure_tables(self):
        """Creates the leads table if it doesn't exist yet."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_slug TEXT,
                telegram_handle TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        
    def save_asset(self, owner_id, file_id, file_type, local_path):
        self.cursor.execute(
            "INSERT INTO assets (owner_id, file_id, file_type, local_path) VALUES (?, ?, ?, ?)",
            (owner_id, file_id, file_type, local_path)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    # ---------------------------
    # OWNERSHIP & QUERY HELPERS
    # ---------------------------

    def get_project_owner(self, slug):
        """Returns the Telegram ID of the project owner."""
        self.cursor.execute("SELECT owner_id FROM projects WHERE slug=?", (slug,))
        row = self.cursor.fetchone()
        return str(row["owner_id"]) if row else None

    def get_user_projects(self, owner_id):
        """Returns all projects belonging to a specific user."""
        self.cursor.execute("SELECT name, slug FROM projects WHERE owner_id=?", (owner_id,))
        return self.cursor.fetchall()

    # ---------------------------
    # CREATE PROJECT
    # ---------------------------

    def create_project(self, name, owner_id, files):
        slug = name.lower().replace(" ", "-").strip()

        # Double check uniqueness before inserting
        if self.get_project_owner(slug):
            return False, "This project name is already taken."

        self.cursor.execute(
            "INSERT INTO projects (name, slug, owner_id) VALUES (?, ?, ?)",
            (name, slug, owner_id)
        )
        project_id = self.cursor.lastrowid

        for path, content in files.items():
            self.cursor.execute(
                """INSERT INTO project_files (project_id, file_path, content, content_type)
                   VALUES (?, ?, ?, ?)""",
                (project_id, path, content, "text/html")
            )
        self.conn.commit()
        return True, slug

    # ---------------------------
    # GET PROJECT FILE
    # ---------------------------

    def get_project_file(self, slug, file_path):
        self.cursor.execute(
            """SELECT pf.content, pf.content_type
               FROM project_files pf
               JOIN projects p ON pf.project_id = p.id
               WHERE p.slug=? AND pf.file_path=?""",
            (slug, file_path)
        )
        row = self.cursor.fetchone()
        if not row: return None
        return {"content": row["content"], "content_type": row["content_type"]}

    # ---------------------------
    # UPDATE / DELETE
    # ---------------------------

    def update_project_file(self, slug, file_path, content):
        self.cursor.execute(
            """UPDATE project_files SET content=?
               WHERE file_path=? AND project_id=(SELECT id FROM projects WHERE slug=?)""",
            (content, file_path, slug)
        )
        self.conn.commit()

    def delete_project(self, slug):
        self.cursor.execute("DELETE FROM project_files WHERE project_id=(SELECT id FROM projects WHERE slug=?)", (slug,))
        self.cursor.execute("DELETE FROM projects WHERE slug=?", (slug,))
        self.conn.commit()
        return True

    # ---------------------------
    # CONFIG MANAGEMENT
    # ---------------------------

    def save_project_config(self, slug, config):
        self.cursor.execute("UPDATE projects SET config=? WHERE slug=?", (json.dumps(config), slug))
        self.conn.commit()

    def get_project_config(self, slug):
        self.cursor.execute("SELECT config FROM projects WHERE slug=?", (slug,))
        row = self.cursor.fetchone()
        return json.loads(row["config"]) if row and row["config"] else None