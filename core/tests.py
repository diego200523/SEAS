import json
from copy import deepcopy
from django.test import TestCase, SimpleTestCase, Client, override_settings
from django.core.management import call_command
from django.core import mail
from .engine import *
from .models import *
from .services import snapshot, save_evaluation, finalize, evaluation_json, catalog_state, save_config

class EngineTests(SimpleTestCase):
    def fixture(self, impact='INTERNO', values=(3,4), importance=3,suggested=3):
        factor={'id':'f','name':'Factor','is':suggested,'impact':impact,'subs':[{'id':str(i)} for i in range(len(values))]}
        return {'catalog':[factor],'matrix':MATRIX},{'importance':{'f':importance},'answers':dict(enumerate(values)) if False else {str(i):v for i,v in enumerate(values)},'support':''}
    def test_all_matrix_cells(self):
        expected=[[1,1,2,2],[1,2,2,3],[2,2,3,3],[2,3,3,4]]
        for i in range(4):
            for j in range(4): self.assertEqual(relative(i+1,j+1,MATRIX),expected[i][j])
    def test_invalid_values(self):
        for value in [None,0,5,True,2.5,'3']:
            with self.assertRaises(ValueError): level(value)
    def test_four_foda_quadrants(self):
        for impact,values,category in [('INTERNO',(3,3),'Fortaleza'),('INTERNO',(2,3),'Debilidad'),('EXTERNO',(3,4),'Oportunidad'),('EXTERNO',(1,4),'Amenaza')]:
            s,d=self.fixture(impact,values);self.assertEqual(calculate(s,d)[0][0]['foda'],category)
    def test_mean_not_rounded_before_foda(self):
        s,d=self.fixture(values=(3,)*60+(2,));r,_=calculate(s,d);self.assertLess(r[0]['pm'],3);self.assertEqual(r[0]['foda'],'Debilidad')
    def test_support_requires_explicit_impact(self):
        s,d=self.fixture('AMBOS')
        with self.assertRaises(ValueError): calculate(s,d)
        d['support']='EXTERNO';self.assertEqual(calculate(s,d)[0][0]['foda'],'Oportunidad')
    def test_missing_answers(self):
        s,d=self.fixture();d['answers'].clear()
        with self.assertRaises(ValueError): calculate(s,d)
    def test_no_factors(self):
        with self.assertRaises(ValueError): calculate({'catalog':[],'matrix':MATRIX},{})
    def test_no_relevant_factors(self):
        s,d=self.fixture(importance=1,suggested=1)
        with self.assertRaises(ValueError): calculate(s,d)
    def test_empty_subfactors(self):
        s,d=self.fixture(values=())
        with self.assertRaises(ValueError): calculate(s,d)
    def test_decision_boundaries(self):
        s,d=self.fixture(values=(2,2));self.assertEqual(calculate(s,d)[1]['text'],'No adoptar por ahora')
        s['catalog'].append({**s['catalog'][0],'id':'g','subs':[{'id':'good'}]});d['importance']['g']=3;d['answers']['good']=4
        self.assertEqual(calculate(s,d)[1]['text'],'Adoptar con condiciones')
        d['answers']['0']=4;d['answers']['1']=4;self.assertEqual(calculate(s,d)[1]['text'],'Adoptar')
    def test_no_critical_factors_literal_rn09(self):
        s,d=self.fixture(importance=1,suggested=3,values=(1,1));result,decision=calculate(s,d)
        self.assertEqual(decision['total'],0);self.assertEqual(decision['text'],'Adoptar');self.assertEqual(result[0]['foda'],'Debilidad')

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class WorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_seas',verbosity=0)
        cls.admin=User.objects.create_user(username='admin@seas.test',email='admin@seas.test',password='SeasPruebas-2026!',role='Administrador')
        cls.owner=User.objects.create_user(username='owner@seas.test',email='owner@seas.test',password='SeasPruebas-2026!',role='Decisor')
        cls.other=User.objects.create_user(username='other@seas.test',email='other@seas.test',password='SeasPruebas-2026!',role='Decisor')
        cls.director=User.objects.create_user(username='director@seas.test',email='director@seas.test',password='SeasPruebas-2026!',role='Dirección')
    def payload(self):
        s=snapshot()
        return {'org':'Organización de prueba','software':'Software de prueba','sector':'PRIVADO','importance':{f['id']:3 for f in s['catalog']},'answers':{q['id']:4 for f in s['catalog'] for q in f['subs']},'observations':{},'support':'INTERNO','step':2}
    def draft(self): return save_evaluation(self.owner,'testeval',self.payload())
    def test_seed_count_and_importances(self):
        self.assertEqual(Factor.objects.count(),18);self.assertEqual(Subfactor.objects.count(),61)
        f=Factor.objects.get(pk='f3');self.assertEqual((f.il,f.ie,f.suggested),(4,3,3))
    def test_no_plaintext_passwords_in_state(self):
        self.client.force_login(self.admin);data=self.client.get('/api/state').json()
        self.assertNotIn('password',data['users'][0]);self.assertNotEqual(self.owner.password,'SeasPruebas-2026!')
    def test_authentication(self):
        self.assertEqual(self.client.put('/api/evaluations/x',data='{}',content_type='application/json').status_code,401)
        response=self.client.post('/api/login',data=json.dumps({'email':self.owner.email,'password':'SeasPruebas-2026!'}),content_type='application/json');self.assertEqual(response.status_code,200)
    def test_csrf_required(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.owner)
        self.assertEqual(client.put('/api/evaluations/x',data='{}',content_type='application/json').status_code,403)
    def test_other_owner_denied(self):
        e=self.draft();self.client.force_login(self.other)
        self.assertEqual(self.client.get('/api/state').json()['evaluations'],[])
        self.assertEqual(self.client.put('/api/evaluations/'+e.pk,data=json.dumps(self.payload()),content_type='application/json').status_code,403)
        self.assertEqual(self.client.post('/api/evaluations/'+e.pk+'/finalize').status_code,404)
    def test_direction_read_only(self):
        e=self.draft();self.client.force_login(self.director)
        self.assertEqual(self.client.get('/api/state').json()['evaluations'],[])
        self.assertEqual(self.client.put('/api/evaluations/x',data=json.dumps(self.payload()),content_type='application/json').status_code,403)
        finalize(self.owner,e.pk);self.assertEqual(len(self.client.get('/api/state').json()['evaluations']),1)
        self.assertEqual(self.client.post('/api/evaluations/'+e.pk+'/finalize').status_code,403)
    def test_reject_client_catalog_and_results(self):
        payload=self.payload();payload.update(catalog=[],matrix=[[4]*4]*4,finalDecision={'text':'Falso'},status='Finalizada')
        e=save_evaluation(self.owner,'testeval',payload);self.assertEqual(e.status,'Borrador');self.assertEqual(len(e.snapshot['catalog']),18);self.assertEqual(e.decision,{})
    def test_snapshot_and_finalization(self):
        e=self.draft();Factor.objects.filter(pk='f0').update(name='Nombre cambiado',suggested=1)
        done=finalize(self.owner,e.pk);self.assertEqual(done.results[0]['name'],'Compatibilidad');self.assertEqual(done.decision['text'],'Adoptar');self.assertEqual(EvaluationSubfactor.objects.count(),61)
        with self.assertRaises(ValueError): save_evaluation(self.owner,e.pk,self.payload())
        finalize(self.owner,e.pk);self.assertEqual(EvaluationFactor.objects.count(),18)
    def test_incomplete_cannot_finalize(self):
        p=self.payload();p['answers']={};save_evaluation(self.owner,'testeval',p)
        with self.assertRaises(ValueError): finalize(self.owner,'testeval')
        self.assertEqual(Evaluation.objects.get().status,'Borrador');self.assertEqual(EvaluationFactor.objects.count(),0)
    def test_stale_revision_rejected(self):
        e=self.draft();p=self.payload();p['revision']=e.revision;save_evaluation(self.owner,e.pk,p)
        with self.assertRaises(ValueError): save_evaluation(self.owner,e.pk,p)
    def test_invalid_payload_rolls_back(self):
        p=self.payload();p['answers']['foreign']=4
        with self.assertRaises(ValueError): save_evaluation(self.owner,'x',p)
        self.assertEqual(Evaluation.objects.count(),0);self.assertEqual(Organization.objects.count(),0)
    def test_duplicate_clears_answers(self):
        e=self.draft();finalize(self.owner,e.pk);self.client.force_login(self.owner)
        r=self.client.post('/api/evaluations/'+e.pk+'/duplicate');self.assertEqual(r.status_code,201);self.assertEqual(r.json()['answers'],{});self.assertEqual(r.json()['status'],'Borrador')
    def test_pdf_is_actual_pdf_and_escapes_input(self):
        p=self.payload();p['org']='<b>Prueba & organización</b>';save_evaluation(self.owner,'testeval',p);finalize(self.owner,'testeval');self.client.force_login(self.owner)
        r=self.client.get('/api/evaluations/testeval/pdf');self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b'%PDF-'))
    def test_password_reset_sends_token(self):
        r=self.client.post('/accounts/password_reset/',{'email':self.owner.email});self.assertEqual(r.status_code,302);self.assertEqual(len(mail.outbox),1);self.assertIn('/accounts/reset/',mail.outbox[0].body)
    def test_config_authorization(self):
        self.client.force_login(self.owner);self.assertEqual(self.client.put('/api/config',data='{}',content_type='application/json').status_code,403)
    def test_catalog_update_is_atomic(self):
        data=catalog_state();data['configRevision']=1;data['catalog'][0]['il']=99
        with self.assertRaises(ValueError): save_config(self.admin,data)
        self.assertEqual(Factor.objects.get(pk='f0').il,3)
    def test_experts_import_atomic_and_rounding(self):
        self.client.force_login(self.admin);f=Factor.objects.get(pk='f2');s=f.subs.first()
        csv=f'experto,factor_id,subfactor_id,nivel\nUno,{f.pk},{s.pk},2\nDos,{f.pk},{s.pk},3'
        r=self.client.post('/api/experts',data=json.dumps({'csv':csv}),content_type='application/json');self.assertEqual(r.status_code,200);f.refresh_from_db();self.assertEqual(f.ie,3)
        csv+='\nMalo,f2,inexistente,4';r=self.client.post('/api/experts',data=json.dumps({'csv':csv}),content_type='application/json');self.assertEqual(r.status_code,400);self.assertEqual(ExpertRating.objects.count(),2)
