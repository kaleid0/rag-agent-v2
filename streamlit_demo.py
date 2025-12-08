"""
简单的前端示例 - 使用 Streamlit 构建聊天界面

运行: streamlit run streamlit_demo.py
"""

import json
import time
import streamlit as st
import requests
from typing import Optional

# API 配置
API_BASE_URL = "http://127.0.0.1:8000"

# 初始化 session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "streamlit_user"
if "current_page" not in st.session_state:
    st.session_state.current_page = "chat"  # chat, kb_manage, session_manage


def create_session(user_id: str) -> Optional[str]:
    """创建新会话"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/sessions", json={"user_id": user_id}
        )
        response.raise_for_status()
        return response.json()["session_id"]
    except Exception as e:
        st.error(f"创建会话失败: {e}")
        return None


def delete_session_if_blank(session_id: str) -> None:
    """如果会话为空，则删除之"""
    try:
        requests.post(f"{API_BASE_URL}/api/v1/sessions/{session_id}/exit")
    except Exception:
        pass


def send_message(
    session_id: str, content: str, kb_id: Optional[str] = None
) -> Optional[dict]:
    """发送消息"""
    try:
        payload = {"session_id": session_id, "content": content}
        if kb_id:
            payload["knowledge_base_id"] = kb_id

        response = requests.post(f"{API_BASE_URL}/api/v1/chat", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"发送消息失败: {e}")
        return None


def send_message_stream(session_id: str, content: str, kb_id: Optional[str] = None):
    """使用流式接口发送消息并返回流响应的迭代器"""
    try:
        payload = {"session_id": session_id, "content": content}
        if kb_id:
            payload["knowledge_base_id"] = kb_id

        # 使用 stream=True 来逐步读取响应
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/chat-stream", json=payload, stream=True
        )
        resp.raise_for_status()
        # 逐行/逐块迭代文本流
        for chunk in resp.iter_content(chunk_size=None):
            if chunk:
                yield chunk.decode("utf-8")
    except Exception as e:
        yield f"[ERROR]{e}"


def main():
    st.set_page_config(page_title="RAG Chatbot", page_icon="🔷", layout="wide")

    # 侧边栏 - 页面导航
    with st.sidebar:
        st.title("🔷 RAG Chatbot")
        # st.divider()

        # 页面导航按钮
        if st.button(
            "💬 聊天",
            use_container_width=True,
            type="primary" if st.session_state.current_page == "chat" else "secondary",
        ):
            st.session_state.current_page = "chat"
            st.rerun()

        if st.button(
            "📋 会话管理",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.current_page == "session_manage"
                else "secondary"
            ),
        ):
            st.session_state.current_page = "session_manage"
            st.rerun()

        if st.button(
            "📚 知识库管理",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.current_page == "kb_manage"
                else "secondary"
            ),
        ):
            st.session_state.current_page = "kb_manage"
            st.rerun()

        if st.button(
            "📄 文档管理",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.current_page == "document_manage"
                else "secondary"
            ),
        ):
            st.session_state.current_page = "document_manage"
            st.rerun()

        st.divider()

    # 根据当前页面显示不同内容
    if st.session_state.current_page == "chat":
        render_chat_page()
    elif st.session_state.current_page == "kb_manage":
        render_knowledge_base_manage_page()
    elif st.session_state.current_page == "session_manage":
        render_session_manage_page()
    elif st.session_state.current_page == "document_manage":
        render_document_manage_page()


def render_chat_page():
    """渲染聊天页面"""
    # 侧边栏 - 会话相关控制
    with st.sidebar:

        # 知识库控制
        st.subheader("知识库控制")

        # 获取知识库列表
        try:
            kb_response = requests.get(f"{API_BASE_URL}/api/v1/knowledge-bases").json()
            kb_list = kb_response.get("knowledge_base_list", [])
        except Exception as e:
            st.error(f"获取知识库列表失败: {e}")
            kb_list = []
        # 选择知识库
        selectable_dkbs = [kb.get("name", "未命名知识库") for kb in kb_list]
        selectable_dkbs.insert(0, "不使用知识库")
        st.selectbox(
            label="知识库",
            options=selectable_dkbs,  # TODO: 填充知识库列表
            key="kb_selector",
            help="选择要使用的知识库",
            width=200,
        )
        st.divider()

        # 会话列表
        st.subheader("会话列表")

        # 创建新会话按钮
        if st.button("➕ 创建新会话", type="tertiary", use_container_width=True):
            # 如果当前有 session_id，尝试退出（若为空会话则后端会删除）
            if st.session_state.session_id:
                delete_session_if_blank(st.session_state.session_id)

            session_id = create_session(st.session_state.user_id)  # type: ignore
            if session_id:
                st.session_state.session_id = session_id
                st.session_state.messages = []
                st.rerun()

        try:
            session_list = requests.get(
                f"{API_BASE_URL}/api/v1/session-list",
                params={"user_id": st.session_state.user_id},
            ).json()

            if not session_list:
                st.info("暂无会话")
            else:
                for sess in session_list:
                    sess_id = sess["session_id"]
                    title = (
                        sess.get("metadata", {}).get("title", None)
                        or f"{sess_id[:15]}..."
                    )
                    is_current = st.session_state.session_id == sess_id

                    btn_type = "primary" if is_current else "secondary"
                    if st.button(
                        f"{'📌 ' if is_current else ''}{title}",
                        key=f"chat_sess_btn_{sess_id}",
                        use_container_width=True,
                        type=btn_type,
                    ):
                        # 在切换前，尝试退出当前会话（若为空会话则后端会删除）
                        if (
                            st.session_state.session_id
                            and st.session_state.session_id != sess_id
                        ):
                            delete_session_if_blank(st.session_state.session_id)

                        st.session_state.session_id = sess_id
                        history = requests.get(
                            f"{API_BASE_URL}/api/v1/sessions/{sess_id}"
                        ).json()
                        st.session_state.messages = [
                            {
                                "role": (
                                    "user" if msg["role"] == "user" else "assistant"
                                ),
                                "content": msg["content"],
                            }
                            for msg in history["messages"]
                        ]
                        st.rerun()
        except Exception as e:
            st.error(f"获取会话列表失败: {e}")

    # 主聊天界面
    # st.title("💬 聊天")

    if not st.session_state.session_id:
        st.info("⬅️ 请先在侧边栏创建会话")
        return

    # 显示聊天历史
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 用户输入
    if prompt := st.chat_input("输入消息..."):
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 获取助手回复（流式）
        with st.chat_message("assistant"):
            # 知识库
            selected_kb_name = st.session_state[f"kb_selector"]
            if selected_kb_name == "不使用知识库":
                selected_id = None
            else:
                for kn in kb_list:
                    if kn.get("name", "未命名知识库") == selected_kb_name:
                        selected_id = kn.get("id", None)
                        break

            placeholder = st.empty()
            full_text = ""

            # 显示思考中动画
            with placeholder.container():
                with st.spinner("思考中..."):
                    # 获取第一个数据块
                    stream_generator = send_message_stream(
                        st.session_state.session_id, prompt, selected_id
                    )
                    first_chunk = next(stream_generator, None)

            # 检查是否有未闭合的公式标记
            def has_unclosed_formula(text):
                """检查文本是否包含未闭合的 LaTeX 公式"""
                # 检查单$符号（排除$$）
                temp = text.replace("$$", "")
                single_dollar_count = temp.count("$")
                # 检查双$$符号
                double_dollar_count = text.count("$$")
                return (single_dollar_count % 2 != 0) or (double_dollar_count % 2 != 0)

            # 处理响应
            if first_chunk:
                if first_chunk.startswith("[ERROR]"):
                    placeholder.error(first_chunk.replace("[ERROR]", ""))
                else:
                    full_text = first_chunk
                    buffer = ""  # 缓冲区用于处理不完整的公式

                    # 显示初始内容
                    if not has_unclosed_formula(full_text):
                        placeholder.markdown(full_text)
                    else:
                        buffer = full_text

                    # 继续处理剩余的流数据
                    for chunk in stream_generator:
                        if chunk.startswith("[ERROR]"):
                            placeholder.error(chunk.replace("[ERROR]", ""))
                            break

                        full_text += chunk

                        # 如果有缓冲内容，先累积
                        if buffer:
                            buffer += chunk
                            # 检查缓冲区是否包含完整公式
                            if not has_unclosed_formula(buffer):
                                placeholder.markdown(full_text)
                                buffer = ""
                        else:
                            # 检查是否导致公式不完整
                            if not has_unclosed_formula(full_text):
                                placeholder.markdown(full_text)
                            else:
                                buffer = chunk

                    # 确保最后显示完整内容
                    if full_text:
                        placeholder.markdown(full_text)

            if full_text:
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_text}
                )


def render_knowledge_base_manage_page():
    """渲染知识库管理页面"""

    st.title("📚 知识库管理")

    # 知识库列表 =======================================================================================
    st.header("知识库列表")
    try:
        kb_response = requests.get(f"{API_BASE_URL}/api/v1/knowledge-bases").json()
        document_list = (
            requests.get(f"{API_BASE_URL}/api/v1/document").json().get("documents", [])
        )
    except Exception as e:
        st.error(f"获取知识库列表失败: {e}")
        kb_list = []

    kb_list = kb_response.get("knowledge_base_list", [])
    document_list = [
        doc for doc in document_list if doc.get("metadata", {}).get("is_prased", False)
    ]
    id_to_title = {
        doc["id"]: doc.get("metadata", {}).get("title", "无标题")
        for doc in document_list
    }

    if not kb_list:
        st.info("未找到知识库")
    else:
        for kb in kb_list:
            kb_id = kb["id"]
            kb_name = kb["name"]

            with st.expander(f"📖 {kb_name}", expanded=False):
                st.write(f"**描述:** {kb.get('description', '无')}")

                st.markdown("**包含文档:**")
                record_titles = kb.get("document_titles", [])
                if record_titles:
                    for title in record_titles:
                        st.write(f"- {title}")

                with st.form(key=f"form_{kb_id}"):
                    selectable_doc_ids = [
                        doc["id"]
                        for doc in document_list
                        if doc["id"] not in kb.get("document_ids", [])
                    ]
                    st.multiselect(
                        "添加文档",
                        options=selectable_doc_ids,
                        format_func=lambda x: id_to_title.get(x, "无标题"),
                        key=f"doc_selector_{kb_id}",
                    )
                    submitted = st.form_submit_button("提交", use_container_width=True)

                if submitted:
                    selected_ids = st.session_state[f"doc_selector_{kb_id}"]

                    # 发送请求
                    resp = requests.post(
                        f"{API_BASE_URL}/api/v1/knowledge-bases/{kb_id}/files",
                        data=json.dumps(selected_ids),  # 转成 JSON 数组
                        headers={"Content-Type": "application/json"},  # 指定 JSON
                    )
                    if resp.status_code == 200:
                        st.success("已添加选中文档到知识库")
                    else:
                        st.error(f"添加文档失败: {resp.text}")

                if st.button("删除", key=f"del_kb_{kb_id}", type="primary"):
                    try:
                        resp = requests.delete(
                            f"{API_BASE_URL}/api/v1/knowledge-bases/{kb_id}"
                        )
                        resp.raise_for_status()
                        st.success(f"已删除 {kb_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")

    st.divider()

    # 新建知识库 ======================================================================================
    st.header("新建知识库")
    with st.form(key="create_kb_form"):
        new_kb_name = st.text_input("知识库名称", value="")
        new_kb_desc = st.text_area("描述 (可选)", value="")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            new_kb_chunk_size = st.number_input(
                "分块大小", min_value=100, max_value=1000, value=300, step=50
            )
        with c2:
            new_kb_chunk_overlap = st.number_input(
                "分块重叠大小", min_value=0, max_value=300, value=50, step=10
            )
        with c3:
            new_kb_split_method = st.selectbox(
                "分块方法",
                options=["hierarchical", "recursive"],
                format_func=lambda s: s.capitalize(),
                index=0,
            )
        with c4:
            new_kb_retriever_type = st.selectbox(
                "检索器类型",
                options=["hybrid", "vector", "sparse"],
                format_func=lambda s: s.capitalize(),
                index=0,
            )
        create_kb_btn = st.form_submit_button("创建知识库", type="primary")

    if create_kb_btn:
        if not new_kb_name:
            st.error("请输入知识库名称")
        else:
            try:
                # TODO 选择文档
                payload = {
                    "name": new_kb_name,
                    "description": new_kb_desc,
                    "chunk_size": new_kb_chunk_size,
                    "chunk_overlap": new_kb_chunk_overlap,
                    "split_method": new_kb_split_method,
                    "retriever_type": new_kb_retriever_type,
                    "document_ids": [],  # 目前不支持直接选择文档创建知识库
                }
                resp = requests.post(
                    f"{API_BASE_URL}/api/v1/knowledge-bases", json=payload
                )
                resp.raise_for_status()
                created = resp.json()
                st.success(
                    f"创建成功: {created.get('id') or created.get('knowledge_base_id') or created.get('_id','')}"
                )
                st.rerun()
            except Exception as e:
                st.error(f"创建失败: {e}")

    st.divider()


def render_session_manage_page():
    """渲染会话管理页面"""
    st.title("📋 会话管理")

    user_id = st.session_state.user_id
    st.write(f"**当前用户:** {user_id}")

    st.divider()

    # 获取会话列表
    try:
        session_list = requests.get(
            f"{API_BASE_URL}/api/v1/session-list",
            params={"user_id": user_id},
        ).json()
    except Exception as e:
        st.error(f"获取会话列表失败: {e}")
        session_list = []

    st.header(f"会话列表 ({len(session_list)})")

    if not session_list:
        st.info("暂无会话")
    else:
        for sess in session_list:
            sess_id = sess["session_id"]
            title = (
                sess.get("metadata", {}).get("title", None) or f"会话 {sess_id[:8]}..."
            )
            is_current = st.session_state.session_id == sess_id

            with st.expander(
                f"{'📌 ' if is_current else '💬 '}{title}", expanded=False
            ):
                st.write(f"**会话ID:** `{sess_id}`")
                st.write(f"**创建时间:** {sess.get('created_at', '未知')}")
                st.write(f"**更新时间:** {sess.get('updated_at', '未知')}")

                cols = st.columns([1, 1, 1])

                # 查看会话
                if cols[0].button("查看消息", key=f"view_sess_{sess_id}"):
                    try:
                        history = requests.get(
                            f"{API_BASE_URL}/api/v1/sessions/{sess_id}"
                        ).json()

                        st.subheader("会话消息:")
                        for idx, msg in enumerate(history.get("messages", [])):
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")
                            st.text(f"[{idx+1}] [{role.upper()}] {content[:100]}...")
                    except Exception as e:
                        st.error(f"查看失败: {e}")

                # 切换到该会话
                if cols[1].button("切换聊天", key=f"switch_sess_{sess_id}"):
                    if st.session_state.session_id != sess_id:
                        if st.session_state.session_id:
                            delete_session_if_blank(st.session_state.session_id)

                        st.session_state.session_id = sess_id
                        try:
                            history = requests.get(
                                f"{API_BASE_URL}/api/v1/sessions/{sess_id}"
                            ).json()
                            st.session_state.messages = [
                                {
                                    "role": (
                                        "user" if msg["role"] == "user" else "assistant"
                                    ),
                                    "content": msg["content"],
                                }
                                for msg in history["messages"]
                            ]
                            st.session_state.current_page = "chat"
                            st.success(f"已切换到会话: {title}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"切换失败: {e}")
                    else:
                        st.session_state.current_page = "chat"
                        st.rerun()

                # 删除会话
                if cols[2].button(
                    "删除", key=f"delete_sess_{sess_id}", type="secondary"
                ):
                    try:
                        resp = requests.post(
                            f"{API_BASE_URL}/api/v1/sessions/{sess_id}/exit"
                        )
                        resp.raise_for_status()
                        st.success(f"已删除会话: {title}")
                        if st.session_state.session_id == sess_id:
                            st.session_state.session_id = None
                            st.session_state.messages = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")


def render_document_manage_page():
    """渲染文档管理页面"""
    st.title("📄 文档管理")

    # 获取文档列表
    try:
        doc_list = (
            requests.get(f"{API_BASE_URL}/api/v1/document").json().get("documents", [])
        )
    except Exception as e:
        st.error(f"获取文档列表失败: {e}")
        doc_list = []

    st.header(f"文档列表")

    # 文档列表
    if not doc_list:
        st.info("暂无文档")
    else:
        for doc in doc_list:
            doc_id = doc.get("id")
            metadata = doc.get("metadata", {})
            doc_title = metadata.get("title") or doc.get("source", "未命名文档")
            doc_summary = metadata.get("abstract", "无摘要")
            doc_keywords = metadata.get("keywords", [])

            with st.expander(f"📄 {doc_title}", expanded=False):
                if metadata.get("title"):
                    st.write(f"**摘要:** {doc_summary}")
                    st.write(f"**关键词:** {doc_keywords}")
                else:
                    st.spinner("解析中")

                if st.button("删除文档", key=f"del_doc_{doc_id}", type="secondary"):
                    try:
                        resp = requests.delete(
                            f"{API_BASE_URL}/api/v1/document/{doc_id}"
                        )
                        resp.raise_for_status()
                        st.success(f"已删除文档: {doc_title}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")

    st.divider()
    # 上传文档
    st.header("上传文档")
    with st.form(key="upload_doc_form"):
        # upload_kb_id = st.text_input("目标知识库 ID", value="")
        uploaded_file = st.file_uploader(
            "选择要上传的文档",
            type=["pdf", "txt", "md", "docx"],
            accept_multiple_files=False,
        )
        upload_btn = st.form_submit_button("上传文档", type="primary")

    if upload_btn:
        if not uploaded_file:
            st.error("请选择要上传的文档")
        else:
            try:
                file_bytes = uploaded_file.read()
                files = {"file": (uploaded_file.name, file_bytes)}
                resp = requests.post(
                    f"{API_BASE_URL}/api/v1/document/upload",
                    files=files,
                )
                resp.raise_for_status()
                st.success("上传成功")
            except Exception as e:
                st.error(f"上传失败: {e}")


if __name__ == "__main__":
    main()
