(function () {
  'use strict';

  /* ══ PRICING CALCULATOR ══ */
  var COST_PER_DIAL   = 0.015;   // Telnyx + ElevenLabs per dial
  var HUMAN_SDR_COST  = 5000;    // avg human SDR monthly cost

  var dialSlider    = document.getElementById('dialSlider');
  var daysSlider    = document.getElementById('daysSlider');
  var dialDisplay   = document.getElementById('dialDisplay');
  var daysDisplay   = document.getElementById('daysDisplay');
  var platformFeeEl = document.getElementById('platformFeeDisplay');
  var usageEl       = document.getElementById('usageDisplay');
  var usageNoteEl   = document.getElementById('usageNote');
  var totalEl       = document.getElementById('totalDisplay');
  var vsUsEl        = document.getElementById('vsUsDisplay');
  var savingsPill   = document.getElementById('savingsPill');
  var planBadgeEl   = document.getElementById('planBadge');
  var calcCtaBtn    = document.getElementById('calcCtaBtn');

  function fmt(n) {
    return '$' + Math.round(n).toLocaleString('en-US');
  }

  function updateCalc() {
    var dials = parseInt(dialSlider.value, 10);
    var days  = parseInt(daysSlider.value, 10);

    var isBusiness   = dials > 300;
    var platformFee  = isBusiness ? 399 : 99;
    var planLabel    = isBusiness ? 'Business Plan' : 'Starter Plan';
    var planSlug     = isBusiness ? 'business' : 'starter';

    var usage  = dials * days * COST_PER_DIAL;
    var total  = platformFee + usage;
    var saving = HUMAN_SDR_COST - total;

    dialDisplay.textContent  = dials.toLocaleString('en-US');
    daysDisplay.textContent  = days;
    platformFeeEl.textContent = fmt(platformFee);
    usageEl.textContent       = fmt(usage);
    usageNoteEl.textContent   = dials.toLocaleString('en-US') + ' dials × ' + days + ' days × $' + COST_PER_DIAL.toFixed(3) + '/dial';
    totalEl.textContent       = fmt(total) + ' / mo';
    vsUsEl.textContent        = fmt(total);
    savingsPill.textContent   = 'Save ~' + fmt(Math.max(0, saving)) + '/mo';

    planBadgeEl.textContent   = planLabel;
    planBadgeEl.classList.toggle('business', isBusiness);

    calcCtaBtn.setAttribute('data-plan', planSlug);
    calcCtaBtn.setAttribute('data-amount', platformFee);
    calcCtaBtn.textContent = 'Get Started for ' + fmt(platformFee) + '/mo →';

    /* live-fill the slider track color behind the thumb */
    [dialSlider, daysSlider].forEach(function(sl) {
      var pct = ((sl.value - sl.min) / (sl.max - sl.min)) * 100;
      sl.style.background = 'linear-gradient(to right, #1a1a1a ' + pct + '%, #e5e7eb ' + pct + '%)';
    });
  }

  if (dialSlider && daysSlider) {
    dialSlider.addEventListener('input', updateCalc);
    daysSlider.addEventListener('input', updateCalc);
    updateCalc();

    calcCtaBtn.addEventListener('click', function() {
      var plan = calcCtaBtn.getAttribute('data-plan') || 'starter';
      window.location.href = '/billing?plan=' + encodeURIComponent(plan);
    });
  }



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
