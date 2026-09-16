#!/usr/bin/env python3
"""
SEO Content Scorer

Multi-dimensional content quality scoring for long-form articles.
Adapted from SEO Machine (TheCraigHewitt/seomachine) — stripped of
DataForSEO/WordPress dependencies, tuned for locale-configurable content.

Dimensions (equal weight, 25% each):
- Readability: Flesch score, grade level, sentence/paragraph structure
- SEO Quality: Keyword placement, density, meta elements, headings, links
- Humanity: AI phrase detection, conversational devices, contractions
- Specificity: Concrete data vs. vague words, numbers, currency amounts

Usage:
    python seo_scorer.py <article.md> [--keyword "primary keyword"]
    python seo_scorer.py <page.html> [--keyword "primary keyword"]  # auto-detects HTML
    python seo_scorer.py <article.md> --json  # machine-readable output
"""

import argparse
import os
import re
import sys
import json
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional, Any
from html.parser import HTMLParser
from urllib.parse import urlparse

try:
    import textstat
except ImportError:
    print("ERROR: textstat not installed. Run: pip install textstat")
    sys.exit(1)


# ─── LOCALE CONFIG (env-driven, empty by default) ─────────────────────

LOCAL_CURRENCY = os.environ.get("LOCAL_CURRENCY", "")
LOCAL_AUTHORITIES = [a.strip() for a in os.environ.get("LOCAL_AUTHORITIES", "").split(",") if a.strip()]
SCORE_THRESHOLD = float(os.environ.get("SCORE_THRESHOLD", "70"))
LINKING_MAP = os.environ.get("LINKING_MAP", "")


@lru_cache(maxsize=1)
def linked_hosts() -> frozenset:
    """Hosts named in the LINKING_MAP file. Links to these count as internal.

    LINKING_MAP is a path. A missing file raises FileNotFoundError naming it.
    """
    if not LINKING_MAP:
        return frozenset()
    text = Path(LINKING_MAP).read_text(encoding="utf-8")
    return frozenset(h.lower().removeprefix("www.")
                     for h in re.findall(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))


def is_internal_url(url: str) -> bool:
    """True when an absolute URL points at a host listed in LINKING_MAP."""
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return bool(host) and host in linked_hosts()


def local_patterns() -> List[str]:
    """Regexes for the configured locale. Empty when nothing is configured."""
    pats = []
    if LOCAL_CURRENCY:
        cur = re.escape(LOCAL_CURRENCY)
        pats.append(rf"(?<!\w){cur}\s*[\d,]+\b|\b[\d,]+\s*{cur}(?!\w)")
    if LOCAL_AUTHORITIES:
        pats.append(r"\b(?:" + "|".join(re.escape(a) for a in LOCAL_AUTHORITIES) + r")\b")
    return pats


# ─── HTML DETECTION & PARSING ─────────────────────────────────────────

def is_html(content: str) -> bool:
    """Detect if content is HTML (vs markdown)."""
    return bool(re.search(r'<(!DOCTYPE|html|head|body)\b', content[:500], re.IGNORECASE))


