"""Structured, component-targeted AI marketing content planning.

Offline only. One OpenAI response can contain post text and optional image
prompt. User-provided ChatGPT images are uploaded separately through a future
verified-media workflow. No image generation, OpenAI call, or publishing here.
"""
import json
from ai_draft_request import AIDraftRequestBuilder

class AIContentPlan:
    def __init__(self, *, request_builder):
        if not isinstance(request_builder,AIDraftRequestBuilder):
            raise TypeError('Verified-facts request builder required')
        self.builder=request_builder

    def create_request(self, *, token, now, verified_facts, topic, platform,
                       include_image_prompt=True):
        if type(include_image_prompt) is not bool:
            raise ValueError('Image prompt flag required')
        base=self.builder.build(token=token,now=now,
            verified_facts=verified_facts,topic=topic,platform=platform)
        base['instructions']+=(
            ' Return one JSON object with post_text (nonempty string) and '
            'image_prompt (string or null). Create an image_prompt only if '
            'the request asks for one. Image prompts must avoid unsupported '
            'product details, false logos, invented claims or text. '
            'Image generation is external and optional; do not imply an image '
            'was created, attached or approved.'
        )
        payload=json.loads(base['input_json'])
        payload['include_image_prompt']=include_image_prompt
        base['input_json']=json.dumps(payload,sort_keys=True,ensure_ascii=False)
        base['response_schema']={
            'post_text':'string',
            'image_prompt':'string|null'}
        return base

    @staticmethod
    def parse_response(raw, *, include_image_prompt):
        if type(raw) is str:
            if len(raw)>15000:
                raise ValueError('Response too large')
            try:
                value=json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError('Invalid structured response') from exc
        else:
            value=raw
        if type(value) is not dict or set(value)!={
            'post_text','image_prompt'}:
            raise ValueError('Expected structured post and image prompt')
        post=value['post_text']
        image=value['image_prompt']
        if type(post) is not str or not post.strip() or len(post)>4000:
            raise ValueError('Invalid generated post')
        if image is not None and (
            type(image) is not str or not image.strip() or len(image)>2000
            or not include_image_prompt):
            raise ValueError('Unexpected or invalid image prompt')
        return {'post_text':post,'image_prompt':image,
                'status':'draft_pending_verification',
                'image_created':False,'publishing_enabled':False}

    def revision_request(self, *, token, now, verified_facts, topic,
                         platform, current, target, instruction):
        if target not in ('post_text','image_prompt'):
            raise ValueError('Only a single component can be revised')
        if type(instruction) is not str or not instruction.strip() or len(instruction)>500:
            raise ValueError('Revision instruction required')
        if type(current) is not dict or not {'post_text','image_prompt'}.issubset(current):
            raise ValueError('Existing structured draft required')
        # Revalidate content, and preserve the untargeted component verbatim.
        validated=self.parse_response({
            'post_text':current['post_text'],
            'image_prompt':current['image_prompt']},
            include_image_prompt=True)
        if target=='image_prompt' and validated['image_prompt'] is None:
            raise ValueError('No image prompt exists to revise')
        base=self.create_request(token=token,now=now,
            verified_facts=verified_facts,topic=topic,platform=platform,
            include_image_prompt=(target=='image_prompt'))
        base['instructions']+=(
            ' Revise only the selected component. Return one JSON object '
            'with key revised_text. Do not modify or regenerate the other component.'
        )
        payload=json.loads(base['input_json'])
        payload.update({'revision_target':target,
                        'revision_instruction':instruction,
                        'current_component':validated[target]})
        base['input_json']=json.dumps(payload,sort_keys=True,ensure_ascii=False)
        base['response_schema']={'revised_text':'string'}
        return base

    @staticmethod
    def apply_revision(current, *, target, revised_text):
        if target not in ('post_text','image_prompt'):
            raise ValueError('Unknown revision target')
        if type(revised_text) is not str or not revised_text.strip() or (
            len(revised_text)>(4000 if target=='post_text' else 2000)):
            raise ValueError('Invalid revision')
        if type(current) is not dict or not {'post_text','image_prompt'}.issubset(current):
            raise ValueError('Existing structured draft required')
        result=AIContentPlan.parse_response({
            'post_text':current['post_text'],
            'image_prompt':current['image_prompt']},include_image_prompt=True)
        result[target]=revised_text
        result['status']='draft_pending_verification'
        return result

    def batch_requests(self, *, token, now, verified_facts, topics, platform,
                       include_image_prompt=True):
        if type(topics) is not list or not 1<=len(topics)<=14:
            raise ValueError('Batch must contain 1–14 topics')
        if any(type(topic) is not str or not topic.strip() or
               len(topic)>300 for topic in topics):
            raise ValueError('Invalid batch topic')
        if len(set(topics))!=len(topics):
            raise ValueError('Duplicate topics')
        return [self.create_request(token=token,now=now,
            verified_facts=verified_facts,topic=topic,platform=platform,
            include_image_prompt=include_image_prompt) for topic in topics]
