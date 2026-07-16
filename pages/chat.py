"""
师生聊天页面（教师端 + 学生端共用）
微信风格消息气泡 + 表情选择器 + 文件传输
支持文字、表情、图片、视频、文档、压缩包
"""

import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from db import (get_all_students, get_all_teachers, get_last_message_between,
                get_messages, send_message)

# ============================================================
# 上传文件存储目录
# ============================================================
UPLOAD_DIR = Path(__file__).parent.parent / "uploads" / "chat"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HTML 转义
# ============================================================
def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


# ============================================================
# 通用 emoji 列表
# ============================================================
EMOJI_SMILEYS = [
    "😀",
    "😃",
    "😄",
    "😁",
    "😆",
    "😅",
    "🤣",
    "😂",
    "😊",
    "😇",
    "🙂",
    "😉",
    "😌",
    "😍",
    "🥰",
    "😘",
    "😗",
    "😋",
    "😛",
    "😜",
    "🤪",
    "😝",
    "🤑",
    "🤗",
    "🤭",
    "🤫",
    "🤔",
    "🤐",
    "🤨",
    "😐",
    "😑",
    "😶",
    "😏",
    "😒",
    "🙄",
    "😬",
    "😮",
    "🤤",
    "😪",
    "😴",
    "🥱",
]
EMOJI_GESTURES = [
    "👍",
    "👎",
    "👏",
    "🙌",
    "🤝",
    "💪",
    "✍️",
    "🙏",
    "💃",
    "👋",
    "🤙",
    "👌",
    "🤌",
    "✌️",
    "🤞",
    "🤟",
    "👆",
    "👇",
    "☝️",
    "👉",
    "👈",
    "✋",
    "🤚",
    "🖐️",
    "💅",
]
EMOJI_HEARTS = [
    "❤️",
    "🧡",
    "💛",
    "💚",
    "💙",
    "💜",
    "🖤",
    "🤍",
    "🤎",
    "💔",
    "❣️",
    "💕",
    "💞",
    "💓",
    "💗",
    "💖",
    "💘",
    "💝",
    "💟",
    "♥️",
]
EMOJI_OBJECTS = [
    "📚",
    "📝",
    "✏️",
    "💡",
    "⭐",
    "🔥",
    "🎯",
    "🏆",
    "✅",
    "❌",
    "💯",
    "📌",
    "📎",
    "🔗",
    "🎓",
    "💻",
    "📱",
    "⏰",
    "📅",
    "🗂️",
    "📊",
    "📈",
    "🎉",
    "🎊",
    "🔔",
]
ALL_EMOJIS = EMOJI_SMILEYS + EMOJI_GESTURES + EMOJI_HEARTS + EMOJI_OBJECTS


