/**
 * Lógica de validación interactiva para HU-01 (Login)
 * Cumple con la restricción de bloqueo de envío hasta validación completa.
 
document.addEventListener('DOMContentLoaded', () => {
    const emailInput = document.getElementById('email-input');
    const passwordInput = document.getElementById('password-input');
    const submitBtn = document.getElementById('submit-btn');
    const emailError = document.getElementById('email-error');

    function validarFormulario() {
        const emailValue = emailInput.value.trim();
        const passwordValue = passwordInput.value.trim();
        
        // Expresión regular para el formato de correo electrónico obligatorio (Paso 3)
        const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailValue);
        
        // Control visual del error en formato de correo electrónico
        if (emailValue !== "" && !emailValido) {
            emailError.style.display = 'block';
            emailInput.style.borderColor = 'var(--danger)';
        } else {
            emailError.style.display = 'none';
            emailInput.style.borderColor = emailValido ? 'var(--secondary)' : 'var(--g200)';
        }

        // Activación/Bloqueo dinámico del botón según criterios de aceptación (Paso 3)
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
*/

 

document.addEventListener('DOMContentLoaded', () => {
    const emailInput = document.getElementById('email-input');
    const passwordInput = document.getElementById('password-input');
    const submitBtn = document.getElementById('submit-btn');
    const emailError = document.getElementById('email-error');

    function validarFormulario() {
        const emailValue = emailInput.value.trim();
        const passwordValue = passwordInput.value.trim();
        
        // Criterios de desarrollo: es un correo válido o es un nombre de usuario de administrador (sin @)
        const esEmailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailValue);
        const esUsuarioAdmin = emailValue.length > 0 && !emailValue.includes('@');
        
        const identificadorValido = esEmailValido || esUsuarioAdmin;

        // Solo mostramos alerta visual si intentó poner un correo y le falta el formato
        if (emailValue.includes('@') && !esEmailValido) {
            emailError.style.display = 'block';
            emailInput.style.borderColor = 'var(--danger)';
        } else {
            emailError.style.display = 'none';
            emailInput.style.borderColor = identificadorValido ? 'var(--secondary)' : 'var(--g200)';
        }

        // El botón se enciende si el identificador es válido y hay contraseña escrita
        if (identificadorValido && passwordValue.length > 0) {
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

    if (emailInput && passwordInput) {
        emailInput.addEventListener('input', validarFormulario);
        passwordInput.addEventListener('input', validarFormulario);
    }
});