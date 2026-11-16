"""
The rules of the daily puzzle, as plain functions.

Nothing here touches the database or the request, so each rule can be read
(and tested) on its own. views.py calls these to answer each guess.
"""
import re
import unicodedata

MIN_LENGTH = 4
MAX_LENGTH = 12

# Facts unlock after this many guesses: fact 1 after 2, fact 2 after 4.
# Before fact 1, players only have the topic and the answer's length.
FACT_UNLOCK_AFTER = (2, 4)

# Letter results, in the order the share grid and the page use them.
HIT = "hit"      # right letter, right place (green)
CLOSE = "close"  # letter is in the name, somewhere else (yellow)
MISS = "miss"    # not in the name (grey)


def normalise(text):
    """
    Turns a name into the A-Z letters players type, e.g.
    "Ødegaard" -> "ODEGAARD", "Mac Allister" -> "MACALLISTER".

    NFKD splits accented letters into letter + accent so the accent can be
    dropped. A few letters (Ø, Æ, ß...) don't split that way, so they're
    mapped by hand first.
    """
    text = (text or "").translate(str.maketrans({
        "Ø": "O", "ø": "o", "Æ": "AE", "æ": "ae", "ß": "SS", "Ł": "L", "ł": "l", "Đ": "D", "đ": "d",
    }))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z]", "", text.upper())


def max_guesses(answer):
    """6 guesses for answers of up to 6 letters, 7 for longer ones."""
    return 6 if len(answer) <= 6 else 7


def check_guess(guess, answer):
    """
    Returns an error message if `guess` can't be played, or None if it can.

    Any A-Z guess of the right length is allowed -- there's deliberately no
    list of valid names (see the skill file for why). A guess that fails
    here is not counted as one of the player's attempts.
    """
    if not guess:
        return "Type a name first."
    if not re.fullmatch(r"[A-Z]+", guess):
        return "Use letters A to Z only."
    if len(guess) != len(answer):
        return "Needs {:d} letters.".format(len(answer))
    return None


def score(guess, answer):
    """
    Colours each letter of a guess, e.g. score("SALAH", "SAKAH") ->
    [hit, hit, miss, hit, hit].

    Two passes, so repeated letters are handled fairly:
      1. Mark exact matches green, and count the answer's leftover letters.
      2. Go through the rest; a letter is yellow only while the answer still
         has an unmatched copy of it, otherwise grey.
    So guessing "LLLL" against "LAMB" gives one green L and three grey Ls,
    not four yellows.
    """
    marks = [MISS] * len(answer)
    leftover = {}
    for i, (g, a) in enumerate(zip(guess, answer)):
        if g == a:
            marks[i] = HIT
        else:
            leftover[a] = leftover.get(a, 0) + 1

    for i, g in enumerate(guess):
        if marks[i] != HIT and leftover.get(g):
            marks[i] = CLOSE
            leftover[g] -= 1
    return marks


def facts_unlocked(guess_count, game_over):
    """How many of the two facts the player can see now."""
    if game_over:
        return len(FACT_UNLOCK_AFTER)
    return sum(1 for after in FACT_UNLOCK_AFTER if guess_count >= after)


def is_over(guesses, answer):
    """The game ends when the answer is guessed or the guesses run out."""
    return bool(guesses) and (guesses[-1] == answer or len(guesses) >= max_guesses(answer))
