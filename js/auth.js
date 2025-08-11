const container = document.getElementById('auth-container');
const formTitle = document.getElementById('form-title');
const authForm = document.getElementById('auth-form');
const toggleFormLink = document.getElementById('toggle-form');
const submitBtn = document.getElementById('submit-btn');
const messageDiv = document.getElementById('message');

let isLogin = true;

toggleFormLink.addEventListener('click', () => {
  isLogin = !isLogin;
  if (isLogin) {
    formTitle.textContent = 'تسجيل الدخول';
    submitBtn.textContent = 'دخول';
    toggleFormLink.textContent = 'ليس لديك حساب؟ سجل الآن';
    // إزالة حقل الاسم إذا موجود
    const nameInput = document.getElementById('name');
    if(nameInput) nameInput.remove();
  } else {
    formTitle.textContent = 'إنشاء حساب جديد';
    submitBtn.textContent = 'تسجيل';
    toggleFormLink.textContent = 'لديك حساب؟ سجل دخول';
    // إضافة حقل الاسم
    if (!document.getElementById('name')) {
      const nameInput = document.createElement('input');
      nameInput.setAttribute('type', 'text');
      nameInput.setAttribute('id', 'name');
      nameInput.setAttribute('placeholder', 'الاسم الكامل');
      nameInput.required = true;
      authForm.insertBefore(nameInput, authForm.firstChild);
    }
  }
  messageDiv.textContent = '';
  authForm.reset();
});

authForm.addEventListener('submit', (e) => {
  e.preventDefault();
  messageDiv.style.color = '#d00000'; // افتراضياً احمر للخطأ
  if(isLogin) {
    // محاكاة تسجيل الدخول
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    if(email === "user@eduvia.com" && password === "123456") {
      messageDiv.style.color = '#007700';
      messageDiv.textContent = 'تم تسجيل الدخول بنجاح! جاري تحويلك...';
      setTimeout(() => {
        window.location.href = 'dashboard.html';
      }, 1500); // 1.5 ثانية قبل التحويل
    } else {
      messageDiv.textContent = 'البريد الإلكتروني أو كلمة المرور غير صحيحة.';
    }
  } else {
    // محاكاة تسجيل حساب
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    if(name.length < 3) {
      messageDiv.textContent = 'الاسم يجب أن يكون 3 أحرف على الأقل.';
      return;
    }
    if(password.length < 6) {
      messageDiv.textContent = 'كلمة المرور يجب أن تكون 6 أحرف على الأقل.';
      return;
    }
    messageDiv.style.color = '#007700';
        messageDiv.textContent = `تم إنشاء الحساب بنجاح يا ${name}! سيتم تحويلك لتسجيل الدخول.`;
        setTimeout(() => {
          // In a real app, you might auto-login, but here we go to the login page.
          isLogin = true; // Set state back to login
          formTitle.textContent = 'تسجيل الدخول';
          submitBtn.textContent = 'دخول';
          toggleFormLink.textContent = 'ليس لديك حساب؟ سجل الآن';
          const nameInput = document.getElementById('name');
          if(nameInput) nameInput.remove();
          authForm.reset();
          messageDiv.textContent = 'تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول.';
        }, 2000);
  }
});
