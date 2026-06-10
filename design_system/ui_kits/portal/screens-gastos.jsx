// Gastos / CEAP panel
function Gastos({ dep, onNav, onCobrar }) {
  useLucideRefresh();
  const d = dep || DEPUTIES[0];
  const g = GASTOS;
  const maxCat = g.categories[0].value;
  const maxMonth = Math.max(...g.monthly);
  const months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const hiMonth = g.monthly.indexOf(maxMonth);
  return (
    <div>
      <div className="wrap wrap-wide page-head">
        <span className="eyebrow">Cota parlamentar (CEAP) · {d.name}</span>
        <h1 className="h1">Para onde foi a cota</h1>
        <p className="lead" style={{ marginTop: 8, fontSize: 16, maxWidth: '60ch' }}>
          Todo deputado tem uma verba paga com dinheiro público para o exercício do mandato.
          Aqui está cada real declarado por {d.name.split(' ')[0]} em {g.year}.
        </p>
      </div>

      {/* top stats */}
      <div className="wrap wrap-wide" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, paddingTop: 8 }}>
        <div className="card card-pad">
          <span className="eyebrow">Total gasto · {g.year}</span>
          <div className="data" style={{ fontSize: 32, color: 'var(--clay-600)', margin: '8px 0 2px' }}>{brl(g.total)}</div>
          <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--clay-600)', display: 'inline-flex', alignItems: 'center', gap: 3, whiteSpace: 'nowrap' }}>
            <Icon name="trending-up" style={{ width: 13, height: 13 }} />+{g.vsLast}% vs {g.year - 1}
          </span>
        </div>
        <div className="card card-pad">
          <span className="eyebrow">Maior categoria</span>
          <div className="data" style={{ fontSize: 32, margin: '8px 0 2px' }}>{brl(g.categories[0].value)}</div>
          <span className="muted" style={{ fontSize: 12.5 }}>{g.categories[0].label}</span>
        </div>
        <div className="card card-pad">
          <span className="eyebrow">Limite mensal da cota</span>
          <div className="data" style={{ fontSize: 32, margin: '8px 0 2px' }}>R$ 45k</div>
          <span className="muted" style={{ fontSize: 12.5 }}>varia por estado (SP)</span>
        </div>
      </div>

      <div className="wrap wrap-wide gastos-grid">
        {/* categories */}
        <div className="card card-pad">
          <h3 className="h3" style={{ marginBottom: 14 }}>Por categoria</h3>
          {g.categories.map((c, i) => (
            <div key={i} className="cat-row">
              <div className="cat-label"><span className="sq" style={{ background: c.color }}></span>{c.label}</div>
              <div className="data" style={{ fontSize: 13.5 }}>{brlFull(c.value)}</div>
              <div className="cat-track"><div className="fill" style={{ width: (c.value / maxCat * 100) + '%', background: c.color }}></div></div>
            </div>
          ))}
        </div>

        {/* monthly */}
        <div className="card card-pad">
          <h3 className="h3" style={{ marginBottom: 6 }}>Mês a mês</h3>
          <p className="muted" style={{ fontSize: 13, marginBottom: 6 }}>Valores em R$ mil. Pico em {months[hiMonth]}.</p>
          <div className="month-bars">
            {g.monthly.map((m, i) => (
              <div key={i} className={'mb' + (i === hiMonth ? ' hi' : '')} style={{ height: (m / maxMonth * 100) + '%' }} title={months[i] + ': R$ ' + m + 'k'}></div>
            ))}
          </div>
          <div className="month-x">{months.map((m, i) => <span key={i}>{m}</span>)}</div>
        </div>
      </div>

      {/* receipts table */}
      <div className="wrap wrap-wide" style={{ paddingBottom: 32 }}>
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 18px' }}>
            <h3 className="h3">Notas fiscais recentes</h3>
            <button className="btn btn-secondary btn-sm"><Icon name="download" />Baixar CSV</button>
          </div>
          <table className="rec-table">
            <thead>
              <tr><th>Data</th><th>Fornecedor</th><th>Categoria</th><th style={{ textAlign: 'right' }}>Valor</th></tr>
            </thead>
            <tbody>
              {g.receipts.map((r, i) => (
                <tr key={i}>
                  <td className="data" style={{ fontSize: 12.5, color: 'var(--fg-2)' }}>{r.date}</td>
                  <td>{r.vendor}</td>
                  <td><span className="tag">{r.cat}</span></td>
                  <td className="num">{brlFull(r.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* cobre band */}
      <div className="band">
        <div className="wrap wrap-wide band-in">
          <div>
            <h2>Achou o gasto alto?</h2>
            <p>Peça explicação direto pro gabinete. Em produção, a mensagem já vem com o número da nota.</p>
          </div>
          <button className="btn btn-action btn-lg" onClick={() => onCobrar(d)}><Icon name="megaphone" />Cobrar {d.name.split(' ')[0]}</button>
        </div>
      </div>
    </div>
  );
}
Object.assign(window, { Gastos });
