import {useEffect, useState} from 'react';
import {t} from './bridge';
import {Badge, Button, DataTable, Feedback, Field, Icon, Input, Pagination} from './components';
import {useDebounced, useLiveUpdates, useResource} from './hooks';

type RegisterRow = {
 name: string; pp_reference?: string; docstatus: number; work_date: string;
 site: string; site_title?: string; project: string; event_title?: string;
};
type Result = {rows: RegisterRow[]; has_more: boolean};

export default function AttendanceList({canCreate, canDelete, project}: {
 canCreate: boolean; canDelete: boolean; project?: string;
}) {
 const [query, setQuery] = useState('');
 const [event, setEvent] = useState(project);
 const [page, setPage] = useState(1);
 const [selected, setSelected] = useState(new Set<string>());
 const search = useDebounced(query);
 const {data, loading, error, refresh} = useResource(signal => window.plus_point.form_rpc<Result>(
  'attendance.list_registers', {search, project: event, start: (page - 1) * 20}, {signal}
 ), [search, event, page]);
 useLiveUpdates(['PP Daily Register'], refresh, ['pp:data-changed']);
 useEffect(() => {setSelected(new Set());}, [data]);
 const open = (row: RegisterRow) => '/desk/pp-daily-register/' + encodeURIComponent(row.name);
 return <section className="pp-r-screen pp-r-planning" aria-label={t('Attendance registers')} aria-busy={loading}>
  <header className="pp-resource-heading">
   <h1>{t('Attendance registers')}</h1>
   <div className="pp-actions">
    <Button icon="refresh" aria-label={t('Refresh records')} disabled={loading} onClick={refresh}/>
    {canCreate && <Button icon="plus" tone="primary" onClick={() => window.plus_point.open_attendance_picker()}>{t('Create register')}</Button>}
   </div>
  </header>
  <div className="pp-r-list-filters">
   <Field label="Register or tracking ID">{id => <Input id={id} type="search" value={query} onChange={e => {setQuery(e.target.value); setPage(1); setSelected(new Set());}}/>}</Field>
   {event && <Button onClick={() => {setEvent(undefined); setPage(1); setSelected(new Set());}}>{t('Show all events')}</Button>}
   <Button onClick={() => {sessionStorage.setItem('pp:attendance:advanced', '1'); location.assign('/desk/pp-daily-register');}}>{t('Advanced filters & exports')}</Button>
  </div>
  <Feedback message={error}/>{error && <Button onClick={refresh}>{t('Try again')}</Button>}
  <DataTable label="Attendance registers" rows={data?.rows ?? []} rowKey={row => row.name} selected={selected} onSelect={setSelected}
   actions={canDelete && <Button tone="danger" icon="delete" disabled={loading} onClick={() =>
    window.plus_point.delete_records('PP Daily Register', [...selected], () => {setSelected(new Set()); setPage(1); refresh();})
   }>{t('Delete selected')}</Button>}
   empty={loading ? 'Loading records…' : 'No registers match these filters'}
   columns={[
    {key:'name', label:'ID', render:row => <><a className="pp-r-record-name" href={open(row)}>{row.name}</a><small>{row.pp_reference}</small></>},
    {key:'status', label:'Status', render:row => <Badge tone={row.docstatus === 1 ? 'success' : row.docstatus === 2 ? 'error' : 'neutral'}>{t(row.docstatus === 1 ? 'Submitted' : row.docstatus === 2 ? 'Cancelled' : 'Draft')}</Badge>},
    {key:'date', label:'Work Date', render:row => <span className="pp-r-no-break">{row.work_date}</span>},
    {key:'site', label:'Site', render:row => row.site_title || row.site},
    {key:'event', label:'Event', render:row => row.event_title || row.project},
    {key:'actions', label:'Actions', actions:true, render:row => <a className="btn btn-default pp-list-action" href={open(row)} aria-label={t('Open register') + ' ' + row.name} title={t('Open register')}><Icon name="eye"/></a>},
   ]}/>
  <Pagination page={page} pages={page + Number(Boolean(data?.has_more))} disabled={loading} onPage={value => {setSelected(new Set()); setPage(value);}}/>
 </section>;
}
