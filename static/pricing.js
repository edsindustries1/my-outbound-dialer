(function () {
  'use strict';

  var paymentOverlay = document.getElementById('paymentOverlay');
  var paymentBackdrop = document.getElementById('paymentBackdrop');
  var paymentModal = document.getElementById('paymentModal');
  var paymentClose = document.getElementById('paymentClose');
  var paymentTitle = document.getElementById('paymentTitle');
  var paymentPlanName = document.getElementById('paymentPlanName');
  var paymentPlanPrice = document.getElementById('paymentPlanPrice');
  var paypalContainer = document.getElementById('paypalContainer');
  var paymentLoading = document.getElementById('paymentLoading');
  var paymentSuccess = document.getElementById('paymentSuccess');
  var paymentBody = document.querySelector('.payment-body');

  var contactOverlay = document.getElementById('contactOverlay');
  var contactBackdrop = document.getElementById('contactBackdrop');
  var contactModal = document.getElementById('contactModal');
  var contactClose = document.getElementById('contactClose');
  var contactForm = document.getElementById('contactForm');
  var contactSuccess = document.getElementById('contactSuccess');

  var currentPlan = '';
  var currentAmount = 0;

  function openPaymentModal(plan, amount) {
    currentPlan = plan;
    currentAmount = amount;

    var planNames = { starter: 'Hire One Employee', business: 'Hire a Team' };
    paymentPlanName.textContent = planNames[plan] || plan;
    paymentPlanPrice.textContent = '$' + amount + '/mo';
    paymentTitle.textContent = 'Complete Your Purchase';

    paypalContainer.innerHTML = '';
    paymentLoading.style.display = 'flex';
    paymentSuccess.style.display = 'none';
    paymentBody.style.display = '';

    paymentOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';

    renderPayPalButtons(plan, amount);
  }

  function closePaymentModal() {
    paymentOverlay.classList.remove('active');
    document.body.style.overflow = '';
  }

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

  paymentClose.addEventListener('click', closePaymentModal);
  paymentBackdrop.addEventListener('click', closePaymentModal);
  contactClose.addEventListener('click', closeContactModal);
  contactBackdrop.addEventListener('click', closeContactModal);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      closePaymentModal();
      closeContactModal();
    }
  });

  document.querySelectorAll('[data-plan]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var plan = btn.getAttribute('data-plan');
      var amount = parseInt(btn.getAttribute('data-amount'), 10);
      openPaymentModal(plan, amount);
    });
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

  function renderPayPalButtons(plan, amount) {
    if (typeof paypal_sdk === 'undefined') {
      paymentLoading.innerHTML = '<span>Payment system unavailable. Please <a href="/login" style="color:var(--accent);text-decoration:underline;">log in</a> and visit your billing page.</span>';
      return;
    }

    paypal_sdk.Buttons({
      style: {
        shape: 'rect',
        color: 'black',
        layout: 'vertical',
        label: 'pay',
        height: 48,
        tagline: false
      },
      createOrder: function (data, actions) {
        return fetch('/api/paypal/create-order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plan: plan, amount: amount })
        })
        .then(function (res) { return res.json(); })
        .then(function (order) {
          if (order.error) throw new Error(order.error);
          return order.id;
        });
      },
      onApprove: function (data, actions) {
        return fetch('/api/paypal/capture-order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ order_id: data.orderID, plan: plan })
        })
        .then(function (res) { return res.json(); })
        .then(function (result) {
          if (result.error) throw new Error(result.error);
          paymentBody.style.display = 'none';
          paymentSuccess.style.display = 'block';
          setTimeout(function () {
            window.location.href = '/';
          }, 3000);
        });
      },
      onError: function (err) {
        console.error('PayPal error:', err);
        paypalContainer.innerHTML = '<p style="text-align:center;color:#ef4444;font-size:.88rem;padding:16px 0;">Payment could not be processed. Please try again or <a href="/login" style="color:var(--accent);text-decoration:underline;">log in</a> first.</p>';
      },
      onInit: function () {
        paymentLoading.style.display = 'none';
      }
    }).render('#paypalContainer').catch(function () {
      paymentLoading.innerHTML = '<span style="color:#ef4444;">Failed to load payment buttons. Please try again.</span>';
    });
  }
})();
