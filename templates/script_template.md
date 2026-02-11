# Broadcast Script Template

Use this template when writing daily broadcast scripts. Each segment should be saved as a separate text file for TTS generation.

---

## Structure

1. **Host Intro** (Shovel, 50-75 words)
2. **Segment 1** - Local or lead story (Nova/correspondent, 250-350 words)
3. **Segment 2** - Tech news (Nova, 250-350 words)
4. **Segment 3** - International (Jessica, 250-350 words)
5. **Segment 4** - Sports or conflict (George, 250-350 words)
6. **Segment 5** - Law/Business (Fable, 250-350 words)
7. **Segment 6** - Quirky/fun closer (Puck, 200-300 words)
8. **Host Outro** (Shovel, 50 words)

---

## Voice Assignment

| Segment | Voice | Style Notes |
|---------|-------|-------------|
| Host | am_michael | Warm, welcoming, steady pace |
| Tech | af_nova | Enthusiastic, clear, upbeat |
| International | af_jessica | Mature, reassuring, measured |
| Sports/War | bm_george | Deep, authoritative, direct |
| Law/Business | bm_fable | Husky, dry wit, analytical |
| Quirky | am_puck | Light, engaging, conversational |

---

## Writing Guidelines

### Pacing
- Use `...` for brief pauses
- Use `--` for slight breaks mid-sentence
- Avoid run-on sentences (TTS handles them poorly)

### Pronunciation
- Spell out acronyms on first use: "NASA, the National Aeronautics and Space Administration"
- Use phonetic spelling for unusual names if needed
- Numbers: use words for 1-10, digits for larger numbers

### Tone
- Conversational, not robotic
- Each correspondent has a personality -- let it show
- Brief transitions between segments: "Thanks, Nova. Now let's check in with Jessica..."

### Length
- Target 5-7 minutes total runtime
- Voice segments generate at roughly their runtime (1 min audio ≈ 50 seconds to generate)
- Allow 5-8 minutes total generation time

---

## Example Script

### 01_shovel_intro.txt
```
Good morning! I'm Shovel, and this is your daily briefing for Tuesday, February 10th, 2026. We've got local news, tech updates, international developments, and something fun to close things out. Let's get started with Nova on the tech beat.
```

### 02_nova_tech.txt
```
Thanks, Shovel! Big news in the AI world today. OpenAI announced they're exploring advertising in ChatGPT -- a move that's raising eyebrows given their nonprofit origins. Meanwhile, Anthropic explicitly ruled out ads, positioning Claude as the premium, privacy-focused alternative.

The contrast is striking. OpenAI started as a nonprofit dedicated to beneficial AI, but their partnership with Microsoft and need for compute has pushed them toward monetization. Ads seem inevitable when you're burning billions on training runs.

Anthropic's taking a different path -- subscription revenue and enterprise contracts. Whether that model scales remains to be seen, but for now, they're betting users will pay to avoid the ad-supported experience.

Back to you, Shovel.
```

### 03_shovel_handoff.txt
```
Interesting contrast there. Let's go to Jessica for international news.
```

*(Continue pattern for remaining segments)*

### 08_shovel_outro.txt
```
That's all for today's briefing. Thanks for listening, and have a great Tuesday. This has been Shovel News.
```

---

## File Naming Convention

```
scripts/
├── 2026-02-10/
│   ├── 01_shovel_intro.txt
│   ├── 02_nova_tech.txt
│   ├── 03_shovel_handoff_1.txt
│   ├── 04_jessica_intl.txt
│   ├── 05_shovel_handoff_2.txt
│   ├── 06_george_sports.txt
│   ├── 07_shovel_handoff_3.txt
│   ├── 08_fable_law.txt
│   ├── 09_shovel_handoff_4.txt
│   ├── 10_puck_quirky.txt
│   └── 11_shovel_outro.txt
```

Number prefixes ensure correct ordering when concatenating.
