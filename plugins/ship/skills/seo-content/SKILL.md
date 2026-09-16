---
name: seo-content
description: "Research, write, optimize, and score long-form SEO articles through a 4-phase pipeline (Research, Write, Optimize, Score). Use it even when only one phase is needed. Fires on SEO article, blog post, write an article/post for a product, long-form content, content pipeline, keyword research, or 'optimize/score this article'."
---

**What it does:** Runs a 4-phase content pipeline (Research, Write, Optimize, Score) that produces long-form SEO articles and scores them against a composite quality bar before publish.

**When it fires:** SEO article, blog post, write an article/post/content for a product, long-form content, content pipeline, "research a topic for [product]", "optimize/score this article", "keyword research for [topic]".

**Config:** (set in your project's config file, e.g. `.claude/config.md` or env vars — see README)
- `CONTENT_ROOT` — base path for articles/briefs/scores (default: `content/seo-articles/`)
- `VOICE_FILE` — path to your brand voice/tone doc (default: none — skip voice-matching if unset)
- `BRAND_GUIDE` — path to a project-specific brand/style guide (default: none)
- `LINKING_MAP` — path to a cross-project internal-linking map, if you run more than one site (default: none — skip cross-site linking, and the scorer applies no internal-link penalty)
- `SCORE_THRESHOLD` — composite score needed to pass Phase 4 (default: 70). The scorer reads it from the environment and uses it for the pass flag and the report.
- `LOCAL_CURRENCY` — currency symbol or code the scorer counts as a specificity signal, e.g. `USD` (default: empty — the local check is skipped)
- `LOCAL_AUTHORITIES` — comma-separated regulator or standards-body names the scorer counts as local specificity (default: empty — the local check is skipped)

`VOICE_FILE` and `BRAND_GUIDE` steer the writing phases. The scorer does not read them.

---

# SEO Content Pipeline

A 4-phase content creation pipeline: Research, Write, Optimize, Score. Produces long-form, SEO-optimized articles that rank while keeping a consistent brand voice.

**Architecture borrowed from:** SEO Machine (TheCraigHewitt/seomachine), adapted to remove WordPress/DataForSEO dependencies and run with no external APIs beyond web search.

---

## When This Skill Triggers

Any request involving SEO content creation, optimization, or scoring. This includes:

- Writing blog posts or articles
- SEO research for a topic or keyword
- Optimizing existing content for search
- Scoring content quality before publishing
- Content strategy for a specific niche's SEO articles

---

## Phase 1: RESEARCH

### What to Read First
- The project's own context file (positioning, audience, product context)
- `VOICE_FILE`, if configured (for tone)
- `BRAND_GUIDE`, if configured (for design/copy philosophy)

### Research Process

1. **Keyword Research**
   - Identify primary keyword (what the article targets)
   - Find 3-5 secondary keywords and long-tail variations
   - Determine search intent: informational, commercial, transactional
   - Web-search validate: actual SERP landscape, who ranks, what they cover

2. **Competitive Analysis**
   - Analyze top 5 ranking articles for the target keyword
   - Note: word count ranges, common sections, content gaps
   - Identify what's *missing* — that's your angle

3. **Niche Angle**
   - Every article should have a concrete, specific angle relevant to its audience
   - Reference real local/domain data where it applies (regulator names, standards bodies, official sources)
   - Use the audience's native currency/units (convert if needed)
   - Apply a "real user test": would someone in the target audience actually find this useful?

4. **Output: Research Brief**
   Save to `<CONTENT_ROOT>/research/brief-[slug]-[YYYY-MM-DD].md`

   Contents:
   - Primary keyword + volume estimate + difficulty assessment
   - Secondary keywords
   - Top 3 competitor articles (URL + key takeaways)
   - Content gaps (what competitors miss)
   - Recommended outline (H1 + H2 sections)
   - Domain-specific data points to include
   - Target word count (based on competition)
   - Internal linking opportunities (from `LINKING_MAP`, if configured)

---

## Phase 2: WRITE

### Pre-Writing Checklist
- Read the research brief from Phase 1
- Read `VOICE_FILE` and `BRAND_GUIDE`, if configured
- Read a founder/author profile doc if the article needs a personal perspective

### Content Structure

**H1:** Includes primary keyword. Compelling. Under 60 characters.

**Introduction (150-200 words):**
- Hook: Use ONE of these types — provocative question, specific scenario, surprising statistic, bold statement, counterintuitive claim
- NEVER open with "In today's..." or "When it comes to..." or any generic definition
- Include primary keyword in first 100 words
- Promise clear value

**Body (target word count from research brief, minimum 1,500 words):**
- 4-7 H2 sections, logical progression
- Primary keyword at 1-2% density, natural placement
- 2-3 H2 headings include keyword variations
- Domain-specific data and examples throughout
- 2-3 internal links (via `LINKING_MAP`, if configured)
- 2-3 external links to authoritative sources (government sites, industry reports)
- Information-only language where the topic touches regulated advice: avoid "you should" or "we recommend"
- Disclaimers on any content touching legal, tax, or financial topics

**Conclusion (100-150 words):**
- Summarize key takeaways (not a rehash — add new value)
- Clear next action for the reader
- End with energy, not a whimper

**Meta Elements:**
```
Meta Title: [50-60 characters, includes primary keyword]
Meta Description: [150-160 characters, includes keyword + clear value prop]
Primary Keyword: [keyword]
Secondary Keywords: [list]
URL Slug: /[optimized-slug]
```

### Writing Rules

1. **Voice:** Match whatever `VOICE_FILE` specifies. Default: clear, direct, warm — not fluffy.
2. **Never use:** "game-changing," "revolutionary," "synergy," "paradigm shift," "just my two cents"
3. **Information tools only:** where the topic is regulated (legal/tax/financial), reframe advisory language as data/information.
4. **Legal safety:** Flag any content that could be interpreted as advice. Add disclaimers.
5. **Sentence variety:** Mix short (5-10 words) with medium (15-20 words). Avoid uniformity.
6. **Specificity over vagueness:** Use exact numbers, dates, amounts, percentages. Never "many" or "significant" without data.

### File Output
Save article to: `<CONTENT_ROOT>/[slug]-[YYYY-MM-DD].md`

---

## Phase 3: OPTIMIZE

Run the SEO optimization pass on the completed article.

### Optimization Checklist

**Keyword Placement:**
- [ ] Primary keyword in H1
- [ ] Primary keyword in first 100 words
- [ ] Primary keyword in 2+ H2 headings
- [ ] Keyword density 1-2% (not higher — avoid stuffing)
- [ ] Secondary keywords present naturally
- [ ] Keyword in meta title and meta description

**Structure:**
- [ ] Single H1
- [ ] 4-7 H2 sections
- [ ] Proper H2→H3 nesting (no skipped levels)
- [ ] Paragraphs max 4 sentences
- [ ] Lists used for scannability where appropriate

**Links:**
- [ ] 2-3+ internal links (via `LINKING_MAP`, if configured — the scorer only penalises missing internal links when `LINKING_MAP` is set)
- [ ] 2-3 external authority links (government, industry)
- [ ] Anchor text is descriptive, not "click here"

**Meta Elements:**
- [ ] Meta title 50-60 characters with keyword
- [ ] Meta description 150-160 characters with keyword + CTA
- [ ] URL slug is clean, short, includes keyword

**Readability:**
- [ ] Average sentence length <20 words
- [ ] Reading level 8th-10th grade
- [ ] Active voice predominantly
- [ ] No paragraphs >4 sentences
- [ ] Sentence rhythm varies (mix short and long)

**Compliance:**
- [ ] No advisory language ("you should", "we recommend") on regulated topics
- [ ] Disclaimers present on legal/tax/financial content
- [ ] Domain-specific angle present
- [ ] Correct currency/units used (set `LOCAL_CURRENCY` and `LOCAL_AUTHORITIES` if you want the scorer to check this)
- [ ] Real-user test: useful to the target audience? YES/NO

---

## Phase 4: SCORE

Run the Python scoring module on the final content. This is the verification gate.

### How to Score

Install the one dependency first, and let any error show:

```bash
pip install textstat
```

Run the scorer by its installed path, inside this skill's own directory — not a `scripts/`
folder in the project being written about:

```bash
python3 <path-to-this-skill>/scripts/seo_scorer.py "[path-to-article.md]" --keyword "primary keyword"
```

`--help` lists the flags. `--json` gives machine-readable output.

### Score Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Readability | 25% | Flesch score (target 60-70), grade level (8-10), sentence length, paragraph length |
| SEO Quality | 25% | Keyword placement, density, meta elements, heading structure, links |
| Humanity | 25% | AI phrase detection, conversational devices, contractions, passive voice |
| Specificity | 25% | Concrete numbers vs. vague words, data points, percentages, currency amounts |

### Pass Threshold

One threshold governs everything: `SCORE_THRESHOLD` (default 70). The scorer reads it from the
environment, sets `passed` against it, and prints it in the report.

- **Composite ≥ `SCORE_THRESHOLD`:** publish-ready
- **Within 10 points below it:** minor fixes — address the top 3 priority fixes, then re-score
- **More than 10 points below it:** major revision — re-enter Phase 2 with the scoring feedback

### Score Output
The scorer produces:
- Composite score (0-100)
- Per-dimension breakdown
- Top 5 priority fixes, each with its dimension, the issue, a remedy, and a severity
- Publish-ready: YES/NO, measured against `SCORE_THRESHOLD`

Save score report to: `<CONTENT_ROOT>/scores/score-[slug]-[YYYY-MM-DD].md`

---

## Cross-Site Internal Linking

If you maintain more than one site or product and want cross-linking, set `LINKING_MAP` to a file mapping each site to related sites/tools worth linking to when natural. Without it, this skill skips cross-site linking and only uses in-article links.

---

## Quick Reference: When to Read What

| If doing... | Read these first |
|-------------|-----------------|
| Full pipeline (research → publish) | This file + project context + voice files |
| Just research | This file (Phase 1) + project context |
| Just writing | This file (Phase 2) + research brief + voice files |
| Just optimization | This file (Phase 3) + the article |
| Just scoring | This file (Phase 4) + run the script |

---

## Dependencies

- Python packages: `textstat` (install with `pip install textstat`; if the install fails, read the error rather than suppressing it)
- No external APIs required (no DataForSEO, no WordPress)
- Web search for research phase
- All scoring runs locally — no cost per score