class HTMLContentExtractor(HTMLParser):
    """Extract text, meta tags, headings, and links from HTML."""

    SKIP_TAGS = {'script', 'style', 'noscript', 'svg', 'path'}

    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self.meta_title = ""
        self.meta_description = ""
        self.h1s: List[str] = []
        self.h2s: List[str] = []
        self.h3s: List[str] = []
        self.internal_links = 0
        self.external_links = 0
        self.primary_keyword = ""
        self._current_tag = ""
        self._current_heading = ""
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        attr_dict = dict(attrs)
        tag_lower = tag.lower()

        if tag_lower in self.SKIP_TAGS:
            self._skip_depth += 1
            return

        if tag_lower == 'title' and not self.meta_title:
            self._current_tag = 'title'
            self._current_heading = ""

        elif tag_lower == 'meta':
            name = attr_dict.get('name', '').lower()
            prop = attr_dict.get('property', '').lower()
            content = attr_dict.get('content', '')
            if name == 'description' or prop == 'og:description':
                if not self.meta_description:
                    self.meta_description = content
            elif name == 'keywords':
                # Extract first keyword as primary
                kws = [k.strip() for k in content.split(',') if k.strip()]
                if kws and not self.primary_keyword:
                    self.primary_keyword = kws[0]

        elif tag_lower in ('h1', 'h2', 'h3'):
            self._current_tag = tag_lower
            self._current_heading = ""

        elif tag_lower == 'a':
            href = attr_dict.get('href', '')
            if href.startswith(('http://', 'https://')):
                if is_internal_url(href):
                    self.internal_links += 1
                else:
                    self.external_links += 1
            elif href and not href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                self.internal_links += 1

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()

        if tag_lower in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return

        if tag_lower == 'title' and self._current_tag == 'title':
            self.meta_title = self._current_heading.strip()
            self._current_tag = ""
        elif tag_lower == 'h1' and self._current_tag == 'h1':
            self.h1s.append(self._current_heading.strip())
            self._current_tag = ""
        elif tag_lower == 'h2' and self._current_tag == 'h2':
            self.h2s.append(self._current_heading.strip())
            self._current_tag = ""
        elif tag_lower == 'h3' and self._current_tag == 'h3':
            self.h3s.append(self._current_heading.strip())
            self._current_tag = ""

        if tag_lower in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'tr'):
            self.text_parts.append('\n')

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        if self._current_tag in ('title', 'h1', 'h2', 'h3'):
            self._current_heading += data
        self.text_parts.append(data)

    def get_text(self) -> str:
        raw = ''.join(self.text_parts)
        # Collapse whitespace
        raw = re.sub(r'[ \t]+', ' ', raw)
        raw = re.sub(r'\n{3,}', '\n\n', raw)
        return raw.strip()


def parse_html(content: str) -> Dict[str, Any]:
    """Parse HTML and return structured content for scoring."""
    extractor = HTMLContentExtractor()
    extractor.feed(content)
    return {
        "text": extractor.get_text(),
        "meta_title": extractor.meta_title,
        "meta_description": extractor.meta_description,
        "h1s": extractor.h1s,
        "h2s": extractor.h2s,
        "h3s": extractor.h3s,
        "internal_links": extractor.internal_links,
        "external_links": extractor.external_links,
        "primary_keyword": extractor.primary_keyword,
    }


# ─── AI PHRASE DETECTION ───────────────────────────────────────────────

AI_PHRASES = [
    r'\bin today\'s (?:digital|modern|fast-paced)\b',
    r'\bwhen it comes to\b',
    r'\bit\'s important to (?:note|remember|understand)\b',
    r'\bin the world of\b',
    r'\blet\'s dive (?:in|into)\b',
    r'\bfurthermore\b',
    r'\bmoreover\b',
    r'\badditionally\b',
    r'\bin order to\b',
    r'\bdue to the fact that\b',
    r'\bat the end of the day\b',
    r'\bgoing forward\b',
    r'\bleverage\b',
    r'\butilize\b',
    r'\bsynergy\b',
    r'\bholistic\b',
    r'\brobust\b',
    r'\bseamless(?:ly)?\b',
    r'\bgame.?chang(?:er|ing)\b',
    r'\brunlock(?:ing)? (?:the )?(?:power|potential)\b',
    r'\btake (?:your|it) to the next level\b',
    r'\blandscape\b',
    r'\bparadigm\b',
    r'\bfacilitate\b',
    r'\brevolutionary\b',
    r'\bjust my two cents\b',
    r'\bfood for thought\b',
    r'\blet that sink in\b',
    r'\bread that again\b',
    r'\bhere\'s the thing\b',
]

VAGUE_WORDS = [
    r'\bmany\b', r'\bsome\b', r'\bvarious\b', r'\bnumerous\b',
    r'\bseveral\b', r'\boften\b', r'\bsometimes\b', r'\busually\b',
    r'\bgenerally\b', r'\btypically\b', r'\bsignificant(?:ly)?\b',
    r'\bsubstantial(?:ly)?\b', r'\bconsiderable\b',
    r'\bvery\b', r'\breally\b', r'\bquite\b', r'\brather\b',
    r'\brelatively\b', r'\brecently\b',
]

