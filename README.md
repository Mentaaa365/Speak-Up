# 🎓 SpeakUp

## 📖 Descripción

SpeakUp es una plataforma web inteligente para el aprendizaje del idioma inglés, diseñada principalmente para estudiantes de bachillerato ecuatorianos.

El sistema utiliza Inteligencia Artificial, reconocimiento de voz (Speech-to-Text y Text-to-Speech) y aprendizaje adaptativo para ayudar a los estudiantes a mejorar sus habilidades de:

- 🎧 Listening (Comprensión Auditiva)
- 🗣️ Speaking (Expresión Oral)
- ✍️ Writing (Expresión Escrita)
- 🎵 Aprendizaje mediante Música

La plataforma ofrece una experiencia interactiva inspirada en aplicaciones modernas de aprendizaje de idiomas, proporcionando retroalimentación inmediata, seguimiento del progreso y actividades personalizadas según el nivel de cada estudiante.

---

## 🎯 Objetivo

Desarrollar una plataforma educativa inteligente que permita a los estudiantes mejorar sus competencias en inglés mediante ejercicios interactivos, evaluación automática y herramientas basadas en inteligencia artificial.

---

## 🚀 Funcionalidades Principales

### 🔐 Gestión de Usuarios
- Registro de usuarios.
- Inicio de sesión seguro.
- Recuperación de contraseña.
- Gestión de perfiles.

### 📊 Diagnóstico Inicial
- Evaluación automática del nivel de inglés.
- Clasificación según el Marco Común Europeo de Referencia (MCER).
- Niveles A1, A2 y B1.

### 📚 Aprendizaje por Niveles
- Actividades de vocabulario.
- Ejercicios de lectura.
- Prácticas de pronunciación.
- Adaptación automática de dificultad.

### 🎵 Aprendizaje con Música
- Canciones adaptadas al nivel del estudiante.
- Ejercicios de comprensión auditiva.
- Prácticas de pronunciación utilizando letras musicales.

### 🤖 Entrevistas con Inteligencia Artificial
- Conversaciones dinámicas con IA.
- Evaluación de fluidez oral.
- Retroalimentación personalizada.

### 📝 Evaluaciones y Certificación
- Exámenes de promoción entre niveles.
- Seguimiento de intentos.
- Certificados digitales al completar los niveles establecidos.

### 📈 Seguimiento de Progreso
- Barra de progreso global.
- Seguimiento por nivel.
- Seguimiento por actividades.
- Guardado automático del avance.

---

## 🏗️ Arquitectura

El proyecto sigue una arquitectura de **Monolito Modular** utilizando el patrón **MTV (Model - Template - View)** de Django.

Los módulos principales son:

- Authentication
- Diagnosis
- Learning
- Exams
- Progress
- Question Bank

---

## 🛠️ Tecnologías Utilizadas

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Django 5

### Base de Datos
- SQL Server

### Inteligencia Artificial y Voz
- APIs de Inteligencia Artificial
- Speech To Text (STT)
- Text To Speech (TTS)

### Seguridad
- HTTPS
- bcrypt
- Sesiones seguras de Django
- Protección CSRF

---

## 👥 Público Objetivo

- Estudiantes de bachillerato ecuatorianos.
- Estudiantes con niveles de inglés A1, A2 y B1.
- Personas interesadas en mejorar sus habilidades comunicativas en inglés.

---

## 🌟 Beneficios

- Aprendizaje personalizado.
- Retroalimentación inmediata.
- Mejora de la pronunciación.
- Desarrollo de habilidades de listening y speaking.
- Mayor motivación mediante actividades interactivas y musicales.
- Seguimiento continuo del progreso académico.

---

## 📋 Requisitos

- Python 3.12 o superior
- Django 5.x
- SQL Server
- Navegador moderno (Chrome o Firefox)
- Conexión a Internet
- Micrófono para actividades de speaking

---

## 🗄️ Database Seeding

After running migrations (`python manage.py migrate`), populate the database with the following commands **in this order**:

```bash
# 1. Levels, submodules, exercises (music LRC + writing), and WRITING questions
python manage.py seed_curriculum_data

# 2. Promotion exam questions (SPEAKING, LISTENING, CHOICE) for all levels
python manage.py seed_promo_questions

# 3. Diagnostic questions (SPEAKING, LISTENING, CHOICE) from CSV
python poblar_bd.py
```

| Command | What it loads | bank_context |
|---------|--------------|--------------|
| `seed_curriculum_data` | NivelMCER (A1/A2/B1), Submodulos (4 per level), music exercises with LRC, writing exercises, WRITING questions | DIAGNOSTIC + PROMOTION_EXAM |
| `seed_promo_questions` | SPEAKING, LISTENING, CHOICE questions for promotion exams | PROMOTION_EXAM |
| `poblar_bd.py` | SPEAKING, LISTENING, CHOICE questions from `preguntas.csv` | DIAGNOSTIC |

All three are idempotent — they use `get_or_create` and can be run multiple times without duplicating data. Use `python poblar_bd.py --reset` to clear the question bank before reloading (requires confirmation).

---

## 👨‍💻 Equipo de Desarrollo

| Integrante | Rol |
|------------|------|
| Oscar Pilataxi | Líder del Proyecto |
| Ian Poveda | Desarrollador Frontend |
| Emanuel Tito | Desarrollador Backend |

---

## 📚 Proyecto Académico

Proyecto desarrollado para la asignatura de Construcción de Software de la Carrera de Ingeniería de Software.

**Universidad Estatal de Milagro (UNEMI)**

---

### 🇪🇨 SpeakUp
*"Aprender inglés de forma inteligente, interactiva y adaptada a cada estudiante."*
