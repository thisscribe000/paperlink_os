import os
import requests
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from database import Database

# 1. INITIAL SETUP
load_dotenv()
db = Database()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# --- PASTE YOUR NEW GROUP LINK HERE ---
SUCCESS_REDIRECT_URL = "https://t.me/PaperLinkBuilders" 

class PaperLinkHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/submit-lead':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            slug = params.get('slug', [''])[0]
            # Strip all @ symbols and force exactly one at the start
            raw_handle = params.get('handle', [''])[0].replace('%40', '').strip('@')
            clean_handle = f"@{raw_handle}" if raw_handle else "Anonymous"
            
            if slug and raw_handle:
                # Save Lead
                db.cursor.execute("INSERT INTO leads (project_slug, telegram_handle) VALUES (?, ?)", (slug, clean_handle))
                db.conn.commit()
                
                # Barraos Notification
                msg = f"🚨 *Barraos Alert!*\nNew Collaborator: {clean_handle}\nProject: `{slug}`"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                             data={"chat_id": ADMIN_ID, "text": msg, "parse_mode": "Markdown"})
                
                # Instant Redirect
                self.send_response(303)
                self.send_header('Location', SUCCESS_REDIRECT_URL)
                self.end_headers()

    def do_GET(self):
        try:
            if self.path == '/' or self.path == '':
                # Serve the Admin Dashboard
                db.cursor.execute("SELECT name, slug FROM projects")
                projects = db.cursor.fetchall()
                db.cursor.execute("SELECT telegram_handle, project_slug, created_at FROM leads ORDER BY created_at DESC")
                leads = db.cursor.fetchall()

                p_rows = "".join([f"<li class='py-3 border-b flex justify-between items-center'><span class='font-medium'>{p['name']}</span><a href='/{p['slug']}/index.html' class='text-blue-600 font-bold'>Live Site</a></li>" for p in projects])
                l_rows = "".join([f"<tr><td class='p-3 border-b'>{l['telegram_handle']}</td><td class='p-3 border-b'>{l['project_slug']}</td><td class='p-3 border-b opacity-40 text-xs'>{l['created_at']}</td></tr>" for l in leads])

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                html = f"""
                <html>
                <head><script src="https://cdn.tailwindcss.com"></script></head>
                <body class="bg-white p-10 font-sans">
                    <div class="max-w-5xl mx-auto">
                        <header class="mb-12"><h1 class="text-5xl font-black italic tracking-tighter uppercase">PaperLink OS</h1></header>
                        <div class="grid md:grid-cols-2 gap-10">
                            <div class="bg-gray-50 p-8 rounded-[2rem] border">
                                <h2 class="text-xl font-bold mb-6">Active Pulses</h2><ul class="divide-y">{p_rows}</ul>
                            </div>
                            <div class="bg-gray-50 p-8 rounded-[2rem] border">
                                <h2 class="text-xl font-bold mb-6">Collaborators</h2>
                                <table class="w-full text-left text-sm"><tbody>{l_rows}</tbody></table>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))
                return

            parts = self.path.strip('/').split('/')
            if len(parts) >= 2:
                slug, file_path = parts[0], "/".join(parts[1:])
                file_data = db.get_project_file(slug, file_path)
                if file_data:
                    self.send_response(200)
                    self.send_header('Content-type', file_data['content_type'])
                    self.end_headers()
                    self.wfile.write(file_data['content'])
                    return
            self.send_error(404)
        except Exception as e:
            print(f"Server Error: {e}")
            self.send_error(500)

if __name__ == "__main__":
    server = HTTPServer(('localhost', 8000), PaperLinkHandler)
    print("🚀 PaperLink OS: Infrastructure Live on Barraos.")
    server.serve_forever()