SPECIFICITY_PATTERNS = [
    r'\b\d{1,3}%\b',                    # Percentages
    r'\b\d{4}\b',                        # Years
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',
    r'\b\d+(?:,\d{3})*\s*(?:customers?|users?|subscribers?|visitors?)\b',
    r'\"[^\"]{10,}\"',                   # Quoted text
]

CONVERSATIONAL_PATTERNS = [
    r'\([^)]{5,50}\)',      # Parenthetical asides
    r'\?(?:\s|$)',          # Questions
    r'\bdon\'t\b', r'\bcan\'t\b', r'\bwon\'t\b',
    r'\byou\'re\b', r'\byou\'ve\b', r'\bit\'s\b',
    r'\bthat\'s\b', r'\bhere\'s\b', r'\bwe\'re\b',
]


# ─── CLEAN CONTENT ─────────────────────────────────────────────────────

def clean_content(content: str) -> str:
    """Remove markdown formatting for text analysis."""
    text = content
    text = re.sub(r'^\*\*[^*]+\*\*:\s*.+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'```[^`]*```', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    return text.strip()


# ─── DIMENSION 1: READABILITY ──────────────────────────────────────────

def score_readability(content: str) -> Dict[str, Any]:
    """Score readability: Flesch, grade level, sentence/paragraph structure."""
    clean = clean_content(content)
    issues = []

    flesch = round(textstat.flesch_reading_ease(clean), 1)
    grade = round(textstat.flesch_kincaid_grade(clean), 1)

    # Sentence analysis
    sentences = [s.strip() for s in re.split(r'[.!?]+', clean) if s.strip()]
    lengths = [len(s.split()) for s in sentences]
    avg_sentence = sum(lengths) / len(lengths) if lengths else 0
    long_sentences = len([l for l in lengths if l > 25])
    very_long = len([l for l in lengths if l > 35])

    # Paragraph analysis
    paragraphs = [p for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
    long_paragraphs = 0
    for para in paragraphs:
        para_sentences = [s.strip() for s in re.split(r'[.!?]+', para) if s.strip() and len(s.strip()) > 10]
        if len(para_sentences) > 4:
            long_paragraphs += 1

    # Sentence rhythm (variety)
    if len(lengths) >= 10:
        mean_len = sum(lengths) / len(lengths)
        std_dev = (sum((l - mean_len)**2 for l in lengths) / len(lengths)) ** 0.5
    else:
        std_dev = 8  # default OK

    # Calculate score
    score = 100

    if flesch < 50:
        score -= min(25, (50 - flesch) * 1.5)
        issues.append({"issue": f"Content too difficult (Flesch: {flesch})", "fix": "Simplify sentences, use shorter words", "severity": "high"})
    elif flesch < 60:
        score -= 10
        issues.append({"issue": f"Content slightly difficult (Flesch: {flesch})", "fix": "Simplify some complex sentences", "severity": "medium"})

    if grade > 12:
        score -= 10
        issues.append({"issue": f"Grade level too high ({grade})", "fix": "Target 8th-10th grade", "severity": "medium"})

    if avg_sentence > 25:
        score -= 15
        issues.append({"issue": f"Avg sentence length too high ({avg_sentence:.0f} words)", "fix": "Break up long sentences (target <20)", "severity": "high"})
    elif avg_sentence > 20:
        score -= 5

    if very_long > 0:
        score -= min(10, very_long * 3)

    if long_paragraphs > 0:
        score -= min(10, long_paragraphs * 3)
        issues.append({"issue": f"{long_paragraphs} paragraphs exceed 4 sentences", "fix": "Break long paragraphs into 2-4 sentence chunks", "severity": "medium"})

    if std_dev < 5:
        score -= 10
        issues.append({"issue": "Monotonous sentence rhythm", "fix": "Mix short punchy (5-10 words) with longer flowing (15-25 words)", "severity": "medium"})

    return {
        "score": max(0, min(100, round(score))),
        "issues": issues,
        "details": {
            "flesch_reading_ease": flesch,
            "grade_level": grade,
            "avg_sentence_length": round(avg_sentence, 1),
            "long_sentences_25plus": long_sentences,
            "very_long_35plus": very_long,
            "long_paragraphs": long_paragraphs,
            "sentence_rhythm_stddev": round(std_dev, 1),
        }
    }


# ─── DIMENSION 2: SEO QUALITY ─────────────────────────────────────────

def score_seo(content: str, primary_keyword: Optional[str] = None, html_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Score SEO: keyword placement, density, meta, headings, links.

    If html_data is provided (from parse_html()), use pre-extracted meta tags,
    headings, and links instead of parsing markdown patterns.
    """
    issues = []
    clean = clean_content(content) if not html_data else html_data["text"]
    word_count = len(clean.split())

    if html_data:
        # Use pre-extracted HTML data
        meta_title = html_data["meta_title"]
        meta_desc = html_data["meta_description"]
        h1_matches = html_data["h1s"]
        h2_matches = html_data["h2s"]
        internal_links = html_data["internal_links"]
        external_links = html_data["external_links"]
        if not primary_keyword and html_data["primary_keyword"]:
            primary_keyword = html_data["primary_keyword"]
    else:
        # Markdown fallback: extract meta elements from content
        meta_title = ""
        meta_desc = ""
        mt = re.search(r'Meta Title:\s*(.+)', content)
        if mt:
            meta_title = mt.group(1).strip()
        md = re.search(r'Meta Description:\s*(.+)', content)
        if md:
            meta_desc = md.group(1).strip()

        # Extract keyword from content if not provided
        if not primary_keyword:
            kw = re.search(r'(?:Primary )?Keyword:\s*(.+)', content)
            if kw:
                primary_keyword = kw.group(1).strip()

        # Heading analysis
        h1_matches = re.findall(r'^#\s+(.+)$', content, re.MULTILINE)
        h2_matches = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)

        # Link analysis
        internal_links = len(re.findall(r'\[([^\]]+)\]\((?!http)', content))
        absolute = re.findall(r'\[[^\]]+\]\((https?://[^)\s]+)', content)
        internal_links += sum(1 for u in absolute if is_internal_url(u))
        external_links = sum(1 for u in absolute if not is_internal_url(u))

    score = 100

    # Word count
    if word_count < 1500:
        score -= 20
        issues.append({"issue": f"Content too short ({word_count} words)", "fix": "Expand to at least 1,500 words", "severity": "high"})
    elif word_count < 2000:
        score -= 5

    # H1
    if not h1_matches:
        score -= 15
        issues.append({"issue": "Missing H1 heading", "fix": "Add H1 with primary keyword", "severity": "high"})
    elif len(h1_matches) > 1:
        score -= 10
        issues.append({"issue": f"Multiple H1 headings ({len(h1_matches)})", "fix": "Use only one H1", "severity": "medium"})

    # H2 count
    if len(h2_matches) < 4:
        score -= 10
        issues.append({"issue": f"Too few H2 sections ({len(h2_matches)})", "fix": "Add more H2 sections (target 4-7)", "severity": "medium"})

    # Keyword checks
    if primary_keyword:
        kw_lower = primary_keyword.lower()

        # In H1
        if h1_matches and kw_lower not in h1_matches[0].lower():
            score -= 10
            issues.append({"issue": f"Keyword '{primary_keyword}' not in H1", "fix": "Include keyword in H1 headline", "severity": "high"})

        # In first 100 words
        first_100 = ' '.join(clean.split()[:100]).lower()
        if kw_lower not in first_100:
            score -= 10
            issues.append({"issue": "Keyword not in first 100 words", "fix": "Include keyword in introduction", "severity": "high"})

        # Density
        kw_count = clean.lower().count(kw_lower)
        density = (kw_count / max(word_count, 1)) * 100
        if density < 0.8:
            score -= 10
            issues.append({"issue": f"Keyword density too low ({density:.1f}%)", "fix": "Add more natural keyword mentions (target 1-2%)", "severity": "medium"})
        elif density > 2.5:
            score -= 15
            issues.append({"issue": f"Keyword density too high ({density:.1f}%)", "fix": "Reduce keyword mentions to avoid stuffing", "severity": "high"})

        # In H2s
        h2_with_kw = sum(1 for h in h2_matches if kw_lower in h.lower())
        if len(h2_matches) > 0 and h2_with_kw < 2:
            score -= 5
            issues.append({"issue": f"Keyword in only {h2_with_kw}/{len(h2_matches)} H2 headings", "fix": "Include keyword in 2-3 H2 headings", "severity": "low"})

    # Meta title — Google truncates at ~60 chars
    mt_len = len(meta_title)
    if not meta_title:
        score -= 15
        issues.append({"issue": "Missing meta title", "fix": "Add meta title (50-60 chars)", "severity": "high"})
    elif mt_len > 60:
        over = mt_len - 60
        penalty = min(15, 5 + over // 5)  # escalates: 5 at 61, 10 at 85, 15 at 100+
        score -= penalty
        issues.append({"issue": f"Meta title too long ({mt_len} chars, Google truncates at ~60)", "fix": f"Trim by {over} chars — cut to 50-60 chars", "severity": "high" if mt_len > 80 else "medium"})
    elif mt_len < 30:
        score -= 5
        issues.append({"issue": f"Meta title too short ({mt_len} chars)", "fix": "Expand to 50-60 chars for maximum SERP real estate", "severity": "medium"})

    # Meta description — Google truncates at ~160 chars
    md_len = len(meta_desc)
    if not meta_desc:
        score -= 15
        issues.append({"issue": "Missing meta description", "fix": "Add meta description (140-160 chars)", "severity": "high"})
    elif md_len > 160:
        over = md_len - 160
        penalty = min(15, 5 + over // 10)  # escalates: 5 at 161, 10 at 210, 15 at 260+
        score -= penalty
        issues.append({"issue": f"Meta description too long ({md_len} chars, Google truncates at ~160)", "fix": f"Trim by {over} chars — target 140-160 chars", "severity": "high" if md_len > 200 else "medium"})
    elif md_len < 120:
        score -= 5
        issues.append({"issue": f"Meta description too short ({md_len} chars)", "fix": "Expand to 140-160 chars for maximum SERP visibility", "severity": "medium"})

    # Links — internal linking is only expected when a LINKING_MAP is configured
    if LINKING_MAP and internal_links < 2:
        score -= 10
        issues.append({"issue": f"Too few internal links ({internal_links})", "fix": "Add 2-3 internal links to related pages/projects", "severity": "medium"})
    if external_links < 2:
        score -= 5
        issues.append({"issue": f"Too few external links ({external_links})", "fix": "Add 2-3 authority links", "severity": "low"})

    return {
        "score": max(0, min(100, round(score))),
        "issues": issues,
        "details": {
            "word_count": word_count,
            "h1_count": len(h1_matches),
            "h2_count": len(h2_matches),
            "internal_links": internal_links,
            "external_links": external_links,
            "meta_title_length": len(meta_title),
            "meta_description_length": len(meta_desc),
        }
    }


# ─── DIMENSION 3: HUMANITY ────────────────────────────────────────────

def score_humanity(content: str) -> Dict[str, Any]:
    """Score for human voice: AI phrases, conversational devices, contractions."""
    clean = clean_content(content)
    content_lower = clean.lower()
    word_count = len(clean.split())
    issues = []

    # AI phrases
    ai_count = 0
    ai_found = []
    for pattern in AI_PHRASES:
        matches = re.findall(pattern, content_lower)
        ai_count += len(matches)
        if matches:
            ai_found.extend(matches[:2])
    ai_per_1000 = (ai_count / max(word_count, 1)) * 1000

    # Conversational devices
    conv_count = sum(len(re.findall(p, clean, re.IGNORECASE)) for p in CONVERSATIONAL_PATTERNS)
    conv_per_1000 = (conv_count / max(word_count, 1)) * 1000

    # Contractions
    contractions = len(re.findall(r"'(?:t|s|re|ve|ll|d|m)\b", clean))
    contraction_per_100 = (contractions / max(word_count, 1)) * 100

    # Passive voice (simplified)
    passive = len(re.findall(r'\b(?:is|are|was|were|been|being)\s+\w+ed\b', content_lower))
    passive_ratio = passive / max(word_count / 100, 1)

    score = 100

    if ai_per_1000 > 5:
        penalty = min(30, (ai_per_1000 - 5) * 3)
        score -= penalty
        issues.append({"issue": f"AI phrases detected ({ai_count} instances)", "fix": f"Remove/rephrase: {', '.join(list(set(ai_found))[:3])}", "severity": "high" if ai_per_1000 > 10 else "medium"})

    if passive_ratio > 2:
        score -= min(15, (passive_ratio - 2) * 5)
        issues.append({"issue": "High passive voice usage", "fix": "Convert to active voice", "severity": "medium"})

    if conv_per_1000 > 3:
        score = min(100, score + min(15, (conv_per_1000 - 3) * 2))

    if contraction_per_100 < 1:
        score -= 10
        issues.append({"issue": "Lacks contractions (sounds formal/robotic)", "fix": "Use contractions: don't, can't, you're, it's", "severity": "low"})

    return {
        "score": max(0, min(100, round(score))),
        "issues": issues,
        "details": {
            "ai_phrases_per_1000": round(ai_per_1000, 1),
            "ai_phrases_found": list(set(ai_found))[:5],
            "conversational_per_1000": round(conv_per_1000, 1),
            "contractions_per_100": round(contraction_per_100, 1),
            "passive_voice_ratio": round(passive_ratio, 2),
        }
    }


# ─── DIMENSION 4: SPECIFICITY ─────────────────────────────────────────

def score_specificity(content: str) -> Dict[str, Any]:
    """Score for concrete data vs. vague generalizations."""
    clean = clean_content(content)
    content_lower = clean.lower()
    word_count = len(clean.split())
    issues = []

    # Vague words
    vague_count = sum(len(re.findall(p, content_lower)) for p in VAGUE_WORDS)
    vague_per_1000 = (vague_count / max(word_count, 1)) * 1000

    # Specificity indicators
    patterns = SPECIFICITY_PATTERNS + local_patterns()
    specific_count = sum(len(re.findall(p, clean)) for p in patterns)
    specific_per_1000 = (specific_count / max(word_count, 1)) * 1000

    # Numbers
    numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', clean)
    number_per_1000 = (len(numbers) / max(word_count, 1)) * 1000

    # Local specificity (bonus) — skipped entirely when no locale is configured
    local_pats = local_patterns()
    local_refs = sum(len(re.findall(p, clean, re.IGNORECASE)) for p in local_pats)

    score = 70  # baseline

    if vague_per_1000 > 15:
        penalty = min(25, (vague_per_1000 - 15) * 1.5)
        score -= penalty
        issues.append({"issue": f"Too many vague words ({vague_count} instances)", "fix": "Replace 'many', 'significant', 'often' with exact numbers", "severity": "high" if vague_per_1000 > 25 else "medium"})

    if specific_per_1000 > 2:
        score += min(30, specific_per_1000 * 5)

    if number_per_1000 < 3:
        score -= min(15, (3 - number_per_1000) * 5)
        issues.append({"issue": "Lacks specific numbers/data", "fix": "Add percentages, currency amounts, dates, or counts", "severity": "medium"})

    # Local bonus — no penalty when LOCAL_CURRENCY/LOCAL_AUTHORITIES are unset
    if local_pats:
        if local_refs >= 5:
            score = min(100, score + 5)
        elif local_refs == 0:
            score -= 10
            issues.append({"issue": "No local references", "fix": "Add local data points, regulations, or context", "severity": "high"})

    return {
        "score": max(0, min(100, round(score))),
        "issues": issues,
        "details": {
            "vague_words_per_1000": round(vague_per_1000, 1),
            "specifics_per_1000": round(specific_per_1000, 1),
            "numbers_per_1000": round(number_per_1000, 1),
            "local_references": local_refs,
        }
    }


# ─── COMPOSITE SCORER ─────────────────────────────────────────────────

def score_content(content: str, primary_keyword: Optional[str] = None) -> Dict[str, Any]:
    """Run all 4 dimensions and produce composite score.

    Automatically detects HTML vs markdown. For HTML files, extracts meta tags,
    headings, and links from the DOM — giving accurate SEO dimension scores.
    """
    html_data = None
    scoring_content = content

    if is_html(content):
        html_data = parse_html(content)
        scoring_content = html_data["text"]  # stripped text for readability/humanity/specificity
        if not primary_keyword and html_data["primary_keyword"]:
            primary_keyword = html_data["primary_keyword"]

    readability = score_readability(scoring_content)
    seo = score_seo(content, primary_keyword, html_data)
    humanity = score_humanity(scoring_content)
    specificity = score_specificity(scoring_content)

    composite = (
        readability["score"] * 0.25 +
        seo["score"] * 0.25 +
        humanity["score"] * 0.25 +
        specificity["score"] * 0.25
    )
    composite = round(composite, 1)

    # Collect all issues and prioritize by impact
    all_issues = []
    for dim_name, dim_data in [("readability", readability), ("seo", seo), ("humanity", humanity), ("specificity", specificity)]:
        for issue in dim_data["issues"]:
            issue["dimension"] = dim_name
            deficit = 100 - dim_data["score"]
            issue["impact"] = 0.25 * deficit
            all_issues.append(issue)

    priority_fixes = sorted(all_issues, key=lambda x: -x["impact"])[:5]

    return {
        "composite_score": composite,
        "passed": composite >= SCORE_THRESHOLD,
        "threshold": SCORE_THRESHOLD,
        "format": "html" if html_data else "markdown",
        "dimensions": {
            "readability": readability,
            "seo": seo,
            "humanity": humanity,
            "specificity": specificity,
        },
        "priority_fixes": priority_fixes,
    }


# ─── CLI ───────────────────────────────────────────────────────────────

def format_report(result: Dict[str, Any]) -> str:
    """Format as human-readable report."""
    lines = []
    lines.append("=" * 55)
    lines.append("  SEO CONTENT SCORE")
    lines.append("=" * 55)
    lines.append("")

    status = "PASSED" if result["passed"] else "BELOW THRESHOLD"
    fmt = result.get("format", "markdown")
    lines.append(f"  Composite Score: {result['composite_score']}/100  [{status}]")
    lines.append(f"  Threshold: {result['threshold']:g}  |  Format: {fmt}")
    lines.append("")
    lines.append("-" * 55)
    lines.append("  DIMENSION BREAKDOWN")
    lines.append("-" * 55)

    for dim_name, dim_data in result["dimensions"].items():
        s = dim_data["score"]
        bar = "█" * (s // 5) + "░" * (20 - s // 5)
        check = "OK" if s >= 70 else "FIX"
        lines.append(f"  {dim_name:15} {bar} {s:3}/100 [{check}]")

    lines.append("")

    if result["priority_fixes"]:
        lines.append("-" * 55)
        lines.append("  TOP PRIORITY FIXES")
        lines.append("-" * 55)
        for i, fix in enumerate(result["priority_fixes"], 1):
            sev = fix.get("severity", "medium").upper()
            lines.append(f"  {i}. [{fix['dimension']}] {fix['issue']}")
            lines.append(f"     Fix: {fix['fix']}  ({sev})")
            lines.append("")

    lines.append("=" * 55)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score a markdown or HTML article on readability, SEO, humanity, and specificity.",
        epilog="Env config: SCORE_THRESHOLD (default 70), LOCAL_CURRENCY, LOCAL_AUTHORITIES (comma-separated), LINKING_MAP.",
    )
    parser.add_argument("file", help="path to the article (.md or .html)")
    parser.add_argument("--keyword", help="primary keyword to score against")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    try:
        content = Path(args.file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Error: cannot read {args.file}: {exc}")
        sys.exit(1)

    result = score_content(content, args.keyword)
    print(json.dumps(result, indent=2) if args.json else format_report(result))


if __name__ == "__main__":
    main()
