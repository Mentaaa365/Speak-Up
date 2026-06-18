from django.contrib import admin
from .models import NivelMCER, Submodulo, Ejercicio

@admin.register(NivelMCER)
class NivelMCERAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'orden')
    ordering = ('orden',)

@admin.register(Submodulo)
class SubmoduloAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'nivel', 'orden')
    list_filter = ('nivel',)
    ordering = ('nivel__orden', 'orden')

@admin.register(Ejercicio)
class EjercicioAdmin(admin.ModelAdmin):
    # Esto te permitirá buscar y filtrar los ejercicios fácilmente cuando tengas muchos
    list_display = ('texto_objetivo', 'submodulo', 'nivel_dificultad')
    list_filter = ('submodulo__nivel', 'submodulo__tipo')
    search_fields = ('texto_objetivo',)