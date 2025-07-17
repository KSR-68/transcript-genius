import streamlit as st
import re
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Core Logic ---

def get_video_id(youtube_url):
    """Extracts the video ID from various YouTube URL formats."""
    # Regex to find the video ID from various YouTube URL patterns
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11}).*'
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None

def generate_transcript(youtube_url):
    """Fetches the transcript for a given YouTube URL."""
    if not youtube_url:
        st.warning("Please enter a valid YouTube URL.")
        return ""

    video_id = get_video_id(youtube_url)
    if not video_id:
        st.error("Invalid YouTube URL. Could not extract video ID.")
        return ""

    try:
        # Fetch transcript, trying 'en' first, then common fallbacks
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
        text = " ".join([d['text'] for d in transcript_list])
        return text
    except Exception as e:
        st.error(f"Could not fetch subtitles for this video. Please ensure the video has English subtitles enabled. Error: {e}")
        return ""

def summarize(text):
    """Generates a summary of the text using the Gemini API."""
    if not text:
        return ""
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Summarize the following YouTube transcript in clear, concise points:\n\n{text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"An error occurred during summarization: {e}")
        return ""

def generate_quiz(text):
    """Generates a quiz from the text using the Gemini API and ensures valid JSON output."""
    if not text:
        return None
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = (
            f"{text}\n\n"
            "Based on the text above, generate a quiz as a single, valid JSON object.\n"
            "Your entire response must be only the JSON object, starting with `{` and ending with `}`. Do not include any introductory text, explanations, or markdown formatting.\n\n"
            "The JSON object must meet these requirements:\n"
            "1.  It must have a root object with two keys: `\"questions\"` (an array) and `\"answer_key\"` (an object).\n"
            "2.  The `\"questions\"` array must contain exactly 10 questions total:\n"
            "    - 6 of type `\"multiple_choice\"`\n"
            "    - 2 of type `\"true_false\"`\n"
            "    - 2 of type `\"fill_blank\"`\n\n"
            "Use the following precise structure for each question type:\n\n"
            "## For `\"multiple_choice\"` questions:\n"
            "The object must have `\"number\"`, `\"type\"`, `\"text\"`, and `\"options\"` keys. The `\"options\"` key must be an array of four objects, each with a `\"letter\"` and `\"text\"`. The corresponding answer in `\"answer_key\"` must be the correct letter (e.g., `\"b\"`).\n"
            "Example:\n"
            "{\n"
            "  \"number\": 1,\n"
            "  \"type\": \"multiple_choice\",\n"
            "  \"text\": \"What is the primary topic of the text?\",\n"
            "  \"options\": [\n"
            "    {\"letter\": \"a\", \"text\": \"Option A\"},\n"
            "    {\"letter\": \"b\", \"text\": \"Option B\"},\n"
            "    {\"letter\": \"c\", \"text\": \"Option C\"},\n"
            "    {\"letter\": \"d\", \"text\": \"Option D\"}\n"
            "  ]\n"
            "}\n\n"
            "## For `\"true_false\"` questions:\n"
            "The object must have `\"number\"`, `\"type\"`, `\"text\"`, and `\"options\"` keys. The `\"options\"` must be an array with two fixed options: True (`\"a\"`) and False (`\"b\"`). The corresponding answer in `\"answer_key\"` must be `\"a\"` or `\"b\"`.\n"
            "Example:\n"
            "{\n"
            "  \"number\": 7,\n"
            "  \"type\": \"true_false\",\n"
            "  \"text\": \"Is the following statement true?\",\n"
            "  \"options\": [\n"
            "    {\"letter\": \"a\", \"text\": \"True\"},\n"
            "    {\"letter\": \"b\", \"text\": \"False\"}\n"
            "  ]\n"
            "}\n\n"
            "## For `\"fill_blank\"` questions:\n"
            "The object must have `\"number\"`, `\"type\"`, and `\"text\"` keys. The `\"options\"` key must be omitted. The corresponding answer in `\"answer_key\"` must be the string that completes the sentence.\n"
            "Example:\n"
            "{\n"
            "  \"number\": 9,\n"
            "  \"type\": \"fill_blank\",\n"
            "  \"text\": \"The most important concept mentioned was ______.\"\n"
            "}\n"
        )

        response = model.generate_content(prompt)

        # Clean the response to ensure it's valid JSON
        if response and response.text:
            clean_text = response.text.strip()
            # Remove markdown fences that the model might add
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            # Now, parse the cleaned text
            return json.loads(clean_text.strip())
        else:
            st.error("The model returned an empty response.")
            return None
            
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse quiz JSON. The model's response was not valid JSON. Error: {e}")
        st.text_area("Model's Raw Response:", value=response.text if response else "No response", height=200)
        return None
    except Exception as e:
        st.error(f"An error occurred while generating the quiz: {e}")
        return None

