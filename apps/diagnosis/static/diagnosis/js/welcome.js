/**
 * Controlador para UC3 - Examen de Diagnóstico (Fase de Bienvenida)
 * Comprueba de forma asíncrona la disponibilidad del micrófono antes de liberar el examen.
 */
document.addEventListener('DOMContentLoaded', () => {
    const micStatusBox = document.getElementById('mic-status-box');
    const micIcon = document.getElementById('mic-icon');
    const micTitle = document.getElementById('mic-title');
    const micDesc = document.getElementById('mic-desc');
    const startBtn = document.getElementById('start-test-btn');

    async function verificarMicrofono() {
        try {
            // Intenta solicitar acceso al micrófono del sistema (Paso 1)
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Si el flujo es exitoso, actualizamos los componentes visuales (RNF-04)
            micStatusBox.style.background = 'var(--secondary-light)';
            micStatusBox.style.borderColor = 'var(--secondary)';
            micIcon.textContent = '🎤';
            micTitle.textContent = '¡Micrófono listo y detectado con éxito! ✓';
            micDesc.textContent = 'Los niveles de hardware son estables. Ya puedes iniciar tu evaluación de diagnóstico.';
            
            // Habilitar el botón de envío
            startBtn.disabled = false;
            startBtn.textContent = 'Iniciar Examen Oficial →';
            startBtn.style.background = 'var(--primary)';
            startBtn.style.color = '#FFFFFF';
            startBtn.style.cursor = 'pointer';

            // Liberamos el micrófono inmediatamente para no dejarlo encendido innecesariamente
            stream.getTracks().forEach(track => track.stop());

            // Escuchador para avanzar a la ejecución del examen
            startBtn.addEventListener('click', () => {
                window.location.href = '/diagnosis/test/';
            });

        } catch (error) {
            // Excepción Paso 1: Micrófono denegado, ocupado o inexistente
            console.warn('Acceso al hardware denegado:', error);
            micStatusBox.style.background = 'var(--danger-light)';
            micStatusBox.style.borderColor = 'var(--danger)';
            micIcon.textContent = '❌';
            micTitle.textContent = 'Acceso al micrófono bloqueado';
            micDesc.innerHTML = 'El examen requiere hardware de grabación activo. <strong>Instrucciones para continuar:</strong><br>' +
                                '1. En <strong>Google Chrome / Firefox</strong>: haz clic en el icono del candado junto a la URL (127.0.0.1).<br>' +
                                '2. Cambia el permiso de "Micrófono" de "Bloquear" a "Permitir".<br>' +
                                '3. Recarga la página (F5).';
            
            startBtn.disabled = true;
            startBtn.textContent = 'Esperando hardware de audio...';
            startBtn.style.background = 'var(--g300)';
            startBtn.style.color = 'var(--g500)';
            startBtn.style.cursor = 'not-allowed';
        }
    }

    // Ejecuta la prueba automática al cargar la vista
    verificarMicrofono();
});