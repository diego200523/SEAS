import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import *

class Command(BaseCommand):
    help='Carga el catálogo y crea el administrador inicial sin sobrescribir datos existentes.'
    @transaction.atomic
    def handle(self,*args,**kwargs):
        seed=json.loads((Path(__file__).resolve().parents[2]/'data/catalog.json').read_text(encoding='utf-8'))
        for name in seed['dimensions']: Dimension.objects.get_or_create(name=name)
        for f in seed['catalog']:
            factor,_=Factor.objects.get_or_create(pk=f['id'],defaults={'dimension':Dimension.objects.get(name=f['dimension']),'name':f['name'],'impact':f['impact'],'il':f['il'],'ie':f['ie'],'suggested':f['is'],'active':True})
            for s in f['subs']: Subfactor.objects.get_or_create(pk=s['id'],defaults={'factor':factor,'text':s['text'],'active':True})
        for i,row in enumerate(seed['matrix']):
            for j,value in enumerate(row): MatrixCell.objects.get_or_create(row=i+1,column=j+1,defaults={'value':value})
        for category,text in seed['templates'].items(): RecommendationTemplate.objects.get_or_create(category=category,defaults={'text':text})
        Configuration.objects.get_or_create(key='revision',defaults={'value':1})
        email=os.environ.get('SEAS_ADMIN_EMAIL');password=os.environ.get('SEAS_ADMIN_PASSWORD')
        if email and not User.objects.filter(email=email.lower()).exists():
            if not password: raise CommandError('Configure SEAS_ADMIN_PASSWORD para crear el administrador.')
            from django.contrib.auth.password_validation import validate_password
            validate_password(password)
            User.objects.create_superuser(username=email.lower(),email=email.lower(),password=password,first_name='Administrador SEAS',role='Administrador')
        self.stdout.write(self.style.SUCCESS(f'Catálogo disponible: {Factor.objects.count()} factores y {Subfactor.objects.count()} subfactores.'))
