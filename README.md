# Transcript Genius

## Summarize youtube videos and test your knowledge by generating a Quiz.

Try: https://transcript-genius.streamlit.app/

### If you want to run locally follow these steps:

1. Create a virtual env (optional)

2. Create a Folder named .streamlit and inside this folder create a file secrets.toml and in that file write your API key in this format:

```bash
GOOGLE_API_KEY="YOUR_API_KEY"
```
You can Generate API KEY from this link: https://aistudio.google.com/apikey

3. Open Terminal and run this command:

```bash
pip install -q -r requirements.txt
```

4. If you did everything correct then run this command:

```bash
streamlit run main.py
```

## Extra:
You can Change models in main.py file,  I used Google Gemini Models which are free and provide large context windows.
