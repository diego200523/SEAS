import re
from copy import deepcopy
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from .models import *
from .engine import MATRIX, CATEGORIES, level, calculate

def user_json(u):
    return {'id':str(u.pk),'name':u.first_name or u.username,'email':u.email,'role':u.role,'active':u.is_active,'organization':u.organization_id}

def catalog_state():
    matrix = deepcopy(MATRIX)
    for cell in MatrixCell.objects.all(): matrix[cell.row-1][cell.column-1]=cell.value
    catalog = [{'id':f.pk,'name':f.name,'dimension':f.dimension.name,'il':f.il,'ie':f.ie,'is':f.suggested,'impact':f.impact,'active':f.active,'subs':[{'id':s.pk,'text':s.text,'active':s.active} for s in f.subs.order_by('id')]} for f in Factor.objects.select_related('dimension').prefetch_related('subs').order_by('id')]
    catalog.sort(key=lambda f:(0,int(f['id'][1:])) if re.fullmatch(r'f\d+',f['id']) else (1,f['id']))
    for factor in catalog:
        factor['subs'].sort(key=lambda s:(0,int(s['id'].split('s')[-1])) if re.fullmatch(r'f\d+s\d+',s['id']) else (1,s['id']))
    return {'catalog':catalog,'matrix':matrix,'dimensions':list(Dimension.objects.values_list('name',flat=True)),'templates':dict(RecommendationTemplate.objects.values_list('category','text'))}

def snapshot():
    state = catalog_state()
    state['catalog'] = [{**f,'subs':[s for s in f['subs'] if s['active']]} for f in state['catalog'] if f['active']]
    state['catalog'] = [f for f in state['catalog'] if f['subs']]
    return state

def visible(user):
    qs=Evaluation.objects.select_related('owner','software__organization')
    if user.role=='Administrador': return qs
    if user.role=='Dirección':
        qs=qs.filter(status='Finalizada')
        return qs.filter(software__organization_id=user.organization_id) if user.organization_id else qs
    return qs.filter(owner=user)

def evaluation_json(e):
    s=e.software; o=s.organization
    return {**e.snapshot,**e.data,'id':e.pk,'owner':str(e.owner_id),'author':e.owner.first_name or e.owner.username,'org':o.name,'sector':o.sector,'size':o.size,'description':o.description,'software':s.name,'version':s.version,'license':s.license,'provider':s.provider,'purpose':s.purpose,'status':e.status,'created':e.created.isoformat(),'updated':e.updated.isoformat(),'finished':e.finished.isoformat() if e.finished else None,'step':e.step,'revision':e.revision,**({'finalResults':e.results,'finalDecision':e.decision} if e.status=='Finalizada' else {})}

def text_value(data,key,limit,required=False):
    value=data.get(key,'')
    if not isinstance(value,str) or len(value)>limit or (required and not value.strip()): raise ValueError(f'Campo inválido: {key} (máximo {limit} caracteres).')
    return value.strip()

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,50}',value): raise ValueError('Identificador inválido.')
    return value

