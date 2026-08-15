import json
import os
import sys
import random
import argparse
import urllib.request
from datetime import datetime, timezone

stateFile = "data/state.json"
svgFile = "assets/wordle.svg"
wordsFile = "data/valid.txt"

defaultWords = [
    "REACT", "LINUX", "PYTHON", "CACHE", "TOKEN", 
    "CLOUD", "DEBUG", "PIXEL", "MACRO", "PROXY",
    "VIRUS", "ARRAY", "BYTES", "CLICK", "LOGIC",
    "STATE", "QUERY", "INDEX", "MODEM", "TRACK"
]

wordleColors = {
    "empty": "#0c1117",
    "absent": "#3a3a3c",
    "present": "#b59f3b",
    "correct": "#538d4e",
    "text": "#ffffff",
    "border": "#3a3a3c",
    "key_empty": "#818384"
}

def getWordList():
    wordsEnv = os.environ.get("WORD_LIST", "")
    if wordsEnv:
        return [w.strip().upper() for w in wordsEnv.split(",") if w.strip()]
    return defaultWords

def getTodayStr():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def getTargetWord():
    today = getTodayStr()
    try:
        url = f"https://www.nytimes.com/svc/wordle/v2/{today}.json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data["solution"].upper()
    except Exception as e:
        print(f"Failed to fetch from NYT: {e}")
        random.seed(today)
        words = getWordList()
        return random.choice(words)

def loadState():
    today = getTodayStr()
    if os.path.exists(stateFile):
        with open(stateFile, "r") as f:
            state = json.load(f)
            if state.get("date") != today:
                return resetState()
            return state
    return resetState()

def saveState(state):
    with open(stateFile, "w") as f:
        json.dump(state, f, indent=2)

def resetState():
    state = {
        "date": getTodayStr(),
        "guesses": [],
        "status": "playing"
    }
    saveState(state)
    return state

def generateSvg(state):
    target = getTargetWord()
    guesses = state["guesses"]
    
    tileSize = 50
    gap = 10
    cols = 5
    rows = 6
    gridWidth = cols * (tileSize + gap) + gap
    gridHeight = rows * (tileSize + gap) + gap
    
    keyWidth = 28
    keyHeight = 42
    keyGap = 6
    kbRows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
    
    kbHeight = len(kbRows) * (keyHeight + keyGap)
    
    width = 360
    topPadding = 20
    middlePadding = 25
    bottomPadding = 15
    height = topPadding + gridHeight + middlePadding + kbHeight + bottomPadding
    
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">\n'
    svg += f'  <style>\n'
    svg += f'    .t {{ font-family: "Courier New", Courier, monospace; font-size: 34px; font-weight: bold; fill: {wordleColors["text"]}; text-anchor: middle; dominant-baseline: central; }}\n'
    svg += f'    .k {{ font-family: "Courier New", Courier, monospace; font-size: 18px; font-weight: bold; fill: {wordleColors["text"]}; text-anchor: middle; dominant-baseline: central; }}\n'
    svg += f'  </style>\n'
    svg += f'  <rect width="{width}" height="{height}" fill="{wordleColors["empty"]}" />\n'
    
    letterColors = {chr(i): "key_empty" for i in range(65, 91)}
    
    for r in range(rows):
        guess = guesses[r] if r < len(guesses) else ""
        
        targetCounts = {}
        for char in target:
            targetCounts[char] = targetCounts.get(char, 0) + 1
            
        rowColors = ["empty"] * cols
        if r < len(guesses):
            for c in range(cols):
                if guess[c] == target[c]:
                    rowColors[c] = "correct"
                    targetCounts[guess[c]] -= 1
            
            for c in range(cols):
                if rowColors[c] == "empty" and guess[c] in targetCounts and targetCounts[guess[c]] > 0:
                    rowColors[c] = "present"
                    targetCounts[guess[c]] -= 1
                elif rowColors[c] == "empty":
                    rowColors[c] = "absent"
                    
            for c in range(cols):
                char = guess[c]
                current = letterColors[char]
                newCol = rowColors[c]
                if newCol == "correct":
                    letterColors[char] = "correct"
                elif newCol == "present" and current != "correct":
                    letterColors[char] = "present"
                elif newCol == "absent" and current not in ("correct", "present"):
                    letterColors[char] = "absent"
                    
        gridOffsetX = (width - gridWidth) / 2
        for c in range(cols):
            x = gridOffsetX + gap + c * (tileSize + gap)
            y = topPadding + gap + r * (tileSize + gap)
            
            fillColor = wordleColors[rowColors[c]]
            stroke = "" if fillColor != wordleColors["empty"] else f'stroke="{wordleColors["border"]}" stroke-width="2"'
            
            svg += f'  <rect x="{x}" y="{y}" width="{tileSize}" height="{tileSize}" fill="{fillColor}" {stroke} rx="4" />\n'
            
            if r < len(guesses):
                char = guess[c]
                cx = x + tileSize / 2
                cy = y + tileSize / 2 + 2
                svg += f'  <text x="{cx}" y="{cy}" class="t">{char}</text>\n'
                
    kbYStart = topPadding + gridHeight + middlePadding
    for i, kRow in enumerate(kbRows):
        rowWidth = len(kRow) * keyWidth + (len(kRow) - 1) * keyGap
        startX = (width - rowWidth) / 2
        for j, char in enumerate(kRow):
            x = startX + j * (keyWidth + keyGap)
            y = kbYStart + i * (keyHeight + keyGap)
            fillColor = wordleColors[letterColors[char]]
            svg += f'  <rect x="{x}" y="{y}" width="{keyWidth}" height="{keyHeight}" fill="{fillColor}" rx="4" />\n'
            cx = x + keyWidth / 2
            cy = y + keyHeight / 2 + 1
            svg += f'  <text x="{cx}" y="{cy}" class="k">{char}</text>\n'
                
    svg += '</svg>'
    
    with open(svgFile, "w") as f:
        f.write(svg)

def guessWord(guess):
    state = loadState()
    
    if state["status"] != "playing":
        print("Game is already over for today.")
        return False
        
    target = getTargetWord()
        
    guess = guess.upper().strip()
    if len(guess) != 5 or not guess.isalpha():
        print("Guess must be a 5-letter word.")
        return False
        
    if os.path.exists(wordsFile):
        with open(wordsFile, "r") as f:
            validWords = set(w.strip().upper() for w in f)
        if guess not in validWords:
            print("Not in word list.")
            return False

    state["guesses"].append(guess)
    
    if guess == target:
        state["status"] = "won"
    elif len(state["guesses"]) >= 6:
        state["status"] = "lost"
        
    saveState(state)
    generateSvg(state)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=["guess", "reset", "init"])
    parser.add_argument("--guess", type=str, help="The 5-letter word guess")
    args = parser.parse_args()
    
    if args.action == "reset":
        state = resetState()
        generateSvg(state)
        print("Game reset for today.")
    elif args.action == "init":
        if not os.path.exists(stateFile):
            state = resetState()
            generateSvg(state)
        else:
            generateSvg(loadState())
    elif args.action == "guess":
        if not args.guess:
            print("Must provide --guess")
            sys.exit(1)
        success = guessWord(args.guess)
        if not success:
            sys.exit(1)
