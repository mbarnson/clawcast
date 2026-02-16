#!/usr/bin/env python3
"""
Preprocess text for TTS engines (OpenAI, Kokoro, ElevenLabs).
Handles numbers, abbreviations, and other TTS-unfriendly formats.

Usage:
    echo "The project cost $11,000" | prep_for_tts.py
    prep_for_tts.py "The project cost $11,000"
    prep_for_tts.py < script.txt > script-tts.txt
"""

import sys
import re

def number_to_words(n):
    """Convert integer to words."""
    if n == 0:
        return "zero"
    
    ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
            "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    
    def _convert(num):
        if num < 20:
            return ones[num]
        elif num < 100:
            return tens[num // 10] + ("-" + ones[num % 10] if num % 10 else "")
        elif num < 1000:
            return ones[num // 100] + " hundred" + (" " + _convert(num % 100) if num % 100 else "")
        elif num < 1_000_000:
            return _convert(num // 1000) + " thousand" + (" " + _convert(num % 1000) if num % 1000 else "")
        elif num < 1_000_000_000:
            return _convert(num // 1_000_000) + " million" + (" " + _convert(num % 1_000_000) if num % 1_000_000 else "")
        elif num < 1_000_000_000_000:
            return _convert(num // 1_000_000_000) + " billion" + (" " + _convert(num % 1_000_000_000) if num % 1_000_000_000 else "")
        else:
            return _convert(num // 1_000_000_000_000) + " trillion" + (" " + _convert(num % 1_000_000_000_000) if num % 1_000_000_000_000 else "")
    
    return _convert(n)

def prep_for_tts(text):
    """Preprocess text for TTS."""
    
    # Handle currency with commas: $11,000 -> eleven thousand dollars
    def replace_currency(m):
        symbol = m.group(1)
        num_str = m.group(2).replace(",", "")
        try:
            num = int(num_str)
            words = number_to_words(num)
            currency = "dollars" if symbol == "$" else "euros" if symbol == "€" else "pounds" if symbol == "£" else "yen"
            if num == 1:
                currency = currency.rstrip("s")
            return words + " " + currency
        except:
            return m.group(0)
    
    text = re.sub(r'([$€£¥])(\d{1,3}(?:,\d{3})*)', replace_currency, text)
    
    # Handle numbers with commas: 11,000 -> eleven thousand
    def replace_number(m):
        num_str = m.group(0).replace(",", "")
        try:
            num = int(num_str)
            if num >= 1000:
                return number_to_words(num)
            return m.group(0)
        except:
            return m.group(0)
    
    text = re.sub(r'\b\d{1,3}(?:,\d{3})+\b', replace_number, text)
    
    # Handle percentages: 3.5% -> three point five percent
    def replace_percent(m):
        num = m.group(1)
        if "." in num:
            whole, decimal = num.split(".")
            whole_words = number_to_words(int(whole)) if whole else "zero"
            decimal_words = " ".join(number_to_words(int(d)) for d in decimal)
            return whole_words + " point " + decimal_words + " percent"
        else:
            return number_to_words(int(num)) + " percent"
    
    text = re.sub(r'(\d+(?:\.\d+)?)\s*%', replace_percent, text)
    
    # Handle common abbreviations
    abbrevs = {
        r'\bDr\.': 'Doctor',
        r'\bMr\.': 'Mister',
        r'\bMrs\.': 'Missus',
        r'\bMs\.': 'Ms',
        r'\bvs\.': 'versus',
        r'\betc\.': 'et cetera',
        r'\be\.g\.': 'for example',
        r'\bi\.e\.': 'that is',
        r'\bUS\b': 'U.S.',
        r'\bUK\b': 'U.K.',
        r'\bAI\b': 'A.I.',
        r'\bAPI\b': 'A.P.I.',
        r'\bCEO\b': 'C.E.O.',
        r'\bGDP\b': 'G.D.P.',
    }
    
    for pattern, replacement in abbrevs.items():
        text = re.sub(pattern, replacement, text)
    
    return text

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        print(prep_for_tts(text))
    else:
        text = sys.stdin.read()
        print(prep_for_tts(text), end="")
