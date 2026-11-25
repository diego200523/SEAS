import csv
import io
import json
import uuid
from functools import wraps
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import escape
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from .services import *

def api(methods,auth=True,admin=False):
    def wrap(fn):
        @wraps(fn)
        def inner(request,*args,**kwargs):
            if request.method not in methods: return JsonResponse({'error':'Método no permitido.'},status=405)
            if auth and not request.user.is_authenticated: return JsonResponse({'error':'Inicie sesión para continuar.'},status=401)
            if admin and request.user.role!='Administrador': return JsonResponse({'error':'Acceso restringido a administración.'},status=403)
            try: return fn(request,*args,**kwargs)
            except PermissionError as e: return JsonResponse({'error':str(e)},status=403)
            except Evaluation.DoesNotExist: return JsonResponse({'error':'Evaluación no disponible.'},status=404)
            except (ValueError,KeyError,TypeError,ValidationError,IntegrityError) as e:
                message='Datos inválidos o duplicados.' if isinstance(e,(KeyError,TypeError,IntegrityError)) else str(e)
                return JsonResponse({'error':message},status=400)
        return inner
    return wrap

def body(request):
    data=json.loads(request.body)
    if not isinstance(data,dict): raise ValueError('Se esperaba un objeto JSON.')
    return data

@ensure_csrf_cookie
@require_GET
def home(request): return render(request,'index.html')

@api(['GET'],auth=False)
def state(request):
    if not request.user.is_authenticated: return JsonResponse({'session':None})
    data=catalog_state();u=request.user
    config,_=Configuration.objects.get_or_create(key='revision',defaults={'value':1})
    data.update(session=user_json(u),users=[user_json(x) for x in User.objects.order_by('pk')] if u.role=='Administrador' else [user_json(u)],evaluations=[evaluation_json(e) for e in visible(u).order_by('-updated')],configRevision=config.value)
    data['organizations']=list(Organization.objects.values('id','name')) if u.role=='Administrador' else []
    return JsonResponse(data)

@api(['POST'],auth=False)
def sign_in(request):
    data=body(request);email=text_value(data,'email',254,True).lower()
    throttle,_=Configuration.objects.get_or_create(key='login-'+__import__('hashlib').sha256(email.encode()).hexdigest()[:40],defaults={'value':{'count':0,'until':0}})
    stamp=timezone.now().timestamp()
    if throttle.value.get('until',0)>stamp: return JsonResponse({'error':'Demasiados intentos. Espere 5 minutos.'},status=429)
    account=User.objects.filter(email__iexact=email).first()
    user=authenticate(request,username=account.username if account else email,password=data.get('password',''))
    if not user:
        n=throttle.value.get('count',0)+1;throttle.value={'count':n if n<5 else 0,'until':stamp+300 if n>=5 else 0};throttle.save()
        return JsonResponse({'error':'Correo o contraseña incorrectos.'},status=401)
    throttle.value={'count':0,'until':0};throttle.save();login(request,user)
    AuditEvent.objects.create(user=user,action='iniciar_sesion',target=str(user.pk))
    return JsonResponse({'session':user_json(user)})

@api(['POST'])
def sign_out(request): logout(request);return JsonResponse({'ok':True})

@api(['PUT'])
def evaluation(request,ident): return JsonResponse(evaluation_json(save_evaluation(request.user,ident,body(request))))

@api(['POST'])
def finish(request,ident): return JsonResponse(evaluation_json(finalize(request.user,ident)))

@api(['POST'])
@transaction.atomic
def duplicate(request,ident):
    source=visible(request.user).get(pk=ident)
    if source.status!='Finalizada': raise ValueError('Solo se duplican evaluaciones finalizadas.')
    data=evaluation_json(source);current=snapshot()
    ids={f['id'] for f in current['catalog']};subids={s['id'] for f in current['catalog'] for s in f['subs']}
    data['importance']={k:v for k,v in data['importance'].items() if k in ids}
    data['answers']={};data['observations']={};data['step']=0
    return JsonResponse(evaluation_json(save_evaluation(request.user,uuid.uuid4().hex,data)),status=201)

@api(['PUT'],admin=True)
def config(request):
    save_config(request.user,body(request))
    return state(request)

