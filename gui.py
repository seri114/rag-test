
from typing import Callable, Generator
from ai.gpt import completions
import streamlit as st

def gen_generator(user_prompt: str) -> Callable[[None], Generator[str, None, None]]:
    def chat_generator() -> Generator[str, None, None]:
        button_mode = False
        for t in completions(user_prompt):
            if t == "--------------------------":
                button_mode = True
                continue
            if not button_mode:
                yield t
            else:
                st.button(t, on_click=on_change, args=(t,))
        st.text_input("続いて質問", on_change=on_change_ui, key="user_prompt_next")
    return chat_generator

def on_change_ui():
    if "user_prompt_next" in st.session_state:
        prompt = st.session_state["user_prompt_next"]
        st.session_state["user_prompt_next"] = ""
        on_change(prompt)

def on_change(chat: str):

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.session_state.chat_history.append(
        {
            "name": "user",
            "message": chat,
            "stream": False
        }
    )
    st.session_state.chat_history.append(
        {
            "name": "assistant",
            "message": chat,
            "stream": True
        }
    )

def render_chat():
    if "chat_history" in st.session_state:
        chats = st.session_state.chat_history.copy()
        for chat in st.session_state.chat_history:
            with st.chat_message(chat["name"]):
                if chat["stream"] == True:
                    chat["stream"] = False
                    chat["message"] = st.write_stream(gen_generator(chat["message"]))
                else:
                    st.write(chat["message"])
        del st.session_state["chat_history"]
        st.session_state.chat_history = []
        for c in chats:
            st.session_state.chat_history.append(c)

def main():
    render_chat()
    if prompt := st.chat_input("新しい質問", key="user_prompt_"):
        st.session_state.chat_history = []
        on_change(prompt)
        st.rerun()


if __name__ == "__main__":
    main()

    