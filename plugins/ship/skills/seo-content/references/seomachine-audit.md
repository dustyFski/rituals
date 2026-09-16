# SEO Machine Audit — What We Took, What We Left

> Source: github.com/TheCraigHewitt/seomachine (478 commits, MIT license)
> Purpose: Cherry-pick what moves the needle for a small, no-code-first content operation; skip what doesn't

---

## Architecture Summary

SEO Machine is a Claude Code workspace with:
- 10 agents (content analysis, SEO optimization, editing, CRO, headlines, meta, internal linking, keyword mapping, performance, landing page)
- 12 commands (research, write, optimize, publish, landing-audit, etc.)
- 26 marketing skills (copywriting, pricing strategy, email sequences, A/B testing, etc.)
- 30+ Python modules (readability, keyword analysis, SEO quality, WordPress publisher, DataForSEO, Google Analytics, etc.)
- Outputs to WordPress via REST API + Yoast SEO metadata

---

## What We Took (Adapted)

### Python Scoring Modules → `seo_scorer.py`

**Source files:**
- `readability_scorer.py` — Flesch scores, grade level, sentence/paragraph analysis
- `seo_quality_rater.py` — keyword placement, density, meta elements, heading structure, links
- `content_scorer.py` — multi-dimensional composite scoring (humanity, specificity, structure balance, SEO, readability)
- `keyword_analyzer.py` — keyword density, distribution, stuffing detection, LSI keywords

**What we adapted:**
- Merged all 4 scorers into a single `seo_scorer.py` (~700 lines, no external API dependencies)
- Replaced the 5-dimension model (humanity 30%, specificity 25%, structure 20%, SEO 15%, readability 10%) with an equal-weight 4-dimension model (25% each) — readability and SEO matter as much as voice quality for this use case
- Added domain-specific scoring hooks: currency-amount detection and configurable local-authority acronyms as specificity boosters
- Removed: scikit-learn dependency (topic clustering), numpy dependency — not worth the install cost for most use cases
- Removed: DataForSEO integration, WordPress publisher, Google Analytics/Search Console modules

### Content Quality Loop → Phase 4 of SKILL.md

**Source:** Write command's "Automatic Quality Loop" (score → fix → re-score → route)

**What we adapted:**
- Same concept: score article, fix top issues, re-score
- Threshold: `SCORE_THRESHOLD`, default 70 composite (same as SEO Machine)
- Output: human-readable report + JSON for machine parsing
- Removed: automatic file routing to a `review-required/` folder (use whatever path convention your project already has)

### Research Brief Structure → Phase 1 of SKILL.md

**Source:** Research command workflow

**What we adapted:**
- Same output structure: keyword + competition + outline + linking strategy
- Added: a mandatory domain-specific angle section
- Added: an optional cross-site internal linking map (`LINKING_MAP`), for anyone running more than one site
- Removed: DataForSEO SERP API calls (uses web search instead)

### Writing Workflow → Phase 2 of SKILL.md

**Source:** Write command + Editor agent

**What we adapted:**
- Hook types (provocative question, specific scenario, surprising statistic, bold statement, counterintuitive claim)
- Content structure (H1 → intro → body with H2/H3 → conclusion → meta)
- Engagement requirements (no generic openings, sentence rhythm, paragraph limits)
- Added: configurable voice rules, domain-specific requirements, legal safety language, information-only framing for regulated topics
- Removed: Mini-stories requirement (good for generic SaaS blogs, not for calculator/tool content)
- Removed: CTA distribution (assumes tool-specific CTAs, not SaaS trial funnels)
- Removed: content scrubbing/watermark removal (that belongs in a separate humanizing pass, if you run one)

---

## What We Left Behind

### Agents We Skipped

| Agent | Why Skipped |
|-------|-------------|
| **CRO Analyst** | Needs real traffic data — revisit once you have volume |
| **Performance Agent** | Requires Google Analytics + Search Console APIs — add when you have real traffic |
| **Landing Page Optimizer** | Relevant later, but premature for simple static landing pages |
| **Headline Generator** | H1s come from keyword research here, not A/B headline generation |
| **Internal Linker** | Replaced with a static, config-driven linking map (simpler, portfolio-aware) |

### Skills We Skipped

| Skill | Why Skipped |
|-------|-------------|
| **Paid Ads** | Out of scope for a no-ad-spend content operation |
| **Pricing Strategy** | Out of scope. A project's business model, free tool or paid tiers, is not something a content scorer can optimize |
| **A/B Test Setup** | Out of scope for a content scorer; revisit if you run split tests |
| **Onboarding CRO** | Out of scope — onboarding is a product concern, not a content one |
| **Referral Program** | Out of scope — growth loops are a separate pipeline concern |
| **Analytics Tracking** | Google Analytics setup is separate from content creation |
| **Social Content** | Out of scope — social distribution is a separate pipeline concern |
| **Programmatic SEO** | Interesting but premature. Revisit when you have data-driven page templates |

### Python Modules We Skipped

| Module | Why Skipped |
|--------|-------------|
| `wordpress_publisher.py` | Not tied to WordPress |
| `dataforseo.py` | API cost, not needed at this scale |
| `google_analytics.py` | No GA data yet |
| `google_search_console.py` | No GSC data yet |
| `landing_page_scorer.py` | Premature |
| `landing_performance.py` | Premature |
| `competitor_gap_analyzer.py` | Uses DataForSEO — done via web search instead |
| `social_research_aggregator.py` | Out of scope for this skill |
| `cro_checker.py` | Premature |
| `above_fold_analyzer.py` | Premature |
| `section_writer.py` | Writes full articles, not section-by-section |

---

## What to Revisit Later

1. **Programmatic SEO skill** — when a project has structured data, use programmatic templates to generate pages at scale
2. **Performance Agent** — once you have 3+ months of GSC data, add GA4/GSC integration for content performance analysis
3. **CRO skills** — once any project has meaningful monthly traffic, add conversion optimization
4. **Schema Markup skill** — the SEO Machine `schema-markup` skill is solid. Add when you deploy structured data beyond basic Article schema
5. **Topic clustering** — the keyword_analyzer's scikit-learn clustering is overkill early on but useful once you have 50+ articles and need to manage content cannibalization

---

## Key Architectural Decisions

1. **Single scorer, not 4 separate modules.** SEO Machine splits scoring across 4 files + a composite. Merged into one file. Easier to maintain, easier to run.
2. **No external API dependencies.** Everything runs locally with just `textstat`. No DataForSEO, no Google APIs, no WordPress. Keeps it free and fast.
3. **Equal dimension weights (25% each).** SEO Machine weighted humanity at 30% and readability at 10%. Equalized because SEO and readability matter as much as voice quality for most projects using this.
4. **Domain-specific scoring is configurable, not baked in.** SEO Machine has none of this at all. This version adds currency-amount detection and configurable local-authority acronym lists as specificity boosters.
5. **Portfolio-aware linking, when you want it.** SEO Machine links within one site. This version can link across multiple sites via `LINKING_MAP`, but works fine single-site with it unset.
