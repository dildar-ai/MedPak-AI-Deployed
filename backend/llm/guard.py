"""
MedPak AI — Pre-LLM Input Guard
Deterministic keyword checks that catch blatant guardrail violations BEFORE
calling the LLM (saves tokens and guarantees refusal for obvious cases).

Catches (English + Roman Urdu + Urdu):
  - Medicine SUGGESTION requests ("which medicine should I take", "konsi dawa lun")
  - DIAGNOSIS requests ("what do I have", "diagnose me", "meri bimari kya hai")
  - MEDICAL EMERGENCIES (overdose, poisoning, suicide) → emergency response
  - BLATANT OFF-TOPIC requests ("write a poem", "tell me a joke")
  - Simple GREETINGS ("hi", "salam") → friendly welcome instead of an LLM refusal

The LLM's strict system prompt handles nuanced cases these patterns miss.

Returns from check_query_guards(message):
  None                      → safe to send to LLM
  {"blocked": True, ...}    → standard refusal / emergency answer to return
"""

import re
from typing import Optional

# ── Refusal answers ───────────────────────────────────────────────────────────

SUGGESTION_REFUSAL = (
    "I can't suggest or recommend medicines — that decision must be made by a "
    "licensed doctor who knows your condition and history.\n\n"
    "I *can* give you factual information about any medicine you're already "
    "considering (uses, side effects, prices in Pakistan). Just name the medicine!\n\n"
    "مجھے دوا تجویز کرنے کی اجازت نہیں — یہ فیصلہ لائسنس یافتہ ڈاکٹر ہی کرے گا۔ "
    "اگر آپ کسی دوا کے بارے میں معلومات چاہتے ہیں تو اس کا نام بتائیں۔\n\n"
    "⚠️ Disclaimer: Always consult a licensed doctor or pharmacist before taking any medicine."
)

DIAGNOSIS_REFUSAL = (
    "I can't diagnose illnesses — I'm an information assistant, not a doctor. "
    "Please see a licensed doctor who can examine you properly.\n\n"
    "I *can* answer questions about specific medicines you've been prescribed "
    "or are considering (uses, side effects, interactions, prices).\n\n"
    "مجھے بیماری کی تشخیص کرنے کی اجازت نہیں — براہ کرم ڈاکٹر سے رجوع کریں۔ "
    "میں دوا کی معلومات دے سکتا ہوں، تشخیص نہیں۔\n\n"
    "⚠️ Disclaimer: Always consult a licensed doctor or pharmacist."
)

EMERGENCY_RESPONSE = (
    "🚨 **This may be a medical emergency.**\n\n"
    "**Call 1122 (Pakistan Emergency) or go to the nearest hospital immediately.**\n\n"
    "Do not wait. If you or someone else has taken an overdose, ingested poison, "
    "or is in danger, emergency services can help right now.\n\n"
    "🚨 **یہ ایک ایمرجنسی ہو سکتی ہے — فوراً 1122 پر کال کریں یا قریبی ہسپتال جائیں۔**\n\n"
    "⚠️ Disclaimer: This is not medical treatment. Seek immediate professional help."
)

OFF_TOPIC_REFUSAL = (
    "I'm MedPak AI — I can only help with medicine information: uses, side "
    "effects, interactions, brands, and prices in Pakistan. I can't help with "
    "other topics.\n\n"
    "Try asking about a medicine by name — e.g. *\"What is Panadol used for?\"*\n\n"
    "میں صرف ادویات کی معلومات فراہم کر سکتا ہوں — نظم، کہانی یا دوسرے موضوعات پر "
    "بات نہیں کر سکتا۔ کسی دوا کے بارے میں پوچھیں!\n\n"
    "⚠️ Disclaimer: Always consult a licensed doctor or pharmacist."
)

