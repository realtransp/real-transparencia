// Votação detail page
function Votacao({ onNav, onOpenDeputy }) {
  useLucideRefresh();
  const v = VOTACAO;
  const total = v.forN + v.againstN + v.absentN;
  const depVotes = [
    { d: DEPUTIES[0], v: 'sim' },
    { d: DEPUTIES[1], v: 'nao' },
    { d: DEPUTIES[2], v: 'sim' },
    { d: DEPUTIES[3], v: 'abs' },
  ];
  return (
    <div>
      <div className="wrap vot-head" style={{ maxWidth: 860 }}>
        <a className="eyebrow" style={{ cursor: 'pointer', color: 'var(--green-700)' }} onClick={() => onNav('feed')}>← Voltar pro feed</a>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', margin: '14px 0 6px' }}>
          <span className="tag">{v.code}</span>
          <span className="muted" style={{ fontSize: 13 }}>{v.where} · {v.date}</span>
        </div>
        <h1 className="h1">{v.title}</h1>
        <p className="lead" style={{ marginTop: 12, fontSize: 16 }}>{v.summary}</p>

        <div className={'result-banner rb-' + v.result}>
          <div className="rk" style={{ background: v.result === 'aprovado' ? 'var(--green-600)' : 'var(--clay-600)', color: '#fff' }}>
            <Icon name={v.result === 'aprovado' ? 'check' : 'x'} />
          </div>
          <div>
            <div className="rt" style={{ color: v.result === 'aprovado' ? 'var(--green-700)' : 'var(--clay-700)' }}>
              {v.result === 'aprovado' ? 'Aprovado' : 'Rejeitado'} · {v.forN} a {v.againstN}
            </div>
            <div className="muted" style={{ fontSize: 13 }}>{v.absentN} ausentes ou em abstenção · {total} parlamentares</div>
          </div>
        </div>

        {/* tally bar */}
        <div className="tally-bar">
          <div className="seg" style={{ width: (v.forN / total * 100) + '%', background: 'var(--green-600)' }}></div>
          <div className="seg" style={{ width: (v.againstN / total * 100) + '%', background: 'var(--clay-600)' }}></div>
          <div className="seg" style={{ width: (v.absentN / total * 100) + '%', background: 'var(--ink-3)' }}></div>
        </div>
        <div className="tally">
          <div className="tally-col"><span className="vote v-sim"><Icon name="check" />{v.forN} Sim</span></div>
          <div className="tally-col" style={{ textAlign: 'center' }}><span className="vote v-nao"><Icon name="x" />{v.againstN} Não</span></div>
          <div className="tally-col" style={{ textAlign: 'right' }}><span className="vote v-abs"><Icon name="minus" />{v.absentN} ausentes</span></div>
        </div>

        {/* party breakdown */}
        <h3 className="h3" style={{ margin: '34px 0 12px' }}>Como votaram os partidos</h3>
        <div className="card card-pad">
          {v.parties.map((p, i) => {
            const t = p.for + p.against;
            return (
              <div key={i} className="party-row">
                <span className="tag" style={{ justifyContent: 'center' }}>{p.party}</span>
                <div>
                  <div className="party-bar">
                    <div className="pf" style={{ width: (p.for / t * 100) + '%' }}></div>
                    <div className="pa" style={{ width: (p.against / t * 100) + '%' }}></div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
                    <span className="data" style={{ fontSize: 11.5, color: 'var(--green-700)' }}>{p.for} sim</span>
                    <span className="data" style={{ fontSize: 11.5, color: 'var(--clay-700)' }}>{p.against} não</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* how specific deputies voted */}
        <h3 className="h3" style={{ margin: '34px 0 12px' }}>Voto por deputado</h3>
        <div className="card card-pad">
          {depVotes.map((dv, i) => (
            <div key={i} className="vote-row" onClick={() => onOpenDeputy(dv.d)} style={{ cursor: 'pointer' }}>
              <Avatar dep={dv.d} size={40} />
              <div className="vt">
                <div className="t">{dv.d.name}</div>
                <div className="c">{dv.d.party} · {dv.d.uf}</div>
              </div>
              <VoteBadge kind={dv.v} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
Object.assign(window, { Votacao });
