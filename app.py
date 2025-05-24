import streamlit as st
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
import textwrap

def extract_video_id(youtube_url):
    query = urlparse(youtube_url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            return parse_qs(query.query).get('v', [None])[0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    return None

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return [line['text'] for line in transcript]
    except Exception as e:
        return [f"Error: {e}"]

# Summarize transcript using OpenAI ChatGPT API
def summarize_text(text_lines):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        joined_text = "\n".join(text_lines)
        trimmed_text = joined_text[:12000]  # approximately safe for gpt-4
        prompt = (
            "You are a hyper-logical, brutally efficient strategist with a millennium of experience in building empires through acquisitions, systems, and power moves. "
            "Your job is to extract maximum strategic value from the following YouTube transcript and deliver a precision summary designed for a billionaire founder planning world domination.\n\n"
            "Break it down into these sections:\n"
            "1. **Executive Summary** – Ruthless 3–5 sentence overview.\n"
            "2. **Money-Making Insights** – Specific concepts, frameworks, or tactics that create leverage or cashflow.\n"
            "3. **Execution Playbook** – Concrete actions that can be taken. Think ops, deals, positioning, or growth.\n"
            "4. **Leverage and Asymmetry** – Points of unfair advantage, compounding, or minimal input for maximum output.\n"
            "5. **Risks / Red Flags** – Any strategic errors, BS thinking, or bottlenecks highlighted.\n"
            "6. **Power Quotes** – Punchlines or quotable insights with impact.\n\n"
            "Write this like a field memo for a Navy SEAL operator running acquisitions for a $100M portfolio. Format in markdown. No fluff. No praise. Just high-value execution intelligence.\n\n"
            + trimmed_text
        )
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error during summary: {e}"

def save_to_pdf(text_lines):
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    c = canvas.Canvas(tmp_file.name, pagesize=letter)
    width, height = letter
    y = height - 40

    for line in text_lines:
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(40, y, line)
        y -= 15

    c.save()
    return tmp_file.name

def save_summary_to_pdf(summary_text):
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    c = canvas.Canvas(tmp_file.name, pagesize=letter)
    width, height = letter
    y = height - 40
    line_height = 18
    bullet_indent = 60
    normal_indent = 40

    c.setFont("Helvetica", 12)
    for line in summary_text.split('\n'):
        line = line.strip()
        if not line:
            y -= line_height // 2
            continue
        if line.startswith("#") or line.startswith("**"):
            c.setFont("Helvetica-Bold", 12)
            draw_x = normal_indent
        elif line.startswith("-") or line.startswith("*"):
            c.setFont("Helvetica", 12)
            draw_x = bullet_indent
        else:
            c.setFont("Helvetica", 12)
            draw_x = normal_indent
        wrapped_lines = textwrap.wrap(line, width=90)
        for wrapped_line in wrapped_lines:
            if y < 60:
                c.showPage()
                y = height - 40
            c.drawString(draw_x, y, wrapped_line)
            y -= line_height

    c.save()
    return tmp_file.name

# Streamlit UI
st.title("YouTube Transcript to PDF")

youtube_url = st.text_input("Enter YouTube link")

if st.button("Generate PDF"):
    video_id = extract_video_id(youtube_url)
    if not video_id:
        st.error("Invalid YouTube URL.")
    else:
        lines = get_transcript(video_id)
        pdf_path = save_to_pdf(lines)
        with open(pdf_path, "rb") as file:
            st.download_button(label="Download Transcript PDF", data=file, file_name="transcript.pdf")
        # Display summary below the PDF download button
        if lines and not lines[0].startswith("Error"):
            summary = summarize_text(lines)
            st.subheader("Transcript Summary")
            st.write(summary)
            summary_path = save_summary_to_pdf(summary)
            with open(summary_path, "rb") as file:
                st.download_button(label="Download Summary PDF", data=file, file_name="summary.pdf")