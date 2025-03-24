import streamlit as st
import re
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import os

# Core Logic
def generate_transcript(youtube_url):
    if not youtube_url:
        st.warning("Please enter a valid YouTube URL")
        return ""
    
    try:
        video_id = youtube_url.split("v=")[1]
        if "&" in video_id:
            video_id = video_id.split("&")[0]
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        except Exception:
            # Try fetching with auto-generated subtitles
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en-US', 'en'])
            except:
                st.error("Could not fetch subtitles. Please ensure the video has subtitles enabled.")
                return ""
        text = format_transcript(transcript)
        text = remove_timestamps(text)
        return text
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return ""

# Remove Timestamps
def remove_timestamps(text):
    timestamp_pattern = r'\[\d+:\d+:\d+\.\d+ --> \d+:\d+:\d+\.\d+\]'
    return re.sub(timestamp_pattern, '', text)

# Format the time into HH:MM:SS
def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):05.2f}"

# Format the transcript
def format_transcript(transcript):
    formatted_transcript = ""
    for entry in transcript:
        start_time = entry["start"]
        end_time = entry["start"] + entry["duration"]
        formatted_transcript += f"[{format_time(start_time)} --> {format_time(end_time)}] {entry['text']}\n"
    return formatted_transcript

# Summarize the text
def summarize(text):
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro')
    prompt = text + "\n Summarize the above youtube transcript in points"
    response = model.generate_content(prompt)
    return response.text

# Generate Quiz
def generate_quiz(text):
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    #Prompt for generating quiz and make parsing easy
    prompt = (
        f"{text}\n\n"
        "Please generate a quiz based on the above YouTube transcript with exactly 10 questions total, "
        "divided as follows:\n"
        "- 6 multiple choice questions (a, b, c, d options)\n"
        "- 2 true/false questions\n"
        "- 2 fill-in-the-blank questions\n\n"
        "Format the quiz EXACTLY as follows, with NO ADDITIONAL TEXT before Question 1:\n" #Yeah because I have remove it myself by code why not make it easy for me by not generating :)
        "Question 1: [question text]\n"
        "a) [option text]\n"
        "b) [option text]\n"
        "c) [option text]\n"
        "d) [option text]\n\n"
        "Question 2: [question text]\n"
        "a) [option text]\n"
        "... and so on\n\n"
        "For true/false questions:\n"
        "Question X: [statement]\n"
        "True\n"
        "False\n\n"
        "For fill-in-the-blank:\n"
        "Question X: [sentence with _____ for the blank]\n\n"
        "After all questions, include 'ANSWER KEY:' followed by the answers in the format:\n"
        "1. [correct answer]\n"
        "2. [correct answer]\n"
        "And so on for all 10 questions."
    )
    
    response = model.generate_content(prompt)
    return response.text

def parse_quiz(quiz_text):
    quiz_data = {
        'questions': [],
        'answer_key': {}
    }
    
    # Separate questions from answer key
    # Because of better prompt now I can easily separate the questions and answer key
    parts = quiz_text.split("ANSWER KEY:", 1)
    questions_text = parts[0]
    answer_key_text = parts[1] if len(parts) > 1 else ""
    
    # Extract questions using regex pattern that specifically looks for "Question X:" format
    questions_pattern = r'Question\s+(\d+):\s*(.*?)(?=Question\s+\d+:|ANSWER KEY:|$)'
    question_matches = re.findall(questions_pattern, questions_text, re.DOTALL)
    
    for num_str, content in question_matches:
        question_num = int(num_str)
        content = content.strip()
        lines = content.split('\n')
        
        question_data = {
            'number': question_num,
            'text': lines[0].strip(),
            'type': 'multiple_choice',
            'options': []
        }
        
        if "True" in content and "False" in content and len(lines) <= 3:
            question_data['type'] = 'true_false'
            question_data['options'] = [
                {'letter': 'true', 'text': 'True'},
                {'letter': 'false', 'text': 'False'}
            ]
        elif "_____" in content or "________" in content:
            question_data['type'] = 'fill_blank'
            question_data['options'] = []
        else:
          
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                    
                # Match options like "a) Option text" or "a. Option text"
                match = re.match(r'([a-d])[).]\s*(.*)', line)
                if match:
                    letter, text = match.groups()
                    text = text.rstrip('(').strip()
                    question_data['options'].append({'letter': letter, 'text': text})
        
        quiz_data['questions'].append(question_data)
    
    # Parse answer key
    if answer_key_text:
        answer_lines = answer_key_text.strip().split('\n')
        for line in answer_lines:
            line = line.strip()
            if not line:
                continue
                
            match = re.match(r'(\d+)[.)]?\s*(.*)', line)
            if match:
                q_num, answer = match.groups()
                q_num = int(q_num)
                
                # Clean up the answer text
                answer = answer.strip()
                if answer.startswith('(') and answer.endswith(')'):
                    answer = answer[1:-1]
                
                # For multiple choice, extract just the letter
                mc_match = re.match(r'[(.]*([a-d])[).]*', answer)
                if mc_match:
                    answer = mc_match.group(1)
                
                # Convert True/False to lowercase for consistency
                if answer.lower() in ['true', 'false']:
                    answer = answer.lower()
                    
                quiz_data['answer_key'][q_num] = answer
    
    return quiz_data

