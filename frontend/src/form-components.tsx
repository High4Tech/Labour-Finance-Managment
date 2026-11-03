import {useEffect,useId,useMemo,useRef,type ReactNode} from 'react';
import {Button,Dialog,Field,Icon,Input} from './components';
import {t} from './bridge';

export function Tabs({value,onChange,items,label,panelId}:{value:string;onChange:(value:string)=>void;items:{key:string;label:string}[];label:string;panelId:string}){const id=useId(),refs=useRef<(HTMLButtonElement|null)[]>([]);return <nav className="pp-agreement-tabs" role="tablist" aria-label={t(label)}>{items.map((item,index)=><button key={item.key} ref={el=>{refs.current[index]=el;}} id={id+'-'+item.key} type="button" role="tab" aria-selected={value===item.key} aria-controls={panelId} tabIndex={value===item.key?0:-1} onClick={()=>onChange(item.key)} onKeyDown={event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?items.length-1:(index+(event.key==='ArrowRight'?1:-1)+items.length)%items.length;onChange(items[next].key);refs.current[next]?.focus();}}>{t(item.label)}</button>)}</nav>;}
export function Facts({items}:{items:{label:string;value:ReactNode;wide?:boolean}[]}){return <dl className="pp-profile-facts">{items.map(item=><div key={item.label} className={item.wide?'pp-fact-wide':undefined}><dt>{t(item.label)}</dt><dd>{item.value==null||item.value===''?'—':item.value}</dd></div>)}</dl>;}
/* The read-only rich-text variant retains document formatting without accepting
   active content or arbitrary HTML attributes from an imported agreement. */
