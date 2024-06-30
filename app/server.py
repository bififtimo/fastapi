import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Path, BackgroundTasks
from app.celery import celery
from app.database import engine, Base, Session
from app.models import Documents, Documents_text
from datetime import datetime
from uuid import uuid4
import pytesseract
from PIL import Image
from app.database import get_db

app = FastAPI()

Base.metadata.create_all(bind=engine)

# Убедимся, что папка для документов существует
DOCUMENTS_FOLDER = "documents"
if not os.path.exists(DOCUMENTS_FOLDER):
    os.makedirs(DOCUMENTS_FOLDER)

@app.get("/")
def hello():
    """
    Пример простого эндпоинта для приветствия.
    """
    return "Hello world!"

@app.post("/upload_doc/", response_model=dict)
async def upload_doc(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Загружает документ на сервер, сохраняет его на диск и добавляет запись в базу данных.

    Parameters:
    - file (UploadFile): Файл для загрузки.
    - db (Session): Сессия базы данных SQLAlchemy.

    Returns:
    - dict: JSON с информацией о загруженном документе (id, путь, дата).
    """
    # Генерируем уникальное имя файла и сохраняем его на диск
    file_extension = os.path.splitext(file.filename)[-1]
    unique_filename = f"{uuid4()}{file_extension}"
    file_path = os.path.join(DOCUMENTS_FOLDER, unique_filename)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Добавляем запись в базу данных
    new_document = Documents(
        path=file_path,
        date=datetime.utcnow()
    )

    try:
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"id": new_document.id, "path": new_document.path, "date": new_document.date}

@app.delete("/doc_delete/{document_id}")
def delete_document(document_id: int = Path(..., title="The ID of the document to delete"),
                    db: Session = Depends(get_db)):
    """
    Удаляет документ по его ID из базы данных и с диска.

    Parameters:
    - document_id (int): ID документа для удаления (часть URL).
    - db (Session): Сессия базы данных SQLAlchemy.

    Returns:
    - dict: JSON с информацией об успешности выполнения запроса.
    """
    # Find the document by id
    document = db.query(Documents).filter(Documents.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete document from disk
    try:
        os.remove(document.path)  # Assuming path is stored in the database
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document from disk: {str(e)}")

    # Delete document from the database
    db.delete(document)
    db.commit()

    return {"message": f"Document with id {document_id} has been deleted"}

@app.post("/analyse_doc/")
async def analyse_doc(id: int, db: Session = Depends(get_db)):
    """
    Анализирует документ по его ID.

    Parameters:
    - id (int): ID документа для анализа.
    - background_tasks (BackgroundTasks): Задачи, которые будут выполнены в фоновом режиме.
    - db (Session): Сессия базы данных SQLAlchemy.

    Returns:
    - dict: JSON с информацией об успешности выполнения запроса.
    """
    document = db.query(Documents).filter(Documents.id == id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Запускаем задачу на анализ документа в фоновом режиме
    """
    Обработка документа: извлечение текста и сохранение его в базу данных.
    """
    text_result = image_to_text(document.path)
    if text_result == 1:
        logging.error("Failed to process the document")
        return

    document_text = Documents_text(id_doc=document.id, text=text_result)
    db.add(document_text)
    db.commit()
    db.refresh(document_text)

    return document_text

    return {"message": "Document analysis started", "document_id": id}

@celery.task
def image_to_text(path: str):
    """
    Задача Celery для извлечения текста из изображения.
    """
    try:
        image = Image.open(path)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        logging.error(f"Error processing image to text: {e}")
        return 1
    return text

@app.get("/get_text/{doc_id}", response_model=dict)
async def get_text(doc_id: int, db: Session = Depends(get_db)):
    """
    Получение извлеченного текста по ID документа.

    Parameters:
    - doc_id (int): ID документа.

    Returns:
    - dict: JSON с извлеченными текстами.
    """
    texts = db.query(Documents_text).filter(Documents_text.id_doc == doc_id).all()
    if not texts:
        raise HTTPException(status_code=404, detail="Text not found")

    return {"texts": [text.text for text in texts]}