@transaction.atomic
def save_evaluation(user, ident, payload):
    identifier(ident)
    if user.role not in ('Decisor','Administrador'): raise PermissionError('Su rol solo permite consultas.')
    e=Evaluation.objects.select_for_update().filter(pk=ident).first()
    if e:
        if e.owner_id != user.pk and user.role!='Administrador': raise PermissionError('No tiene acceso a esta evaluación.')
        if e.status=='Finalizada': raise ValueError('La evaluación está finalizada. Duplíquela para reevaluar.')
        if payload.get('revision')!=e.revision: raise ValueError('La evaluación cambió en otra sesión. Recargue antes de guardar.')
        snap=e.snapshot
    else:
        snap=snapshot()
    if not snap['catalog']: raise ValueError('Configure factores y subfactores activos antes de evaluar.')
    importance=payload.get('importance',{});answers=payload.get('answers',{});obs=payload.get('observations',{})
    factors={f['id'] for f in snap['catalog']};subs={s['id'] for f in snap['catalog'] for s in f['subs']}
    for values, keys in [(importance,factors),(answers,subs)]:
        if not isinstance(values,dict) or not set(values)<=keys: raise ValueError('La evaluación contiene referencias ajenas a su catálogo.')
        for v in values.values(): level(v)
    if not isinstance(obs,dict) or not set(obs)<=factors or any(not isinstance(v,str) or len(v)>2000 for v in obs.values()): raise ValueError('Observaciones inválidas (máximo 2000 caracteres por factor).')
    support=payload.get('support','')
    if support not in ('','INTERNO','EXTERNO'): raise ValueError('Impacto de soporte inválido.')
    step=payload.get('step',0)
    if type(step) is not int or not 0<=step<=5: raise ValueError('Paso inválido.')
    org_name=text_value(payload,'org',120)
    sector=payload.get('sector','PRIVADO')
    if sector not in ('PRIVADO','PUBLICO','INDEPENDIENTE'): raise ValueError('Sector inválido.')
    if e:
        org=e.software.organization;software=e.software
    else:
        org=Organization();software=Software()
    org.name=org_name;org.sector=sector;org.size=text_value(payload,'size',30);org.description=text_value(payload,'description',2000);org.save()
    software.organization=org;software.name=text_value(payload,'software',100);software.version=text_value(payload,'version',30);software.license=text_value(payload,'license',50);software.provider=text_value(payload,'provider',100);software.purpose=text_value(payload,'purpose',2000);software.save()
    if not e: e=Evaluation(id=ident,owner=user,software=software,snapshot=snap)
    else: e.revision+=1
    e.step=step;e.data={'importance':importance,'answers':answers,'observations':obs,'support':support};e.save()
    AuditEvent.objects.create(user=user,action='guardar_evaluacion',target=e.pk)
    return e

@transaction.atomic
def finalize(user,ident):
    e=visible(user).select_for_update(of=('self',)).get(pk=ident)
    if user.role=='Dirección': raise PermissionError('Su rol solo permite consultas.')
    if e.status=='Finalizada': return e
    if not e.software.name.strip() or not e.software.organization.name.strip(): raise ValueError('Organización y software son obligatorios.')
    results,decision=calculate(e.snapshot,e.data)
    for r in results:
        ef=EvaluationFactor.objects.create(evaluation=e,factor_id=r['id'],importance=e.data['importance'][r['id']],relative=r['ir'],impact=r['impact'],mean=r['pm'],category=r['foda'])
        EvaluationSubfactor.objects.bulk_create([EvaluationSubfactor(evaluation_factor=ef,subfactor_id=s['id'],rating=e.data['answers'][s['id']],observation=e.data['observations'].get(r['id'],'')) for s in r['subs']])
        Recommendation.objects.create(evaluation=e,evaluation_factor=ef,text=e.snapshot['templates'][r['foda']].replace('{factor}',r['name']),priority=1 if r['ir']>=3 and r['pm']<3 else 2)
    e.results=results;e.decision=decision;e.status='Finalizada';e.finished=timezone.now();e.step=5;e.revision+=1;e.save()
    AuditEvent.objects.create(user=user,action='finalizar_evaluacion',target=e.pk)
    return e

