# Daily Multilingual Devotional Pinterest Automation

Automatically generates **fresh, unique daily devotional posters** (1000×1500 Pinterest vertical format) with the **day of the week, date, optional Hindu lunar Tithi, and localized blessings**, and publishes them daily to **Pinterest API v5**.

## Features
- **Monday–Sunday Hindu Deities**:
  - Monday: Lord Shiva
  - Tuesday: Lord Hanuman
  - Wednesday: Lord Ganesha
  - Thursday: Lord Vishnu & Sai Baba
  - Friday: Goddess Mahalakshmi
  - Saturday: Lord Shani Dev & Hanuman
  - Sunday: Surya Dev
- **All Religions Supported** (`config/traditions.json`): `hindu`, `sikh`, `christian`, `islamic`, `buddhist`, `jain`.
- **All Languages Supported** (`config/languages.json`): Gujarati (`gu`), Hindi (`hi`), English (`en`), Marathi (`mr`), Tamil (`ta`), Telugu (`te`), Kannada (`kn`), Bengali (`bn`), Punjabi (`pa`), Arabic (`ar`).
- **Crisp Native Typography**: Uses HTML/CSS + headless Microsoft Edge so complex Indic & RTL scripts render with 100% accurate ligatures, vowel marks, and native numerals.
- **1 AI Artwork per Religion/Day**: Reuses the day's AI-generated artwork across all selected languages to save API cost.

## Setup
1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Run the one-click Pinterest OAuth setup (opens your browser, logs you in, and automatically saves your access token, refresh token, and board ID to `.env`):
   ```powershell
   python setup_pinterest.py
   ```
   *(Make sure `http://localhost:8085/callback` is added as a Redirect URI in your app at [developers.pinterest.com](https://developers.pinterest.com/).)*
3. *(Optional)* Copy `config/boards.example.json` to `config/boards.json` to route each religion/language to a separate Pinterest board.

## Usage
```powershell
# Generate today's Gujarati, Hindi, and English Hindu posters locally (dry-run)
python main.py

# Generate a full week (Monday to Sunday) for all languages
python main.py --week --languages all

# Generate for all religions and all languages
python main.py --religions all --languages all

# Generate and publish today's pins to Pinterest
python main.py --publish

# Schedule automatic daily posting at 6:00 AM via Windows Task Scheduler
.\setup_schedule.ps1 -Time "06:00" -Religions "hindu" -Languages "gu,hi,en"
```
