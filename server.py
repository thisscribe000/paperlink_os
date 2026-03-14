import os
import requests
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from database import Database

load_dotenv()
db = Database()
TOKEN = os.getenv("TELEGRAM_TOKEN")
SUCCESS_REDIRECT_URL = "https://t.me/PaperLinkBuilders" 

class PaperLinkHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/submit-lead':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            slug = params.get('slug', [''])[0]
            raw_handle = params.get('handle', [''])[0].replace('%40', '').strip('@')
            clean_handle = f"@{raw_handle}" if raw_handle else "Anonymous"
            
            if slug and raw_handle:
                # 1. Save Lead to DB
                db.cursor.execute("INSERT INTO leads (project_slug, telegram_handle) VALUES (?, ?)", (slug, clean_handle))
                db.conn.commit()
                
                # 2. Lookup Owner to notify them
                owner_id = db.get_project_owner(slug)
                if owner_id:
                    msg = f"🔔 *New Lead Captured!*\n\nProject: `{slug}`\nUser: {clean_handle}\n\nGo close that deal!"
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                 data={"chat_id": owner_id, "text": msg, "parse_mode": "Markdown"})
                
                # 3. Redirect back to Telegram
                self.send_response(303)
                self.send_header('Location', SUCCESS_REDIRECT_URL)
                self.end_headers()

    def do_GET(self):
        try:
            # Simple Admin Dashboard
            if self.path == '/' or self.path == '':
                db.cursor.execute("SELECT name, slug FROM projects")
                projects = db.cursor.fetchall()
                db.cursor.execute("SELECT telegram_handle, project_slug, created_at FROM leads ORDER BY created_at DESC LIMIT 10")
                leads = db.cursor.fetchall()

                p_rows = "".join([f"<li class='py-3 border-b flex justify-between items-center'><span>{p['name']}</span><a href='/{p['slug']}/index.html' class='text-blue-600 font-bold'>View</a></li>" for p in projects])
                l_rows = "".join([f"<tr><td class='p-2 border-b'>{l['telegram_handle']}</td><td class='p-2 border-b'>{l['project_slug']}</td></tr>" for l in leads])

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                html = f"""
                <html>
                <head><script src="https://cdn.tailwindcss.com"></script></head>
                <body class="bg-white p-10 font-sans">
                    <div class="max-w-4xl mx-auto">
                        <h1 class="text-4xl font-black mb-10 tracking-tighter uppercase">PaperLink OS Monitor</h1>
                        <div class="grid grid-cols-2 gap-10">
                            <div class="bg-gray-50 p-6 rounded-3xl border">
                                <h2 class="font-bold mb-4">Active Sites</h2><ul>{p_rows}</ul>
                            </div>
                            <div class="bg-gray-50 p-6 rounded-3xl border">
                                <h2 class="font-bold mb-4">Recent Leads</h2>
                                <table class="w-full text-sm"><tbody>{l_rows}</tbody></table>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))
                return

            # Serve Dynamic Files
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


        if self.path.startswith('/assets/'):
            local_path = self.path.strip('/')
            if os.path.exists(local_path):
                self.send_response(200)
                # Simple way to set content type
                if local_path.endswith(".jpg") or local_path.endswith(".jpeg"):
                    self.send_header('Content-type', 'image/jpeg')
                elif local_path.endswith(".png"):
                    self.send_header('Content-type', 'image/png')
                self.end_headers()
                with open(local_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
if __name__ == "__main__":
    server = HTTPServer(('localhost', 8000), PaperLinkHandler)
    print("🚀 PaperLink Server Online.")
    server.serve_forever()