@transaction.atomic
def save_config(user,payload):
    if user.role!='Administrador': raise PermissionError('Solo administración puede modificar el catálogo.')
    # Lock a singleton to serialize catalog revisions across administrators.
    config,_=Configuration.objects.get_or_create(key='revision',defaults={'value':1})
    config=Configuration.objects.select_for_update().get(pk='revision')
    if payload.get('configRevision')!=config.value: raise ValueError('La configuración cambió en otra sesión. Recargue la página.')
    matrix=payload['matrix']
    if not isinstance(matrix,list) or len(matrix)!=4 or any(not isinstance(row,list) or len(row)!=4 for row in matrix): raise ValueError('La matriz debe tener 4 filas y 4 columnas.')
    for i,row in enumerate(matrix):
        for j,v in enumerate(row): MatrixCell.objects.update_or_create(row=i+1,column=j+1,defaults={'value':level(v)})
    dimensions=payload['dimensions']
    if not isinstance(dimensions,list) or not dimensions or len(dimensions)>30 or len(set(dimensions))!=len(dimensions): raise ValueError('Dimensiones inválidas.')
    for name in dimensions:
        if not isinstance(name,str) or not name.strip() or len(name)>60: raise ValueError('Nombre de dimensión inválido.')
        Dimension.objects.get_or_create(name=name)
    catalog=payload['catalog']
    if not isinstance(catalog,list) or len(catalog)>200: raise ValueError('Catálogo inválido.')
    factor_ids=set();sub_ids=set()
    for f in catalog:
        fid=identifier(f['id'])
        if fid in factor_ids: raise ValueError('Factor duplicado.')
        factor_ids.add(fid)
        if f['dimension'] not in dimensions or f['impact'] not in ('INTERNO','EXTERNO','AMBOS') or type(f['active']) is not bool: raise ValueError('Dimensión, impacto o estado inválido.')
        il,ie=level(f['il']),level(f['ie'])
        obj,_=Factor.objects.update_or_create(pk=fid,defaults={'name':text_value(f,'name',100,True),'dimension':Dimension.objects.get(name=f['dimension']),'impact':f['impact'],'il':il,'ie':ie,'suggested':matrix[ie-1][il-1],'active':f['active']})
        if not f['subs'] or len(f['subs'])>100: raise ValueError('Registre entre 1 y 100 subfactores por factor.')
        current=[]
        for s in f['subs']:
            sid=identifier(s['id'])
            if sid in sub_ids or type(s['active']) is not bool: raise ValueError('Subfactor duplicado o estado inválido.')
            if Subfactor.objects.filter(pk=sid).exclude(factor=obj).exists(): raise ValueError('No se permite trasladar subfactores entre factores.')
            sub_ids.add(sid);current.append(sid)
            Subfactor.objects.update_or_create(pk=sid,defaults={'factor':obj,'text':text_value(s,'text',300,True),'active':s['active']})
        obj.subs.exclude(pk__in=current).update(active=False)
    Factor.objects.exclude(pk__in=factor_ids).update(active=False)
    for category in CATEGORIES:
        template=text_value(payload['templates'],category,5000,True)
        RecommendationTemplate.objects.update_or_create(category=category,defaults={'text':template})
    for u in payload.get('users',[]):
        validate_email(u['email'])
        if u['role'] not in ('Administrador','Decisor','Dirección') or type(u['active']) is not bool: raise ValueError('Rol o estado inválido.')
        uid=str(u['id']);existing=User.objects.filter(pk=int(uid)).first() if uid.isdigit() else None
        if existing and existing.pk==user.pk and (not u['active'] or u['role']!='Administrador'): raise ValueError('Conserve activa su cuenta de administrador.')
        email=u['email'].lower().strip()
        if User.objects.filter(email__iexact=email).exclude(pk=existing.pk if existing else None).exists(): raise ValueError('El correo ya está registrado.')
        obj=existing or User(username=email)
        obj.email=email;obj.username=email;obj.first_name=text_value(u,'name',150,True);obj.role=u['role'];obj.is_active=u['active']
        organization=u.get('organization')
        if organization is not None and (type(organization) is not int or not Organization.objects.filter(pk=organization).exists()): raise ValueError('Organización inválida.')
        obj.organization_id=organization
        password=u.get('password')
        if not existing and not password: raise ValueError('Defina una contraseña para el nuevo usuario.')
        if password:
            validate_password(password,obj);obj.set_password(password)
        obj.save()
    config.value+=1;config.save()
    AuditEvent.objects.create(user=user,action='actualizar_configuracion',target=str(config.value))
    return config.value
