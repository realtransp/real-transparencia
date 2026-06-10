// Landing / marketing homepage
function Landing({ onNav, onCobrar }) {
  useLucideRefresh();
  const [q, setQ] = useState('');
  return (
    <div>
      {/* HERO */}
      <section className="hero">
        <div className="wrap wrap-wide hero-in">
          <span className="eyebrow" style={{ color: 'var(--green-300)' }}>Câmara dos Deputados · dados abertos</span>
          <h1 style={{ marginTop: 14 }}>Onde o seu dinheiro<br /><span className="em">vira voto.</span></h1>
          <p>
            Acompanhe o que está rolando na Câmara — votações, gastos da cota e presença —
            em linguagem clara. E quando não gostar, <strong style={{ color: '#fff' }}>cobre seu deputado</strong> em 30 segundos.
          </p>
          <div className="hero-search">
            <div className="field">
              <Icon name="search" />
              <input value={q} onChange={e => setQ(e.target.value)} placeholder="Busque por nome, partido ou estado…" />
            </div>
            <button className="btn btn-amber btn-lg" onClick={() => onNav('feed')}>Buscar</button>
          </div>
          <div className="hero-stats">
            <div className="s"><div className="n">513</div><div className="l">deputados monitorados</div></div>
            <div className="s"><div className="n">1.240</div><div className="l">votações neste ano</div></div>
            <div className="s"><div className="n">R$ 1,4 bi</div><div className="l">em cotas rastreadas</div></div>
          </div>
        </div>
      </section>

      {/* O QUE TÁ ROLANDO — preview do feed */}
      <section className="section">
        <div className="wrap wrap-wide">
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 24 }}>
            <div className="section-head" style={{ marginBottom: 0 }}>
              <span className="eyebrow">Agora</span>
              <h2 className="h2">O que tá rolando</h2>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => onNav('feed')}>Ver tudo <Icon name="arrow-right" /></button>
          </div>
          <div className="feed-list">
            {FEED.slice(0, 3).map(item => (
              <div key={item.id} className="card feed-item" onClick={() => onNav(item.kind === 'tramitando' ? 'feed' : 'votacao')}>
                <div className={'icn icn-' + item.kind}>
                  <Icon name={item.kind === 'aprovado' ? 'check' : item.kind === 'rejeitado' ? 'x' : 'clock'} />
                </div>
                <div style={{ flex: 1 }}>
                  <div className="meta"><span className="eyebrow" style={{ textTransform: 'none', letterSpacing: 0 }}>{item.where} · {item.when}</span></div>
                  <div className="ft">{item.title}</div>
                  <div className="meta">
                    <span className="tag">{item.code}</span>
                    <span className="res" style={{ color: item.kind === 'rejeitado' ? 'var(--clay-700)' : item.kind === 'aprovado' ? 'var(--green-700)' : 'var(--amber-700)' }}>{item.tally}</span>
                    <span className="muted">· {item.detail}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="section" style={{ background: 'var(--paper-1)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <div className="wrap wrap-wide">
          <div className="section-head">
            <span className="eyebrow">Por dentro</span>
            <h2 className="h2">Tudo o que é público, finalmente legível</h2>
            <p>Pegamos os dados abertos da Câmara — densos e fragmentados — e transformamos em algo que dá pra entender e agir.</p>
          </div>
          <div className="feat-grid">
            <div className="card feat" onClick={() => onNav('votacao')} style={{ cursor: 'pointer' }}>
              <div className="ic"><Icon name="vote" /></div>
              <h3>Como cada um vota</h3>
              <p>Veja o voto de cada deputado nas votações que importam, com o placar e o recorte por partido.</p>
            </div>
            <div className="card feat" onClick={() => onNav('gastos')} style={{ cursor: 'pointer' }}>
              <div className="ic" style={{ background: 'var(--clay-100)', color: 'var(--clay-700)' }}><Icon name="receipt" /></div>
              <h3>Para onde vai a cota</h3>
              <p>Cada nota fiscal da cota parlamentar (CEAP), agrupada por categoria e fácil de comparar.</p>
            </div>
            <div className="card feat" onClick={() => onNav('deputy')} style={{ cursor: 'pointer' }}>
              <div className="ic" style={{ background: 'var(--amber-100)', color: 'var(--amber-700)' }}><Icon name="user-check" /></div>
              <h3>Presença e atuação</h3>
              <p>Quem aparece, quem falta, em quais comissões atua. O retrato completo de cada mandato.</p>
            </div>
          </div>
        </div>
      </section>

      {/* COMO COBRAR */}
      <section className="section">
        <div className="wrap wrap-wide">
          <div className="section-head">
            <span className="eyebrow">Cobre seu deputado</span>
            <h2 className="h2">Da indignação à mensagem, em três passos</h2>
            <p>Não fica só na revolta do grupo da família. Mande direto pro gabinete.</p>
          </div>
          <div className="steps">
            <div className="step">
              <div className="num">01</div>
              <h4>Encontre o deputado</h4>
              <p>Busque pelo nome ou pelo seu estado e abra o perfil com votos e gastos.</p>
            </div>
            <div className="step">
              <div className="num">02</div>
              <h4>Monte a mensagem</h4>
              <p>Comece de um modelo pronto — sobre um voto, um gasto ou uma cobrança — e edite com suas palavras.</p>
            </div>
            <div className="step">
              <div className="num">03</div>
              <h4>Envie em 30 segundos</h4>
              <p>Dispare por e-mail ou direto no WhatsApp do gabinete. Sem cadastro, sem burocracia.</p>
            </div>
          </div>
        </div>
      </section>

      {/* BAND CTA */}
      <section className="band">
        <div className="wrap wrap-wide band-in">
          <div>
            <h2>Pronto pra cobrar?</h2>
            <p>Escolha um deputado e mande sua mensagem agora. Leva menos tempo que reclamar no almoço de domingo.</p>
          </div>
          <button className="btn btn-action btn-lg" onClick={() => onCobrar(DEPUTIES[1])}><Icon name="megaphone" />Cobrar um deputado</button>
        </div>
      </section>
    </div>
  );
}
Object.assign(window, { Landing });
