/**
 * Lógica de validación interactiva para HU-01 (Login)
 * Cumple con la restricción de bloqueo de envío hasta validación completa por correo.
 */
document.addEventListener('DOMContentLoaded', () => {
    const emailInput = document.getElementById('email-input');
    const passwordInput = document.getElementById('password-input');
    const submitBtn = document.getElementById('submit-btn');
    const emailError = document.getElementById('email-error');

    function validarFormulario() {
        const emailValue = emailInput.value.trim();
        const passwordValue = passwordInput.value.trim();
        
        // Expresión regular estricta para el formato de correo electrónico
        const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailValue);
        
        // Control visual del error en formato de correo electrónico
        if (emailValue !== "" && !emailValido) {
            emailError.style.display = 'block';
            emailInput.style.borderColor = 'var(--danger)';
        } else {
            emailError.style.display = 'none';
            emailInput.style.borderColor = emailValido ? 'var(--secondary)' : 'var(--g200)';
        }

        // Activación/Bloqueo dinámico del botón (Solo se activa con correo válido y contraseña)
        if (emailValido && passwordValue.length > 0) {
            submitBtn.disabled = false;
            submitBtn.style.background = 'var(--primary)';
            submitBtn.style.color = '#FFFFFF';
            submitBtn.style.cursor = 'pointer';
        } else {
            submitBtn.disabled = true;
            submitBtn.style.background = 'var(--g300)';
            submitBtn.style.color = 'var(--g500)';
            submitBtn.style.cursor = 'not-allowed';
        }
    }

    // Escuchadores de eventos para ejecución en tiempo real
    if (emailInput && passwordInput) {
        emailInput.addEventListener('input', validarFormulario);
        passwordInput.addEventListener('input', validarFormulario);
    }
});