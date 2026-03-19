import os

import langchain
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.embeddings.dashscope import DashScopeEmbeddings
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
# 添加必要的导入
import time
from fastapi import UploadFile, File, Form
import tempfile
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
# import pymysql
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_community.llms import Tongyi
from langchain_openai import ChatOpenAI
from langchain_community.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from starlette.responses import StreamingResponse

from rag.deepseek_rag.init_chromadb import init_chroma

# 禁用 Streamlit 警告
import warnings
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=f'backend_{datetime.now().strftime("%Y%m%d")}.log'
)
logger = logging.getLogger("rag_db")


# 初始化FastAPI应用
app = FastAPI(
    title="智能知识助手后端",
    description="提供知识查询、SQL执行和系统状态检查的API服务",
    version="1.0"
)

class UserContext(BaseModel):
    username: str
    role: str

class QueryRequest(BaseModel):
    #  用户输入问题
    question: str
    # 用户其他的信息
    user_ctx: UserContext
    # 历史记录
    chat_history: List[Dict[str, Any]] = []


# 全局初始化（在函数外部）
#llm = init_chat_model("deepseek-chat", model_provider="deepseek")
llm = ChatTongyi(model="qwen-max")
# 完成知识库构建
vector_db = init_chroma()
retriever = vector_db.as_retriever(search_kwargs={"k": 5})


def format_chat_history(chat_history):
    """格式化聊天历史"""
    if not chat_history:
        return "无历史对话"

    formatted = []
    for msg in chat_history[-6:]:  # 只保留最近6轮
        role = "用户" if msg["role"] == "user" else "助手"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)


def rewrite_query_with_history(question, chat_history):
    """根据对话历史重写查询，使其更完整"""
    if not chat_history:
        return question  # 如果没有历史，直接返回原问题

    # 构建重写提示
    rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个查询优化助手。根据对话历史重新表述当前问题，使其更完整、更易于检索相关信息。

        对话历史：
        {chat_history}

        当前问题：{question}

        请输出重写后的问题，不要添加其他内容。""")
    ])

    rewrite_chain = rewrite_prompt | llm | StrOutputParser()

    formatted_history = format_chat_history(chat_history)
    rewritten_query = rewrite_chain.invoke({
        "chat_history": formatted_history,
        "question": question
    })

    logger.info(f"原始问题: {question} -> 重写后: {rewritten_query}")
    return rewritten_query.strip()

@app.post("/query")
async def query_knowledge(request: QueryRequest):
    logger.info(f"收到知识查询: {request.question}")
    if not request.chat_history:
        request.chat_history= []

    logger.info(f"上下文内容查询: {request.chat_history}")

    # 实现查询
    try:
        # 提问
        # 检索器检索，屏蔽了向量数据库的api调用  chroma数据库检索
        # docs = retriever.invoke("参数量是多少")
        # 1. 查询重写：基于对话历史优化当前问题

        if request.chat_history:
            rewritten_question = rewrite_query_with_history(request.question, request.chat_history)
        else:
            rewritten_question = request.question  # 直接使用原问题
        # 2. 使用重写后的问题进行检索
        docs = retriever.invoke(rewritten_question)


        context = "\n".join([doc.page_content for doc in docs])

        system_prompt = """
        您是问答任务的助理。使用以下的检索上下文和对话历史来回答问题。

        对话历史：
        {chat_history}
        检索到的上下文：
        {context}

        当前问题：{question}

        请根据以上信息回答问题。如果信息不足，请说明你不知道。
        """

        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{question}")
            ]
        )
        # 格式化对话历史
        formatted_history = format_chat_history(request.chat_history)
        # print(f"上下文历史：{formatted_history}")
        logger.info(f"开始执行链路")

        # 拼接上下文组装Chain
        rag_chain = (
                        {
                            "question": RunnablePassthrough(),
                            "context": RunnableLambda(lambda x: context),
                            "chat_history": RunnableLambda(lambda x: formatted_history)
                        }
                        | prompt_template | llm | StrOutputParser()
                    )

        logger.info(f"结束执行链路")
        # result = rag_chain.invoke(request.question)
        # 创建源数据（在流式输出前准备好）
        source_data = [{"query": doc.page_content} for doc in docs]

        # 定义流式生成器
        async def generate():
            result = ""
            for chunk in rag_chain.stream(request.question):
                result += chunk
                # 实时推送每个 chunk 给前端
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

            # 发送完成信号和源数据
            yield f"data: {json.dumps({'done': True, 'source_data': source_data}, ensure_ascii=False)}\n\n"

        # 返回 SSE 流
        return StreamingResponse(generate(), media_type="text/event-stream")

        # print("--"*20)
        #
        # logger.info(f"执行链路返回的结果：{result}")
        # #  把结果返回给前端
        # answer = result
        # source_data = []
        # #res -- 返回的数据
        # for doc in docs:
        #     source_data.append({"query":doc.page_content})
        #
        # logger.info(f'返回的数据：{source_data}')
        # return {
        #     "answer": answer,
        #     "source_data": source_data
        # }
    except Exception as e:
        logger.error(f"知识查询失败: {str(e)}")

        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)