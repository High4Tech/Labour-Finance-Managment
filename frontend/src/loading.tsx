import {t} from './bridge';

/** Same dashboard grid and gutters at the first and final frame. */
export function DashboardSkeleton(){return <div className="pp-overview pp-overview-loading" role="status" aria-busy="true"><span className="sr-only">{t('Loading your dashboard…')}</span><div className="pp-overview-header"><i className="pp-loading-heading"/></div><div className="pp-overview-upper"><div className="pp-overview-primary"><div className="pp-kpi-grid"><i/><i/><i/></div><div className="pp-overview-tables"><i/><i/></div></div><aside className="pp-overview-activity"><i/></aside></div><div className="pp-overview-attendance"><i/><i/></div></div>;}
