// Feed "Agora" — what's happening + sidebar
function Feed({ onNav, onCobrar, onOpenDeputy }) {
  useLucideRefresh();
  return (
    <div>
      <div className="wrap wrap-wide page-head">
        <span className="eyebrow">Câmara dos Deputados · atualizado hoje, 14h20</span>
        <h1 className="h1">O que tá rolando</h1>
        <p className="lead" style={{ marginTop: 8, fontSize: 16 }}>Votações, urgências e tramitações dos últimos dias — em ordem cronológica.</p>
      </div>
      <div className="wrap wrap-wide feed-layout">
        {/* feed list */}
        <div className="feed-list">
          {FEED.map(item => (
            <div key={item.id} className="card feed-item" onClick={() => onNav(item.kind === 'tramitando' ? 'votacao' : 'votacao')}>
              <div className={'icn icn-' + item.kind}>
                <Icon name={item.kind === 'aprovado' ? 'check' : item.kind === 'rejeitado' ? 'x' : 'clock'} />
              </div>
              <div style={{ flex: 1 }}>
                <span className="eyebrow" style={{ textTransform: 'none', letterSpacing: 0 }}>{item.where} · {item.when}</span>
                <div className="ft">{item.title}</div>
                <div className="meta">
                  <span className="tag">{item.code}</span>
                  <span className="res" style={{ color: item.kind === 'rejeitado' ? 'var(--clay-700)' : item.kind === 'aprovado' ? 'var(--green-700)' : 'var(--amber-700)' }}>{item.tally}</span>
                  <span className="muted">· {item.detail}</span>
                </div>
                <div className="sm">{item.summary}</div>
              </div>
              <Icon name="chevron-right" className="muted" />
            </div>
          ))}
        </div>

        {/* sidebar */}
        <aside style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="card side-card">
            <h4>Mais vigiados esta semana</h4>
            {DEPUTIES.map(d => (
              <div key={d.id} className="mini-dep" onClick={() => onOpenDeputy(d)}>
                <Avatar dep={d} size={38} />
                <div>
                  <div className="mn">{d.name}</div>
                  <div className="ms">{d.party} · {d.uf}</div>
                </div>
                <span className="val" style={{ color: d.presence < 70 ? 'var(--clay-600)' : 'var(--green-600)' }}>{d.presence}%</span>
              </div>
            ))}
          </div>
          <div className="card side-card" style={{ background: 'var(--green-800)', border: 0, color: 'var(--ink-on-dark)' }}>
            <h4 style={{ color: '#fff' }}>Viu algo que não curtiu?</h4>
            <p style={{ fontSize: 13.5, color: 'var(--green-200)', lineHeight: 1.55, margin: '0 0 14px' }}>
              Escolha um deputado e mande sua cobrança direto pro gabinete.
            </p>
            <button className="btn btn-action btn-block" onClick={() => onCobrar(DEPUTIES[1])}><Icon name="megaphone" />Cobrar deputado</button>
          </div>
        </aside>
      </div>
    </div>
  );
}
Object.assign(window, { Feed });
