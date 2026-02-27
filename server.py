from http.server import BaseHTTPRequestHandler, HTTPServer
import io
from database import Database
from zip_processor import ZipProcessor

# Single persistent connection for speed
db = Database()

class PaperLinkRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handles ZIP uploads via Bot/Curl"""
        if self.path == '/submit-lead':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Simple parsing: slug=waitlist&handle=@username
            params = dict(x.split('=') for x in post_data.split('&'))
            slug = params.get('slug')
            handle = params.get('handle', '').replace('%40', '@') # Clean the @ symbol
            
            if slug and handle:
                db.cursor.execute("INSERT INTO leads (project_slug, telegram_handle) VALUES (?, ?)", (slug, handle))
                db.conn.commit()
                
                # Send back a success message
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(bytes("<h3>Success! See you in the community.</h3>", "utf-8"))
            return
        if self.path == '/upload':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            processor = ZipProcessor()
            # Default to 'Manual-Upload' for now
            slug = processor.process_and_upload("Manual-Upload", 99, body)
            if slug:
                self.send_response(201); self.end_headers()
                self.wfile.write(bytes(f"Deployed: {slug}", "utf8"))

    def do_GET(self):
        """Routes requests from the Cloudflare tunnel"""
        try:
            path = self.path
            if path == '/favicon.ico':
                self.send_response(404); self.end_headers(); return

            # 1. SHOW DASHBOARD
            if path == '/' or path == '':
                db.cursor.execute("SELECT name, slug FROM projects")
                projects = db.cursor.fetchall()
                links = "".join([f"<li>{p['name']} - <a href='/{p['slug']}/index.html'>Visit</a></li>" for p in projects])
                
                self.send_response(200); self.send_header('Content-type', 'text/html'); self.end_headers()
                self.wfile.write(bytes(f"<h1>🚀 PaperLink Console</h1><ul>{links}</ul>", "utf8"))
                return

            # 2. ROUTE FOLDER-STYLE PATHS (e.g., /my-slug/index.html)
            parts = path.strip('/').split('/')
            if len(parts) >= 1:
                slug = parts[0]
                # Default to index.html if just the slug is provided
                requested_file = "/".join(parts[1:]) if len(parts) > 1 else 'index.html'

                file_data = db.get_project_file(slug, requested_file)
                if file_data:
                    self.send_response(200)
                    self.send_header('Content-type', file_data['content_type'])
                    self.end_headers()
                    self.wfile.write(file_data['content'])
                    return

            self.send_response(404); self.end_headers()
        except Exception as e:
            print(f"Error: {e}"); self.send_response(500); self.end_headers()

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, PaperLinkRequestHandler)
    print(f"PaperLink Server live on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()