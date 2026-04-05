(function () {
  'use strict';

  /* ══ PRICING CONSTANTS ══ */
  var DIAL_RATE            = { autodialer: 0.03, business: 0.05 };
  var TRANSFER_RATE        = { autodialer: 0.15, business: 0.20 };
  var TRANSFER_CONNECT_PCT = 0.20; // 20% of dials assumed to connect to a live human
  var SDR_COST_PER_UNIT    = 5000;
  var SDR_CALLS_PER_DAY    = 550;
  var SDR_WORKING_DAYS     = 22;
  var SDR_MONTHLY_CAPACITY = SDR_CALLS_PER_DAY * SDR_WORKING_DAYS;

  var ANNUAL_PRICES = {
    autodialer: { annual: 690,  monthly: 57.50,  save: 138  },
    business:   { annual: 1690, monthly: 140.83, save: 338  }
  };

  var ADDONS = [
    { id: 'personalizedVm', label: 'Personalized AI Voicemails', costPerDial: 0.02, monthlyFlat: 0 },
    { id: 'gatekeeper',     label: 'Gatekeeper Navigator',        costPerDial: 0.03, monthlyFlat: 0 },
    { id: 'transcription',  label: 'Recording & Transcription',   costPerDial: 0.03, monthlyFlat: 0 },
    { id: 'voiceCloning',   label: 'Voice Cloning',               costPerDial: 0,    monthlyFlat: 19 }
  ];

  /* ── Billing cycle state ── */
  var billingCycle = 'monthly'; // 'monthly' | 'annual'

  /* ── Selected plan state ── */
  var selectedPlan = 'autodialer'; // 'autodialer' | 'business'

  function selectPlan(slug) {
    selectedPlan = slug;
    document.querySelectorAll('.pricing-card[data-plan-card]').forEach(function (card) {
      card.classList.toggle('plan-card-selected', card.getAttribute('data-plan-card') === slug);
    });
    if (dialSlider) {
      dialSlider.value = slug === 'business' ? 300 : 100;
    }
    var ltPriceEl = document.getElementById('feat-liveTransfer-price');
    if (ltPriceEl) {
      ltPriceEl.innerHTML = '+$' + (slug === 'business' ? '0.20' : '0.15') + '<span class="calc-feat-price-unit">/transfer</span>';
    }
    if (dialSlider && daysSlider) updateCalc();
  }

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
  var btnMonthly        = document.getElementById('btnMonthly');
  var btnAnnual         = document.getElementById('btnAnnual');

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
  function updateAddonLines(dials, days, activeAddons, liveTransferTotal, extraNumTotal) {
    ADDONS.forEach(function (addon) {
      var wrap   = document.getElementById('addonWrap-' + addon.id);
      var noteEl = document.getElementById('addonNote-' + addon.id);
      var amtEl  = document.getElementById('addonAmt-' + addon.id);
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

    /* Live transfer (per-event, not per-dial) */
    var ltWrap = document.getElementById('addonWrap-liveTransfer');
    var ltNote = document.getElementById('addonNote-liveTransfer');
    var ltAmt  = document.getElementById('addonAmt-liveTransfer');
    var ltCb   = document.getElementById('feat-liveTransfer');
    if (ltWrap) {
      if (ltCb && ltCb.checked) {
        ltWrap.classList.add('active');
        var transfers = Math.round(dials * days * TRANSFER_CONNECT_PCT);
        var rate = selectedPlan === 'business' ? 0.20 : 0.15;
        if (ltNote) ltNote.textContent = transfers.toLocaleString('en-US') + ' est. transfers × $' + rate.toFixed(2) + '/transfer (20% connect rate)';
        if (ltAmt)  ltAmt.textContent  = fmt(liveTransferTotal);
      } else {
        ltWrap.classList.remove('active');
      }
    }

    /* Extra phone numbers */
    var enWrap = document.getElementById('addonWrap-extraNumbers');
    var enNote = document.getElementById('addonNote-extraNumbers');
    var enAmt  = document.getElementById('addonAmt-extraNumbers');
    var enEl   = document.getElementById('feat-extraNumbers');
    if (enWrap) {
      var extraNums = enEl ? (parseInt(enEl.value, 10) || 0) : 0;
      if (extraNums > 0) {
        enWrap.classList.add('active');
        if (enNote) enNote.textContent = extraNums + ' extra number' + (extraNums !== 1 ? 's' : '') + ' × $5/mo';
        if (enAmt)  enAmt.textContent  = '$' + (extraNums * 5);
      } else {
        enWrap.classList.remove('active');
      }
    }
  }

  /* ── Update the plan cards' price display ── */
  function updatePriceCards() {
    var isAnnual = billingCycle === 'annual';

    var autodialerEl   = document.getElementById('autodialerPriceDisplay');
    var businessEl     = document.getElementById('businessPriceDisplay');
    var autodialerInfo = document.getElementById('autodialerAnnualInfo');
    var businessInfo   = document.getElementById('businessAnnualInfo');

    if (autodialerEl)   autodialerEl.textContent   = isAnnual ? '57.50' : '69';
    if (businessEl)     businessEl.textContent     = isAnnual ? '140.83' : '169';
    if (autodialerInfo) autodialerInfo.classList.toggle('show', isAnnual);
    if (businessInfo)   businessInfo.classList.toggle('show', isAnnual);
  }

  /* ── Main calculation ── */
  function updateCalc() {
    var dials = parseInt(dialSlider.value, 10);
    var days  = parseInt(daysSlider.value, 10);

    var isBusiness   = selectedPlan === 'business';
    var planSlug     = isBusiness ? 'business' : 'autodialer';
    var platformFee  = isBusiness ? 169 : 69;
    var planLabel    = isBusiness ? 'Open Humana Sales Floor' : 'Open Humana Starter';
    var dialRate     = isBusiness ? DIAL_RATE.business     : DIAL_RATE.autodialer;
    var transferRate = isBusiness ? TRANSFER_RATE.business : TRANSFER_RATE.autodialer;

    var baseUsage = dials * days * dialRate;

    var activeAddons  = getActiveAddons();
    var addonDialCost = 0;
    var addonFlatCost = 0;
    activeAddons.forEach(function (a) {
      addonDialCost += a.costPerDial;
      addonFlatCost += a.monthlyFlat;
    });
    var addonDialTotal = dials * days * addonDialCost;

    /* Live transfer — per transfer event */
    var ltCb = document.getElementById('feat-liveTransfer');
    var liveTransferTotal = 0;
    if (ltCb && ltCb.checked) {
      liveTransferTotal = dials * days * TRANSFER_CONNECT_PCT * transferRate;
    }

    /* Extra phone numbers */
    var enEl      = document.getElementById('feat-extraNumbers');
    var extraNums = enEl ? (parseInt(enEl.value, 10) || 0) : 0;
    var extraNumTotal = extraNums * 5;

    var total        = platformFee + baseUsage + addonDialTotal + addonFlatCost + liveTransferTotal + extraNumTotal;
    var effectiveRate = dialRate + addonDialCost;

    var totalMonthlyDials = dials * days;
    var sdrsNeeded        = Math.max(1, Math.ceil(totalMonthlyDials / SDR_MONTHLY_CAPACITY));
    var humanSdrCost      = sdrsNeeded * SDR_COST_PER_UNIT;
    var saving            = humanSdrCost - total;
    var savingPct         = Math.round((saving / humanSdrCost) * 100);

    dialDisplay.textContent = dials.toLocaleString('en-US');
    daysDisplay.textContent = days;

    platformFeeEl.textContent = fmt(platformFee);
    usageEl.textContent       = fmt(baseUsage);
    usageNoteEl.textContent   = dials.toLocaleString('en-US') + ' dials × ' + days + ' days × $' + dialRate.toFixed(2) + '/dial';

    updateAddonLines(dials, days, activeAddons, liveTransferTotal, extraNumTotal);

    if (effectiveRateNote) {
      effectiveRateNote.textContent = 'at ' + fmtDecimal(effectiveRate) + '/dial effective rate';
    }

    var annualData = ANNUAL_PRICES[planSlug];
    if (billingCycle === 'annual' && annualData) {
      /* In annual mode the platform fee is discounted — recalculate full monthly cost */
      var annualMonthlyTotal = annualData.monthly + baseUsage + addonDialTotal + addonFlatCost + liveTransferTotal + extraNumTotal;
      totalEl.textContent = fmt(annualMonthlyTotal) + ' / mo (annualized platform fee)';
      vsUsEl.textContent  = fmt(annualMonthlyTotal);
    } else {
      totalEl.textContent = fmt(total) + ' / mo';
      vsUsEl.textContent  = fmt(total);
    }

    if (vsSdrEl)       vsSdrEl.textContent = fmt(humanSdrCost);
    if (sdrCountLabel) {
      var sdrWord = sdrsNeeded === 1 ? 'human SDR' : 'human SDRs';
      sdrCountLabel.textContent = '/ month (' + sdrsNeeded + ' ' + sdrWord + ')';
    }

    var sdrIconWrap = document.getElementById('sdrIconWrap');
    if (sdrIconWrap) {
      var iconSvg = '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>';
      var visibleIcons = Math.min(sdrsNeeded, 3);
      if (visibleIcons <= 1) {
        sdrIconWrap.style.display = '';
        sdrIconWrap.innerHTML = iconSvg;
      } else {
        var stackHtml = '<div style="display:flex;justify-content:center;align-items:center;">';
        var smallSvg = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>';
        for (var i = 0; i < visibleIcons; i++) {
          var offset  = i * -10;
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

    var safeSaving = Math.max(0, saving);
    savingsPill.textContent = 'Save ~' + fmt(safeSaving) + '/mo';
    if (savingsPctLabel) {
      var pctText = saving > 0 ? savingPct + '% cheaper' : 'comparable cost';
      savingsPctLabel.textContent = pctText;
    }

    planBadgeEl.textContent = planLabel;
    planBadgeEl.classList.toggle('business', isBusiness);

    calcCtaBtn.setAttribute('data-plan', planSlug);
    calcCtaBtn.setAttribute('data-amount', platformFee);
    if (billingCycle === 'annual' && annualData) {
      calcCtaBtn.textContent = 'Get Started — ' + fmt(annualMonthlyTotal) + '/mo (platform billed annually) →';
    } else {
      calcCtaBtn.textContent = 'Get Started for ' + fmt(platformFee) + '/mo →';
    }

    [dialSlider, daysSlider].forEach(function (sl) {
      var pct = ((sl.value - sl.min) / (sl.max - sl.min)) * 100;
      sl.style.background = 'linear-gradient(to right, #1a1a1a ' + pct + '%, #e5e7eb ' + pct + '%)';
    });
  }

  /* ── Billing toggle ── */
  function setBillingCycle(cycle) {
    billingCycle = cycle;
    if (btnMonthly) btnMonthly.classList.toggle('btog-active', cycle === 'monthly');
    if (btnAnnual)  btnAnnual.classList.toggle('btog-active', cycle === 'annual');
    updatePriceCards();
    if (dialSlider && daysSlider) updateCalc();
  }

  if (btnMonthly) btnMonthly.addEventListener('click', function () { setBillingCycle('monthly'); });
  if (btnAnnual)  btnAnnual.addEventListener('click',  function () { setBillingCycle('annual');  });

  /* ── Plan card selection (click card to lock calculator to that plan) ── */
  document.querySelectorAll('.pricing-card[data-plan-card]').forEach(function (card) {
    card.addEventListener('click', function (e) {
      if (e.target.closest('button') || e.target.closest('a') || e.target.closest('input')) return;
      var slug = card.getAttribute('data-plan-card');
      selectPlan(slug);
      var calcSection = document.getElementById('calculator');
      if (calcSection) calcSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  /* ── Wire up sliders ── */
  if (dialSlider && daysSlider) {
    dialSlider.addEventListener('input', updateCalc);
    daysSlider.addEventListener('input', updateCalc);
  }

  /* ── Wire up feature checkboxes ── */
  document.querySelectorAll('.calc-addon-cb').forEach(function (cb) {
    cb.addEventListener('change', updateCalc);
  });

  /* ── Wire up extra numbers input ── */
  var extraNumInput = document.getElementById('feat-extraNumbers');
  if (extraNumInput) extraNumInput.addEventListener('input', updateCalc);

  /* ── Initial render ── */
  updatePriceCards();

  if (dialSlider && daysSlider) {
    selectPlan('business'); // Default to Digital Sales Floor

    calcCtaBtn.addEventListener('click', function () {
      var plan = calcCtaBtn.getAttribute('data-plan') || 'business';
      var url = '/billing?plan=' + encodeURIComponent(plan);
      if (billingCycle === 'annual') url += '&cycle=annual';
      window.location.href = url;
    });
  }

  /* ── Plan card buttons (with billing cycle) ── */
  document.querySelectorAll('[data-plan]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var plan = btn.getAttribute('data-plan');
      if (!plan) return;
      var url = '/billing?plan=' + encodeURIComponent(plan);
      if (billingCycle === 'annual') url += '&cycle=annual';
      window.location.href = url;
    });
  });

  /* ══ CONTACT MODAL ══ */
  var contactOverlay  = document.getElementById('contactOverlay');
  var contactBackdrop = document.getElementById('contactBackdrop');
  var contactClose    = document.getElementById('contactClose');
  var contactForm     = document.getElementById('contactForm');
  var contactSuccess  = document.getElementById('contactSuccess');

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

  /* ══ BUILD YOUR PLAN MINI CALCULATOR ══ */
  var buildBase        = 'autodialer';
  var buildDialSlider  = document.getElementById('buildDialSlider');
  var buildDialDisplay = document.getElementById('buildDialDisplay');
  var buildTotalEl     = document.getElementById('buildTotal');
  var buildLtPrice     = document.getElementById('build-ltPrice');

  var BUILD_ADDONS = [
    { id: 'personalizedVm', costPerDial: 0.02, monthlyFlat: 0,  isTransfer: false },
    { id: 'liveTransfer',   costPerDial: 0,    monthlyFlat: 0,  isTransfer: true  },
    { id: 'gatekeeper',     costPerDial: 0.03, monthlyFlat: 0,  isTransfer: false },
    { id: 'transcription',  costPerDial: 0.03, monthlyFlat: 0,  isTransfer: false },
    { id: 'voiceCloning',   costPerDial: 0,    monthlyFlat: 19, isTransfer: false }
  ];

  function updateBuildCard() {
    var dials = buildDialSlider ? parseInt(buildDialSlider.value, 10) : 100;
    var days  = 22;
    var baseFee      = buildBase === 'business' ? 169 : 69;
    var dialRate     = DIAL_RATE[buildBase];
    var transferRate = TRANSFER_RATE[buildBase];

    var usage     = dials * days * dialRate;
    var addonCost = 0;

    BUILD_ADDONS.forEach(function (addon) {
      var cb = document.getElementById('build-' + addon.id);
      if (!cb || !cb.checked) return;
      if (addon.isTransfer) {
        addonCost += dials * days * TRANSFER_CONNECT_PCT * transferRate;
      } else if (addon.costPerDial > 0) {
        addonCost += dials * days * addon.costPerDial;
      } else if (addon.monthlyFlat > 0) {
        addonCost += addon.monthlyFlat;
      }
    });

    var total = baseFee + usage + addonCost;
    if (buildTotalEl)     buildTotalEl.textContent    = Math.round(total).toLocaleString('en-US');
    if (buildDialDisplay) buildDialDisplay.textContent = dials.toLocaleString('en-US');

    if (buildLtPrice) {
      var rate = buildBase === 'business' ? '0.20' : '0.15';
      buildLtPrice.textContent = '+$' + rate + '/transfer';
    }

    if (buildDialSlider) {
      var pct = ((buildDialSlider.value - buildDialSlider.min) / (buildDialSlider.max - buildDialSlider.min)) * 100;
      buildDialSlider.style.background = 'linear-gradient(to right, #1a1a1a ' + pct + '%, #e5e7eb ' + pct + '%)';
    }
  }

  /* Base plan buttons */
  ['autodialer', 'business'].forEach(function (slug) {
    var btn = document.getElementById('buildBase-' + slug);
    if (!btn) return;
    btn.addEventListener('click', function () {
      buildBase = slug;
      document.querySelectorAll('.build-base-btn').forEach(function (b) {
        b.classList.toggle('build-base-btn--active', b.id === 'buildBase-' + slug);
      });
      updateBuildCard();
    });
  });

  if (buildDialSlider) buildDialSlider.addEventListener('input', updateBuildCard);

  document.querySelectorAll('.build-addon-cb').forEach(function (cb) {
    cb.addEventListener('change', updateBuildCard);
  });

  /* "See full breakdown" — sync state to main calculator and scroll */
  var buildSeeFullBtn = document.getElementById('buildSeeFullBtn');
  if (buildSeeFullBtn) {
    buildSeeFullBtn.addEventListener('click', function () {
      selectPlan(buildBase);
      if (dialSlider && buildDialSlider) dialSlider.value = buildDialSlider.value;
      BUILD_ADDONS.forEach(function (addon) {
        var buildCb = document.getElementById('build-' + addon.id);
        var calcCb  = document.getElementById('feat-' + addon.id);
        if (buildCb && calcCb) calcCb.checked = buildCb.checked;
      });
      if (dialSlider && daysSlider) updateCalc();
      var calcSection = document.getElementById('calculator');
      if (calcSection) calcSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  updateBuildCard();

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
