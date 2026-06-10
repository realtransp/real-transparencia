// Mock data for the R$ Transparência portal UI kit.
// All names, values and tallies are fictional and illustrative.

const DEPUTIES = [
  {
    id: 'carla', name: 'Carla Medeiros', party: 'PT', uf: 'SP', term: '3º mandato',
    color: 'var(--green-600)', initials: 'CM', presence: 91, cota: 198450, cotaRank: 'média',
    bio: 'Comissão de Constituição e Justiça (CCJ) · Frente Parlamentar de Educação',
    votesFor: 142, votesAgainst: 38, absences: 12,
  },
  {
    id: 'rui', name: 'Rui Alencar', party: 'PL', uf: 'RJ', term: '1º mandato',
    color: 'var(--clay-600)', initials: 'RA', presence: 63, cota: 241980, cotaRank: '12% acima da média',
    bio: 'Comissão de Finanças e Tributação · Frente da Agropecuária',
    votesFor: 88, votesAgainst: 96, absences: 41,
  },
  {
    id: 'bea', name: 'Beatriz Nunes', party: 'PSDB', uf: 'MG', term: '2º mandato',
    color: 'var(--petro-500)', initials: 'BN', presence: 84, cota: 176300, cotaRank: 'abaixo da média',
    bio: 'Comissão de Meio Ambiente · Frente das Cidades',
    votesFor: 120, votesAgainst: 54, absences: 19,
  },
  {
    id: 'joao', name: 'João Peixoto', party: 'MDB', uf: 'BA', term: '4º mandato',
    color: 'var(--amber-500)', initials: 'JP', presence: 77, cota: 213040, cotaRank: 'média',
    bio: 'Comissão de Saúde · Frente do Comércio e Serviços',
    votesFor: 134, votesAgainst: 41, absences: 27,
  },
];

const FEED = [
  {
    id: 'v1', kind: 'aprovado', where: 'Plenário', when: 'há 2 horas',
    title: 'Aprovado o marco legal da inteligência artificial',
    code: 'PL 2338/2023', tally: '312 a 138', detail: '13 ausentes',
    summary: 'Define regras para sistemas de IA de alto risco e cria autoridade de fiscalização.',
  },
  {
    id: 'v2', kind: 'rejeitado', where: 'Comissão · CCJ', when: 'ontem',
    title: 'Rejeitada a urgência para o projeto do salário mínimo',
    code: 'REQ 45/2024', tally: '9 a 14', detail: 'segue tramitação ordinária',
    summary: 'Pedido para acelerar a votação foi barrado; texto volta para análise das comissões.',
  },
  {
    id: 'v3', kind: 'tramitando', where: 'Plenário', when: 'há 3 dias',
    title: 'Em discussão a reforma do imposto sobre combustíveis',
    code: 'PLP 68/2024', tally: 'votação prevista', detail: 'relatório lido',
    summary: 'Texto unifica alíquotas e muda a repartição entre estados. Votação marcada para a próxima semana.',
  },
  {
    id: 'v4', kind: 'aprovado', where: 'Plenário', when: 'há 4 dias',
    title: 'Aprovado o aumento do orçamento da saúde para 2025',
    code: 'PLN 12/2024', tally: '388 a 41', detail: '2 abstenções',
    summary: 'Adiciona R$ 22 bilhões ao piso da saúde no próximo exercício.',
  },
];

const VOTACAO = {
  title: 'Marco legal da inteligência artificial',
  code: 'PL 2338/2023', date: '28 de maio de 2025', where: 'Plenário',
  result: 'aprovado', forN: 312, againstN: 138, absentN: 13,
  summary: 'Estabelece princípios, direitos e deveres para o desenvolvimento e uso de sistemas de inteligência artificial no Brasil, com regras mais rígidas para aplicações de alto risco e criação de uma autoridade de fiscalização.',
  parties: [
    { party: 'PT', for: 64, against: 2 },
    { party: 'PL', for: 18, against: 78 },
    { party: 'MDB', for: 41, against: 9 },
    { party: 'PSDB', for: 28, against: 4 },
    { party: 'PSD', for: 36, against: 11 },
  ],
};

// CEAP spending categories for the gastos panel
const GASTOS = {
  total: 218450,
  year: 2024,
  vsLast: 12,
  categories: [
    { label: 'Passagens aéreas', value: 64120, color: 'var(--viz-1)' },
    { label: 'Combustível', value: 38905, color: 'var(--viz-2)' },
    { label: 'Aluguel de escritório', value: 33200, color: 'var(--viz-4)' },
    { label: 'Divulgação da atividade', value: 29770, color: 'var(--viz-3)' },
    { label: 'Consultoria e pesquisa', value: 27600, color: 'var(--viz-5)' },
    { label: 'Telefonia e correios', value: 14855, color: 'var(--viz-6)' },
    { label: 'Outros', value: 10000, color: 'var(--ink-3)' },
  ],
  monthly: [14, 21, 16, 34, 24, 19, 17, 22, 28, 15, 20, 26],
  receipts: [
    { date: '12/12/2024', vendor: 'Cia. Aérea — GRU→BSB', cat: 'Passagens', value: 1840.00 },
    { date: '09/12/2024', vendor: 'Posto Central Ltda.', cat: 'Combustível', value: 412.50 },
    { date: '03/12/2024', vendor: 'Gráfica Boa Impressão', cat: 'Divulgação', value: 6200.00 },
    { date: '28/11/2024', vendor: 'Imobiliária Horizonte', cat: 'Aluguel', value: 2766.67 },
  ],
};

Object.assign(window, { DEPUTIES, FEED, VOTACAO, GASTOS });
