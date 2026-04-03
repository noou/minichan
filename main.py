from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
from datetime import datetime

from database import init_db, get_db, Thread, Post

app = FastAPI(title="Minichan")

# Initialize database
init_db()

# Setup static files and templates
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def save_upload_file(file: UploadFile) -> Optional[str]:
    """Save uploaded file and return filename or None"""
    if not file or not file.filename:
        return None

    # Get file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None

    # Generate unique filename
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Save file
    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())

    return filename


def format_date(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%d/%m/%Y %H:%M:%S")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """Main page - list all threads"""
    threads = db.query(Thread).order_by(Thread.bumped_at.desc()).all()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "threads": threads, "format_date": format_date}
    )


@app.post("/create")
async def create_thread(
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Create a new thread"""
    if not title or not content:
        raise HTTPException(status_code=400, detail="Title and content are required")

    image_filename = save_upload_file(image)

    thread = Thread(
        title=title,
        content=content,
        image=image_filename
    )
    db.add(thread)
    db.commit()

    return RedirectResponse(url="/", status_code=303)


@app.get("/thread/{thread_id}", response_class=HTMLResponse)
async def view_thread(thread_id: int, request: Request, db: Session = Depends(get_db)):
    """View a single thread with all posts"""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    posts = db.query(Post).filter(Post.thread_id == thread_id).order_by(Post.created_at.asc()).all()

    return templates.TemplateResponse(
        "thread.html",
        {
            "request": request,
            "thread": thread,
            "posts": posts,
            "format_date": format_date
        }
    )


@app.post("/thread/{thread_id}/reply")
async def reply_to_thread(
    thread_id: int,
    content: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Reply to a thread"""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    image_filename = save_upload_file(image)

    post = Post(
        thread_id=thread_id,
        content=content,
        image=image_filename
    )
    db.add(post)

    # Update thread bump time
    thread.bumped_at = datetime.utcnow()
    db.commit()

    return RedirectResponse(url=f"/thread/{thread_id}", status_code=303)


@app.post("/thread/{thread_id}/delete")
async def delete_thread(thread_id: int, db: Session = Depends(get_db)):
    """Delete a thread"""
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Delete thread images
    if thread.image:
        try:
            os.remove(os.path.join(UPLOAD_DIR, thread.image))
        except OSError:
            pass

    # Delete post images
    for post in thread.posts:
        if post.image:
            try:
                os.remove(os.path.join(UPLOAD_DIR, post.image))
            except OSError:
                pass

    db.delete(thread)
    db.commit()

    return RedirectResponse(url="/", status_code=303)


@app.post("/post/{post_id}/delete")
async def delete_post(post_id: int, db: Session = Depends(get_db)):
    """Delete a single post"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    thread_id = post.thread_id

    # Delete post image
    if post.image:
        try:
            os.remove(os.path.join(UPLOAD_DIR, post.image))
        except OSError:
            pass

    db.delete(post)
    db.commit()

    return RedirectResponse(url=f"/thread/{thread_id}", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)