def display_quiz(quiz_data):
    """Renders the quiz form and handles submission."""
    if not quiz_data or 'questions' not in quiz_data or not quiz_data['questions']:
        st.error("Failed to generate or display quiz data.")
        return

    with st.form(key="quiz_form"):
        user_answers = {}
        for question in quiz_data['questions']:
            q_num = question['number']
            q_text = question['text']
            q_type = question['type']

            st.markdown(f"**Question {q_num}:** {q_text}")

            if q_type == 'multiple_choice':
                options = {opt['letter']: f"{opt['letter'].upper()}) {opt['text']}" for opt in question.get('options', [])}
                if options:
                    user_answers[q_num] = st.radio(
                        "Select your answer:",
                        list(options.keys()),
                        format_func=lambda x: options[x],
                        key=f"q{q_num}",
                        label_visibility="collapsed"
                    )
            elif q_type == 'true_false':
                options = {opt['letter']: opt['text'] for opt in question.get('options', [])}
                if options:
                    user_answers[q_num] = st.radio(
                        "Select your answer:",
                        list(options.keys()),
                        format_func=lambda x: options[x],
                        key=f"q{q_num}",
                        label_visibility="collapsed"
                    )
            elif q_type == 'fill_blank':
                user_answers[q_num] = st.text_input(
                    "Your answer:",
                    key=f"q{q_num}",
                    label_visibility="collapsed"
                )
        
        submit_button = st.form_submit_button(label="Submit Quiz")

        if submit_button:
            score = 0
            results = []
            answer_key = quiz_data.get('answer_key', {})
            questions = quiz_data.get('questions', [])

            for q_num, user_answer in user_answers.items():
                correct_answer_val = answer_key.get(str(q_num))
                is_correct = user_answer.strip().lower() == str(correct_answer_val).strip().lower()
                
                # Find the full question details
                question_details = next((q for q in questions if q['number'] == q_num), None)

                if is_correct:
                    score += 1
                    results.append(f"**Question {q_num}: Correct!** ✅")
                else:
                    results.append(f"**Question {q_num}: Incorrect!** ❌")
                    results.append(f"  - Your answer: `{user_answer}`")
                    
                    # Display the correct answer in a more readable format
                    if question_details:
                        q_type = question_details['type']
                        if q_type == 'true_false':
                            correct_text = "True" if correct_answer_val == 'a' else "False"
                            results.append(f"  - Correct answer: `{correct_text}`")
                        elif q_type == 'multiple_choice':
                            # Find the text of the correct option
                            correct_option = next((opt['text'] for opt in question_details.get('options', []) if opt['letter'] == correct_answer_val), "N/A")
                            results.append(f"  - Correct answer: `{correct_answer_val.upper()}) {correct_option}`")
                        else: # fill_blank
                            results.append(f"  - Correct answer: `{correct_answer_val}`")
                    else:
                        results.append(f"  - Correct answer: `{correct_answer_val}`")


            st.success(f"### Your Score: {score}/{len(questions)}")
            with st.expander("See detailed results"):
                for result in results:
                    st.markdown(result)


def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Transcript Genius", layout="wide")
    st.markdown("<h1 style='text-align: center; color: #4A4A4A;'>🚀 Transcript Genius</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Turn any YouTube video into a summary or a quiz instantly!</p>", unsafe_allow_html=True)

    # Initialize session state
    if 'quiz_data' not in st.session_state:
        st.session_state.quiz_data = None
    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    if 'current_url' not in st.session_state:
        st.session_state.current_url = ""

    youtube_url = st.text_input("Enter the YouTube URL", placeholder="e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    col1, col2 = st.columns(2)
    with col1:
        generate_summary_button = st.button("📝 Generate Summary")
    with col2:
        generate_quiz_button = st.button("🧠 Generate Quiz")

    if youtube_url and youtube_url != st.session_state.current_url:
        # Clear old data if new URL is entered
        st.session_state.summary = ""
        st.session_state.quiz_data = None
        st.session_state.current_url = youtube_url

    if generate_summary_button:
        if youtube_url:
            with st.spinner("Generating summary..."):
                transcript = generate_transcript(youtube_url)
                if transcript:
                    st.session_state.summary = summarize(transcript)
                    st.session_state.quiz_data = None # Clear quiz if summary is generated
        else:
            st.warning("Please enter a YouTube URL first.")

    if generate_quiz_button:
        if youtube_url:
            with st.spinner("Generating quiz... This may take a moment."):
                transcript = generate_transcript(youtube_url)
                if transcript:
                    st.session_state.quiz_data = generate_quiz(transcript)
                    st.session_state.summary = "" # Clear summary if quiz is generated
        else:
            st.warning("Please enter a YouTube URL first.")

    # Display content based on session state
    if st.session_state.summary:
        st.markdown("---")
        st.subheader("Summary")
        st.markdown(st.session_state.summary)

    if st.session_state.quiz_data:
        st.markdown("---")
        st.subheader("Quiz Time!")
        display_quiz(st.session_state.quiz_data)


if __name__ == "__main__":
    main()
