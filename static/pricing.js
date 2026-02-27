(function () {
  'use strict';

  var contactOverlay = document.getElementById('contactOverlay');
  var contactBackdrop = document.getElementById('contactBackdrop');
  var contactClose = document.getElementById('contactClose');
  var contactForm = document.getElementById('contactForm');
  var contactSuccess = document.getElementById('contactSuccess');

  document.querySelectorAll('[data-plan]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var plan = btn.getAttribute('data-plan');
      window.location.href = '/billing?plan=' + encodeURIComponent(plan);
    });
  });

  function openContactModal() {
    contactForm.style.display = '';
    contactSuccess.style.display = 'none';
    contactOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeContactModal() {
    contactOverlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  contactClose.addEventListener('click', closeContactModal);
  contactBackdrop.addEventListener('click', closeContactModal);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeContactModal();
  });

  document.getElementById('contactUsBtn').addEventListener('click', openContactModal);

  contactForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    var submitBtn = document.getElementById('contactSubmit');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Sending...</span>';

    var formData = {
      name: contactForm.querySelector('[name="name"]').value.trim(),
      email: contactForm.querySelector('[name="email"]').value.trim(),
      phone: contactForm.querySelector('[name="phone"]').value.trim(),
      company: contactForm.querySelector('[name="company"]').value.trim(),
      message: contactForm.querySelector('[name="message"]').value.trim()
    };

    try {
      await fetch('/api/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
    } catch (err) {}

    contactForm.style.display = 'none';
    contactSuccess.style.display = 'block';

    setTimeout(function () {
      closeContactModal();
      setTimeout(function () {
        contactForm.style.display = '';
        contactSuccess.style.display = 'none';
        contactForm.reset();
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span>Send Message</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
      }, 500);
    }, 3000);
  });
})();
