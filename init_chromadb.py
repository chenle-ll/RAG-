# init_chromadb.py
import chromadb
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_community.chat_models import ChatTongyi
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from langchain_community.embeddings import DashScopeEmbeddings
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter


def init_chroma():
    # 创建嵌入模型
    # 全局初始化
    embeddings = DashScopeEmbeddings(model="text-embedding-v1", dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"))
    # llm = init_chat_model("deepseek-chat", model_provider="deepseek")
    llm = ChatTongyi(model="qwen-max")
    # 加载文档  pip install pymupdf
    loader = PyMuPDFLoader("《城市信息模型（CIM）基础平台技术导则》（修订版）.pdf")
    # loader = Docx2txtLoader("../人事管理流程.docx")
    pages = loader.load_and_split()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=200,
                                                   separators=["\n\n", "\n", "。", ";"])
    texts = text_splitter.create_documents([page.page_content for page in pages])
    # 返回Chroma数据库
    return Chroma.from_documents(documents=texts, embedding=embeddings)

