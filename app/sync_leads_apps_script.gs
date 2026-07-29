/**
 * Sincroniza leads_qualificados + enriquecimento_contato_piloto (Supabase) com a
 * aba "Leads" desta planilha, sem apagar o trabalho manual do comercial
 * (Status, Responsável, Última Interação, Observações).
 *
 * So traz leads com ja_tem_solar_aneel = false (cruzamento com a ANEEL,
 * 28/07/2026) - quem ja converteu fica de fora da planilha, nao so marcado.
 * A analise de % com/sem solar entre os leads quentes com contato vive no
 * dashboard (app/dashboard.py), nao aqui.
 *
 * Limitacao conhecida: se um lead que ja esta na planilha vier a instalar
 * solar depois (ja_tem_solar_aneel virar true numa proxima atualizacao do
 * dataset ANEEL), essa linha nao some sozinha - o script so adiciona/atualiza,
 * nunca remove linha (pra nao arriscar apagar trabalho comercial). Remocao
 * nesse caso e manual.
 *
 * Configuração (uma vez só):
 * 1. Extensions > Apps Script > cole este arquivo inteiro no Code.gs
 * 2. No editor: ícone de engrenagem (Project Settings) > Script Properties > Add:
 *      SUPABASE_URL  = https://SEU-PROJETO.supabase.co   (sem barra no final)
 *      SUPABASE_KEY  = <service_role key, a mesma do .env do projeto>
 * 3. Rode `sincronizarLeads` uma vez manualmente (autoriza o script)
 * 4. Triggers (ícone de relógio) > Add Trigger > sincronizarLeads > time-driven >
 *    diário (ou a cada hora, se quiser mais frequente)
 *
 * IMPORTANTE: quem tiver acesso de Editor nesta planilha também consegue abrir
 * o Apps Script e ver a service_role key nas Script Properties. Compartilhe
 * a edição só com quem for de confiança (mesmo nível de acesso que teria a
 * um CRM real com esses dados).
 */

const ABA_LEADS = 'Leads';
const SCORE_MINIMO = 80; // leads quentes - troque pra 60 se quiser incluir "Lead Bom" também
const TAMANHO_PAGINA = 1000; // teto do PostgREST nesse projeto Supabase

const COLUNAS = [
  'CNPJ', 'Razão Social', 'UF', 'Cidade', 'Segmento', 'Score', 'Classificação',
  'Telefone', 'Email', 'Site', 'Data Criação',
  'Status', 'Responsável', 'Última Interação', 'Observações', 'Última Sincronização',
];
// Colunas de acompanhamento comercial - o sync NUNCA escreve nelas se a linha já existir
const COLUNAS_COMERCIAIS = ['Status', 'Responsável', 'Última Interação', 'Observações'];
const COL_ULTIMA_SYNC = COLUNAS.length; // coluna O

function config_() {
  const props = PropertiesService.getScriptProperties();
  const url = props.getProperty('SUPABASE_URL');
  const key = props.getProperty('SUPABASE_KEY');
  if (!url || !key) {
    throw new Error('Configure SUPABASE_URL e SUPABASE_KEY em Project Settings > Script Properties.');
  }
  return { url: url.replace(/\/$/, ''), key: key };
}

function chamarSupabase_(caminho, cfg) {
  const resp = UrlFetchApp.fetch(cfg.url + caminho, {
    headers: { apikey: cfg.key, Authorization: 'Bearer ' + cfg.key },
    muteHttpExceptions: true,
  });
  const codigo = resp.getResponseCode();
  if (codigo >= 300) {
    throw new Error('Supabase respondeu ' + codigo + ': ' + resp.getContentText());
  }
  return JSON.parse(resp.getContentText());
}

function buscarLeadsQualificados_(cfg) {
  const campos = 'cnpj,razao_social,uf,municipio,segmento,score,classificacao,data_criacao';
  let todos = [];
  let offset = 0;
  while (true) {
    const caminho = '/rest/v1/leads_qualificados?select=' + campos +
      '&score=gte.' + SCORE_MINIMO + '&ja_tem_solar_aneel=eq.false&order=score.desc' +
      '&offset=' + offset + '&limit=' + TAMANHO_PAGINA;
    const pagina = chamarSupabase_(caminho, cfg);
    if (!pagina || pagina.length === 0) break;
    todos = todos.concat(pagina);
    if (pagina.length < TAMANHO_PAGINA) break;
    offset += TAMANHO_PAGINA;
  }
  return todos;
}

function buscarContatos_(cfg) {
  const campos = 'cnpj,telefone,email,site';
  const linhas = chamarSupabase_('/rest/v1/enriquecimento_contato_piloto?select=' + campos, cfg);
  const porCnpj = {};
  linhas.forEach(function (linha) { porCnpj[linha.cnpj] = linha; });
  return porCnpj;
}

function sincronizarLeads() {
  const cfg = config_();
  const planilha = SpreadsheetApp.getActiveSpreadsheet();
  const aba = planilha.getSheetByName(ABA_LEADS) || planilha.insertSheet(ABA_LEADS);

  if (aba.getLastRow() === 0) {
    aba.appendRow(COLUNAS);
  }

  // Mapeia linhas existentes por CNPJ, preservando as colunas comerciais
  const dados = aba.getDataRange().getValues();
  const cabecalho = dados[0];
  const idxCnpj = cabecalho.indexOf('CNPJ');
  const linhasPorCnpj = {};
  for (let i = 1; i < dados.length; i++) {
    const cnpj = dados[i][idxCnpj];
    if (cnpj) linhasPorCnpj[cnpj] = { linhaPlanilha: i + 1, valores: dados[i] };
  }

  const leads = buscarLeadsQualificados_(cfg);
  const contatos = buscarContatos_(cfg);
  const agora = new Date();

  let novos = 0;
  let atualizados = 0;

  leads.forEach(function (lead) {
    const contato = contatos[lead.cnpj] || {};
    const linhaOrigem = [
      lead.cnpj, lead.razao_social, lead.uf, lead.municipio, lead.segmento, lead.score, lead.classificacao,
      contato.telefone || '', contato.email || '', contato.site || '', lead.data_criacao,
    ];

    const existente = linhasPorCnpj[lead.cnpj];
    if (existente) {
      // Atualiza só as colunas de origem (A-K) e o timestamp (P) - preserva L-O
      aba.getRange(existente.linhaPlanilha, 1, 1, linhaOrigem.length).setValues([linhaOrigem]);
      aba.getRange(existente.linhaPlanilha, COL_ULTIMA_SYNC).setValue(agora);
      atualizados++;
    } else {
      const linhaComercial = ['Novo', '', '', ''];
      aba.appendRow(linhaOrigem.concat(linhaComercial).concat([agora]));
      novos++;
    }
  });

  Logger.log('Sync concluído: %s novos, %s atualizados, %s no total consultado.', novos, atualizados, leads.length);
}
