// Deputy profile
function DeputyProfile({ dep, onNav, onCobrar }) {
  useLucideRefresh();
  const [tab, setTab] = useState('votos');
  const d = dep || DEPUTIES[0];
  const recentVotes = [
    { t: 'Marco legal da inteligência artificial', c: 'PL 2338/2023', v: 'sim' },
    { t: 'Urgência para o projeto do salário mínimo', c: 'REQ 45/2024', v: 'nao' },
    { t: 'Reforma do imposto sobre combustíveis', c: 'PLP 68/2024', v: 'sim' },
    { t: 'Orçamento da saúde para 2025', c: 'PLN 12/2024', v: 'abs' },
    { t: 'Marco temporal das terras indígenas', c: 'PL 490/2007', v: 'aus' },
  ];
  return (
    <div>
      <div className="dep-hero">
        <div className="wrap wrap-wide dep-hero-in">
          <div className="dep-top">
            <Avatar dep={d} size={84} />
            <div style={{ flex: 1 }}>
              <div className="dep-name">{d.name}</div>
              <div className="dep-meta">
                <PartyTag dep={d} withTerm />
                <span className="muted" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{d.cotaRank === 'média' ? 'gasto na média' : d.cotaRank}</span>
              </div>
              <div className="dep-bio">{d.bio}</div>
            </div>
            <div className="dep-actions">
              <button className="btn btn-secondary" onClick={() => onNav('gastos')}><Icon name="receipt" />Ver gastos</button>
              <button className="btn btn-action" onClick={() => onCobrar(d)}><Icon name="megaphone" />Cobrar</button>
            </div>
          </div>
          <div className="dep-stats">
            <div className="dep-stat"><div className="v" style={{ color: d.presence < 70 ? 'var(--clay-600)' : 'var(--fg-1)' }}>{d.presence}%</div><div className="l">Presença em plenário</div></div>
            <div className="dep-stat"><div className="v">{d.votesFor}</div><div className="l">Votos "Sim" no ano</div></div>
            <div className="dep-stat"><div className="v">{d.votesAgainst}</div><div className="l">Votos "Não" no ano</div></div>
            <div className="dep-stat"><div className="v" style={{ color: 'var(--clay-600)' }}>{brl(d.cota)}</div><div className="l">Cota gasta · 2024</div></div>
          </div>
          <div className="tabs">
            <div className={'tab' + (tab === 'votos' ? ' on' : '')} onClick={() => setTab('votos')}>Votações</div>
            <div className={'tab' + (tab === 'gastos' ? ' on' : '')} onClick={() => setTab('gastos')}>Gastos</div>
            <div className={'tab' + (tab === 'sobre' ? ' on' : '')} onClick={() => setTab('sobre')}>Sobre</div>
          </div>
        </div>
      </div>

      <div className="wrap wrap-wide dep-body">
        {tab === 'votos' && (
          <div className="card card-pad">
            <h3 className="h3" style={{ marginBottom: 6 }}>Como {d.name.split(' ')[0]} votou</h3>
            <p className="muted" style={{ fontSize: 13.5, marginBottom: 8 }}>Votações nominais mais relevantes de 2025.</p>
            {recentVotes.map((rv, i) => (
              <div key={i} className="vote-row">
                <div className="vt">
                  <div className="t">{rv.t}</div>
                  <div className="c">{rv.c}</div>
                </div>
                <VoteBadge kind={rv.v} />
                <Icon name="chevron-right" className="muted" />
              </div>
            ))}
          </div>
        )}
        {tab === 'gastos' && (
          <div className="card card-pad">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div>
                <h3 className="h3">Resumo da cota · 2024</h3>
                <p className="muted" style={{ fontSize: 13.5 }}>Total declarado: <strong className="data" style={{ color: 'var(--clay-600)' }}>{brlFull(d.cota)}</strong></p>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => onNav('gastos')}>Detalhar <Icon name="arrow-right" /></button>
            </div>
            {GASTOS.categories.slice(0, 4).map((c, i) => {
              const pct = Math.round((c.value / GASTOS.categories[0].value) * 100);
              return (
                <div key={i} className="cat-row">
                  <div className="cat-label"><span className="sq" style={{ background: c.color }}></span>{c.label}</div>
                  <div className="data" style={{ fontSize: 13.5 }}>{brlFull(c.value)}</div>
                  <div className="cat-track"><div className="fill" style={{ width: pct + '%', background: c.color }}></div></div>
                </div>
              );
            })}
          </div>
        )}
        {tab === 'sobre' && (
          <div className="card card-pad">
            <h3 className="h3" style={{ marginBottom: 8 }}>Sobre o mandato</h3>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--fg-2)', maxWidth: '60ch' }}>
              {d.name} ({d.party}-{d.uf}) está no {d.term.toLowerCase()}. {d.bio}.
              Os dados de votação, presença e gastos são extraídos da API de Dados Abertos da Câmara
              e atualizados diariamente.
            </p>
            <div style={{ display: 'flex', gap: 18, marginTop: 18, flexWrap: 'wrap' }}>
              <div className="tag"><Icon name="mail" style={{ width: 13, height: 13 }} />dep.{d.id}@camara.leg.br</div>
              <div className="tag"><Icon name="phone" style={{ width: 13, height: 13 }} />(61) 3215-0000</div>
              <div className="tag"><Icon name="map-pin" style={{ width: 13, height: 13 }} />Gabinete {200 + DEPUTIES.indexOf(d) * 14}, Anexo IV</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
Object.assign(window, { DeputyProfile });
