import streamlit as st
import requests
import PyPDF2
import re

st.title("Multi-PDF Abbreviation Index Generator")

try:
    API_KEY = st.secrets["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"]
except KeyError:
    st.error("GROQ_API_KEY not found in Streamlit secrets. Please add it.")
    st.stop()


uploaded_files = st.file_uploader(
    "Upload PDFs", type=["pdf"], accept_multiple_files=True
)


def extract_text(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_abbreviation_context(text):
    pattern = r'(.{0,50}\b[A-Z]{2,10}(?:&[A-Z]{1,10})?\b.{0,50})'
    matches = re.findall(pattern, text)
    return "\n".join(matches)


def call_llm(prompt):
    try:
       response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "llama-3.2-chat",  # <- updated model
        "messages": [{"role": "user", "content": prompt}]
    }
)
            timeout=60  # seconds
        )
        data = response.json()
    except Exception as e:
        st.error(f"Error contacting Groq API: {e}")
        return ""

    if "error" in data:
        st.error(f"API error: {data['error']}")
        return ""
    if "choices" not in data or not data["choices"]:
        st.error(f"No output from API. Full response: {data}")
        return ""

    return data["choices"][0]["message"]["content"]


def parse_abbreviations(text):
    abbr_dict = {}
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("•"):
            parts = line[1:].split(":", 1)
            if len(parts) == 2:
                abbr = parts[0].strip()
                definition = parts[1].strip()
                # Keep longest definition
                if abbr in abbr_dict:
                    if len(definition) > len(abbr_dict[abbr]):
                        abbr_dict[abbr] = definition
                else:
                    abbr_dict[abbr] = definition
    return abbr_dict


if st.button("Generate Merged Abbreviation Index"):
    if not uploaded_files:
        st.error("Please upload at least one PDF.")
    else:
        merged_abbreviations = {}

        for file in uploaded_files:
            text = extract_text(file)
            snippets = extract_abbreviation_context(text)
            if snippets.strip():
                prompt = f"""
ONLY extract abbreviations from the text snippets below. DO NOT summarize or comment.
Output exactly in this format:

• ABBR: full definition
• XYZ: full definition

RULES:
1. Only include abbreviations of 2–10 capital letters (A-Z), optionally with &.
2. Use the definition provided in parentheses or immediately in the snippet.
3. List each abbreviation only once.
4. If no abbreviations exist, return exactly: No abbreviations found.

TEXT SNIPPETS:
{snippets}
"""
                response_text = call_llm(prompt)
                abbr_dict = parse_abbreviations(response_text)

                for abbr, definition in abbr_dict.items():
                    if abbr in merged_abbreviations:
                        if len(definition) > len(merged_abbreviations[abbr]):
                            merged_abbreviations[abbr] = definition
                    else:
                        merged_abbreviations[abbr] = definition

        if not merged_abbreviations:
            st.info("No abbreviations found in the uploaded PDFs.")
        else:
            st.subheader("Merged Abbreviation Index:")
            for abbr, definition in sorted(merged_abbreviations.items()):
                st.write(f"• {abbr}: {definition}")