GREETING_RESPONSE = (
    "👋 **Salam! I'm MedPak AI** — your medicine information assistant.\n\n"
    "Here's what you can ask me:\n"
    "- *\"What is Panadol used for?\"*\n"
    "- *\"Side effects of Brufen?\"*\n"
    "- *\"Can I take Panadol with Aspirin?\"*\n"
    "- *\"Brufen ki price kitni hai?\"* — Roman Urdu works too!\n\n"
    "💡 Tip: use the search bar to compare **live pharmacy prices** and find "
    "cheaper alternatives with the same salts.\n\n"
    "⚠️ *Disclaimer: I provide information only — always consult a licensed "
    "doctor or pharmacist.*"
)


# ── Detection patterns ────────────────────────────────────────────────────────
# Tight lists — false negatives are fine (the LLM prompt catches them);
# false positives (blocking legit questions) are NOT fine.

# Asking for a medicine suggestion / prescription (when no medicine is named)
_SUGGESTION_PATTERNS = [
    r"which\s+(medicine|medication|tablet|dawa|drug|antibiotic|syrup)\b",
    r"what\s+(medicine|medication|tablet|dawa|drug|antibiotic|syrup)\s+(should|can|do|to)\b",
    r"best\s+(medicine|medication|tablet|drug)\s+for\b",
    r"(suggest|recommend|prescribe)\s+(me\s+)?((a|an|some|any)?\s*(medicine|medication|tablet|dawa|drug|antibiotic)|something|anything)",
    r"konsi\s+(dawa|medicine|goli|tablets?)\s",            # konsi dawa ...
    r"(kaunsi|kaunsi|kon\s?si)\s+(dawa|medicine)\b",
    r"kya\s+(dawa|medicine)\s+(lun|loon|leni|lena)\s+chahiye",
    r"(dawa|ilaaj|treatment|prescription)\s+batao",
    r"mera\s+(ilaaj|treatment)\s+bata",
    r"dawa\s+(tajweez|recommend)\s+karo",
    r"کس\s+دوا",                                            # Urdu: which dawa
    r"مجھے\s+دوا",                                          # Urdu: give me dawa
]

# Asking for a diagnosis
_DIAGNOSIS_PATTERNS = [
    r"\bdiagnose\s+(me|this|my)\b",
    r"what\s+(do|does)\s+(i|he|she)\s+have\b",
    r"what'?s\s+wrong\s+with\s+(me|him|her|my)\b",
    r"what\s+illness\s+(do|does)\s+(i|he|she)\b",
    r"do\s+i\s+have\s+(cancer|diabetes|dengue|malaria|corona|covid|tb|hiv|aids|tumor)\b",
    r"mujhe\s+kya\s+(hua|huwa|problem)\s*(hai)?\b",
    r"meri\s+(bimari|illness|problem)\s+kya\s hai\b",
    r"kya\s+mujhe\s+(dengue|malaria|diabetes|cancer|corona|covid|tb)\s*(hai)?\b",
    r"میری\s+بیماری\s+کیا\s+ہے",                            # Urdu: what is my illness
    r"مجھے\s+کیا\s+ہوا\s+ہے",                               # Urdu: what happened to me
]

# Medical emergencies — respond with emergency info, not refusal
_EMERGENCY_PATTERNS = [
    r"\boverdose[d]?\b",
    r"\b(poison|poisoned|poisoning)\b",
    r"\bsuicide\b",
    r"(kill|hurt|hang|harm)\s+(myself|himself|herself)",
    r"too\s+many\s+(pills|tablets)",
    r"took\s+\d+\s+(pills|tablets|capsules)",
    r"zahar\s+khaya",
    r"khudkushi",
    r"bohat\s+sari\s+(goliyan|tablets)\s+khay",             # ate too many pills
    r"زياده\s+مقدار",                                        # Urdu: overdose
    r"خودکشی",                                               # Urdu: suicide
]

_SUGGESTION_RE = [re.compile(p, re.IGNORECASE) for p in _SUGGESTION_PATTERNS]
_DIAGNOSIS_RE = [re.compile(p, re.IGNORECASE) for p in _DIAGNOSIS_PATTERNS]
_EMERGENCY_RE = [re.compile(p, re.IGNORECASE) for p in _EMERGENCY_PATTERNS]