export function RichContent({value}:{value:string}){
 const html=useMemo(()=>{
  const source=new DOMParser().parseFromString(value||'','text/html'),target=document.createElement('div');
  const tags=new Set('P DIV SPAN BR STRONG B EM I U S STRIKE BLOCKQUOTE PRE CODE H1 H2 H3 H4 H5 H6 OL UL LI TABLE THEAD TBODY TFOOT TR TD TH A IMG HR SUB SUP'.split(' '));
  const active=new Set('SCRIPT STYLE IFRAME OBJECT EMBED SVG MATH LINK META FORM INPUT BUTTON SELECT TEXTAREA TEMPLATE'.split(' '));
  const styles=['color','background-color','font-size','font-family','font-weight','font-style','text-decoration','text-align','direction','padding-left','margin-left'];
  const copy=(node:Node,parent:Node)=>{
   if(node.nodeType===Node.TEXT_NODE){parent.appendChild(document.createTextNode(node.textContent||''));return;}
   if(!(node instanceof Element)||active.has(node.tagName))return;
   if(!tags.has(node.tagName)){node.childNodes.forEach(child=>copy(child,parent));return;}
   const element=document.createElement(node.tagName.toLowerCase());
   if(node instanceof HTMLElement)styles.forEach(key=>{const css=node.style.getPropertyValue(key);if(css&&!/url\s*\(|expression\s*\(|[<>]/i.test(css))element.style.setProperty(key,css);});
   if(node.tagName==='A'){const href=node.getAttribute('href')||'';if(/^(?:https?:|mailto:|tel:|#|\/(?!\/))/i.test(href)){element.setAttribute('href',href);element.setAttribute('target','_blank');element.setAttribute('rel','noopener noreferrer');}}
   if(node.tagName==='IMG'){const src=node.getAttribute('src')||'';if(!/^(?:https?:\/\/|\/(?!\/)|data:image\/(?:png|jpeg|gif|webp);base64,)/i.test(src))return;element.setAttribute('src',src);element.setAttribute('alt',node.getAttribute('alt')||'');element.setAttribute('loading','lazy');}
   if(['TD','TH'].includes(node.tagName))['colspan','rowspan'].forEach(key=>{const n=Number(node.getAttribute(key));if(Number.isInteger(n)&&n>0&&n<=100)element.setAttribute(key,String(n));});
   parent.appendChild(element);node.childNodes.forEach(child=>copy(child,element));
  };
  source.body.childNodes.forEach(node=>copy(node,target));return target.innerHTML;
 },[value]);
 return <div className="pp-document-prose" dangerouslySetInnerHTML={{__html:html}}/>;
}
export function EmailFields({recipient,copies,onRecipient,onCopies,errors={},disabled=false}:{recipient:string;copies:string[];onRecipient:(value:string)=>void;onCopies:(values:string[])=>void;errors?:Record<string,string>;disabled?:boolean}){return <div className="pp-r-email-grid"><div><Field label="Client email *" error={errors.recipient}>{(id,help)=><Input id={id} type="email" value={recipient} disabled={disabled} required aria-invalid={!!errors.recipient} aria-describedby={help} onChange={e=>onRecipient(e.target.value)}/>}</Field><Button icon="plus" disabled={disabled||copies.length>=10} onClick={()=>onCopies([...copies,''])}>{t('Add CC email')}</Button></div><div className="pp-r-cc-grid">{copies.map((value,index)=><div className="pp-r-cc-row" key={index}><Field label={'CC email '+(index+1)} error={errors['cc'+index]}>{(id,help)=><Input id={id} type="email" value={value} disabled={disabled} aria-invalid={!!errors['cc'+index]} aria-describedby={help} onChange={e=>onCopies(copies.map((old,i)=>i===index?e.target.value:old))}/>}</Field><Button tone="danger" icon="close" disabled={disabled} aria-label={t('Remove CC email')+' '+(index+1)} onClick={()=>onCopies(copies.filter((_,i)=>i!==index))}/></div>)}</div></div>;}

/* Quill is the installed rich-text engine, not a second form renderer. React
   owns this isolated widget's value, mount and disposal. Native extensions and
   toolbar tools are retained instead of shipping another rich-text package. */
export function RichText({id,value,onChange,disabled=false,invalid=false,describedBy}:{id:string;value:string;onChange:(value:string)=>void;disabled?:boolean;invalid?:boolean;describedBy?:string}){
 const host=useRef<HTMLDivElement>(null),latest=useRef(onChange),control=useRef<any>(null),initial=useRef(value);latest.current=onChange;
 useEffect(()=>{const node=host.current!;const native=(window.frappe as any).ui.form.make_control({parent:node,df:{fieldtype:'Text Editor',fieldname:'rich_text',label:'',hide_label:1,default:initial.current},render_input:true});control.current=native;void native.set_value(initial.current);native.quill?.on('text-change',()=>{if(control.current===native)latest.current(native.get_input_value()||'');});const input=node.querySelector<HTMLElement>('.ql-editor[contenteditable]');if(input){input.id=id;input.setAttribute('role','textbox');input.setAttribute('aria-labelledby',id+'-label');input.setAttribute('aria-multiline','true');}return()=>{native.quill?.off('text-change');native.quill?.off('selection-change');native.quill?.disable();native.pp_disposed=true;control.current=null;node.replaceChildren();};},[]);
 useEffect(()=>{const node=host.current?.querySelector<HTMLElement>('.ql-editor[contenteditable]');if(node){node.setAttribute('aria-invalid',String(invalid));if(describedBy)node.setAttribute('aria-describedby',describedBy);else node.removeAttribute('aria-describedby');}control.current?.quill?.enable(!disabled);},[disabled,invalid,describedBy]);
 return <div ref={host} className="pp-r-rich-text" data-invalid={invalid||undefined}/>;
}

export function CostConfirmation({message,busy,onClose,onConfirm}:{message:string;busy:boolean;onClose:()=>void;onConfirm:()=>void}){return <Dialog title="Review projected labour cost" busy={busy} onClose={onClose} footer={<><Button disabled={busy} onClick={onClose}>{t('Back to review')}</Button><Button tone="primary" loading={busy} onClick={onConfirm}>{t('Continue with these costs')}</Button></>}><p>{message}</p><p>{t('Actual labour costs are recorded from approved attendance. This confirms only the projected budget exception.')}</p></Dialog>;}

/* Wizard navigation is a documented Button variant, not a second button system. */
export function CreationSteps({items,current,onStep}:{items:{title:string;description:string}[];current:number;onStep:(index:number)=>void}){return <nav className="pp-r-builder-steps" aria-label={t('Creation steps')}>{items.map((item,index)=><Button key={item.title} className="pp-r-step btn-reset" aria-current={current===index?'step':undefined} onClick={()=>onStep(index)}><span className="pp-r-step-number">{index<current?<Icon name="check"/>:index+1}</span><span><strong>{t(item.title)}</strong><small>{t(item.description)}</small></span></Button>)}</nav>;}
export function CreationFooter({step,total,title,children}:{step:number;total:number;title:string;children:ReactNode}){return <footer className="pp-r-builder-footer"><span>{t('Step')} {step+1} {t('of')} {total} · {t(title)}</span><div className="pp-actions">{children}</div></footer>;}
