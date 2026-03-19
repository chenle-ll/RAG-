# RAG-
这是一个基于 FastAPI 的 RAG 知识问答系统后端，主要实现了智能知识助手的核心功能。核心流程是用户提问、查询重写、向量检索、构建上下文、LLM生成答案、返回结果。LangChain组织的链路顺序：数据输入 → prompt_template → llm → OutputParser

