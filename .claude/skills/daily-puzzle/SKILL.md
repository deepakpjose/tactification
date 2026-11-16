---
name: daily-puzzle
description: Rules for Tactification Daily, the fact-clue name-guessing football puzzle. Use when writing, checking or editing puzzles or their facts, when drafting a batch of puzzles for approval, or when changing the game's code (scoring, guess validation, clues, sharing).
---

# Tactification Daily

A daily football puzzle. Players guess the answer (a player, coach, club,
country, stadium, nickname: anything in football) letter by letter, as in a word game, and fascinating facts about the
answer unlock as they go. Everyone gets the same puzzle each day.

Never call it "Wordle" anywhere (page copy, share text, code names). The New
York Times owns that name. The mechanic is free to use; the name is not.

## Game rules

1. **The answer** can be anything in football: a player or coach (by
   surname), a club, a national team, a stadium, a trophy, a nickname.
   - 4 to 12 letters, A–Z only. (Years and other numbers aren't supported yet.)
   - Strip accents and punctuation: ØDEGAARD → ODEGAARD, ČECH → CECH.
   - Use the name fans actually say: the surname for most players (SALAH), the
     single known name where that's how he's known (PELE, KAKA). Names over
     12 letters (SCHWEINSTEIGER) can't be answers.
   - Names with a space or hyphen are fine only if they collapse cleanly
     (MAC ALLISTER → MACALLISTER). Skip any whose spelling fans would argue over.
2. **Guesses allowed:** 6 for answers of up to 6 letters, 7 for 7–12 letters.
3. **Valid guesses:** any A–Z guess with exactly the answer's number of
   letters. There is no name list to check against: keeping one complete is
   impossible, and rejecting a real but unlisted name is worse than allowing
   the odd letter-fishing guess. A guess of the wrong length is refused with
   a message and not counted.
4. **Letter colours,** standard rules including repeated letters:
   - Green: right letter, right place.
   - Yellow: the letter is in the name, in another place. A letter is marked
     yellow only as many times as it still appears unmatched in the answer.
   - Grey: not in the name (or all its copies are already accounted for).
5. **Clues:**
   - At the start, players get only the `topic` label (Player, Coach,
     Stadium...) and the answer's length. There is no hint: the first two
     guesses are played on letters alone, which is what makes the colours
     matter. Don't add one back without the owner's say-so.
   - Fact 1 is shown after first two attempts.
   - Fact 2 unlocks after the 4th guess, or when the game ends.
   - The board shows the answer's length from the start (empty boxes).
6. **End of game:** reveal the full display name, both facts and the source
   link(s), whether the player won or not.
7. **Share text** is spoiler-free: puzzle number, score (or X), one emoji row
   per guess, and the site link. Never include letters or the answer.
   ```
   Tactification Daily #14 4/7
   ⬛🟨⬛⬛🟩⬛⬛
   🟩⬛🟨⬛🟩⬛⬛
   🟩🟩🟩⬛🟩🟩⬛
   🟩🟩🟩🟩🟩🟩🟩
   tactification.com/daily
   ```
8. **Answers are checked on the server** in the live game. The page must never
   contain the answer before the game ends.

## Writing facts

The facts are the point of the game. A good one makes someone say "I didn't
know that" and want to share it.

### What makes a good fact
- **Surprising, not trivial.** Records, oddities, contradictions and firsts:
  "never booked in 16 years", "sent off in his last ever match".
  Not "he played for Liverpool".
- **True, and checkable.** Every fact needs a source a reader could open: the
  player's Wikipedia page, a club or federation site, a major outlet (BBC,
  ESPN, The Athletic, Guardian), or Opta/official stats.
- **Specific.** Numbers and dates make a fact believable and memorable:
  "974 minutes without conceding", "260 Premier League goals".
- **Not a giveaway.** Fact 1 must not name the player, his club or anything
  that answers it outright. It should narrow things down, not solve them.
- **Fact 2 is more identifying** than fact 1: a well-known achievement, the
  club, the era. Someone who knows football should usually solve it after
  fact 2.

### Style
- Write in the first person, as the answer speaking: "I scored…", "We won…"
  (national teams use "we").
