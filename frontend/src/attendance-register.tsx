import {useEffect, useState} from 'react';
import {amount, changed, t} from './bridge';
import {Button, DataTable, Dialog, Feedback, Field, Panel} from './components';

const units = {'Present': 1, 'Half day': 0.5, 'Absent': 0, 'Not marked': 0};
type Status = keyof typeof units;
type Row = {id: string; employee: string; title: string; designation: string; status: Status; wage_rate: string; locked: boolean};
type Register = {event: string; site: string; date: string; approved: boolean; can_correct: boolean; required: number | null; currency: string; rows: Row[]};
type Marks = {id: string; status: Status}[];
type Budget = {blocked: boolean; enabled: boolean; level: string; projected: number; limit: number; currency: string};
const rpc = <T,>(method: string, args: Record<string, unknown>, signal?: AbortSignal) =>
 window.plus_point.form_rpc<T>('attendance.' + method, args, {signal});

export default function AttendanceRegister({name, preview}: {name: string; preview: (marks: Marks) => Promise<Budget[]>}) {
 const [register, setRegister] = useState<Register>();
 const [marks, setMarks] = useState<Record<string, Status>>({});
 const [revision, setRevision] = useState(0);
 const [query, setQuery] = useState('');
 const [error, setError] = useState('');
 const [notice, setNotice] = useState('');
 const [busy, setBusy] = useState(false);
 const [loading, setLoading] = useState(true);
 const [correcting, setCorrecting] = useState(false);
 const [reason, setReason] = useState('');
 const [warning, setWarning] = useState('');
 useEffect(() => {
  const controller = new AbortController();
  setLoading(true);
  rpc<Register>('detail', {name}, controller.signal).then(data => {
   if (!controller.signal.aborted) {setRegister(data); setMarks({});}
  }).catch(cause => {
   if (!controller.signal.aborted) setError(cause.message);
  }).finally(() => {
   if (!controller.signal.aborted) setLoading(false);
  });
  return () => controller.abort();
 }, [name, revision]);
 if (!register) return <Panel title="Attendance register"><Feedback message={error}/>{loading
  ? <p role="status">{t('Loading attendance…')}</p>
  : <Button onClick={() => {setError(''); setRevision(value => value + 1);}}>{t('Try again')}</Button>}</Panel>;
 const status = (row: Row) => marks[row.id] ?? row.status;
 const earned = (row: Row) => Number(row.wage_rate) * units[status(row)];
 const money = (value: unknown) => amount(value) + ' ' + register.currency;
 const payload = () => register.rows.map(row => ({id: row.id, status: status(row)}));
 const dirty = Object.keys(marks).length > 0;
 const blocked = busy || loading;
 const reset = () => {setCorrecting(false); setMarks({}); setReason(''); setError('');};
 async function save(action: 'draft' | 'approve' | 'correct' | 'refresh', confirmed = false) {
  if (blocked) return;
  setBusy(true); setError(''); setNotice('');
  try {
   if (action === 'approve' && !confirmed) {
    const budgets = await preview(payload());
    const limit = budgets.find(row => row.blocked) ?? budgets.find(row => row.enabled && row.level === 'warning');
    if (limit) {
     const message = t('Projected spending') + ': ' + amount(limit.projected) + ' / ' + amount(limit.limit) + ' ' + limit.currency;
     if (limit.blocked) throw new Error(t('Spending budget exceeded. Review the project budget or attendance.') + ' ' + message);
     setWarning(message);
     return;
    }
   }
   if (action === 'refresh') await rpc('refresh_roster', {name});
   else if (action === 'correct') await rpc('correct_marks', {name, marks: payload(), reason: reason.trim()});
   else await rpc('save_marks', {name, marks: payload(), approve: action === 'approve' ? 1 : 0});
   reset();
   setLoading(true);
   setRevision(value => value + 1);
   setNotice(t(action === 'approve' ? 'Attendance approved. Finances updated.' : action === 'refresh' ? 'Crew list refreshed.' : 'Attendance saved.'));
   changed();
  } catch (cause) {setError(cause instanceof Error ? cause.message : t('Attendance could not be saved.'));}
  finally {setBusy(false);}
 }
 return <section className="pp-r-list" aria-busy={blocked}>
  <Panel title={register.event} actions={<a className="btn btn-default" href="/desk/pp-daily-register">{t('Back to attendance')}</a>}>
   <p>{register.site} · {register.date} · {t(register.approved ? 'Approved attendance' : 'Attendance to review')}</p>
   <Feedback message={error}/><Feedback message={notice} tone="success"/>
   {register.required != null && register.required !== register.rows.length && <Feedback tone="info" message={register.required + ' ' + t('workers planned') + ' · ' + register.rows.length + ' ' + t('allocated')}/>}
   <p>{(['Present', 'Half day', 'Absent', 'Not marked'] as const).map(value => t(value) + ': ' + register.rows.filter(row => status(row) === value).length).join(' · ')}</p>
   <p>{t('Wages for this register')}: <strong>{money(register.rows.reduce((sum, row) => sum + earned(row), 0))}</strong></p>
   <Field label="Find worker">{id => <input id={id} type="search" className="form-control" value={query} onChange={event => setQuery(event.target.value)}/>}</Field>
   <DataTable label="Attendance marks" rows={register.rows.filter(row => (row.title + ' ' + row.designation).toLowerCase().includes(query.trim().toLowerCase()))} rowKey={row => row.id} columns={[
    {key: 'Worker', label: 'Worker', render: row => <><a href={'/desk/employee/' + encodeURIComponent(row.employee)} onClick={event => {if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return; event.preventDefault(); window.frappe.set_route('Form', 'Employee', row.employee);}}><strong>{row.title}</strong></a><div>{row.designation}</div></>},
    {key: 'Attendance', label: 'Attendance', render: row => <div className="pp-r-actions" role="group" aria-label={row.title + ' — ' + t('Attendance')}>
     {((row.locked && !correcting) || (register.approved && !correcting)) ? t(status(row)) : (Object.keys(units) as Status[]).filter(value => value !== 'Not marked' || (!correcting && status(row) !== 'Not marked')).map(value =>
      <Button key={value} tone={status(row) === value ? 'primary' : 'default'} aria-pressed={status(row) === value} disabled={blocked} onClick={() => setMarks(previous => ({...previous, [row.id]: value}))}>{t(value)}</Button>)}
    </div>},
    {key: 'Daily wage', label: 'Daily wage', render: row => money(row.wage_rate)},
    {key: 'Earned', label: 'Earned', render: row => status(row) === 'Not marked' ? '—' : money(earned(row))}
   ]}/>
   <p>{t(register.approved ? 'Approved wages are included in finances. Corrections keep a reason and audit history.' : 'Draft marks affect finances only after approval.')}</p>
   {correcting && <Field label="Reason for correction">{id => <textarea id={id} className="form-control" maxLength={1000} value={reason} onChange={event => setReason(event.target.value)}/>}</Field>}
   <div className="pp-r-actions">
    {!register.approved && <>
     <Button disabled={blocked || dirty} onClick={() => void save('refresh')}>{t('Refresh crew list')}</Button>
     <Button disabled={blocked || !dirty} onClick={() => void save('draft')}>{t('Save draft')}</Button>
     <Button tone="primary" disabled={blocked || !register.rows.length || register.rows.some(row => status(row) === 'Not marked')} onClick={() => void save('approve')}>{t('Approve attendance')}</Button>
    </>}
    {register.can_correct && !correcting && <Button disabled={blocked} onClick={() => setCorrecting(true)}>{t('Edit attendance')}</Button>}
    {correcting && <><Button disabled={blocked} onClick={reset}>{t('Cancel')}</Button><Button tone="primary" disabled={blocked || !dirty || !reason.trim()} onClick={() => void save('correct')}>{t('Save correction')}</Button></>}
   </div>
  </Panel>
  {warning && <Dialog title="Review spending budget" onClose={() => setWarning('')} footer={<><Button onClick={() => setWarning('')}>{t('Cancel')}</Button><Button tone="primary" onClick={() => {setWarning(''); void save('approve', true);}}>{t('Approve reviewed wages')}</Button></>}><p>{warning}</p></Dialog>}
 </section>;
}
