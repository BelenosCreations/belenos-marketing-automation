"""TruthGuard deterministic risk signals for marketing drafts.

These are review hints, NOT exhaustive claim extraction or a truth oracle.
Every draft remains held for the existing approval and verification gates.
"""
import re

PATTERNS={
    'price_or_discount':r'(?<!\w)(?:\$\s*\d|\d+(?:\.\d+)?\s*%\s*off\b|free\s+(?:shipping|delivery|gift))',
    'guarantee':r'\b(?:guaranteed?|warranty|warranties|lifetime|waterproof|fireproof|100\s*%|never\s+fails?)\b',
    'urgency_or_availability':r'\b(?:today\s+only|limited\s+time|in\s+stock|sold\s+out|same[- ]day|next[- ]day|ready\s+now)\b',
    'business_hours':r'\b(?:open\s+(?:today|tomorrow|24\s*/\s*7)|closing\s+at|hours?\s+are|\d{1,2}\s*(?:am|pm)\s*(?:-|to)\s*\d{1,2}\s*(?:am|pm))\b',
    'testimonial':r'\b(?:customers?\s+(?:say|love|agree)|rated\s+\d|five[- ]star|testimonial|reviewed\s+by)\b',
}
_COMPILED={k:re.compile(v,re.IGNORECASE) for k,v in PATTERNS.items()}

def scan_risk_signals(draft_text):
    if not isinstance(draft_text,str) or not draft_text.strip():
        raise ValueError('Nonempty draft required')
    if len(draft_text)>20000:
        raise ValueError('Draft exceeds scan limit')
    signals=[]
    for category,pattern in _COMPILED.items():
        for match in pattern.finditer(draft_text):
            signals.append({'category':category,'start':match.start(),
                'end':match.end(),'text':match.group(0)})
    signals.sort(key=lambda x:(x['start'],x['end'],x['category']))
    return {'signals':signals,'review_required':True,
            'extraction_complete':False,'publishing_enabled':False,
            'notice':'Heuristic flags are incomplete; absence of flags does not verify a draft'}
