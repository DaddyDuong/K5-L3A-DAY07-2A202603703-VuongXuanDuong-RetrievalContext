"""Protocol and failure checks; these do not measure model answer quality."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))
from day7_agent import ModelController, extract_citation_ids


def response(name, arguments, finish='tool_calls'):
    if name == 'finish':
        arguments = {'abstain': False, **arguments}
    return io.BytesIO(json.dumps({'choices': [{'finish_reason': finish, 'message': {
        'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'call-1',
        'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments)}}]}}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'cost': 0.0001}}).encode())


class ControllerProtocolTests(unittest.TestCase):
    def controller(self):
        return ModelController({'MODEL': 'test-model', 'OPENROUTER_API_KEY': 'test-secret'}, 2)

    def test_tool_result_pair_and_context_follow_search(self):
        c = self.controller()
        with patch('day7_agent.urllib.request.urlopen', side_effect=[
            response('search', {'query': 'read readline'}),
            response('finish', {'answer': 'Một dòng [c1]', 'citations': ['c1']})]) as post:
            self.assertEqual(c.decide('q', []), {'action': 'search', 'query': 'read readline'})
            action = c.decide('q', [{'queries': ['read readline'], 'context': 'evidence', 'context_ids': ['c1']}])
        self.assertEqual(action['citations'], ['c1'])
        payload = json.loads(post.call_args.args[0].data)
        self.assertEqual(payload['messages'][-1]['tool_call_id'], 'call-1')
        self.assertEqual(payload['messages'][-2]['tool_calls'][0]['id'], 'call-1')
        self.assertIn('evidence', payload['messages'][-1]['content'])
        self.assertNotIn('test-secret', json.dumps(c.calls))

    def test_finish_before_search_is_rejected(self):
        with patch('day7_agent.urllib.request.urlopen', return_value=response(
                'finish', {'answer': 'guess', 'citations': []})):
            with self.assertRaises(ValueError):
                self.controller().decide('q', [])

    def test_search_batch_executes_serially_without_extra_model_call(self):
        c = self.controller()
        data = json.loads(response('search', {'query': 'one'}).getvalue())
        second = {'id': 'call-2', 'type': 'function', 'function': {
            'name': 'search', 'arguments': json.dumps({'query': 'two'})}}
        data['choices'][0]['message']['tool_calls'].append(second)
        data['choices'][0]['message']['tool_calls'].append({**second, 'id': 'call-3'})
        with patch('day7_agent.urllib.request.urlopen', return_value=io.BytesIO(json.dumps(data).encode())) as post:
            self.assertEqual(c.decide('q', [])['query'], 'one')
            self.assertEqual(c.decide('q', [{'queries': ['one'], 'context': 'first'}])['query'], 'two')
        self.assertEqual(post.call_count, 1)
        self.assertEqual(c.last_search['tool_calls'], [second])
        self.assertEqual(c.calls[0]['skipped_tool_calls'][0]['id'], 'call-3')
        self.assertFalse(c.pending_searches)

    def test_unlisted_inline_citation_is_rejected(self):
        c = self.controller()
        with patch('day7_agent.urllib.request.urlopen', return_value=response('search', {'query': 'q'})):
            c.decide('q', [])
        with patch('day7_agent.urllib.request.urlopen', side_effect=[response(
                'finish', {'answer': 'Answer [c1] [invented]', 'citations': ['c1']}) for _ in range(2)]):
            with self.assertRaises(ValueError):
                c.decide('q', [{'queries': ['q'], 'context': 'evidence'}])

    def test_provider_failure_has_no_fake_answer_or_secret_body(self):
        c = self.controller()
        error = urllib.error.HTTPError('https://openrouter.ai', 401, 'Unauthorized', {},
                                      io.BytesIO(b'test-secret'))
        with patch('day7_agent.urllib.request.urlopen', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, 'HTTP 401'):
                c.decide('q', [])
        self.assertNotIn('test-secret', json.dumps(c.calls))
        self.assertNotIn('response', c.calls[0])

    def test_english_policy_rewrites_instructions_without_changing_question(self):
        c = ModelController({'MODEL':'test','OPENROUTER_API_KEY':'test'},query_language='english')
        with patch('day7_agent.urllib.request.urlopen',return_value=response('search',{'query':'read file'})) as post:
            c.decide('Đọc file thế nào?',[])
        payload=json.loads(post.call_args.args[0].data)
        self.assertIn('Luôn viết lại mọi query search thành tiếng Anh',payload['messages'][0]['content'])
        self.assertEqual(payload['messages'][1]['content'],'Đọc file thế nào?')

    def test_python_subscriptions_are_not_citations(self):
        answer='Dùng `str_list[2]` và `df[condition]` [c1].\n```python\nx=[1,2]\n```\n[c2]'
        self.assertEqual(extract_citation_ids(answer),['c1','c2'])
        self.assertEqual(extract_citation_ids('loc[] chọn df.loc[row_label, column_label] [c1]'),['c1'])

    def test_model_can_explicitly_abstain_with_background_citation(self):
        c=self.controller()
        with patch('day7_agent.urllib.request.urlopen',side_effect=[
            response('search',{'query':'q'}),response('finish',{
                'answer':'Không đủ thông tin. Tài liệu chỉ giới thiệu Python [c1].',
                'citations':['c1'],'abstain':True})]):
            c.decide('q',[])
            result=c.decide('q',[{'queries':['q'],'context':'source'}])
        self.assertEqual(result['action'],'abstain')

    def test_invalid_argument_json_gets_one_format_retry(self):
        c=self.controller()
        malformed=json.loads(response('search',{'query':'q'}).getvalue())
        malformed['choices'][0]['message']['tool_calls'][0]['function']['arguments']='{invalid'
        with patch('day7_agent.urllib.request.urlopen',side_effect=[
                io.BytesIO(json.dumps(malformed).encode()),response('search',{'query':'valid query'})]) as post:
            action=c.decide('q',[])
        self.assertEqual(action['query'],'valid query')
        self.assertEqual(post.call_count,2)
        self.assertEqual(c.calls[0]['error_type'],'JSONDecodeError')
        self.assertIn('Lượt trước trả tham số tool',c.calls[1]['request']['messages'][0]['content'])


if __name__ == '__main__':
    unittest.main()
