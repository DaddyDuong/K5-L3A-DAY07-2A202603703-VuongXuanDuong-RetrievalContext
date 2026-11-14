"""Ranking/filter/evidence regressions, independent of external services."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))
from baseline import TfidfIndex
from benchmark_retrieval import evidence_hit, evaluate_case
from retrieval import RetrievalSuite, QuestionContextSelector, reciprocal_rank_fusion


def chunk(cid, text='file read', chapter=14, score=0.5):
    return {'id': cid, 'source_id': 'book', 'source': 'book.pdf', 'page': 1,
            'text': text, 'metadata': {'chapter': chapter}, 'score': score}


class RetrievalTests(unittest.TestCase):
    def test_rrf_agreement_and_score_scale_independence(self):
        a, b, c = chunk('a', score=0.99), chunk('b', score=0.5), chunk('c', score=1000)
        rows = reciprocal_rank_fusion({'dense': [a, b], 'lexical': [c, b]}, top_k=3)
        self.assertEqual(rows[0]['id'], 'b')
        self.assertAlmostEqual(rows[0]['score'], 2/62)
        self.assertEqual(rows[0]['component_ranks'], {'dense': 2, 'lexical': 2})
        self.assertEqual(a['score'], 0.99)

    def test_rrf_empty_component_ties_and_duplicate_rejection(self):
        rows = reciprocal_rank_fusion({'dense': [chunk('b')], 'lexical': [chunk('a')]}, top_k=2)
        self.assertEqual([r['id'] for r in rows], ['a', 'b'])
        self.assertEqual(reciprocal_rank_fusion({'dense': [], 'lexical': []}, top_k=3), [])
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion({'dense': [chunk('a'), chunk('a')]}, top_k=3)

    def suite(self, method):
        suite = RetrievalSuite.__new__(RetrievalSuite)
        suite.method, suite.candidates, suite.rrf_constant = method, 10, 60
        suite.calls = []
        suite.dense = Mock()
        suite.dense.search.return_value = [chunk('dense')]
        suite.lexical = TfidfIndex([chunk('wrong', chapter=15), chunk('right', chapter=14)])
        return suite

    def test_lexical_filter_before_cutoff_and_no_embedding_call(self):
        suite = self.suite('lexical')
        rows = suite.search('file read', filters={'chapter': 14}, top_k=1)
        self.assertEqual([r['id'] for r in rows], ['right'])
        suite.dense.search.assert_not_called()
        self.assertEqual(suite.search('unknown_xyz', filters={}, top_k=3), [])
        with self.assertRaises(ValueError):
            suite.search('file', filters={'chapter': True}, top_k=3)

    def test_hybrid_uses_common_query_filter_and_candidate_depth(self):
        suite = self.suite('hybrid')
        rows = suite.search('file read', filters={'chapter': 14}, top_k=3)
        suite.dense.search.assert_called_once_with('file read', filters={'chapter': 14}, top_k=10)
        self.assertTrue(all('component_ranks' in r for r in rows))
        self.assertNotIn('wrong', [r['id'] for r in rows])

    def test_evidence_alternatives_require_source_page_and_full_quote(self):
        case = {'gold_source_id': 'other', 'gold_page': 3, 'evidence_quote': 'no',
                'alternative_gold': [{'gold_source_id': 'book', 'gold_page': 1,
                                      'evidence_quote': 'file  read'}]}
        self.assertTrue(evidence_hit(chunk('x'), case))
        self.assertFalse(evidence_hit({**chunk('x'), 'page': 2}, case))
        self.assertFalse(evidence_hit(chunk('x', text='file'), case))

    def test_retrieval_hit_can_be_lost_from_context_and_gold_not_forwarded(self):
        case = {'id': 'q', 'question': 'read', 'gold_source_id': 'book',
                'gold_page': 1, 'evidence_quote': 'file read'}
        retriever = Mock(method='dense')
        retriever.search.return_value = [chunk('c')]
        result = evaluate_case(retriever, case, budget=1)
        self.assertTrue(result['hit1'])
        self.assertFalse(result['context_hit'])
        retriever.search.assert_called_once_with('read', filters={}, top_k=3)

    def test_context_reranking_uses_original_question_once_and_deduplicates(self):
        dense=Mock(strategy='C')
        dense.embedder.embed_query.return_value=[0.1,0.2]
        dense.store._vector.return_value='[0.1,0.2]'
        dense.store.connection.execute.return_value.fetchall.return_value=[
            {'chunk_id':'later','context_score':0.9},{'chunk_id':'earlier','context_score':0.1}]
        selector=QuestionContextSelector(dense,'original question')
        candidates=[chunk('earlier'),chunk('later'),chunk('earlier')]
        _,ids=selector(candidates,budget=50)
        self.assertEqual(ids,['later'])
        selector(candidates,budget=50)
        dense.embedder.embed_query.assert_called_once_with('original question')
        args=dense.store.connection.execute.call_args.args[1]
        self.assertEqual(args[2],['earlier','later'])


if __name__ == '__main__':
    unittest.main()
