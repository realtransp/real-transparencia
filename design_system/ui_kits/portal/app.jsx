// App shell — routing between screens + cobre modal + toast
function App() {
  const [screen, setScreen] = useState('landing');
  const [dep, setDep] = useState(DEPUTIES[0]);
  const [cobreFor, setCobreFor] = useState(null);
  const [toast, setToast] = useState('');

  useLayoutEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  function nav(s) { setScreen(s); window.scrollTo(0, 0); }
  function openDeputy(d) { setDep(d); nav('deputy'); }
  function cobrar(d) { setCobreFor(d); }
  function onSent() {
    setCobreFor(null);
    setToast('Cobrança enviada ao gabinete. Valeu por participar!');
    setTimeout(() => setToast(''), 3800);
  }

  return (
    <div className="app">
      <Header active={screen} onNav={nav} />
      <main style={{ flex: 1 }}>
        {screen === 'landing' && <Landing onNav={nav} onCobrar={cobrar} />}
        {screen === 'feed' && <Feed onNav={nav} onCobrar={cobrar} onOpenDeputy={openDeputy} />}
        {screen === 'deputy' && <DeputyProfile dep={dep} onNav={nav} onCobrar={cobrar} />}
        {screen === 'votacao' && <Votacao onNav={nav} onOpenDeputy={openDeputy} />}
        {screen === 'gastos' && <Gastos dep={dep} onNav={nav} onCobrar={cobrar} />}
      </main>
      <Footer onNav={nav} />
      {cobreFor && <CobreModal dep={cobreFor} onClose={() => setCobreFor(null)} onSent={onSent} />}
      {toast && <div className="toast"><Icon name="check-circle" />{toast}</div>}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
