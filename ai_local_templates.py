"""Zero-API-cost marketing drafts from verified, literal business facts.

Templates never infer price, hours, availability, discounts or guarantees.
They create review-only drafts, not publishable posts.
"""
from ai_draft_request import AIDraftRequestBuilder

class LocalDraftTemplates:
    def __init__(self, *, request_builder):
        if not isinstance(request_builder,AIDraftRequestBuilder):
            raise TypeError('Authenticated request builder required')
        self.builder=request_builder

    def product_spotlight(self, *, token, now, verified_facts, platform,
                          include_image_prompt=False):
        if type(include_image_prompt) is not bool:
            raise ValueError('Image prompt choice must be boolean')
        if type(verified_facts) is not dict or not all(
            type(verified_facts.get(key)) is str and
            verified_facts[key].strip()
            for key in ('business_name','product')):
            raise ValueError('Verified business name and product required')
        base=self.builder.build(token=token,now=now,
            verified_facts=verified_facts,topic='Product spotlight',
            platform=platform)
        name=verified_facts['business_name'].strip()
        product=verified_facts['product'].strip()
        if len(name)>100 or len(product)>200:
            raise ValueError('Verified fact too long')
        # Literal formatting only; no claims about availability or quality.
        text=f'{name}: {product}. Contact us for details.'
        image_prompt=None
        if include_image_prompt:
            # Category-level illustration, not a claimed photograph or product specification.
            image_prompt=(
                'Make an original, generic marketing illustration featuring '
                'the product category '+repr(product)+' for business '
                +repr(name)+'. This is a conceptual graphic, not a photo of '
                'the actual product. Do not invent specific designs, brand '
                'logos, promotions, prices, store hours, claims, text or '
                'customer testimonials. Leave safe print and crop margins. '
                'The business owner must review before use.'
            )
        return {'tenant_id':base['tenant_id'],
                'subject_id':base['subject_id'],
                'post_text':text,'image_prompt':image_prompt,
                'generation_method':'local_template',
                'openai_requests':0,
                'status':('needs_media' if include_image_prompt
                          else 'draft_pending_verification'),
                'publishing_enabled':False}
