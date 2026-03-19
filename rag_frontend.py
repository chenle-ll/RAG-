
# 运行代码： streamlit run ./rag/deepseek_rag/rag_frontend.py
import streamlit as st
import requests
import json
import time
from streamlit_option_menu import option_menu

# 页面设置
st.set_page_config(
    page_title="浏览器标题",
    page_icon="🏭",
    layout="wide"
)

# 后端API配置
BACKEND_URL = "http://127.0.0.1:8000"

# 初始化会话状态
if 'user_ctx' not in st.session_state:
    st.session_state.user_ctx = None
if 'chat_history' not in st.session_state:
    # streamlit中session_state 能够保持上下文内容
    st.session_state.chat_history = []
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "知识助手"
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

def knowledge_assistant():
    st.header("RAG小项目")

    # 聊天历史显示
    chat_container = st.container(height=600)
    with chat_container:
        for idx, msg in enumerate(st.session_state.chat_history):
            if msg["role"] == "user":
                with st.chat_message("user", avatar="🧑‍🔧"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    # 添加来源标识
                    source_type = "deepseek.pdf"
                    st.caption(f"来源: {source_type}")
                    # 大模型回复的答案
                    st.markdown(msg["content"])
                    # 更健壮的空值检查
                    if msg.get("source_data"):
                        with st.expander("查看来源数据"):
                                    for source in msg.get("source_data"):
                                        st.json(source)
                                        # 安全显示结果
                                        result = source
                                        if result:
                                            try:
                                                # 尝试解析为JSON
                                                result_data = json.loads(result)
                                                st.json(result_data)
                                            except:
                                                # 如果不是JSON，直接显示文本
                                                st.text(result)
                    else:
                        st.warning("无结果数据")

    # 用户输入
    user_input = st.chat_input("请输入您的问题...")

    if user_input:
        cleaned_input = user_input.strip()
        cleaned_input = cleaned_input.replace("'", "")

        # # 显示用户消息--立刻显示
        # with chat_container:
        #     with st.chat_message("user", avatar="🧑‍🔧"):
        #         st.markdown(user_input)

        # 调用后端API
        # with st.spinner("正在思考..."):
        #     try:
        #         response = requests.post(
        #             f"{BACKEND_URL}/query",
        #             json={
        #                 "question": cleaned_input,
        #                 "user_ctx": st.session_state.user_ctx,
        #                 "chat_history":st.session_state.chat_history
        #             }
        #         )
        #         # 添加用户消息到历史
        #         st.session_state.chat_history.append({"role": "user", "content": user_input})
        #         # 判断响应状态
        #         if response.status_code == 200:
        #             result = response.json()
        #             print(f"result:{result}")
        #
        #             # 添加助手回复到历史
        #             st.session_state.chat_history.append({
        #                 "role": "assistant",
        #                 "content": result["answer"],
        #                 "source_data": result.get("source_data", [])
        #             })
        #
        #             # 显示助手回复
        #             with chat_container:
        #                 with st.chat_message("assistant", avatar="🤖"):
        #                     st.markdown(result["answer"])
        #                     # if "source_data" in result:
        #                     #     with st.expander("查看来源数据"):
        #                     #         for source in result["source_data"]:
        #                     #             st.json(source)
        #         else:
        #             # st.error(f"请求失败: {response.text}")
        #             # 更健壮的错误处理
        #             try:
        #                 error_detail = response.json().get('detail', response.text)
        #             except:
        #                 error_detail = response.text[:500]  # 限制长度防止显示问题
        #
        #             # 更友好的错误提示
        #             error_msg = f"请求失败: {error_detail}"
        #             st.error(error_msg)
        #
        #             # 添加到聊天历史
        #             st.session_state.chat_history.append({
        #                 "role": "assistant",
        #                 "content": f"抱歉，处理您的请求时出错: {error_msg}"
        #             })
        #     except Exception as e:
        #         st.error(f"发生错误: {str(e)}")
        #         st.session_state.chat_history.append({
        #             "role": "assistant",
        #             "content": f"抱歉，处理您的请求时出错: {str(e)}"
        #         })
        with st.spinner("正在思考..."):
            try:
                # 先显示用户消息
                with chat_container:
                    with st.chat_message("user", avatar="🧑‍🔧"):
                        st.markdown(user_input)

                # 添加用户消息到历史
                st.session_state.chat_history.append({"role": "user", "content": user_input})

                # 准备助手回复的占位符
                with chat_container:
                    with st.chat_message("assistant", avatar="🤖"):
                        message_placeholder = st.empty()
                        message_placeholder.markdown("正在思考...")
                        source_type = "xxx用户上传的文档.pdf"
                        st.caption(f"来源：{source_type}")

                # 使用 EventSource 接收流式数据
                import time

                response_content = ""
                source_data = []

                # 调用后端流式 API
                import requests
                import json
                from requests.exceptions import ChunkedEncodingError

                try:
                    response = requests.post(
                        f"{BACKEND_URL}/query",
                        json={
                            "question": cleaned_input,
                            "user_ctx": st.session_state.user_ctx,
                            "chat_history": st.session_state.chat_history
                        },
                        stream=True  # 启用流式传输
                    )

                    if response.status_code == 200:
                        # 逐行读取 SSE 数据
                        for line in response.iter_lines():
                            if line:
                                line = line.decode('utf-8')
                                if line.startswith('data: '):
                                    data_str = line[6:]  # 去掉 'data: ' 前缀
                                    data = json.loads(data_str)

                                    # 处理数据块
                                    if 'chunk' in data:
                                        response_content += data['chunk']
                                        # 实时更新显示
                                        message_placeholder.markdown(response_content + "▌")
                                        time.sleep(0.05)  # 打字机效果

                                    # 处理完成信号
                                    if data.get('done'):
                                        source_data = data.get('source_data', [])
                                        message_placeholder.markdown(response_content)
                                        break
                    else:
                        error_detail = response.text[:500]
                        message_placeholder.markdown(f"请求失败：{error_detail}")
                        response_content = f"抱歉，处理您的请求时出错：{error_detail}"

                except Exception as e:
                    message_placeholder.markdown(f"发生错误：{str(e)}")
                    response_content = f"抱歉，处理您的请求时出错：{str(e)}"

                # 添加助手回复到历史
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response_content,
                    "source_data": source_data
                })

                # 显示来源数据
                if source_data:
                    with st.expander("查看来源数据"):
                        for source in source_data:
                            st.json(source)

            except Exception as e:
                st.error(f"发生错误：{str(e)}")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"抱歉，处理您的请求时出错：{str(e)}"
                })