- One or two sentences, under about 25 words each.
- Plain, journalistic English, as on the rest of the blog. British spelling
  (Tactification's football voice): "defence", "colour".
- No hedging words ("reportedly", "allegedly"). If it needs hedging, it isn't
  solid enough for the game.

### Verification rules
These exist because confident-sounding mistakes are easy to write. Two real
examples from building the demo:
- "France never saved a penalty in a shootout between 1998 and 2024" — Barthez
  is recalled saving Albertini's penalty in the 1998 shootout, so as worded it
  is likely false. It stays out until a source settles it.
- "France reached three of the last eight World Cup finals" — wrong, it was
  four between 1998 and 2022. Caught on re-reading.

So:
1. Check every number, date and record against the source before the puzzle
   is approved. Read the source; don't rely on memory.
2. Records change. Phrase time-sensitive facts with a date ("as of 2026", "in
   2016") or check they still hold on the publish date.
3. Watch the boundaries of ranges ("between 1998 and 2024" includes 1998).
   Most false facts fail at the edges.
4. "Never" and "only" are the riskiest words. Look for one counterexample
   before approving them.
5. If a fact can't be confirmed, drop it or rewrite it into something that can
   be. Don't publish it marked as unsure.
6. Facts drafted by AI must be checked by a person before going live. Mark
   drafts as unapproved until then.

## Puzzle record format

Each puzzle is stored or drafted in this shape:

```json
{
  "answer": "LINEKER",
  "display": "Gary Lineker",
  "topic": "Player",
  "facts": [
    "I was never shown a yellow or red card in my 16-year professional career.",
    "I won the Golden Boot at the 1986 World Cup with six goals."
  ],
  "sources": [
    "https://en.wikipedia.org/wiki/Gary_Lineker"
  ],
  "approved": false
}
```

- `answer`: uppercase A–Z, 4–12 letters.
- `display`: the full name with its proper accents, shown on reveal.
- `topic`: what kind of answer it is, up to 24 characters, shown as a label:
  `"Player"`, `"Coach"`, `"Club"`, `"National team"`, `"Stadium"`, `"Trophy"`,
  `"Nickname"`. Use the same wording each time for the same kind of answer.
- `facts`: exactly two, fact 1 the hook, fact 2 the more identifying one.
- `sources`: at least one URL that supports both facts; one per fact if no
  single page covers both.
- `approved`: `false` for drafts. Only a person sets it to `true`.

## Drafting a batch

When asked for a batch of puzzles (for example a week's worth):
1. Mix topics, eras, leagues and nations: in a batch of 7 or more, no more
   than half with the same topic, and no more than half from one region.
2. Vary answer length across the 4–12 range so the week isn't all 5-letter names.
3. Don't repeat an answer used in the last year.
4. Return the batch as JSON records in the format above, all with
   `"approved": false`, and list separately any fact you could not confirm.

## Checklist before approving a puzzle
- [ ] Answer is 4–12 letters, A–Z, and spelt the way fans would type it.
- [ ] Topic label is right for the answer.
- [ ] Fact 1 is surprising and doesn't give the answer away.
- [ ] Fact 2 makes it solvable for a football fan.
- [ ] Every number, date and "never/only" claim checked against the source.
- [ ] Facts are first person, short, British spelling.
- [ ] Source link opens and supports the facts.

## Where it lives in the code
- `app/daily/game.py`: the rules (letter colours, guess limits, fact unlocks).
  If a rule above changes, change it here and in this file.
- `app/daily/schedule.py`: which puzzle runs on which day.
- `app/daily/views.py`: `/daily/` page and `/daily/guess`. The server checks
  each guess. The browser never gets the answer before the game ends.
- `app/daily/admin.py`, `forms.py`, `templates/daily/`: the admin pages at
  `/daily/admin` for writing, approving and pinning puzzles.
- `app/static/js/daily.js`, `app/static/css/daily.css`: the page itself.
- `FactPuzzle` in `app/models.py`.
- Puzzles are entered by hand at `/daily/admin/new`. A drafted batch in the
  record format above is copied in one puzzle at a time.
- Tests: `tests/test_daily.py`.
