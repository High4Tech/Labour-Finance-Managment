import {Component,type ReactNode,lazy,Suspense} from 'react';
import {createRoot,type Root} from 'react-dom/client';
import {Button,Feedback} from './components';
import {t,type NativeList} from './bridge';
import type {Overview} from './dashboard';
import {DashboardSkeleton} from './loading';
const Imports=lazy(()=>import('./imports'));
import type {ImportOptions} from './imports';
const Dashboard=lazy(()=>import('./dashboard'));
let preparedDashboard:typeof import('./dashboard').default|undefined;
export async function prepareDashboard(){preparedDashboard=(await import('./dashboard')).default;}
const Payments=lazy(()=>import('./payments'));
let preparedPayments:typeof import('./payments').default|undefined;
export async function preparePayments(){preparedPayments=(await import('./payments')).default;}
const Notifications=lazy(()=>import('./notifications'));
const Clients=lazy(()=>import('./clients').then(module=>({default:module.Clients})));
const ClientProfile=lazy(()=>import('./clients').then(module=>({default:module.ClientProfile})));
const AgreementBuilder=lazy(()=>import('./agreement-builder'));
export async function prepareAgreementBuilder(){await import('./agreement-builder');}
const AgreementProfile=lazy(()=>import('./agreement-profile'));
export async function prepareAgreementProfile(){await import('./agreement-profile');}
export async function prepareClients(){await import('./clients');}
const Workers=lazy(()=>import('./workers').then(module=>({default:module.Workers})));
const WorkerProfile=lazy(()=>import('./workers').then(module=>({default:module.WorkerProfile})));
const ScopedSearch=lazy(()=>import('./command-dialogs').then(module=>({default:module.ScopedSearch})));
const CreateWorker=lazy(()=>import('./command-dialogs').then(module=>({default:module.CreateWorker})));
const CreateClient=lazy(()=>import('./command-dialogs').then(module=>({default:module.CreateClient})));
export async function prepareWorkers(){await import('./workers');}
const Planning=lazy(()=>import('./planning'));
let preparedPlanning:typeof import('./planning').default|undefined;
export async function preparePlanning(){preparedPlanning=(await import('./planning')).default;}
const roots=new Map<HTMLElement,Root>();
export const stats={activeRoots:0,mounts:0,unmounts:0};
class Boundary extends Component<{children:ReactNode},{failed:boolean}>{
 state={failed:false};static getDerivedStateFromError(){return {failed:true};}
 componentDidCatch(error:Error){console.error('PLUS POINT React screen',error);}
 render(){return this.state.failed?<div><Feedback message="This screen could not finish loading. Refresh to try again."/><Button onClick={()=>location.reload()}>{t('Try again')}</Button></div>:this.props.children;}
}
export function mountPayments(host:HTMLElement,list:NativeList){const Screen=preparedPayments||Payments;mountOwned(host,'payments',<Screen list={list}/>); }
export function mountNotifications(host:HTMLElement,onRead:(unread:number)=>void){mountOwned(host,'notifications',<Notifications onRead={onRead}/>); }
export function unmount(host:HTMLElement){const root=roots.get(host);if(!root)return;root.unmount();roots.delete(host);stats.unmounts++;stats.activeRoots=roots.size;}
export function mountCommand(host:HTMLElement,kind:string,mode:'search'|'create',onClose:()=>void,onSaved?:(name:string)=>void){mountOwned(host,'command',mode==='search'?<ScopedSearch kind={kind} onClose={onClose}/>:kind==='clients'?<CreateClient onClose={onClose} onSaved={onSaved}/>:<CreateWorker onClose={onClose}/>);}
export function mountWorkers(host:HTMLElement){mountOwned(host,'workers',<Workers/>); }
export function mountClients(host:HTMLElement){mountOwned(host,'clients',<Clients/>);}
export function mountClientProfile(host:HTMLElement,customer?:string){mountOwned(host,'client-profile',<ClientProfile customer={customer}/>);}
export function mountAgreementBuilder(host:HTMLElement,name?:string,draftName?:string){mountOwned(host,'agreement-builder',<AgreementBuilder name={name} draftName={draftName}/>);}
export function mountAgreementProfile(host:HTMLElement,name:string){mountOwned(host,'agreement-profile',<AgreementProfile name={name}/>);}
function mountOwned(host:HTMLElement,kind:string,content:ReactNode,fallback:ReactNode=<p role="status">{t('Loading…')}</p>){if(roots.has(host))return;host.dataset.ppReactRoot=kind;const root=createRoot(host);roots.set(host,root);stats.mounts++;stats.activeRoots=roots.size;root.render(<Boundary><Suspense fallback={fallback}>{content}</Suspense></Boundary>);}
export function mountWorkerProfile(host:HTMLElement,employee:string|undefined,onPhoto:()=>void){mountOwned(host,'worker-profile',<WorkerProfile employee={employee} onPhoto={onPhoto}/>); }
export function mountPlanning(host:HTMLElement,list:{doctype:'PP Contract Terms'|'PP Event Plan';can_delete:boolean;can_create:boolean}){const Screen=preparedPlanning||Planning;mountOwned(host,'planning',<Screen list={list}/>); }
export function mountDashboard(host:HTMLElement,initial?:Overview){const Screen=preparedDashboard||Dashboard;mountOwned(host,'dashboard',<Screen initial={initial}/>,<DashboardSkeleton/>); }

