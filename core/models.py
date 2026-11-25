from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

LEVEL = [MinValueValidator(1), MaxValueValidator(4)]

class Organization(models.Model):
    name = models.CharField(max_length=120)
    sector = models.CharField(max_length=15, default='PRIVADO')
    size = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    def __str__(self): return self.name

class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=[(x,x) for x in ['Administrador','Decisor','Dirección']], default='Decisor')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.PROTECT)

class Software(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=30, blank=True)
    license = models.CharField(max_length=50, blank=True)
    provider = models.CharField(max_length=100, blank=True)
    purpose = models.TextField(blank=True)

class Dimension(models.Model):
    name = models.CharField(max_length=60, unique=True)
    def __str__(self): return self.name

class Factor(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    dimension = models.ForeignKey(Dimension, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    impact = models.CharField(max_length=7, choices=[(x,x) for x in ['INTERNO','EXTERNO','AMBOS']])
    il = models.PositiveSmallIntegerField(validators=LEVEL)
    ie = models.PositiveSmallIntegerField(validators=LEVEL)
    suggested = models.PositiveSmallIntegerField(validators=LEVEL)
    active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['dimension','name'],name='unique_factor_name'),models.CheckConstraint(condition=models.Q(il__range=(1,4),ie__range=(1,4),suggested__range=(1,4)),name='factor_levels')]
    def __str__(self): return self.name

class Subfactor(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    factor = models.ForeignKey(Factor, related_name='subs', on_delete=models.PROTECT)
    text = models.CharField(max_length=300)
    active = models.BooleanField(default=True)
    def __str__(self): return self.text

class Expert(models.Model):
    name = models.CharField(max_length=120, unique=True)

class ExpertRating(models.Model):
    expert = models.ForeignKey(Expert,on_delete=models.PROTECT)
    subfactor = models.ForeignKey(Subfactor,on_delete=models.PROTECT)
    level = models.PositiveSmallIntegerField(validators=LEVEL)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['expert','subfactor'],name='unique_expert_subfactor'),models.CheckConstraint(condition=models.Q(level__range=(1,4)),name='expert_level')]

class MatrixCell(models.Model):
    row = models.PositiveSmallIntegerField(validators=LEVEL)
    column = models.PositiveSmallIntegerField(validators=LEVEL)
    value = models.PositiveSmallIntegerField(validators=LEVEL)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['row','column'],name='unique_matrix_cell'),models.CheckConstraint(condition=models.Q(row__range=(1,4),column__range=(1,4),value__range=(1,4)),name='matrix_levels')]

class RecommendationTemplate(models.Model):
    category = models.CharField(max_length=20, unique=True)
    text = models.TextField()

class Evaluation(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    owner = models.ForeignKey(User,on_delete=models.PROTECT)
    software = models.ForeignKey(Software,on_delete=models.PROTECT)
    status = models.CharField(max_length=15, default='Borrador')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    finished = models.DateTimeField(null=True)
    step = models.PositiveSmallIntegerField(default=0)
    snapshot = models.JSONField()
    data = models.JSONField(default=dict)
    results = models.JSONField(default=list)
    decision = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status__in=['Borrador','Finalizada']),name='evaluation_status'),models.CheckConstraint(condition=models.Q(step__range=(0,5)),name='evaluation_step')]

class EvaluationFactor(models.Model):
    evaluation = models.ForeignKey(Evaluation,related_name='factor_results',on_delete=models.CASCADE)
    factor = models.ForeignKey(Factor,on_delete=models.PROTECT)
    importance = models.PositiveSmallIntegerField(validators=LEVEL)
    relative = models.PositiveSmallIntegerField(validators=LEVEL)
    impact = models.CharField(max_length=7)
    mean = models.FloatField()
    category = models.CharField(max_length=20)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['evaluation','factor'],name='unique_eval_factor'),models.CheckConstraint(condition=models.Q(importance__range=(1,4),relative__range=(1,4),mean__gte=1,mean__lte=4),name='result_levels')]

class EvaluationSubfactor(models.Model):
    evaluation_factor = models.ForeignKey(EvaluationFactor,on_delete=models.CASCADE)
    subfactor = models.ForeignKey(Subfactor,on_delete=models.PROTECT)
    rating = models.PositiveSmallIntegerField(validators=LEVEL)
    observation = models.CharField(max_length=2000,blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['evaluation_factor','subfactor'],name='unique_eval_subfactor'),models.CheckConstraint(condition=models.Q(rating__range=(1,4)),name='answer_level')]

class Recommendation(models.Model):
    evaluation = models.ForeignKey(Evaluation,related_name='recommendations',on_delete=models.CASCADE)
    evaluation_factor = models.ForeignKey(EvaluationFactor,on_delete=models.CASCADE)
    text = models.TextField()
    priority = models.PositiveSmallIntegerField()

class Configuration(models.Model):
    key = models.CharField(max_length=50,primary_key=True)
    value = models.JSONField(default=dict)

class AuditEvent(models.Model):
    user = models.ForeignKey(User,null=True,on_delete=models.SET_NULL)
    action = models.CharField(max_length=50)
    target = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
