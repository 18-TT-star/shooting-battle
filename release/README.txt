shooting-battle (minimal) distribution

Contents:
- shooting_game.py (main)
- constants.py
- gameplay.py
- fonts.py
- ui.py
- requirements.txt

How to run:
1) Optional (offline/locked env):
   python3 -m pip install -r requirements.txt
2) Run the game:
   python3 shooting_game.py

Notes:
- The game auto-installs/updates pygame>=2.5.0 if missing (requires internet).
- For Japanese text rendering, put a JP font file (.ttf/.otf/.ttc) under assets/fonts/ or alongside fonts.py.
