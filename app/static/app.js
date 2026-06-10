/* R$ Transparência — interações do portal (sem build, vanilla JS) */
(function () {
  function lucide() { if (window.lucide) window.lucide.createIcons(); }
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    lucide();
    initBrand();
    initTabs();
    initCobre();
    initVotos();
  }

  /* ---------- Animação da marca: R$ → "Real" → abrevia pra R$ ---------- */
  function initBrand() {
    var el = document.querySelector('.js-brand-prefix');
    if (!el) return;
    el.classList.add('brand-anim');
    function swap(t) { el.classList.add('brand-out'); setTimeout(function () { el.textContent = t; el.classList.remove('brand-out'); }, 200); }
    function cycle() {
      swap('Real');                        // R$ vira "Real"
      setTimeout(function () { swap('R$'); }, 1700);  // depois abrevia
    }
    setTimeout(cycle, 900);
    setInterval(cycle, 12000);             // repete suavemente
  }

  /* ---------- Votos: busca por nome + filtro Sim/Não + alfabeto ---------- */
  function initVotos() {
    var list = document.querySelector('.js-votos-list');
    if (!list) return;
    var items = [].slice.call(list.querySelectorAll('.voto-item'));
    var empty = list.querySelector('.js-votos-empty');
    var q = '', vote = 'all', letter = 'all';
    var norm = function (s) { return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); };

    function apply() {
      var n = 0;
      items.forEach(function (it) {
        var name = it.dataset.name, v = it.dataset.vote;
        var okq = !q || norm(name).indexOf(q) > -1;
        var okv = vote === 'all' || (vote === 'outros' ? (v === 'abs' || v === 'aus') : v === vote);
        var okl = letter === 'all' || norm(name).charAt(0) === letter;
        var show = okq && okv && okl;
        it.style.display = show ? '' : 'none';
        if (show) n++;
      });
      if (empty) empty.style.display = n ? 'none' : '';
    }

    var search = document.querySelector('.js-votos-search');
    if (search) search.addEventListener('input', function (e) { q = norm(e.target.value); apply(); });
    document.querySelectorAll('.js-vfilter').forEach(function (b) {
      b.addEventListener('click', function () {
        document.querySelectorAll('.js-vfilter').forEach(function (x) { x.classList.toggle('on', x === b); });
        vote = b.dataset.vote; apply();
      });
    });
    document.querySelectorAll('.js-alpha-bar .alpha').forEach(function (b) {
      b.addEventListener('click', function () {
        document.querySelectorAll('.js-alpha-bar .alpha').forEach(function (x) { x.classList.toggle('on', x === b); });
        letter = b.dataset.letter === 'all' ? 'all' : norm(b.dataset.letter);
        apply();
      });
    });
  }

  /* ---------- Abas (perfil do deputado) ---------- */
  function initTabs() {
    document.querySelectorAll('[data-tabs]').forEach(function (group) {
      var tabs = group.querySelectorAll('.tab');
      tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
          var target = tab.getAttribute('data-tab');
          tabs.forEach(function (t) { t.classList.toggle('on', t === tab); });
          document.querySelectorAll('[data-panel]').forEach(function (p) {
            p.style.display = p.getAttribute('data-panel') === target ? '' : 'none';
          });
        });
      });
    });
  }

  /* ---------- Cobre seu deputado (modal) ---------- */
  var modal, state = {};
  function initCobre() {
    modal = document.getElementById('cobre-modal');
    if (!modal) return;

    document.querySelectorAll('.js-cobrar').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openCobre({
          name: btn.dataset.name,
          party: btn.dataset.party || '',
          uf: btn.dataset.uf || '',
          email: btn.dataset.email || '',
          phone: btn.dataset.phone || '',
          tel: btn.dataset.tel || '',
          initials: btn.dataset.initials || '',
          color: btn.dataset.color || 'var(--amber-500)',
          presence: btn.dataset.presence || '—',
        });
      });
    });

    modal.querySelector('.overlay').addEventListener('click', function (e) {
      if (e.target === modal.querySelector('.overlay')) closeCobre();
    });
    modal.querySelectorAll('.js-cobre-close').forEach(function (b) {
      b.addEventListener('click', closeCobre);
    });
  }

  function tpl(kind, d) {
    var t = {
      voto: 'Olá, deputado(a) ' + d.name + '. Acompanhei pelo R$ Transparência como você votou em uma proposição recente e gostaria de entender melhor o motivo. Como seu eleitor(a), peço que explique sua posição. Obrigado(a).',
      gasto: 'Olá, deputado(a) ' + d.name + '. Acompanhando seus gastos da cota parlamentar (CEAP) pelo R$ Transparência, fiquei com dúvidas sobre algumas despesas. Pode esclarecer? Conto com a transparência. Obrigado(a).',
      presenca: 'Olá, deputado(a) ' + d.name + '. Notei pelo R$ Transparência uma presença de ' + d.presence + '% nas sessões do plenário. Como seu eleitor(a), gostaria de saber como você tem representado nosso estado. Obrigado(a).',
    };
    return t[kind];
  }

  function openCobre(d) {
    state = { d: d, channel: 'email', tpl: 'voto' };
    state.msg = tpl('voto', d);

    var bg = colorBg(d.color), fg = colorFg(d.color);
    modal.querySelector('.js-ava').style.background = bg;
    modal.querySelector('.js-ava').style.color = fg;
    modal.querySelector('.js-ava').textContent = d.initials;
    modal.querySelector('.js-title').textContent = 'Cobrar ' + d.name;
    modal.querySelector('.js-sub').textContent = d.party + ' · ' + d.uf + ' · Gabinete oficial';
    modal.querySelector('.js-email-label').textContent = d.email || 'e-mail do gabinete';
    modal.querySelector('.js-msg').value = state.msg;

    modal.querySelectorAll('.js-tpl').forEach(function (c) {
      c.classList.toggle('on', c.dataset.tpl === 'voto');
    });
    setChannel(state.channel);
    showStep('form');
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    lucide();

    modal.querySelectorAll('.js-channel').forEach(function (c) {
      c.onclick = function () { setChannel(c.dataset.channel); };
    });
    modal.querySelectorAll('.js-tpl').forEach(function (c) {
      c.onclick = function () {
        state.tpl = c.dataset.tpl;
        state.msg = tpl(c.dataset.tpl, d);
        modal.querySelector('.js-msg').value = state.msg;
        modal.querySelectorAll('.js-tpl').forEach(function (x) { x.classList.toggle('on', x === c); });
      };
    });
    modal.querySelector('.js-msg').oninput = function (e) { state.msg = e.target.value; };
    modal.querySelector('.js-send').onclick = send;
  }

  function setChannel(ch) {
    state.channel = 'email';
    var send = modal.querySelector('.js-send');
    send.className = 'btn btn-amber btn-block js-send';
    send.innerHTML = '<i data-lucide="mail"></i>Enviar e-mail';
    lucide();
  }

  function send() {
    var d = state.d, msg = encodeURIComponent(state.msg);
    var subj = encodeURIComponent('Cobrança via R$ Transparência');
    if (d.email) {
      window.open('mailto:' + d.email + '?subject=' + subj + '&body=' + msg, '_blank');
    } else {
      toast('Este gabinete não tem e-mail público cadastrado.');
      return;
    }
    modal.querySelector('.js-sent-text').textContent = 'Abrimos seu e-mail com a mensagem para o gabinete. É só dar enviar.';
    showStep('sent');
    lucide();
  }

  function showStep(step) {
    modal.querySelector('.js-step-form').style.display = step === 'form' ? '' : 'none';
    modal.querySelector('.js-step-sent').style.display = step === 'sent' ? '' : 'none';
  }

  function closeCobre() {
    modal.style.display = 'none';
    document.body.style.overflow = '';
    toast('Valeu por participar! Cobrança pronta pra enviar.');
  }

  function toast(text) {
    var t = document.getElementById('toast');
    if (!t) return;
    t.querySelector('.js-toast-text').textContent = text;
    t.style.display = 'flex';
    lucide();
    setTimeout(function () { t.style.display = 'none'; }, 3800);
  }

  /* ---------- cores do avatar por partido ---------- */
  function colorBg(c) {
    if (c.indexOf('green') > -1) return 'var(--green-100)';
    if (c.indexOf('clay') > -1) return 'var(--clay-100)';
    if (c.indexOf('petro') > -1) return 'var(--petro-100)';
    return 'var(--amber-100)';
  }
  function colorFg(c) {
    if (c.indexOf('green') > -1) return 'var(--green-700)';
    if (c.indexOf('clay') > -1) return 'var(--clay-700)';
    if (c.indexOf('petro') > -1) return 'var(--petro-700)';
    return 'var(--amber-700)';
  }
})();
