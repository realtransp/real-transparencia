// Shared primitives for the portal UI kit.
const { useState, useEffect, useLayoutEffect, useRef } = React;

// Re-render Lucide icons after React commits.
function useLucideRefresh(dep) {
  useLayoutEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
}

function Icon({ name, className }) {
  return <i data-lucide={name} className={className}></i>;
}

// BRL money — pt-BR. full = with decimals.
function brl(n, full) {
  if (full) return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (n >= 1000) return 'R$ ' + Math.round(n / 1000) + 'k';
  return 'R$ ' + n.toLocaleString('pt-BR');
}
function brlFull(n) {
  return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function Avatar({ dep, size = 52 }) {
  const bg = dep.color === 'var(--green-600)' ? 'var(--green-100)'
    : dep.color === 'var(--clay-600)' ? 'var(--clay-100)'
    : dep.color === 'var(--petro-500)' ? 'var(--petro-100)'
    : 'var(--amber-100)';
  const fg = dep.color === 'var(--green-600)' ? 'var(--green-700)'
    : dep.color === 'var(--clay-600)' ? 'var(--clay-700)'
    : dep.color === 'var(--petro-500)' ? 'var(--petro-700)'
    : 'var(--amber-700)';
  return (
    <div className="ava" style={{ width: size, height: size, fontSize: size * 0.38, background: bg, color: fg }}>
      {dep.initials}
    </div>
  );
}

function PartyTag({ dep, withTerm }) {
  return (
    <span className="tag">
      <span className="sq" style={{ background: dep.color }}></span>
      {dep.party} · {dep.uf}{withTerm ? ' · ' + dep.term : ''}
    </span>
  );
}

function VoteBadge({ kind }) {
  if (kind === 'sim') return <span className="vote v-sim"><Icon name="check" />Votou Sim</span>;
  if (kind === 'nao') return <span className="vote v-nao"><Icon name="x" />Votou Não</span>;
  if (kind === 'abs') return <span className="vote v-abs"><Icon name="minus" />Absteve-se</span>;
  return <span className="vote v-abs"><Icon name="user-x" />Ausente</span>;
}

function Header({ active, onNav }) {
  const links = [
    { id: 'feed', label: 'Agora' },
    { id: 'deputy', label: 'Deputados' },
    { id: 'votacao', label: 'Votações' },
    { id: 'gastos', label: 'Gastos' },
  ];
  return (
    <header className="nav">
      <div className="wrap wrap-wide nav-in">
        <div className="brand" onClick={() => onNav('landing')}>
          <div className="mark">R$</div>
          <div className="wm"><span className="r">R$</span> Transparência</div>
        </div>
        <nav className="nav-links">
          {links.map(l => (
            <a key={l.id} className={active === l.id ? 'on' : ''} onClick={() => onNav(l.id)}>{l.label}</a>
          ))}
        </nav>
        <div className="nav-right">
          <div className="nav-search" onClick={() => onNav('feed')}>
            <Icon name="search" /><span>Buscar deputado…</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function Footer({ onNav }) {
  return (
    <footer className="footer">
      <div className="wrap wrap-wide">
        <div className="footer-in">
          <div style={{ maxWidth: 280 }}>
            <div className="brand" style={{ marginBottom: 12 }}>
              <div className="mark" style={{ width: 30, height: 30, fontSize: 13 }}>R$</div>
              <div className="wm"><span className="r">R$</span> Transparência</div>
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--green-200)' }}>
              Observatório independente sobre a Câmara dos Deputados. Dados públicos, leitura clara.
            </p>
          </div>
          <div className="footer-cols">
            <div className="footer-col">
              <h5>Explorar</h5>
              <a onClick={() => onNav('feed')}>O que tá rolando</a>
              <a onClick={() => onNav('deputy')}>Deputados</a>
              <a onClick={() => onNav('votacao')}>Votações</a>
              <a onClick={() => onNav('gastos')}>Gastos da cota</a>
            </div>
            <div className="footer-col">
              <h5>Fontes</h5>
              <a>Dados Abertos da Câmara</a>
              <a>Portal de Transparência</a>
              <a>Como calculamos</a>
              <a>Metodologia</a>
            </div>
          </div>
        </div>
        <p className="footer-note">
          Site independente, sem vínculo com a Câmara dos Deputados ou com o Governo Federal.
          Os dados exibidos neste protótipo são fictícios e ilustrativos. Em produção, os dados vêm
          da API de Dados Abertos da Câmara, atualizada diariamente.
        </p>
      </div>
    </footer>
  );
}

Object.assign(window, {
  useLucideRefresh, Icon, brl, brlFull, Avatar, PartyTag, VoteBadge, Header, Footer,
});
