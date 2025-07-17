# Transcript Genius

Turn any YouTube video into a summary or quiz instantly!

## Setup Instructions

1. **Install [UV](https://github.com/astral-sh/uv):**
   ```sh
   pip install uv
   ```

2. **Create a `.env` file in the project root:**
   ```
   GOOGLE_API_KEY="YOUR_API_KEY"
   ```

3. **Install dependencies:**
   ```sh
   uv add -r requirements.txt
   ```

4. **Run the app:**
   ```sh
   streamlit run main.py
   ```

## Usage

- Enter a YouTube URL.
- Click "Generate Summary" or "Generate Quiz".
- Enjoy your transcript summary
