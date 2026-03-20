(function () {
  'use strict';

  /* ══ PRICING CONSTANTS ══ */
  var BASE_COST_PER_DIAL      = 0.020;
  var SDR_COST_PER_UNIT       = 5000;   // fully-loaded monthly cost per human SDR
  var SDR_CALLS_PER_DAY       = 550;    // realistic power-dialer capacity
  var SDR_WORKING_DAYS        = 22;     // standard SDR working days / month
  var SDR_MONTHLY_CAPACITY    = SDR_CALLS_PER_DAY * SDR_WORKING_DAYS; // 12,100

  var ADDONS = [
    { id: 'personalizedVm', label: 'Personalized AI Voicemails', costPerDial: 0.04, monthlyFlat: 0 },
    { id: 'liveTransfer',   label: 'Live Call Transfer',          costPerDial: 0.02, monthlyFlat: 0 },
    { id: 'gatekeeper',     label: 'Gatekeeper Navigator',        costPerDial: 0.05, monthlyFlat: 0 },
    { id: 'transcription',  label: 'Recording & Transcription',   costPerDial: 0.05, monthlyFlat: 0 },
    { id: 'voiceCloning',   label: 'Voice Cloning',               costPerDial: 0,    monthlyFlat: 19 }
  ];

  /* ── DOM refs ── */
  var dialSlider        = document.getElementById('dialSlider');
  var daysSlider        = document.getElementById('daysSlider');
  var dialDisplay       = document.getElementById('dialDisplay');
  var daysDisplay       = document.getElementById('daysDisplay');
  var platformFeeEl     = document.getElementById('platformFeeDisplay');
  var usageEl           = document.getElementById('usageDisplay');
  var usageNoteEl       = document.getElementById('usageNote');
  var totalEl           = document.getElementById('totalDisplay');
  var vsUsEl            = document.getElementById('vsUsDisplay');
  var vsSdrEl           = document.getElementById('vsSdrDisplay');
  var sdrCountLabel     = document.getElementById('sdrCountLabel');
  var savingsPill       = document.getElementById('savingsPill');
  var savingsPctLabel   = document.getElementById('savingsPctLabel');
  var planBadgeEl       = document.getElementById('planBadge');
  var calcCtaBtn        = document.getElementById('calcCtaBtn');
  var effectiveRateNote = document.getElementById('effectiveRateNote');

  function fmt(n) {
    return '$' + Math.round(n).toLocaleString('en-US');
  }

  function fmtDecimal(n) {
    return '$' + n.toFixed(3).replace(/\.?0+$/, '');
  }

  /* ── Read active add-ons ── */
  function getActiveAddons() {
    var active = [];
    ADDONS.forEach(function (addon) {
      var cb = document.getElementById('feat-' + addon.id);
      if (cb && cb.checked) active.push(addon);
    });
    return active;
  }

  /* ── Update add-on breakdown lines ── */
  function updateAddonLines(dials, days, activeAddons) {
    ADDONS.forEach(function (addon) {
      var wrap    = document.getElementById('addonWrap-' + addon.id);
      var noteEl  = document.getElementById('addonNote-' + addon.id);
      var amtEl   = document.getElementById('addonAmt-' + addon.id);
      if (!wrap) return;

      var isActive = activeAddons.some(function (a) { return a.id === addon.id; });

      if (isActive) {
        wrap.classList.add('active');
        if (addon.costPerDial > 0 && noteEl) {
          noteEl.textContent = dials.toLocaleString('en-US') + ' dials × ' + days + ' days × +' + fmtDecimal(addon.costPerDial) + '/dial';
          amtEl.textContent  = fmt(dials * days * addon.costPerDial);
        } else if (addon.monthlyFlat > 0 && noteEl) {
          noteEl.textContent = 'Flat monthly add-on';
          amtEl.textContent  = '$' + addon.monthlyFlat;
        }
      } else {
        wrap.classList.remove('active');
      }
    });
  }

  /* ── Main calculation ── */
  function updateCalc() {
    var dials = parseInt(dialSlider.value, 10);
    var days  = parseInt(daysSlider.value, 10);

    var isBusiness  = dials > 300;
    var platformFee = isBusiness ? 399 : 99;
    var planLabel   = isBusiness ? 'Business Plan' : 'Starter Plan';
    var planSlug    = isBusiness ? 'business' : 'starter';

    var baseUsage   = dials * days * BASE_COST_PER_DIAL;

    /* sum add-on costs */
    var activeAddons     = getActiveAddons();
    var addonDialCost    = 0;
    var addonFlatCost    = 0;
    activeAddons.forEach(function (a) {
      addonDialCost += a.costPerDial;
      addonFlatCost += a.monthlyFlat;
    });
    var addonDialTotal = dials * days * addonDialCost;
    var total          = platformFee + baseUsage + addonDialTotal + addonFlatCost;
    var effectiveRate  = BASE_COST_PER_DIAL + addonDialCost;

    /* ── Dynamic human SDR cost ──
       A human SDR handles ~550 calls/day over 22 working days = 12,100 calls/month.
       Scale the number of SDRs (and cost) proportionally to the user's selected volume. */
    var totalMonthlyDials = dials * days;
    var sdrsNeeded        = Math.max(1, Math.ceil(totalMonthlyDials / SDR_MONTHLY_CAPACITY));
    var humanSdrCost      = sdrsNeeded * SDR_COST_PER_UNIT;
    var saving            = humanSdrCost - total;
    var savingPct         = Math.round((saving / humanSdrCost) * 100);

    /* ── Update sliders & vol display ── */
    dialDisplay.textContent = dials.toLocaleString('en-US');
    daysDisplay.textContent = days;

    /* ── Update breakdown ── */
    platformFeeEl.textContent = fmt(platformFee);
    usageEl.textContent       = fmt(baseUsage);
    usageNoteEl.textContent   = dials.toLocaleString('en-US') + ' dials × ' + days + ' days × $' + BASE_COST_PER_DIAL.toFixed(3) + '/dial';

    updateAddonLines(dials, days, activeAddons);

    /* ── Effective rate note ── */
    if (effectiveRateNote) {
      effectiveRateNote.textContent = 'at ' + fmtDecimal(effectiveRate) + '/dial effective rate';
    }

    /* ── Totals & savings ── */
    totalEl.textContent     = fmt(total) + ' / mo';
    vsUsEl.textContent      = fmt(total);

    /* ── Dynamic SDR cost display ── */
    if (vsSdrEl)      vsSdrEl.textContent = fmt(humanSdrCost);
    if (sdrCountLabel) {
      var sdrWord = sdrsNeeded === 1 ? 'human SDR' : 'human SDRs';
      sdrCountLabel.textContent = '/ month (' + sdrsNeeded + ' ' + sdrWord + ')';
    }

    /* ── SDR icon stack — show 1, 2, or 3 overlapping person icons ── */
    var sdrIconWrap = document.getElementById('sdrIconWrap');
    if (sdrIconWrap) {
      var iconSvg = '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>';
      var visibleIcons = Math.min(sdrsNeeded, 3); // cap at 3 for layout
      if (visibleIcons <= 1) {
        sdrIconWrap.style.display = '';
        sdrIconWrap.innerHTML = iconSvg;
      } else {
        /* stack icons with slight offsets */
        var stackHtml = '<div style="display:flex;justify-content:center;align-items:center;">';
        var smallSvg = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>';
        for (var i = 0; i < visibleIcons; i++) {
          var offset = i * -10;
          var opacity = 1 - (i * 0.12);
          stackHtml += '<div style="margin-left:' + (i === 0 ? 0 : offset) + 'px;opacity:' + opacity + ';">' + smallSvg + '</div>';
        }
        if (sdrsNeeded > 3) {
          stackHtml += '<div style="font-size:0.72rem;color:rgba(255,255,255,0.5);margin-left:4px;">×' + sdrsNeeded + '</div>';
        }
        stackHtml += '</div>';
        sdrIconWrap.innerHTML = stackHtml;
      }
    }

    /* ── Savings pill + percentage ── */
    var safeSaving = Math.max(0, saving);
    savingsPill.textContent = 'Save ~' + fmt(safeSaving) + '/mo';
    if (savingsPctLabel) {
      var pctText = saving > 0 ? savingPct + '% cheaper' : 'comparable cost';
      savingsPctLabel.textContent = pctText;
    }

    /* ── Plan badge ── */
    planBadgeEl.textContent = planLabel;
    planBadgeEl.classList.toggle('business', isBusiness);

    /* ── CTA button ── */
    calcCtaBtn.setAttribute('data-plan', planSlug);
    calcCtaBtn.setAttribute('data-amount', platformFee);
    calcCtaBtn.textContent = 'Get Started for ' + fmt(platformFee) + '/mo →';

    /* ── Slider track fill ── */
    [dialSlider, daysSlider].forEach(function (sl) {
      var pct = ((sl.value - sl.min) / (sl.max - sl.min)) * 100;
      sl.style.background = 'linear-gradient(to right, #1a1a1a ' + pct + '%, #e5e7eb ' + pct + '%)';
    });
  }

  /* ── Wire up sliders ── */
  if (dialSlider && daysSlider) {
    dialSlider.addEventListener('input', updateCalc);
    daysSlider.addEventListener('input', updateCalc);
  }

  /* ── Wire up feature checkboxes ── */
  document.querySelectorAll('.calc-addon-cb').forEach(function (cb) {
    cb.addEventListener('change', updateCalc);
  });

  /* ── Initial render ── */
  if (dialSlider && daysSlider) {
    updateCalc();

    calcCtaBtn.addEventListener('click', function () {
      var plan = calcCtaBtn.getAttribute('data-plan') || 'starter';
      window.location.href = '/billing?plan=' + encodeURIComponent(plan);
    });
  }

  /* ══ CONTACT MODAL ══ */
  var contactOverlay  = document.getElementById('contactOverlay');
  var contactBackdrop = document.getElementById('contactBackdrop');
  var contactClose    = document.getElementById('contactClose');
  var contactForm     = document.getElementById('contactForm');
  var contactSuccess  = document.getElementById('contactSuccess');

  document.querySelectorAll('[data-plan]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var plan = btn.getAttribute('data-plan');
      if (plan) window.location.href = '/billing?plan=' + encodeURIComponent(plan);
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

  if (contactClose)    contactClose.addEventListener('click', closeContactModal);
  if (contactBackdrop) contactBackdrop.addEventListener('click', closeContactModal);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeContactModal();
  });

  var contactUsBtn = document.getElementById('contactUsBtn');
  if (contactUsBtn) contactUsBtn.addEventListener('click', openContactModal);

  if (contactForm) {
    contactForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      var submitBtn = document.getElementById('contactSubmit');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span>Sending...</span>';

      var formData = {
        name:    contactForm.querySelector('[name="name"]').value.trim(),
        email:   contactForm.querySelector('[name="email"]').value.trim(),
        phone:   contactForm.querySelector('[name="phone"]').value.trim(),
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
  }
})();