export function mountImport(host:HTMLElement,options:ImportOptions,onClose:()=>void){mountOwned(host,'import',<Imports {...options} onClose={onClose}/>);}

const AttendanceRegister = lazy(() => import('./attendance-register'));
export function mountAttendanceRegister(host: HTMLElement, name: string, preview: React.ComponentProps<typeof AttendanceRegister>['preview']) {
 mountOwned(host, 'attendance-register', <AttendanceRegister name={name} preview={preview}/>);
}

const AttendanceList = lazy(() => import('./attendance-list'));
export async function prepareAttendanceList(){await import('./attendance-list');}
export function mountAttendanceList(host: HTMLElement, options: React.ComponentProps<typeof AttendanceList>){
 mountOwned(host,'attendance-list',<AttendanceList {...options}/>);
}

const FinanceList = lazy(() => import('./finance-list'));
export async function prepareFinanceList(){await import('./finance-list');}
export function mountFinanceList(host: HTMLElement, options: React.ComponentProps<typeof FinanceList>){
 mountOwned(host,'finance-list',<FinanceList {...options}/>);
}

const ResourceList = lazy(() => import('./resource-list'));
const ResourceProfile = lazy(() => import('./resource-profile'));
const ResourceEditor = lazy(() => import('./resource-editor').then(module=>({default:module.ResourceEditor})));
const BookingDialog = lazy(() => import('./resource-bookings').then(module=>({default:module.BookingDialog})));
export async function prepareResources(){await import('./resource-list');}
export function mountResourceList(host:HTMLElement,kind:import('./resource-types').ResourceKind){
 mountOwned(host,'resource-list',<ResourceList kind={kind}/>);
}
export function mountResourceProfile(host:HTMLElement,kind:import('./resource-types').ResourceKind,name:string){
 mountOwned(host,'resource-profile',<ResourceProfile kind={kind} name={name}/>);
}
export function mountResourceEditor(host:HTMLElement,props:React.ComponentProps<typeof ResourceEditor>){
 mountOwned(host,'resource-editor',<ResourceEditor {...props}/>);
}
export function mountBooking(host:HTMLElement,props:React.ComponentProps<typeof BookingDialog>){
 mountOwned(host,'resource-booking',<BookingDialog {...props}/>);
}

const BillingPage=lazy(()=>import('./billing'));
export function mountBillingPage(host:HTMLElement,options:React.ComponentProps<typeof BillingPage>){
 mountOwned(host,'billing',<BillingPage {...options}/>);
}

const FinanceRecord=lazy(()=>import('./finance-record'));
export function mountFinanceRecord(host:HTMLElement,options:React.ComponentProps<typeof FinanceRecord>){
 mountOwned(host,'finance-record',<FinanceRecord {...options}/>);
}

const ResourceEditDialog=lazy(()=>import('./resource-editor').then(module=>({default:module.ResourceEditDialog})));
export function mountResourceEdit(host:HTMLElement,props:React.ComponentProps<typeof ResourceEditDialog>){
 mountOwned(host,'resource-edit',<ResourceEditDialog {...props}/>);
}
