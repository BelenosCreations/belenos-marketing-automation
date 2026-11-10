"""TruthGuard source-span integrity for draft claim review.

This checks that submitted claim spans really occur in the immutable draft.
It does not identify facts, judge truth, or authorize publishing.
"""
import hashlib

class ClaimSpanAudit:
    @staticmethod
    def audit(*, draft_text, annotations):
        if not isinstance(draft_text,str) or not draft_text.strip():
            raise ValueError('Nonempty draft required')
        if not isinstance(annotations,(list,tuple)) or len(annotations)>100:
            raise ValueError('Invalid claim annotations')
        issues=[]
        accepted=[]
        for index, entry in enumerate(annotations):
            if not isinstance(entry,dict) or set(entry)!={'start','end','key','text'}:
                issues.append({'index':index,'reason':'invalid_annotation'})
                continue
            start,end,key,text=(entry[k] for k in ('start','end','key','text'))
            if (type(start) is not int or type(end) is not int or
                start<0 or end>len(draft_text) or end<=start or
                not isinstance(key,str) or not key.strip() or
                not isinstance(text,str) or not text.strip() or
                draft_text[start:end]!=text):
                issues.append({'index':index,'reason':'span_mismatch'})
                continue
            if any(start<prior['end'] and end>prior['start'] for prior in accepted):
                issues.append({'index':index,'reason':'overlapping_spans'})
                continue
            accepted.append({'start':start,'end':end,'key':key,'text':text})
        accepted.sort(key=lambda x:x['start'])
        cursor=0
        gaps=[]
        for entry in accepted:
            if entry['start']>cursor:
                gaps.append(draft_text[cursor:entry['start']])
            cursor=entry['end']
        if cursor<len(draft_text):
            gaps.append(draft_text[cursor:])
        # Gaps are informational, not a reliable classifier of factual claims.
        return {'draft_sha256':hashlib.sha256(draft_text.encode('utf-8')).hexdigest(),
                'accepted':accepted,'issues':issues,'unannotated_text':gaps,
                'annotation_integrity':not issues,
                'all_text_annotated':not issues and not any(g.strip() for g in gaps),
                'fact_extraction_complete':False,'publish_eligible':False}
