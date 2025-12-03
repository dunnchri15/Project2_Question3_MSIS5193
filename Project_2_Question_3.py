import streamlit as st
import requests
import PyPDF2
import re

# Load API key from Streamlit secrets
API_KEY = st.secrets["GROQ_API_KEY"]

def call_llm(prompt):
    """Call Groq API to get LLM response safely."""
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "llama-3.1-70b-versatile",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    try:
        data = response.json()
    except Exception:
        st.error(f"Invalid response from API:\n{response.text}")
        return ""

    # Check if there is an error key
    if "error" in data:
        st.error(f"API Error: {data['error']}")
        return ""

    # Check if 'choices' exist
    if "choices" not in data or len(data["choices"]) == 0:
        st.error(f"No choices returned from API. Full response:\n{data}")
        return ""

    return data["choices"][0]["message"]["content"]
st.title("Multi-PDF Abbreviation Index Generator")

# Allow multiple PDF uploads
uploaded_files = st.file_uploader(
    "Upload PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

def extract_text(pdf_file):
    """Extract all text from a PDF."""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_abbreviation_context(text):
    """Return lines/snippets with candidate abbreviations."""
    pattern = r'(.{0,50}\b[A-Z]{2,10}(?:&[A-Z]{1,10})?\b.{0,50})'
    matches = re.findall(pattern, text)
    return "\n".join(matches)

def parse_abbreviations(text):
    """
    Parse the LLM output into a dictionary {ABBR: definition}.
    Assumes output is bullet points like: • ABBR: definition
    """
    abbr_dict = {}
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("•"):
            parts = line[1:].split(":", 1)
            if len(parts) == 2:
                abbr = parts[0].strip()
                definition = parts[1].strip()
                # Keep longest definition if duplicates exist
                if abbr in abbr_dict:
                    if len(definition) > len(abbr_dict[abbr]):
                        abbr_dict[abbr] = definition
                else:
                    abbr_dict[abbr] = definition
    return abbr_dict

# Button to generate merged abbreviation index
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
                # Call Groq API
                response_text = call_llm(prompt)
                abbr_dict = parse_abbreviations(response_text)

                # Merge abbreviations
                for abbr, definition in abbr_dict.items():
                    if abbr in merged_abbreviations:
                        if len(definition) > len(merged_abbreviations[abbr]):
                            merged_abbreviations[abbr] = definition
                    else:
                        merged_abbreviations[abbr] = definition

        if not merged_abbreviations:
            st.write("No abbreviations found in the uploaded PDFs.")
        else:
            st.subheader("Merged Abbreviation Index:")
            for abbr, definition in sorted(merged_abbreviations.items()):
                st.write(f"• {abbr}: {definition}")