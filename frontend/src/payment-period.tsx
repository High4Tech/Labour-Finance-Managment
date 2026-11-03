import {t} from './bridge';
import {date,type Period,type Agreement,type Milestone} from './agreement-types';

export function PaymentName({row,data}:{row:Period|Milestone;data:Agreement}){return <span className="pp-r-payment-name"><strong>{'title' in row?row.title:row.milestone_title}</strong><small>{data.agreement_title}{data.pp_reference?' · '+data.pp_reference:''}</small></span>;}

export function AttendancePeriod({row}:{row:Period}){return <span className="pp-r-period"><span>{date(row.from_date)}{row.from_date!==row.to_date?' – '+date(row.to_date):''}</span>{row.frequency==='Daily'&&<small>{row.work_start&&row.work_end?row.work_start+' – '+row.work_end+(row.work_end<row.work_start?' '+t('(next day)'):''):t('Work hours not set')}</small>}</span>;}
