import os
from pathlib import Path
from docx import Document
from PyPDF2 import PdfReader
import win32com.client  # 用于读取.doc文件

def read_docx(file_path:Path):
    """读取docx文件内容"""
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def read_pdf(file_path:Path):
    """读取pdf文件内容"""
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        text = []
        for page in reader.pages:
            text.append(page.extract_text())
        return '\n'.join(text)

def read_doc(file_path:Path):
    """读取doc文件内容"""
    try:
        # 转换为绝对路径字符串，避免符号链接或相对路径问题
        abs_path = str(file_path.resolve())
        word = win32com.client.Dispatch("Word.Application")
        # 确保Word在后台运行，不显示界面
        word.Visible = False  
        doc = word.Documents.Open(abs_path)
        text = doc.Content.Text
        doc.Close()
        word.Quit()
        return text
    except Exception as e:
        print(f"Error reading .doc file: {e}")
        return None

def read_file(file_path:Path):
    """根据文件类型调用相应的读取函数"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.docx':
        return read_docx(file_path)
    elif ext == '.pdf':
        return read_pdf(file_path)
    elif ext == '.doc':
        return read_doc(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")