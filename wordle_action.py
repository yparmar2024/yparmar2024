import json
import os
import sys
import random
import argparse
from datetime import datetime, timezone

STATE_FILE = "wordle_state.json"
SVG_FILE = "wordle.svg"

# Default fallback list if the GitHub Secret is not set
DEFAULT_WORDS = [
    "REACT", "LINUX", "PYTHON", "CACHE", "TOKEN", 
    "CLOUD", "DEBUG", "PIXEL", "MACRO", "PROXY",
    "VIRUS", "ARRAY", "BYTES", "CLICK", "LOGIC",
    "STATE", "QUERY", "INDEX", "MODEM", "TRACK"
]

COLORS = {
    "empty": "#121213",
    "absent": "#3a3a3c",
    "present": "#b59f3b",
    "correct": "#538d4e",
    "text": "#ffffff",
    "border": "#3a3a3c"
}

def get_word_list():
    words_env = os.environ.get("WORD_LIST", "")
    if words_env:
        return [w.strip().upper() for w in words_env.split(",") if w.strip()]
    return DEFAULT_WORDS

def get_today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def get_target_word():
    # Use today's date string as the random seed so the word is consistent all day
    today = get_today_str()
    random.seed(today)
    words = get_word_list()
    return random.choice(words)

def load_state():
    today = get_today_str()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            # Auto-reset if the state is from a previous day
            if state.get("date") != today:
                return reset_state()
            return state
    return reset_state()

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def reset_state():
    state = {
        "date": get_today_str(),
        "guesses": [],
        "status": "playing" # playing, won, lost
    }
    save_state(state)
    return state

def generate_svg(state):
    target = get_target_word()
    guesses = state["guesses"]
    
    tile_size = 50
    gap = 8
    cols = 5
    rows = 6
    width = cols * (tile_size + gap) + gap
    height = rows * (tile_size + gap) + gap
    
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">\n'
    svg += f'  <style>.t {{ font-family: "Courier New", Courier, monospace; font-size: 32px; font-weight: bold; fill: {COLORS["text"]}; text-anchor: middle; dominant-baseline: central; }}</style>\n'
    svg += f'  <rect width="{width}" height="{height}" fill="{COLORS["empty"]}" />\n'
    
    for r in range(rows):
        guess = guesses[r] if r < len(guesses) else ""
        
        target_counts = {}
        for char in target:
            target_counts[char] = target_counts.get(char, 0) + 1
            
        colors = ["empty"] * cols
        if r < len(guesses):
            for c in range(cols):
                if guess[c] == target[c]:
                    colors[c] = "correct"
                    target_counts[guess[c]] -= 1
            
            for c in range(cols):
                if colors[c] == "empty" and guess[c] in target_counts and target_counts[guess[c]] > 0:
                    colors[c] = "present"
                    target_counts[guess[c]] -= 1
                elif colors[c] == "empty":
                    colors[c] = "absent"
                    
        for c in range(cols):
            x = gap + c * (tile_size + gap)
            y = gap + r * (tile_size + gap)
            
            fill_color = COLORS[colors[c]]
            stroke = "" if fill_color != COLORS["empty"] else f'stroke="{COLORS["border"]}" stroke-width="2"'
            
            svg += f'  <rect x="{x}" y="{y}" width="{tile_size}" height="{tile_size}" fill="{fill_color}" {stroke} />\n'
            
            if r < len(guesses):
                char = guess[c]
                cx = x + tile_size / 2
                cy = y + tile_size / 2 + 2
                svg += f'  <text x="{cx}" y="{cy}" class="t">{char}</text>\n'
                
    svg += '</svg>'
    
    with open(SVG_FILE, "w") as f:
        f.write(svg)

def guess_word(guess):
    state = load_state()
    target = get_target_word()
    
    if state["status"] != "playing":
        print("Game is already over for today.")
        return False
        
    guess = guess.upper().strip()
    if len(guess) != 5:
        print("Guess must be 5 letters.")
        return False
        
    if not guess.isalpha():
        print("Guess must be alphabetic.")
        return False

    state["guesses"].append(guess)
    
    if guess == target:
        state["status"] = "won"
    elif len(state["guesses"]) >= 6:
        state["status"] = "lost"
        
    save_state(state)
    generate_svg(state)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=["guess", "reset", "init"])
    parser.add_argument("--guess", type=str, help="The 5-letter word guess")
    args = parser.parse_args()
    
    if args.action == "reset":
        state = reset_state()
        generate_svg(state)
        print("Game reset for today.")
    elif args.action == "init":
        if not os.path.exists(STATE_FILE):
            state = reset_state()
            generate_svg(state)
        else:
            generate_svg(load_state())
    elif args.action == "guess":
        if not args.guess:
            print("Must provide --guess")
            sys.exit(1)
        success = guess_word(args.guess)
        if not success:
            sys.exit(1)