def display_quiz(quiz_data):
    if not quiz_data or not quiz_data['questions']:
        st.error("Failed to parse quiz data.")
        return
    
    container = st.container()
    with container:
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            st.title("YouTube Video Quiz")
            st.write("Answer all questions and submit to see your score.")
            
            
            with st.form(key="quiz_form"):
                user_answers = {}
                
                for question in quiz_data['questions']: #Parsing according to the question type
                    q_num = question['number']
                    q_text = question['text']
                    q_type = question['type']
                    
                    st.markdown(f"**Question {q_num}:** {q_text}")
                    
                    if q_type == 'multiple_choice':
                        options = {opt['letter']: f"{opt['letter']}) {opt['text']}" for opt in question['options']}
                        if options:
                            user_answers[q_num] = st.radio(
                                f"Select your answer for question {q_num}:",
                                options.keys(),
                                format_func=lambda x: options[x],
                                key=f"q{q_num}"
                            )
                        else:
                            st.warning(f"No options found for question {q_num}")
                    
                    elif q_type == 'true_false':
                        user_answers[q_num] = st.radio(
                            f"Select your answer for question {q_num}:",
                            ['true', 'false'],
                            format_func=lambda x: x.capitalize(),
                            key=f"q{q_num}"
                        )
                    
                    elif q_type == 'fill_blank':
                        user_answers[q_num] = st.text_input(
                            f"Your answer for question {q_num}:",
                            key=f"q{q_num}"
                        )
                
                # Submit button
                submit_button = st.form_submit_button(label="Submit Quiz")
                
                if submit_button:
                    # Calculate score
                    score = 0
                    results = []
                    
                    for q_num, user_answer in user_answers.items():
                        correct_answer = quiz_data['answer_key'].get(q_num, "")
                        
                        # Find question type
                        question_type = next((q['type'] for q in quiz_data['questions'] if q['number'] == q_num), None)
                        
                       
                        if question_type == 'fill_blank':
                            is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
                        else:
                            is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
                        
                        if is_correct:
                            score += 1
                            results.append(f"Question {q_num}: Correct! ✅")
                        else:
                            if question_type == 'multiple_choice':
                                # Find the text of the correct answer
                                question = next((q for q in quiz_data['questions'] if q['number'] == q_num), None)
                                if question:
                                    correct_option = next((opt for opt in question['options'] 
                                                         if opt['letter'] == correct_answer), None)
                                    correct_text = f"{correct_answer}) {correct_option['text']}" if correct_option else correct_answer
                                    results.append(f"Question {q_num}: Incorrect ❌ - Correct answer: {correct_text}")
                            elif question_type == 'true_false':
                                results.append(f"Question {q_num}: Incorrect ❌ - Correct answer: {correct_answer.capitalize()}")
                            else:  
                                results.append(f"Question {q_num}: Incorrect ❌ - Correct answer: {correct_answer}")
                    
                   
                    st.success(f"Your Score: {score}/{len(user_answers)}")
                    
                    with st.expander("See detailed results"):
                        for result in results:
                            st.markdown(result)

def main():
    st.set_page_config(page_title="YouTube Transcript Tool", layout="wide")
    
    st.markdown("<h1 style='text-align: center;'>YouTube Transcript Summarizer</h1>", unsafe_allow_html=True)
    
    youtube_url = st.text_input("Enter the YouTube URL")
    
    col1, col2 = st.columns(2)
    with col1:
        generate_button = st.button("Generate Summary")
    with col2:
        quiz_button = st.button("Generate Quiz")
    
    if generate_button: #Generate Summary Button
        if youtube_url:
            with st.spinner("Generating summary..."):
                text = generate_transcript(youtube_url)
                if text:
                    summary = summarize(text)
                    st.markdown("## Summary")
                    st.markdown(summary)
        else:
            st.warning("Please enter a YouTube URL first")
    
    if quiz_button: #Generate Quiz Button
        if youtube_url:
            with st.spinner("Generating quiz..."):
                text = generate_transcript(youtube_url)
                if text:
                    quiz_text = generate_quiz(text)
                    quiz_data = parse_quiz(quiz_text)
                    st.session_state.quiz_data = quiz_data
                    display_quiz(quiz_data)
                else:
                    st.error("Could not generate quiz. Please try again.")
        else:
            st.warning("Please enter a YouTube URL first")
    
    if 'quiz_data' in st.session_state and not generate_button and not quiz_button:
        display_quiz(st.session_state.quiz_data)

if __name__ == "__main__":
    main()