# ============================================================
# 聊天页面主体
# ============================================================
def page_chat(is_teacher: bool):
    """聊天页面：联系人列表 + 消息区域 + 输入框 + 文件上传"""
    my_id = st.session_state.user_id
    my_name = st.session_state.username

    # 加载联系人列表
    if is_teacher:
        contacts = get_all_students()
        contact_label = "学生"
    else:
        contacts = get_all_teachers()
        contact_label = "教师"

    if not contacts:
        st.info(f"暂无{contact_label}注册")
        return

    # 初始化当前聊天对象
    if "chat_with_id" not in st.session_state or st.session_state.chat_with_id is None:
        st.session_state.chat_with_id = contacts[0]["id"]
        st.session_state.chat_with_name = contacts[0]["username"]

    partner_id = st.session_state.chat_with_id
    partner_name = st.session_state.chat_with_name

    # ============================================================
    # 布局：左联系人列表 + 右聊天区域
    # ============================================================
    col_contacts, col_chat = st.columns([1, 3])

    # --- 左侧：联系人列表 ---
    with col_contacts:
        st.markdown("#### 联系人")
        st.caption(f"共 {len(contacts)} 位{contact_label}")

        for contact in contacts:
            cid = contact["id"]
            cname = contact["username"]
            is_active = cid == partner_id

            last_msg = get_last_message_between(my_id, cid)
            preview = ""
            if last_msg:
                content = last_msg["content"] or "[文件]"
                preview = content[:25] + "..." if len(content) > 25 else content
                if last_msg.get("file_name"):
                    preview = f"[{last_msg.get('file_name', '文件')[:20]}]"

            with st.container():
                cols = st.columns([1, 4])
                with cols[0]:
                    avatar_char = (cname or "?")[0].upper()
                    st.markdown(
                        f"""<div style="width:36px;height:36px;border-radius:4px;
                        background:#07C160;color:white;text-align:center;line-height:36px;
                        font-size:16px;font-weight:bold;">{avatar_char}</div>""",
                        unsafe_allow_html=True,
                    )
                with cols[1]:
                    st.markdown(f"**{cname}**")
                    if preview:
                        st.caption(preview)

                def make_on_select(cid=cid, cname=cname):
                    def _select():
                        st.session_state.chat_with_id = cid
                        st.session_state.chat_with_name = cname
                        st.session_state.chat_refresh_key += 1

                    return _select

                st.button(
                    "选择",
                    key=f"contact_{cid}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                    on_click=make_on_select(),
                )

                st.markdown("---")

    # --- 右侧：聊天区域 ---
    with col_chat:
        st.markdown(f"#### {partner_name}")
        st.caption("在线")

        # --- 定义回调函数 ---
        def on_send_message():
            msg = st.session_state.get("chat_input_text", "")
            if msg.strip():
                send_message(my_id, partner_id, content=msg.strip())
                st.session_state.chat_input_text = ""
                st.session_state.chat_refresh_key += 1

        def on_emoji_click(emoji_char: str):
            current = st.session_state.get("chat_input_text", "")
            st.session_state.chat_input_text = current + emoji_char

        # --- 消息显示区域（使用 fragment 自动刷新） ---
        @st.fragment(run_every=2)
        def render_messages():
            messages = get_messages(my_id, partner_id, limit=200)
            if messages:
                for msg in messages:
                    is_me = msg["sender_id"] == my_id
                    sender_char = (
                        (my_name or "我")[0] if is_me else (partner_name or "?")[0]
                    ).upper()
                    sender_display = "我" if is_me else partner_name
                    time_str = msg["created_at"] if msg["created_at"] else ""
                    if len(time_str) > 16:
                        time_str = time_str[5:16]

                    content = _html_escape(msg["content"] or "")

                    if is_me:
                        bubble_html = f"""<div style="display:flex;justify-content:flex-end;align-items:flex-start;margin:8px 0;gap:8px;"><div style="max-width:70%;"><div style="text-align:right;font-size:11px;color:#999;margin-bottom:2px;">{sender_display} {time_str}</div><div style="background:#95EC69;color:#000;padding:10px 14px;border-radius:8px 2px 8px 8px;font-size:14px;line-height:1.5;word-break:break-word;white-space:pre-wrap;">{content}</div></div><div style="width:32px;height:32px;border-radius:4px;background:#07C160;color:white;text-align:center;line-height:32px;font-size:13px;font-weight:bold;flex-shrink:0;">{sender_char}</div></div>"""
                    else:
                        bubble_html = f"""<div style="display:flex;justify-content:flex-start;align-items:flex-start;margin:8px 0;gap:8px;"><div style="width:32px;height:32px;border-radius:4px;background:#576B95;color:white;text-align:center;line-height:32px;font-size:13px;font-weight:bold;flex-shrink:0;">{sender_char}</div><div style="max-width:70%;"><div style="text-align:left;font-size:11px;color:#999;margin-bottom:2px;">{sender_display} {time_str}</div><div style="background:#FFFFFF;color:#000;padding:10px 14px;border-radius:2px 8px 8px 8px;font-size:14px;line-height:1.5;word-break:break-word;white-space:pre-wrap;border:1px solid #E4E4E4;">{content}</div></div></div>"""
                    st.markdown(bubble_html, unsafe_allow_html=True)

                    if msg["file_path"] and os.path.exists(msg["file_path"]):
                        ft = msg.get("file_type", "")
                        if ft == "image":
                            try:
                                st.image(msg["file_path"], width=240)
                            except Exception:
                                st.caption(f"[图片: {msg.get('file_name', '')}]")
                        elif ft == "video":
                            try:
                                st.video(msg["file_path"])
                            except Exception:
                                st.caption(f"[视频: {msg.get('file_name', '')}]")
                        else:
                            st.caption(f"[文件] {msg.get('file_name', '')}")
            else:
                st.info("暂无消息，开始聊天吧！")

        render_messages()

        # --- emoji 选择器 ---
        emoji_expander = st.expander("表情", expanded=False)
        with emoji_expander:
            emoji_tabs = st.tabs(["笑脸", "手势", "爱心", "物品"])
            emoji_sets_data = [EMOJI_SMILEYS, EMOJI_GESTURES, EMOJI_HEARTS, EMOJI_OBJECTS]
            for tab, emojis in zip(emoji_tabs, emoji_sets_data):
                with tab:
                    cols = st.columns(10)
                    for i, emoji in enumerate(emojis):
                        cols[i % 10].button(
                            emoji,
                            key=f"emoji_{emoji}_{st.session_state.chat_refresh_key}",
                            on_click=on_emoji_click,
                            args=(emoji,),
                        )

        # --- 输入区域 ---
        col_text, col_send = st.columns([9, 1])
        with col_text:
            msg_text = st.text_area(
                "消息",
                key="chat_input_text",
                placeholder="输入消息...",
                label_visibility="collapsed",
                height=68,
            )
        with col_send:
            st.write("")
            st.write("")
            st.button("发送", type="primary", use_container_width=True, on_click=on_send_message)

        # --- 文件上传 ---
        file_col1, file_col2 = st.columns([1, 3])
        with file_col1:
            uploaded_chat_file = st.file_uploader(
                "发送文件/图片/视频",
                type=[
                    "png",
                    "jpg",
                    "jpeg",
                    "gif",
                    "webp",
                    "mp4",
                    "mov",
                    "avi",
                    "pdf",
                    "docx",
                    "txt",
                    "zip",
                    "rar",
                    "pptx",
                ],
                key=f"chat_file_{st.session_state.chat_refresh_key}",
                label_visibility="collapsed",
            )

        # --- 发送文件 ---
        if uploaded_chat_file is not None:
            file_ext = Path(uploaded_chat_file.name).suffix.lower()
            if file_ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
                file_type = "image"
            elif file_ext in [".mp4", ".mov", ".avi"]:
                file_type = "video"
            else:
                file_type = "file"

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            saved_name = f"{timestamp}_{uploaded_chat_file.name}"
            saved_path = UPLOAD_DIR / saved_name
            with open(saved_path, "wb") as f:
                f.write(uploaded_chat_file.getbuffer())

            send_message(
                my_id,
                partner_id,
                content=f"[{file_type}: {uploaded_chat_file.name}]",
                file_path=str(saved_path),
                file_name=uploaded_chat_file.name,
                file_type=file_type,
            )
            st.session_state.chat_refresh_key += 1
            st.rerun()