def login_page():
    st.title("智能知识助手-Rag小项目")
    st.write("此项目仅为个人RAG的整个工作流程")

    with st.form("login_form"):

        role = st.selectbox("角色", ["工程人员", "运维人员", "专家"], index=1)
        username = st.text_input("用户名", value="CHENLE")
        password = st.text_input("密码", type="password", value="666666")

        submitted = st.form_submit_button("登录")
        if submitted:
            if username and password:
                st.session_state.user_ctx = {
                    "role": role,
                    "username": username
                }
                st.session_state.chat_history = []
                st.session_state.is_logged_in = True
                st.success("登录成功！正在跳转主界面...")
                time.sleep(1)
                st.rerun() # 重新加载页面，进入主页面
            else:
                st.error("用户名和密码不能为空")

def main_page():

    # 租户信息显示
    st.sidebar.subheader(f"当前用户")
    st.sidebar.markdown(f"**用户**: {st.session_state.user_ctx['username']}")
    st.sidebar.markdown(f"**角色**: {st.session_state.user_ctx['role']}")

    st.sidebar.divider()
    st.sidebar.markdown("### 快捷操作")
    if st.sidebar.button("清除聊天记录"):
        st.session_state.chat_history = []
        st.rerun()
    # 新增：退出按钮
    st.sidebar.divider()
    if st.sidebar.button("退出登录", key="logout_button"):
        # 清除登录状态和用户上下文
        st.session_state.is_logged_in = False
        st.session_state.user_ctx = None
        st.session_state.chat_history = []
        st.session_state.selected_tab = "知识助手"
        st.rerun()  # 重新运行，返回登录页面
    # # 功能区域
    if st.session_state.selected_tab == "知识助手":
        knowledge_assistant()

# 应用路由
if st.session_state.get('is_logged_in', False) and st.session_state.user_ctx:
    main_page()
else:
    login_page()