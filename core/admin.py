from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

@admin.register(User)
class SEASUserAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets+(('SEAS',{'fields':('role','organization')}),)
    add_fieldsets=UserAdmin.add_fieldsets+(('SEAS',{'fields':('email','role','organization')}),)

admin.site.site_header='Administración técnica de SEAS'
for model in [Organization,Dimension,Factor,Subfactor,Expert,ExpertRating,MatrixCell,RecommendationTemplate]: admin.site.register(model)

@admin.register(AuditEvent)
class AuditAdmin(admin.ModelAdmin):
    list_display=('created','user','action','target')
    readonly_fields=('created','user','action','target')
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False
