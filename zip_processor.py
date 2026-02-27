import zipfile
import io
from database import Database

class ZipProcessor:
    def __init__(self):
        self.db = Database()

    def process_and_upload(self, project_name, owner_id, zip_bytes):
        """
        Takes raw bytes of a ZIP file, extracts them in memory,
        and saves them as a PaperLink project.
        """
        files_to_store = {}
        
        # Use io.BytesIO to treat the raw bytes like a file without saving to disk
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zref:
            for file_info in zref.infolist():
                # Skip directories, we only care about the files themselves
                if file_info.is_dir():
                    continue
                
                # Read file content
                with zref.open(file_info) as f:
                    content = f.read()
                    files_to_store[file_info.filename] = content

        if not files_to_store:
            print("Error: The ZIP file appears to be empty.")
            return None

        # Hand off the structured files to the database layer
        slug = self.db.create_project(project_name, owner_id, files_to_store)
        
        if slug:
            print(f"Deployment Successful! Project live at: /{slug}/index.html")
            return slug
        else:
            print("Deployment failed: Project name might already be taken.")
            return None

# --- Testing the Pipeline ---
if __name__ == "__main__":
    # Mocking a ZIP file for a test run
    def create_mock_zip():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('index.html', '<html><body><h1>Hello PaperLink!</h1></body></html>')
            z.writestr('css/style.css', 'body { background: #f0f0f0; }')
        return buf.getvalue()

    processor = ZipProcessor()
    mock_zip_data = create_mock_zip()
    
    # Simulate an upload
    project_slug = processor.process_and_upload("My First Website", 123, mock_zip_data)