# Blatant off-topic requests — creative writing, jokes, general chit-chat.
# Tight on purpose: nuanced off-topic cases fall through to the LLM prompt.
_OFF_TOPIC_PATTERNS = [
    r"write\s+(me\s+)?(a|an|the)?\s*(short|long|small|little|nice|funny|good|quick)?\s*(poem|poetry|story|song|essay|speech|letter|script|novel)",
    r"write\s+(me\s+)?(some\s+)?code\b",
    r"(tell|say)\s+(me\s+)?(a\s+)?(joke|funny\s+story)",
    r"(shayari|kahani|joke|lateefa)\s+sunao",
    r"(shayari|kahani|nazm)\s+likho",
    r"نظم\s+لکھو",                                          # Urdu: write a poem
    r"کہانی\s+لکھو",                                        # Urdu: write a story
    r"لطیفہ\s+سنا",                                         # Urdu: tell a joke
]

_OFF_TOPIC_RE = [re.compile(p, re.IGNORECASE) for p in _OFF_TOPIC_PATTERNS]


# Simple greetings — answered with a friendly welcome instead of burning an
# LLM call that would just refuse small talk. Full-message match only:
# "hi, what is panadol used for?" still goes to the LLM.
_GREETINGS = {
    "hi", "hii", "hiii", "hey", "heyy", "hello", "hy", "yo", "greetings",
    "salam", "salaam", "aoa", "salamualaikum", "salaamualaikum",
    "assalamualaikum", "assalamoalaikum", "assalam o alaikum",
    "asalam o alaikum", "السلام علیکم", "سلام", "ہیلو",
    "good morning", "good afternoon", "good evening", "good night",
    "kaise ho", "kaisay ho", "kya haal hai", "kya hal hai",
    "how are you", "how are u", "how r u", "hows it going", "how's it going",
    "whats up", "what's up", "sup",
}

# Filler words allowed after a greeting word ("salam sir", "hi there")
_GREETING_FILLERS = {"there", "sir", "madam", "ji", "everyone", "guys", "doc", "doctor", "bhai", "bhaijan"}


