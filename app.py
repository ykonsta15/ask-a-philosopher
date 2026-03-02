import streamlit as st

from llm import generate_philosophers_with_meta
from utils import sanitize_input

st.set_page_config(page_title="Ask a Philosopher", layout="wide")

DEFAULT_STATE = {
    "results": None,
    "error": None,
    "debug_info": None,
    "question_input": "",
    "clear_question_input": False,
}
for key, default_value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


def _reset_state() -> None:
    st.session_state["results"] = None
    st.session_state["error"] = None
    st.session_state["debug_info"] = None
    st.session_state["clear_question_input"] = True


left, center, right = st.columns([1, 2, 1])

with center:
    if st.session_state["clear_question_input"]:
        st.session_state["question_input"] = ""
        st.session_state["clear_question_input"] = False

    st.title("Ask a Philosopher")
    st.caption("Hear from Socrates, Plato, and Aristotle.")

    st.text_area(
        "Your question",
        key="question_input",
        height=140,
        placeholder="e.g., What makes a good life?",
        label_visibility="visible",
    )
    st.caption("Ask anything — practical, ethical, or weird.")

    controls = st.columns([1, 1, 4])
    with controls[0]:
        generate_clicked = st.button(
            "Generate",
            type="primary",
            use_container_width=True,
        )
    with controls[1]:
        reset_clicked = st.button("Reset", use_container_width=True)

    if reset_clicked:
        _reset_state()
        st.rerun()

    if generate_clicked:
        cleaned = sanitize_input(st.session_state["question_input"])
        st.session_state["results"] = None
        st.session_state["error"] = None
        st.session_state["debug_info"] = None

        with st.spinner("Generating responses..."):
            try:
                results, meta = generate_philosophers_with_meta(cleaned)
                st.session_state["results"] = results
                st.session_state["debug_info"] = meta
            except Exception as exc:
                detail = str(exc).strip() or exc.__class__.__name__
                st.session_state["error"] = f"Could not generate answer right now. {detail}"

    if st.session_state["error"]:
        st.error(st.session_state["error"])

    if st.session_state["results"]:
        results = st.session_state["results"]
        tabs = st.tabs(["Socrates", "Plato", "Aristotle"])

        with tabs[0]:
            st.write(results["socrates"])
        with tabs[1]:
            st.write(results["plato"])
        with tabs[2]:
            st.write(results["aristotle"])

    st.markdown(
        "<div style='margin-top:2rem;color:#6b7280;font-size:0.86rem;'>"
        "Philosophical perspectives — not professional advice."
        "</div>",
        unsafe_allow_html=True,
    )
