from django.contrib import admin

from django.contrib import admin
from .models import Question, Option

class OptionInline(admin.TabularInline):
    """
    Permite agregar las opciones de respuesta directamente 
    dentro del formulario de la pregunta.
    """
    model = Option
    extra = 4  # Muestra 4 espacios en blanco por defecto para las opciones

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'level', 'question_type')  # Columnas visibles
    list_filter = ('level', 'question_type')           # Filtros laterales
    search_fields = ('text', 'target_phrase')          # Barra de búsqueda
    inlines = [OptionInline]                           # Conecta las opciones aquí
