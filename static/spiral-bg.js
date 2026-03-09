(function() {
  var canvas = document.getElementById('heroSpiralCanvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  if (!ctx) return;

  var CHANGE_EVENT_TIME = 0.32;
  var CAMERA_Z = -400;
  var CAMERA_TRAVEL = 3400;
  var START_DOT_Y = 28;
  var VIEW_ZOOM = 100;
  var NUM_STARS = 5000;
  var TRAIL_LEN = 80;

  var animTime = { v: 0 };
  var stars = [];
  var size = 0;

  function ease(p, g) {
    return p < 0.5 ? 0.5 * Math.pow(2 * p, g) : 1 - 0.5 * Math.pow(2 * (1 - p), g);
  }

  function easeOutElastic(x) {
    var c4 = (2 * Math.PI) / 4.5;
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    return Math.pow(2, -8 * x) * Math.sin((x * 8 - 0.75) * c4) + 1;
  }

  function map(v, s1, e1, s2, e2) {
    return s2 + (e2 - s2) * ((v - s1) / (e1 - s1));
  }

  function constrain(v, lo, hi) {
    return Math.min(Math.max(v, lo), hi);
  }

  function lerp(a, b, t) {
    return a * (1 - t) + b * t;
  }

  function spiralPath(p) {
    p = constrain(1.2 * p, 0, 1);
    p = ease(p, 1.8);
    var turns = 6;
    var theta = 2 * Math.PI * turns * Math.sqrt(p);
    var r = 170 * Math.sqrt(p);
    return { x: r * Math.cos(theta), y: r * Math.sin(theta) + START_DOT_Y };
  }

  function showProjectedDot(px, py, pz, sizeFactor) {
    var t2 = constrain(map(animTime.v, CHANGE_EVENT_TIME, 1, 0, 1), 0, 1);
    var newCamZ = CAMERA_Z + ease(Math.pow(t2, 1.2), 1.8) * CAMERA_TRAVEL;
    if (pz > newCamZ) {
      var depth = pz - newCamZ;
      var sx = VIEW_ZOOM * px / depth;
      var sy = VIEW_ZOOM * py / depth;
      var sw = 400 * sizeFactor / depth;
      ctx.beginPath();
      ctx.arc(sx, sy, Math.max(sw * 0.5, 0.3), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function createStar(rng) {
    var angle = rng() * Math.PI * 2;
    var dist = 30 * rng() + 15;
    var rotDir = rng() > 0.5 ? 1 : -1;
    var expRate = 1.2 + rng() * 0.8;
    var finScale = 0.7 + rng() * 0.6;
    var dx = dist * Math.cos(angle);
    var dy = dist * Math.sin(angle);
    var spiralLoc = (1 - Math.pow(1 - rng(), 3.0)) / 1.3;
    var z = (0.5 * CAMERA_Z) + rng() * (CAMERA_TRAVEL + CAMERA_Z - 0.5 * CAMERA_Z);
    z = lerp(z, CAMERA_TRAVEL / 2, 0.3 * spiralLoc);
    var swf = Math.pow(rng(), 2.0);

    return {
      angle: angle, distance: dist, rotDir: rotDir, expRate: expRate,
      finScale: finScale, dx: dx, dy: dy, spiralLoc: spiralLoc,
      z: z, swf: swf
    };
  }

  function renderStar(s, p) {
    var sp = spiralPath(s.spiralLoc);
    var q = p - s.spiralLoc;
    if (q <= 0) return;

    var dp = constrain(4 * q, 0, 1);
    var linE = dp;
    var elE = easeOutElastic(dp);
    var powE = Math.pow(dp, 2);
    var easing;
    if (dp < 0.3) { easing = lerp(linE, powE, dp / 0.3); }
    else if (dp < 0.7) { easing = lerp(powE, elE, (dp - 0.3) / 0.4); }
    else { easing = elE; }

    var sx, sy;
    if (dp < 0.3) {
      sx = lerp(sp.x, sp.x + s.dx * 0.3, easing / 0.3);
      sy = lerp(sp.y, sp.y + s.dy * 0.3, easing / 0.3);
    } else if (dp < 0.7) {
      var mid = (dp - 0.3) / 0.4;
      var curve = Math.sin(mid * Math.PI) * s.rotDir * 1.5;
      var bx = sp.x + s.dx * 0.3, by = sp.y + s.dy * 0.3;
      var tx = sp.x + s.dx * 0.7, ty = sp.y + s.dy * 0.7;
      var px2 = -s.dy * 0.4 * curve, py2 = s.dx * 0.4 * curve;
      sx = lerp(bx, tx, mid) + px2 * mid;
      sy = lerp(by, ty, mid) + py2 * mid;
    } else {
      var fp = (dp - 0.7) / 0.3;
      var bx2 = sp.x + s.dx * 0.7, by2 = sp.y + s.dy * 0.7;
      var td = s.distance * s.expRate * 1.5;
      var st2 = 1.2 * s.rotDir;
      var sa = s.angle + st2 * fp * Math.PI;
      var tx2 = sp.x + td * Math.cos(sa), ty2 = sp.y + td * Math.sin(sa);
      sx = lerp(bx2, tx2, fp);
      sy = lerp(by2, ty2, fp);
    }

    var vx = (s.z - CAMERA_Z) * sx / VIEW_ZOOM;
    var vy = (s.z - CAMERA_Z) * sy / VIEW_ZOOM;
    var sm = 1.0;
    if (dp < 0.6) { sm = 1.0 + dp * 0.2; }
    else { var tt = (dp - 0.6) / 0.4; sm = 1.2 * (1 - tt) + s.finScale * tt; }
    showProjectedDot(vx, vy, s.z, 8.5 * s.swf * sm);
  }

  function render() {
    if (!ctx) return;
    ctx.fillStyle = '#050510';
    ctx.fillRect(0, 0, size, size);
    ctx.save();
    ctx.translate(size / 2, size / 2);

    var t1 = constrain(map(animTime.v, 0, CHANGE_EVENT_TIME + 0.25, 0, 1), 0, 1);
    var t2 = constrain(map(animTime.v, CHANGE_EVENT_TIME, 1, 0, 1), 0, 1);
    ctx.rotate(-Math.PI * ease(t2, 2.7));

    for (var i = 0; i < TRAIL_LEN; i++) {
      var f = map(i, 0, TRAIL_LEN, 1.1, 0.1);
      var sw = (1.3 * (1 - t1) + 3.0 * Math.sin(Math.PI * t1)) * f;
      ctx.fillStyle = 'white';
      var pt = t1 - 0.00015 * i;
      var pos = spiralPath(pt);
      var off = { x: pos.x + 5, y: pos.y + 5 };
      var mid = { x: (pos.x + off.x) / 2, y: (pos.y + off.y) / 2 };
      var ddx = pos.x - mid.x, ddy = pos.y - mid.y;
      var ang = Math.atan2(ddy, ddx);
      var rr = Math.sqrt(ddx * ddx + ddy * ddy);
      var o = (i % 2 === 0) ? -1 : 1;
      var rp = Math.sin(animTime.v * Math.PI * 2) * 0.5 + 0.5;
      var bounce = Math.sin(rp * Math.PI) * 0.05 * (1 - rp);
      var rx = mid.x + rr * (1 + bounce) * Math.cos(ang + o * Math.PI * easeOutElastic(rp));
      var ry = mid.y + rr * (1 + bounce) * Math.sin(ang + o * Math.PI * easeOutElastic(rp));
      ctx.beginPath();
      ctx.arc(rx, ry, Math.max(sw / 2, 0.3), 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.fillStyle = 'white';
    for (var j = 0; j < stars.length; j++) {
      renderStar(stars[j], t1);
    }

    if (animTime.v > CHANGE_EVENT_TIME) {
      var dyy = CAMERA_Z * START_DOT_Y / VIEW_ZOOM;
      showProjectedDot(0, dyy, CAMERA_TRAVEL, 2.5);
    }

    ctx.restore();
  }

  function initStars() {
    stars = [];
    var seed = 1234;
    var seededRng = function() {
      seed = (seed * 9301 + 49297) % 233280;
      return seed / 233280;
    };
    for (var i = 0; i < NUM_STARS; i++) {
      stars.push(createStar(seededRng));
    }
  }

  function resize() {
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.parentElement ? canvas.parentElement.offsetWidth : window.innerWidth;
    var h = canvas.parentElement ? canvas.parentElement.offsetHeight : window.innerHeight;
    size = Math.max(w, h);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
  }

  initStars();
  resize();
  window.addEventListener('resize', resize);

  gsap.to(animTime, {
    v: 1,
    duration: 15,
    repeat: -1,
    ease: 'none',
    onUpdate: render
  });
})();
