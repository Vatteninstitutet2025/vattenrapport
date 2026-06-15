<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Preview – Vattenrapport</title>
  <style>
    @page { size: A4; margin: 12mm; }
    :root {
      --ink:#111827; --muted:#64748b; --line:#dbe4ee; --brand:#0f766e;
      --brand-soft:#e6fffb; --warn:#f59e0b; --warn-soft:#fff7ed;
      --danger:#dc2626; --danger-soft:#fef2f2; --good:#16a34a; --soft:#f8fafc;
    }
    * { box-sizing:border-box; }
    body { margin:0; background:#eef3f7; color:var(--ink); font-family:Arial, Helvetica, sans-serif; line-height:1.55; }
    .sheet { width:210mm; min-height:297mm; margin:24px auto; background:white; padding:18mm; box-shadow:0 12px 35px rgba(15,23,42,.12); }
    .top { display:flex; justify-content:space-between; gap:24px; align-items:flex-start; border-bottom:1px solid var(--line); padding-bottom:18px; }
    .brandline { display:inline-block; color:var(--brand); background:var(--brand-soft); border:1px solid #b6ece5; border-radius:999px; padding:6px 12px; font-size:12px; letter-spacing:.08em; text-transform:uppercase; font-weight:700; }
    h1 { margin:18px 0 0; font-size:42px; line-height:1; letter-spacing:-.04em; }
    .meta { min-width:270px; border:1px solid var(--line); border-radius:16px; padding:14px 16px; font-size:13px; background:#fff; }
    .meta-row { display:flex; justify-content:space-between; gap:18px; padding:5px 0; }
    .meta-row span:first-child { color:var(--muted); }
    .meta-row span:last-child { font-weight:700; text-align:right; }
    .summary-box { margin-top:22px; border:1px solid var(--line); border-radius:20px; padding:22px; background:linear-gradient(180deg,#ffffff,#fbfdff); }
    .summary-grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
    .label { color:var(--muted); text-transform:uppercase; letter-spacing:.08em; font-size:12px; font-weight:700; margin-bottom:5px; }
    .status-title { font-size:28px; font-weight:800; margin:0; }
    .status-pill { display:inline-flex; align-items:center; gap:8px; margin-top:10px; padding:8px 12px; border-radius:999px; background:var(--warn-soft); border:1px solid #fed7aa; color:#9a3412; font-weight:700; }
    .dot { width:9px; height:9px; border-radius:99px; background:var(--warn); display:inline-block; }
    .quick { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-top:16px; }
    .quick-card { border:1px solid var(--line); border-radius:14px; padding:14px; background:#fff; }
    .quick-card strong { display:block; margin-bottom:5px; }
    section { margin-top:24px; }
    h2 { font-size:20px; margin:0 0 12px; letter-spacing:-.02em; }
    .finding { border:1px solid #fed7aa; border-left:6px solid var(--warn); background:var(--warn-soft); border-radius:14px; padding:15px 16px; margin-bottom:12px; break-inside:avoid; }
    .finding.danger { border-color:#fecaca; border-left-color:var(--danger); background:var(--danger-soft); }
    .finding h3 { margin:0 0 8px; font-size:16px; }
    .finding .small { color:var(--muted); font-size:13px; margin-bottom:8px; }
    .advice { border:1px solid var(--line); border-radius:16px; padding:16px 18px; background:#f8fafc; }
    .advice ul { margin:0; padding-left:19px; }
    .advice li { margin:8px 0; }
    table { width:100%; border-collapse:collapse; font-size:12px; margin-top:8px; }
    th, td { border-bottom:1px solid var(--line); padding:8px 6px; text-align:left; vertical-align:top; }
    th { color:var(--muted); text-transform:uppercase; letter-spacing:.06em; font-size:11px; background:#f8fafc; }
    .footer { margin-top:28px; padding-top:14px; border-top:1px solid var(--line); color:var(--muted); font-size:11px; display:flex; justify-content:space-between; gap:20px; }
  </style>
</head>
<body>
  <main class="sheet">
    <header class="top">
      <div>
        <div class="brandline">Svenska Vatteninstitutet · Analysrapport</div>
        <h1>Vattenrapport</h1>
      </div>
      <div class="meta">
        <div class="meta-row"><span>Fastighet</span><span>SIGTUNA STORA SÖDERBY 2:21</span></div>
        <div class="meta-row"><span>Provnummer</span><span>177-2026-04102502</span></div>
        <div class="meta-row"><span>Provdatum</span><span>2026-04-10 10:20</span></div>
      </div>
    </header>

    <div class="summary-box">
      <div class="summary-grid">
        <div>
          <div class="label">Samlad bedömning</div>
          <p class="status-title">Tjänligt med anmärkning</p>
          <div class="status-pill"><span class="dot"></span> Bör följas upp</div>
        </div>
        <div>
          <div class="label">Kort slutsats</div>
          <p>Vattnet kan ofta användas, men vissa avvikande värden bör följas upp eftersom de kan påverka smak, installationer eller hälsobedömning.</p>
        </div>
      </div>
      <div class="quick">
        <div class="quick-card"><strong>Viktigaste fynd</strong>Koppar, nitrat och mangan.</div>
        <div class="quick-card"><strong>Åtgärdsnivå</strong>Ingen akut spärr, men uppföljning rekommenderas.</div>
        <div class="quick-card"><strong>Nästa steg</strong>Bedöm brunn, installationer och ta omprov vid behov.</div>
      </div>
    </div>

    <section>
      <h2>Det här bör du ha koll på</h2>
      <article class="finding">
        <h3>Koppar: 1,5 mg/l</h3>
        <div class="small">Status: Tjänligt med anmärkning · Prioritet: Bör följas upp</div>
        <p>Förhöjd kopparhalt kan ge smakpåverkan och blågröna missfärgningar. Koppar bör bedömas tillsammans med pH och installationer, eftersom surt eller korrosivt vatten kan lösa ut koppar från ledningar och varmvattenberedare.</p>
      </article>
      <article class="finding">
        <h3>Nitrat: 23 mg/l</h3>
        <div class="small">Status: Tjänligt med anmärkning · Prioritet: Bör följas upp</div>
        <p>Förhöjda nitrathalter bör tas på allvar, särskilt om vattnet används av spädbarn, små barn eller gravida. Utred möjliga källor som avlopp, gödsel, jordbruk eller ytvattenpåverkan.</p>
      </article>
      <article class="finding">
        <h3>Mangan: 0,60 mg/l</h3>
        <div class="small">Status: Tjänligt med anmärkning · Prioritet: Bör följas upp</div>
        <p>Kan ge svart missfärgning, mörka utfällningar, missfärgad tvätt och beläggningar i sanitet. Förhöjda manganhalter kan även orsaka igensättning av armaturer, ventiler, rör, varmvattenberedare och hushållsmaskiner över tid.</p>
      </article>
    </section>

    <section>
      <h2>Praktiska råd</h2>
      <div class="advice">
        <ul>
          <li>Kontrollera om missfärgning, beläggningar eller igensättningar märks i vardagen, särskilt kopplat till mangan.</li>
          <li>Bedöm koppar tillsammans med pH och installationer för att avgöra om korrosion kan bidra.</li>
          <li>Vid förhöjt nitrat bör annat vatten användas till spädbarn och små barn tills nivån är utredd.</li>
          <li>Ta ett nytt vattenprov efter åtgärd eller om du vill kontrollera om avvikelserna är tillfälliga eller återkommande.</li>
        </ul>
      </div>
    </section>

    <section>
      <h2>Alla analyserade parametrar</h2>
      <table>
        <thead><tr><th>Parameter</th><th>Resultat</th><th>Status</th><th>Kommentar</th></tr></thead>
        <tbody>
          <tr><td>Koppar</td><td>1,5 mg/l</td><td>Tjänligt med anmärkning</td><td>Följ upp tillsammans med pH och installationer.</td></tr>
          <tr><td>Nitrat</td><td>23 mg/l</td><td>Tjänligt med anmärkning</td><td>Relevant för barn och känsliga grupper.</td></tr>
          <tr><td>Mangan</td><td>0,60 mg/l</td><td>Tjänligt med anmärkning</td><td>Kan ge svarta utfällningar och igensättning.</td></tr>
          <tr><td>E. coli</td><td>&lt;1 /100 ml</td><td>Tjänligt</td><td>Ingen påvisad fekal påverkan.</td></tr>
        </tbody>
      </table>
    </section>

    <div class="footer">
      <span>Svenska Vatteninstitutet · Oberoende tolkning av analysresultat</span>
      <span>Rapporten ersätter inte laboratoriets originalrapport.</span>
    </div>
  </main>
</body>
</html>
