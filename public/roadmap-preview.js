// Planning scenarios, not payment dates or entitlement decisions.
function roadmapForecast(code, birth, today, months) {
  const start = new Date(`${today}T00:00:00Z`), born = new Date(`${birth}T00:00:00Z`);
  if (![12,24].includes(months) || !Number.isFinite(+start) || !Number.isFinite(+born)) throw new Error('input');
  const anniversary = n => { const d=new Date(Date.UTC(born.getUTCFullYear(),born.getUTCMonth()+n,1)); d.setUTCDate(Math.min(born.getUTCDate(),new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).getUTCDate()));return d; };
  const rows=[];
  for(let n=0;n<months;n++) {
    const date=new Date(Date.UTC(start.getUTCFullYear(),start.getUTCMonth()+n,1));
    const days=new Date(Date.UTC(date.getUTCFullYear(),date.getUTCMonth()+1,0)).getUTCDate();let amount=0;
    for(let day=1;day<=days;day++) {
      const d=new Date(Date.UTC(date.getUTCFullYear(),date.getUTCMonth(),day));
      if(d<start || d<born)continue;
      if(code==='berna_kopsanas') amount+=(d<anniversary(18)?298:d<anniversary(24)&&birth<='2026-11-02'?42.69:0)/days;
      if(code==='gimenes_valsts' && d>=anniversary(12) && d<anniversary(192))amount+=25/days;
    }
    rows.push({date:date.toISOString().slice(0,10),amount:Math.round((amount+Number.EPSILON)*100)/100});
  }
  return rows;
}
if(typeof module!=='undefined')module.exports={roadmapForecast};
function createRoadmapPreview(child, benefit, today) {
  const make=(tag,text)=>{const el=document.createElement(tag);if(text!=null)el.textContent=text;return el;};
  const root=make('details');root.className='roadmap-preview';root.append(make('summary',t('forecast.preview')));
  const body=make('div');body.className='roadmap-preview-body';root.append(body);
  const code=benefit.code, wage=['maternitates','paternitates','vecaku'].includes(code);
  body.append(make('p',t('forecast.note')));
  if(wage) {
    body.append(make('p',t(code==='vecaku'?'forecast.parental':'forecast.wage')));
    const form=make('form'),label=make('label',t('calc.daily'));const input=make('input');input.type='number';input.min='0.01';input.max='100000';input.step='0.01';input.required=true;label.append(input);form.append(label);
    let option;
    if(code!=='paternitates') {const lab=make('label',t(code==='maternitates'?'forecast.days':'forecast.duration'));option=make('select');for(const value of code==='maternitates'?[112,126,140]:[13,19]){const o=make('option',String(value));o.value=value;option.append(o);}lab.append(option);form.append(lab);}
    const button=make('button',t('forecast.calculate'));button.type='submit';button.className='outline-link';const output=make('p');output.setAttribute('role','status');form.append(button,output);body.append(form);
    form.addEventListener('submit',event=>{event.preventDefault();if(!form.reportValidity())return;try{const result=calculateChildBenefit(code,{daily:input.value,days:code==='maternitates'?Number(option.value):30,duration:option?.value,working:false});output.textContent=`${i18n.formatMoney(result.amount)} · ${t(result.unit)} · ${t('calc.formula')}: ${result.formula}`;}catch{output.textContent=t('calc.invalid');}});
  } else if(code==='berna_piedzimsanas') {
    const value=calculateChildBenefit(code,{birth:child.birthDate});body.append(make('strong',`${i18n.formatMoney(value.amount)} · ${t('calc.once')}`),make('p',t('forecast.once')));
  } else if(['berna_kopsanas','gimenes_valsts'].includes(code)) {
    body.append(make('p',t(code==='berna_kopsanas'?'forecast.care':'forecast.family')));
    const label=make('label',t('forecast.horizon')),select=make('select');for(const n of [12,24]){const o=make('option',t('forecast.months',{count:n}));o.value=n;select.append(o);}label.append(select);body.append(label);
    const output=make('div');output.setAttribute('aria-live','polite');body.append(output);
    const paint=()=>{output.replaceChildren();const rows=roadmapForecast(code,child.birthDate,today,Number(select.value));output.append(make('p',`${t('forecast.total')}: ${i18n.formatMoney(rows.reduce((sum,row)=>sum+row.amount,0))}`));const table=make('table'),head=make('tr');head.append(make('th',t('forecast.month')),make('th',t('forecast.amount')));const thead=make('thead');thead.append(head);table.append(thead);const tbody=make('tbody');for(const row of rows){const tr=make('tr');tr.append(make('td',new Intl.DateTimeFormat(i18n.language==='en'?'en-GB':'lv-LV',{month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(row.date))),make('td',i18n.formatMoney(row.amount)));tbody.append(tr);}table.append(tbody);output.append(table);};select.addEventListener('change',paint);paint();
  }
  const link=make('a',t('forecast.full'));link.href=`calculator.html?benefit=${encodeURIComponent(code)}`;body.append(link);const source=make('a',t('forecast.sources'));source.href='data-licenses.html#calculator-sources';body.append(source);
  return root;
}
