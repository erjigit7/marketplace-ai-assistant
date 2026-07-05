import os
import time

import requests
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://web:8000")

st.set_page_config(page_title="Marketplace AI Assistant", page_icon="🛒")


def login(username, password):
    response = requests.post(f"{API_BASE}/api/auth/token", data={"username": username, "password": password})
    if response.status_code != 200:
        return None
    return response.json()["token"]


def poll_result(token, conversation_id, timeout=60):
    headers = {"Authorization": f"Token {token}"}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = requests.get(f"{API_BASE}/api/conversations/{conversation_id}/result/", headers=headers)
        body = response.json()
        if body["status"] == "SUCCESS":
            return body["result"]
        if body["status"] == "FAILURE":
            return {"answer": f"Ошибка: {body.get('error')}", "tool_calls": []}
        time.sleep(0.5)
    return {"answer": "Не дождались ответа (timeout).", "tool_calls": []}


if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.conversation_id = None
    st.session_state.messages = []

if not st.session_state.token:
    st.title("🛒 Marketplace AI Assistant")
    st.caption("Войдите, чтобы начать разговор с ассистентом")
    with st.form("login"):
        username = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button("Войти")
    if submitted:
        token = login(username, password)
        if token:
            st.session_state.token = token
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
    st.stop()

with st.sidebar:
    st.success("Вы вошли в систему")
    if st.button("Новый разговор"):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()
    if st.button("Выйти"):
        st.session_state.token = None
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("Агент сам выбирает инструмент: поиск по правилам WB/Ozon, калькулятор комиссии или генератор описания товара.")

st.title("🛒 Marketplace AI Assistant")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        for tool_call in message.get("tool_calls", []):
            st.caption(f"🔧 использован инструмент: `{tool_call['tool']}`")

user_message = st.chat_input("Спросите про правила WB/Ozon, комиссию или опишите товар...")

if user_message:
    st.session_state.messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.write(user_message)

    headers = {"Authorization": f"Token {st.session_state.token}"}
    payload = {"message": user_message}
    if st.session_state.conversation_id:
        payload["conversation_id"] = st.session_state.conversation_id

    with st.chat_message("assistant"):
        with st.spinner("Думаю..."):
            response = requests.post(f"{API_BASE}/api/agent/chat", json=payload, headers=headers)
            if response.status_code != 202:
                st.error(f"Ошибка: {response.text}")
                st.stop()
            data = response.json()
            st.session_state.conversation_id = data["conversation_id"]
            result = poll_result(st.session_state.token, data["conversation_id"])

        st.write(result["answer"])
        for tool_call in result.get("tool_calls", []):
            st.caption(f"🔧 использован инструмент: `{tool_call['tool']}`")

    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"], "tool_calls": result.get("tool_calls", [])}
    )