@api(['POST'],admin=True)
@transaction.atomic
def experts(request):
    text=body(request).get('csv','')
    if not isinstance(text,str) or len(text)>500000: raise ValueError('El CSV supera el tamaño permitido.')
    rows=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if rows.fieldnames!=['experto','factor_id','subfactor_id','nivel']: raise ValueError('Encabezado CSV inválido.')
    seen=set();count=0;affected=set()
    for index,row in enumerate(rows,2):
        if None in row or None in row.values(): raise ValueError(f'Fila {index}: número de columnas inválido.')
        name=row['experto'].strip();sid=row['subfactor_id'].strip();fid=row['factor_id'].strip()
        sub=Subfactor.objects.filter(pk=sid,factor_id=fid).first()
        if not name or len(name)>120 or not sub or (name,sid) in seen: raise ValueError(f'Fila {index}: experto, referencia o duplicado inválido.')
        v=level(int(row['nivel']));seen.add((name,sid));expert,_=Expert.objects.get_or_create(name=name)
        ExpertRating.objects.update_or_create(expert=expert,subfactor=sub,defaults={'level':v});affected.add(fid);count+=1
    if not count: raise ValueError('El CSV no contiene valoraciones.')
    matrix=catalog_state()['matrix']
    for fid in affected:
        # Equal weight per subfactor; first average experts, then subfactor means.
        means=[]
        for sub in Subfactor.objects.filter(factor_id=fid,active=True):
            values=list(ExpertRating.objects.filter(subfactor=sub).values_list('level',flat=True))
            if not values: raise ValueError('Cada subfactor activo del factor afectado debe tener al menos una valoración; no se aplicaron cambios.')
            means.append(sum(Decimal(v) for v in values)/len(values))
        f=Factor.objects.get(pk=fid);f.ie=int((sum(means)/len(means)).quantize(Decimal('1'),rounding=ROUND_HALF_UP));f.suggested=matrix[f.ie-1][f.il-1];f.save()
    revision,_=Configuration.objects.get_or_create(key='revision',defaults={'value':1});revision.value+=1;revision.save()
    AuditEvent.objects.create(user=request.user,action='importar_expertos',target=str(count))
    return JsonResponse({'count':count,'factors':len(affected)})

@api(['GET'])
def pdf(request,ident):
    e=visible(request.user).get(pk=ident)
    if e.status!='Finalizada': raise ValueError('Finalice la evaluación antes de generar el informe.')
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    out=io.BytesIO();styles=getSampleStyleSheet()
    for style in styles.byName.values(): style.fontName='Helvetica'
    p=lambda t:Paragraph(escape(str(t)).replace('\n','<br/>'),styles['BodyText'])
    story=[Paragraph('SEAS | Informe de evaluación',styles['Title']),Spacer(1,16),p('Software: '+e.software.name+' '+e.software.version),p('Organización: '+e.software.organization.name),p('Responsable: '+(e.owner.first_name or e.owner.username)),p('Finalización: '+timezone.localtime(e.finished).strftime('%d/%m/%Y %H:%M')),p('Identificador: '+e.pk),Spacer(1,18),Paragraph(e.decision['text'],styles['Heading1']),p(e.decision['rule']),p(f"Factores críticos desfavorables: {e.decision['bad']} de {e.decision['total']}"),Spacer(1,16)]
    rows=[[p(x) for x in ['Factor','ID','IS','IR','PM','FODA']]]
    for r in e.results: rows.append([p(r['name']),p(e.data['importance'][r['id']]),p(r['is']),p(r['ir']),p(f"{r['pm']:.2f}"),p(r['foda'])])
    table=Table(rows,colWidths=[180,35,35,35,45,105],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5f3f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#dde6e9'))]));story.append(table)
    story.extend([Spacer(1,16),Paragraph('Recomendaciones',styles['Heading2'])])
    for r in e.recommendations.order_by('priority','pk'): story.extend([p(r.text),Spacer(1,8)])
    story.extend([Paragraph('Evidencia y respuestas',styles['Heading2'])])
    for r in e.results:
        block=[Paragraph(escape(r['name']),styles['Heading3'])]
        for s in r['subs']: block.append(p(f"{s['text']} — {e.data['answers'][s['id']]} / 4"))
        story.append(KeepTogether(block))
        if e.data['observations'].get(r['id']): story.append(p('Observaciones: '+e.data['observations'][r['id']]))
    story.extend([Spacer(1,16),p('Base metodológica: Rea Sánchez (2022), Universidad de Sevilla, capítulo 5. Catálogo SEAS adaptado; consulte METODOLOGIA.md. La decisión RN09 es una regla del proyecto y requiere juicio del responsable.')])
    def footer(canvas,doc):
        canvas.setFont('Helvetica',9);canvas.drawString(40,25,'SEAS | Resultados conservados al finalizar');canvas.drawRightString(555,25,str(doc.page))
    SimpleDocTemplate(out,pagesize=A4,leftMargin=40,rightMargin=40,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    response=HttpResponse(out.getvalue(),content_type='application/pdf');response['Content-Disposition']=f'attachment; filename="SEAS_{e.pk}.pdf"';return response
