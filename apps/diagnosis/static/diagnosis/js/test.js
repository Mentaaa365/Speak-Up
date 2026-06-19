document.addEventListener('DOMContentLoaded', () => {
    // 1. VARIABLES GLOBALES
    let questions = []; 
    let currentIndex = 0;
    
    // Almacena las respuestas exactas (o transcripciones) para enviarlas al backend
    let userAnswers = [];
    
    // Variables de control
    let playCount = 0; 
    let lastTranscript = "";

    // Elementos del DOM
    const questionCategory = document.getElementById('question-category');
    const questionText = document.getElementById('question-text');
    const optionsContainer = document.getElementById('options-container');
    const btnNext = document.getElementById('btn-next');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressPercentage = document.getElementById('progress-percentage');
    
    const btnTts = document.getElementById('btn-tts');
    const btnStt = document.getElementById('btn-stt');
    const sttFeedback = document.getElementById('stt-feedback');

    // 2. INICIALIZACIÓN Y RECUPERACIÓN DE CACHÉ LOCAL
    const inicializarExamen = () => {
        const savedProgress = localStorage.getItem('diagnostic_progress');
        if (savedProgress) {
            const data = JSON.parse(savedProgress);
            currentIndex = data.currentIndex;
            userAnswers = data.answers;
        }
        cargarPreguntasDesdeBD();
    };

    const cargarPreguntasDesdeBD = () => {
        fetch('/diagnosis/api/get-questions/')
            .then(response => response.json())
            .then(data => {
                questions = data.questions;
                if (currentIndex >= questions.length) {
                    // Si por algún error la caché tiene un índice mayor a las preguntas, limpiamos
                    localStorage.removeItem('diagnostic_progress');
                    currentIndex = 0;
                    userAnswers = [];
                }
                loadQuestion();
            })
            .catch(error => {
                console.error("Error al cargar:", error);
                alert("Error al conectar con la base de datos.");
            });
    };

    // 3. MOTOR TTS (Con límite de 2 reproducciones)
    const speakText = (text) => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 0.9;
        window.speechSynthesis.speak(utterance);
    };

    btnTts.onclick = () => {
        if (playCount < 2) {
            speakText(questions[currentIndex].audioText);
            playCount++;
            if (playCount >= 2) {
                btnTts.disabled = true;
                btnTts.style.opacity = "0.5";
                btnTts.textContent = "🔊 Límite de reproducciones alcanzado";
            }
        }
    };

    // 4. MOTOR STT CON BLINDAJE DE SEGURIDAD
    const startListening = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert("Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge.");
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        
        sttFeedback.style.display = 'block';
        sttFeedback.innerHTML = "<span style='color: var(--secondary); font-weight: 700;'>Escuchando... 🎙️</span>";
        btnStt.disabled = true;

        recognition.start();

        recognition.onresult = (event) => {
            lastTranscript = event.results[0][0].transcript.trim();
            sttFeedback.innerHTML = `Tu respuesta grabada: <b>"${lastTranscript}"</b>`;
            btnStt.disabled = false;
            btnStt.innerHTML = "🔄 Volver a intentar"; // Permite reintentar si no le gustó cómo quedó
        };

        recognition.onerror = (e) => {
            console.error("Error de voz detectado:", e.error);
            sttFeedback.innerHTML = `
                <div style="margin-top:10px;">
                    <p style="color:var(--danger); font-size:13px; font-weight:600;">
                        Error: ${e.error}. Verifica tu micrófono o conexión a internet e intenta nuevamente.
                    </p>
                </div>
            `;
            btnStt.disabled = false;
        };
    };

    btnStt.onclick = startListening;

    // 5. RENDERIZAR PREGUNTA
    const loadQuestion = () => {
        const q = questions[currentIndex];
        
        // Actualizar barra de progreso
        const progress = (currentIndex / questions.length) * 100;
        progressBar.style.width = `${progress}%`;
        progressPercentage.textContent = `${Math.round(progress)}%`;
        progressText.textContent = `Pregunta ${currentIndex + 1} de ${questions.length}`;

        // Limpiar estados previos
        questionCategory.style.display = 'inline-block';
        questionCategory.textContent = q.type;
        questionText.innerHTML = q.text;

        optionsContainer.innerHTML = '';
        btnTts.style.display = 'none';
        btnTts.disabled = false;
        btnTts.style.opacity = "1";
        btnTts.innerHTML = "🔊 Escuchar Audio";
        
        btnStt.style.display = 'none';
        btnStt.innerHTML = "🎙️ Empezar a hablar";
        btnStt.disabled = false;
        
        sttFeedback.style.display = 'none';
        sttFeedback.innerHTML = '';
        
        playCount = 0;
        lastTranscript = "";

        // Mostrar elementos según el tipo de pregunta
        if (q.type === 'CHOICE' || q.type === 'LISTENING') {
            optionsContainer.style.display = 'grid';
            q.options.forEach(opt => {
                const label = document.createElement('label');
                label.style.cssText = "display: flex; align-items: center; gap: 16px; padding: 18px; border: 2px solid var(--g200); border-radius: 12px; cursor: pointer; transition: all 0.2s ease;";
                label.innerHTML = `
                    <input type="radio" name="answer" value="${opt.id}" style="width: 20px; height: 20px; accent-color: var(--primary);">
                    <span style="font-size: 15px; color: var(--g800);">${opt.text}</span>
                `;
                // Efecto visual al seleccionar
                label.addEventListener('click', () => {
                    document.querySelectorAll('#options-container label').forEach(l => l.style.borderColor = 'var(--g200)');
                    label.style.borderColor = 'var(--primary)';
                });
                optionsContainer.appendChild(label);
            });

            if (q.type === 'LISTENING') {
                btnTts.style.display = 'inline-flex';
            }
        } else if (q.type === 'SPEAKING') {
            optionsContainer.style.display = 'none';
            btnStt.style.display = 'inline-flex';
        } else if (q.type === 'WRITING') {
            optionsContainer.style.display = 'block';
            optionsContainer.innerHTML = `
                <textarea id="writing-answer" rows="6" placeholder="Write your answer in English..."
                    style="width: 100%; padding: 16px; border: 2px solid var(--g200); border-radius: 12px;
                    font-size: 15px; font-family: inherit; resize: vertical; box-sizing: border-box;"></textarea>
            `;
        }
    };

    // 6. NAVEGACIÓN Y ENVÍO SEGURO AL SERVIDOR
    btnNext.addEventListener('click', () => {
        const q = questions[currentIndex];
        let answerToSave = "";

        if (q.type === 'WRITING') {
            const textarea = document.getElementById('writing-answer');
            if (!textarea || !textarea.value.trim()) return alert("Por favor, escribe tu respuesta para continuar.");
            answerToSave = textarea.value.trim();
        } else if (q.type === 'SPEAKING') {
            if (!lastTranscript) return alert("Por favor, graba tu respuesta usando el micrófono.");
            answerToSave = lastTranscript;
        } else {
            const selected = document.querySelector('input[name="answer"]:checked');
            if (!selected) return alert("Por favor, selecciona una opción para continuar.");
            answerToSave = selected.value;
        }

        userAnswers.push({
            questionId:   q.id,
            type:         q.type,
            answer:       answerToSave,
            optionId:     (q.type !== 'SPEAKING' && q.type !== 'WRITING') ? answerToSave : '',
            targetPhrase: q.targetPhrase || '',
        });

        // Avanzar a la siguiente pregunta
        currentIndex++;

        // Si hay más preguntas, guardamos progreso y cargamos la siguiente
        if (currentIndex < questions.length) {
            localStorage.setItem('diagnostic_progress', JSON.stringify({
                currentIndex: currentIndex,
                answers: userAnswers
            }));
            loadQuestion();
        } else {
            // TEST FINALIZADO
            btnNext.disabled = true;
            btnNext.textContent = "Evaluando...";
            
            // Limpiar caché
            localStorage.removeItem('diagnostic_progress');

            // Crear formulario oculto para enviar a Django
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/diagnosis/results/'; // URL de tu vista procesadora
            
            const csrfTokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrfTokenElement ? csrfTokenElement.value : '';
            form.appendChild(csrfInput);

            // Pasamos todo el arreglo de respuestas como un string JSON
            const dataInput = document.createElement('input');
            dataInput.type = 'hidden';
            dataInput.name = 'answers_data';
            dataInput.value = JSON.stringify(userAnswers); 
            form.appendChild(dataInput);

            document.body.appendChild(form);
            form.submit(); 
        }
    });

    // Arrancar el sistema
    inicializarExamen();
});