def _is_greeting(msg: str) -> bool:
    """True when the whole message is just a greeting ("hi!", "Salam sir :")."""
    # Drop apostrophes ("what's" -> "whats"), strip punctuation/emoji,
    # collapse whitespace
    cleaned = re.sub(r"['’`]", "", msg.lower())
    cleaned = re.sub(r"[^\w\s\u0600-\u06FF]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return False
    # Collapse stretched letters ("hiii" -> "hi")
    squeezed = re.sub(r"(.)\1{2,}", r"\1", cleaned)
    for text in (cleaned, squeezed):
        words = text.split()
        if text in _GREETINGS:
            return True
        if words and words[0] in _GREETINGS and all(w in _GREETING_FILLERS for w in words[1:]):
            return True
    return False


# ── Main guard function ───────────────────────────────────────────────────────

def check_query_guards(message: str) -> Optional[dict]:
    """
    Check a user message against guardrail patterns BEFORE calling the LLM.

    Returns:
        None — message is safe to send to the LLM.
        {"blocked": True, "reason": str, "answer": str} — return this answer
        to the user instead of calling the LLM.
    """
    if not message or not message.strip():
        return None

    msg = message.strip()

    # 1. Emergencies take priority — respond with emergency guidance
    for rx in _EMERGENCY_RE:
        if rx.search(msg):
            return {
                "blocked": True,
                "reason": "emergency",
                "answer": EMERGENCY_RESPONSE,
            }

    # 1b. Pure greetings get a friendly welcome (not an LLM refusal)
    if _is_greeting(msg):
        return {
            "blocked": True,
            "reason": "greeting",
            "answer": GREETING_RESPONSE,
        }

    # 2. Diagnosis requests
    for rx in _DIAGNOSIS_RE:
        if rx.search(msg):
            return {
                "blocked": True,
                "reason": "diagnosis",
                "answer": DIAGNOSIS_REFUSAL,
            }

    # 3. Medicine suggestion requests
    #    Skip if the user names a specific medicine — "should I take Panadol
    #    or Brufen" is a comparison the LLM can handle per its prompt rules.
    if not _mentions_medicine_name(msg):
        for rx in _SUGGESTION_RE:
            if rx.search(msg):
                return {
                    "blocked": True,
                    "reason": "suggestion",
                    "answer": SUGGESTION_REFUSAL,
                }

    # 4. Blatant off-topic requests (poems, jokes, stories...)
    for rx in _OFF_TOPIC_RE:
        if rx.search(msg):
            return {
                "blocked": True,
                "reason": "off_topic",
                "answer": OFF_TOPIC_REFUSAL,
            }

    return None


# ── Helper: detect if a specific medicine name appears in the message ─────────
# A crude heuristic: uppercase tokens, known salt names, or 2+ word brand-ish
# names. This keeps "which medicine should I take for fever?" blocked while
# letting "which is cheaper: Panadol or Calpol?" through to the LLM.

_KNOWN_SALTS = {
    "panadol", "paracetamol", "brufen", "ibuprofen", "aspirin", "disprin",
    "calpol", "augmentin", "amoxicillin", "flagyl", "metronidazole",
    "zithromax", "azithromycin", "ciplox", "ciprofloxacin", "levaquin",
    "levofloxacin", "ventolin", "salbutamol", "glucophage", "metformin",
    "insulin", "lipitor", "atorvastatin", "tenormin", "atenolol",
    "glucotrol", "lasix", "furosemide", "nexum", "omeprazole",
    "motilium", "domperidone", "gravinate", "dimenhydrinate",
    "tylenol", "acetaminophen", "advil", "nurofen", "voltaren",
    "diclofenac", "naproxen", "allegra", "loratadine", "zyrtec",
    "cetirizine", "benadryl", "chlorpheniramine", "sinemet",
    "prozac", "fluoxetine", "xanax", "alprazolam", "valium",
}


def _mentions_medicine_name(msg: str) -> bool:
    tokens = set(re.findall(r"[a-zA-Z]{3,}", msg.lower()))
    if tokens & _KNOWN_SALTS:
        return True
    return False


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    cases = [
        # (message, should_block)
        ("What is Panadol used for?",                    False),
        ("Panadol ke side effects kya hain?",            False),
        ("Is it safe to take Panadol with Aspirin?",     False),
        ("What is the difference between Brufen and Panadol?", False),
        ("What does extended release mean?",             False),
        ("Which medicine should I take for fever?",      True),
        ("What medicine can I take for headache?",       True),
        ("konsi dawa lun bukhaar ke liye?",              True),
        ("Suggest me a medicine for cough",              True),
        ("Can you prescribe something for pain?",        True),
        ("What illness do I have? I have fever.",        True),
        ("Diagnose me please",                           True),
        ("mujhe kya hua hai?",                           True),
        ("I took 20 tablets of Panadol, what do I do?",  True),  # emergency
        ("I want to kill myself",                        True),  # emergency
        ("Write a poem about the ocean.",                True),  # off-topic
        ("Can you write me a short story?",              True),  # off-topic
        ("Tell me a joke",                               True),  # off-topic
        ("koi shayari sunao",                            True),  # off-topic (Roman Urdu)
        ("How is paracetamol metabolized?",              False),
        ("What is the price of Brufen?",                 False),
        # greetings -> friendly welcome (blocked, reason "greeting")
        ("hi",                                            True),
        ("Hello!",                                        True),
        ("salam sir",                                     True),
        ("Assalam o Alaikum",                             True),
        ("hi, what is panadol used for?",                False),  # greeting + real question -> LLM
    ]

    passed = 0
    for msg, expect_block in cases:
        result = check_query_guards(msg)
        blocked = result is not None
        ok = blocked == expect_block
        passed += ok
        status = "PASS" if ok else "FAIL"
        reason = result["reason"] if result else "-"
        print(f"[{status}] {'BLOCKED' if blocked else 'allowed':8s} ({reason:10s}) {msg}")

    print(f"\n{passed}/{len(cases)} tests passed")
