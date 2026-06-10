// "Cobre seu deputado" — modal flow
function CobreModal({ dep, onClose, onSent }) {
  useLucideRefresh();
  const d = dep;
  const [channel, setChannel] = useState('whatsapp');
  const templates = {
    voto: `Olá, deputado(a) ${d.name}. Vi pelo R$ Transparência como você votou no PL 2338/2023 e gostaria de entender melhor o motivo. Como seu eleitor(a), peço que explique sua posição. Obrigado(a).`,
    gasto: `Olá, deputado(a) ${d.name}. Acompanhando seus gastos da cota parlamentar (CEAP) pelo R$ Transparência, fiquei com dúvidas sobre algumas despesas de 2024. Pode esclarecer? Conto com a transparência. Obrigado(a).`,
    presenca: `Olá, deputado(a) ${d.name}. Notei pelo R$ Transparência uma presença de ${d.presence}% nas votações. Como seu eleitor(a), gostaria de saber como você tem representado nosso estado. Obrigado(a).`,
  };
  const [tpl, setTpl] = useState('voto');
  const [msg, setMsg] = useState(templates.voto);
  const [sent, setSent] = useState(false);

  function pickTpl(k) { setTpl(k); setMsg(templates[k]); }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        {!sent ? (
          <div>
            <div className="modal-head">
              <Avatar dep={d} size={46} />
              <div>
                <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 600, fontSize: 18, whiteSpace: 'nowrap' }}>Cobrar {d.name}</div>
                <div className="muted" style={{ fontSize: 13 }}>{d.party} · {d.uf} · Gabinete oficial</div>
              </div>
              <button className="x" onClick={onClose}><Icon name="x" /></button>
            </div>
            <div className="modal-body">
              {/* channel */}
              <label className="field-label">Como enviar</label>
              <div className="channel-row">
                <div className={'channel' + (channel === 'whatsapp' ? ' on' : '')} onClick={() => setChannel('whatsapp')}>
                  <div className="ci" style={{ background: '#25D366', color: '#06351c' }}><Icon name="message-circle" /></div>
                  <div><div className="ct">WhatsApp</div><div className="cs">do gabinete</div></div>
                </div>
                <div className={'channel' + (channel === 'email' ? ' on' : '')} onClick={() => setChannel('email')}>
                  <div className="ci" style={{ background: 'var(--amber-100)', color: 'var(--amber-700)' }}><Icon name="mail" /></div>
                  <div><div className="ct">E-mail</div><div className="cs">dep.{d.id}@camara.leg.br</div></div>
                </div>
              </div>

              {/* templates */}
              <label className="field-label">Comece de um modelo</label>
              <div className="template-row">
                <button className={'chip' + (tpl === 'voto' ? ' on' : '')} onClick={() => pickTpl('voto')}>Sobre um voto</button>
                <button className={'chip' + (tpl === 'gasto' ? ' on' : '')} onClick={() => pickTpl('gasto')}>Sobre um gasto</button>
                <button className={'chip' + (tpl === 'presenca' ? ' on' : '')} onClick={() => pickTpl('presenca')}>Sobre a presença</button>
              </div>

              {/* message */}
              <label className="field-label">Sua mensagem <span className="muted" style={{ fontWeight: 400 }}>· edite à vontade</span></label>
              <textarea className="msg-box" value={msg} onChange={e => setMsg(e.target.value)}></textarea>

              <div className="modal-foot">
                <button className="btn btn-secondary" onClick={onClose}>Cancelar</button>
                {channel === 'whatsapp'
                  ? <button className="btn btn-wa btn-block" onClick={() => setSent(true)}><Icon name="message-circle" />Abrir no WhatsApp</button>
                  : <button className="btn btn-amber btn-block" onClick={() => setSent(true)}><Icon name="mail" />Enviar e-mail</button>}
              </div>
              <p className="muted" style={{ fontSize: 11.5, marginTop: 12, lineHeight: 1.5, textAlign: 'center' }}>
                Você revê e confirma no seu app antes de enviar. Não guardamos sua mensagem.
              </p>
            </div>
          </div>
        ) : (
          <div className="sent">
            <div className="ok"><Icon name="check" /></div>
            <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 600, fontSize: 21, marginBottom: 6 }}>Mensagem pronta!</div>
            <p className="muted" style={{ fontSize: 14.5, lineHeight: 1.6, maxWidth: '40ch', margin: '0 auto 22px' }}>
              {channel === 'whatsapp'
                ? `Abrimos o WhatsApp do gabinete de ${d.name.split(' ')[0]} com seu texto. É só dar enviar.`
                : `Abrimos seu e-mail com a mensagem para o gabinete de ${d.name.split(' ')[0]}. É só dar enviar.`}
            </p>
            <button className="btn btn-primary" onClick={() => { onSent && onSent(); }}>Voltar ao portal</button>
          </div>
        )}
      </div>
    </div>
  );
}
Object.assign(window, { CobreModal });
