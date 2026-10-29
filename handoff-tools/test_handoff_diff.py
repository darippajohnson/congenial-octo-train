import copy
import unittest
from handoff_diff import compare, build_plan
NOW = '2026-10-29T10:00:00Z'

class Tests(unittest.TestCase):
    def setUp(self):
        self.rows = [{'id':'a','title':'Source','modified_time':NOW}]
        self.state = {'gates':['No spending',{'limit':3}], 'sources':[{'id':'a','url':'https://example.org/a','review_on':'change'}], 'tasks':[{'id':'blocked','status':'blocked','owner':'Reviewer','evidence':'UNKNOWN'}]}
    def plan(self, **kw):
        return build_plan(kw.get('before',self.rows),kw.get('after',self.rows),kw.get('state',self.state),kw.get('now',NOW),kw.get('complete',True))
    def test_changed_added_missing(self):
        r=compare([{'id':'a','updated_at':'1'},{'id':'b','updated_at':'1'}],[{'id':'a','updated_at':'2'},{'id':'c','updated_at':'1'}])
        for name,ids in [('changed',['a']),('added',['c']),('missing_from_snapshot',['b'])]:
            self.assertEqual([x['id'] for x in r[name]],ids)
    def test_provider_timestamp_change(self):
        self.assertEqual(len(compare(self.rows,[{'id':'a','title':'Source','modifiedTime':'2026-10-29T11:00:00Z'}])['changed']),1)
    def test_alias_timezone_equivalent(self):
        self.assertEqual(compare(self.rows,[{'id':'a','name':'Source','updated_at':'2026-10-29T05:00:00-05:00'}])['unchanged_count'],1)
    def test_conflict_fails(self):
        with self.assertRaises(ValueError):compare([],[{'id':'a','updated_at':'1','modified_time':'2'}])
    def test_missing_version_unknown(self):
        r=compare([{'id':'a'}],[{'id':'a'}]); self.assertEqual(r['unchanged_count'],0);self.assertEqual(len(r['unknown_version']),1)
    def test_hash_change(self):
        self.assertEqual(len(compare([{'id':'a','content_sha256':'x'}],[{'id':'a','content_sha256':'y'}])['changed']),1)
    def test_bad_schema(self):
        for bad in ({},[None],[{'id':' '}],[{'id':'a'},{'id':'a'}],[{'id':'a','modifiedTime':10}]):
            with self.subTest(bad=bad),self.assertRaises(ValueError):compare([],bad)
    def test_gates_and_unresolved_verbatim_no_mutation(self):
        baseline=copy.deepcopy(self.state);r=self.plan()
        self.assertEqual(r['gates'],baseline['gates']);self.assertEqual(r['unresolved_tasks'],baseline['tasks'])
        self.assertEqual(r['due_task_ids'],['blocked']);self.assertFalse(r['no_change_candidate'])
        r['gates'].append('other');r['unresolved_tasks'][0]['owner']='other';self.assertEqual(self.state,baseline)
    def test_partial_page_never_no_change(self):
        self.state['tasks']=[];self.assertFalse(self.plan(complete=False)['no_change_candidate']);self.assertTrue(self.plan()['no_change_candidate'])
    def test_failed_read_retried(self):
        after=[{'id':'a','modified_time':'new'}];a=self.plan(after=after);b=self.plan(after=after)
        self.assertTrue(a['reads_required']);self.assertEqual(a,b);self.assertEqual(self.rows[0]['modified_time'],NOW)
    def test_due_unchanged_source(self):
        self.state['sources'][0]['next_review_at']='2026-10-29T04:59:59-05:00';self.assertIn('review_due',self.plan()['review_sources'][0]['reasons'])
    def test_future_blocker_visible(self):
        self.state['tasks'][0]['next_review_at']='2026-10-30T00:00:00Z';r=self.plan();self.assertEqual(len(r['unresolved_tasks']),1);self.assertEqual(r['due_task_ids'],[])
    def test_unknown_trigger_requires_review(self):
        self.state['sources'][0].pop('review_on');self.assertIn('review_trigger_unknown',self.plan()['review_sources'][0]['reasons'])
    def test_missing_not_deleted(self):
        r=self.plan(after=[])['review_sources'][0]['reasons'];self.assertIn('required_source_missing',r);self.assertIn('missing_from_snapshot',r)
    def test_body_not_copied(self):
        self.assertNotIn('SECRET_BODY',str(self.plan(after=[{'id':'a','modified_time':'new','content':'SECRET_BODY'}])))
    def test_bad_review_date(self):
        for date in ('later','2026-10-29T10:00:00',10):
            with self.subTest(date=date),self.assertRaises(ValueError):self.plan(now=date)
    def test_missing_gates_fails(self):
        self.state['gates']=[]
        with self.assertRaises(ValueError):self.plan()
    def test_unknown_task_status_fails(self):
        self.state['tasks'][0]['status']='maybe'
        with self.assertRaises(ValueError):self.plan()
    def test_only_closed_tasks_excluded(self):
        self.state['tasks'].append({'id':'done','status':'done'});self.assertEqual([x['id'] for x in self.plan()['unresolved_tasks']],['blocked'])
if __name__=='__main__':unittest.main()
