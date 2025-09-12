import os
from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    load_dotenv()
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))

    # Point to api.app
    uvicorn.run("api.app:app", port=port, reload=True)
