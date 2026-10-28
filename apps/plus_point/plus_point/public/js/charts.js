/* Shared chart component. Only the customer dashboard loads this adapter/engine.
 * Native Frappe charts remain available to native reports and platform views. */
(()=>{
 frappe.provide('plus_point');const pp=plus_point;
 const stats={created:0,destroyed:0,active:0},mounted=new WeakMap();
 const number=value=>pp.ui.amount(String(value??0));
 const compact=value=>new Intl.NumberFormat(undefined,{notation:'compact',maximumFractionDigits:1}).format(value);
 pp.charts={stats,get:host=>mounted.get(host),ready:()=>pp.load_feature('echarts'),create(host,config){
  mounted.get(host)?.destroy();
  const plot=document.createElement('div');plot.className='pp-chart-plot';plot.tabIndex=0;
  const speech=document.createElement('span');speech.className='sr-only';speech.role='status';speech.setAttribute('aria-live','polite');
  host.replaceChildren(plot,speech);host.dataset.chartEngine='echarts';
  const chart=PlusPointECharts.init(plot,null,{renderer:'svg'});let disposed=false,index=0,lastWidth,lastHeight,signature;
  const labels=config.categories||[],series=config.series||[],unit=config.unit||'',value=n=>number(n)+(unit?' '+unit:'');
  const read=at=>config.type==='comparison'?series[at].name+': '+value(series[at].values[0]):labels[at]+'. '+series.map(row=>row.name+': '+value(row.values[at])).join('. ');const points=config.type==='comparison'?series.length:labels.length;
  const refresh=()=>{
   if(disposed)return;const dark=document.documentElement.dataset.theme==='dark',reduced=matchMedia('(prefers-reduced-motion: reduce)').matches,key=dark+':'+reduced;if(signature===key)return;signature=key;
   const css=getComputedStyle(host),text=css.getPropertyValue('--text-color').trim()||(dark?'#f1f5f9':'#102a25'),muted=css.getPropertyValue('--text-muted').trim()||(dark?'#c0cbc6':'#52665e'),grid=dark?'#354b43':'#e7eeeb';
   const fallback=dark?['#53d5b1','#f1bd50','#93b9db','#bcb0ef','#f29da6']:['#087f65','#b67b12','#567f9a','#8062ac','#b65669'],colors=fallback.map((color,i)=>css.getPropertyValue('--pp-chart-color-'+i).trim()||color);
   const description=config.description||config.title+'. '+__('Use Left and Right arrows to explore values, or open View chart data for the complete table.');
   const option={backgroundColor:'transparent',color:colors,textStyle:{fontFamily:css.fontFamily,color:text,fontSize:13},animation:!reduced,animationDuration:360,animationDurationUpdate:180,aria:{enabled:true,label:{enabled:true,description}},tooltip:{trigger:config.type==='donut'?'item':'axis',renderMode:'richText',confine:true,backgroundColor:dark?'#e5f3ed':'#102f28',borderWidth:0,padding:[10,12],textStyle:{color:dark?'#142d24':'#fff',fontSize:14},axisPointer:{type:config.type==='bar'?'shadow':'line',lineStyle:{color:colors[0],type:'dashed'}},formatter:params=>{const rows=Array.isArray(params)?params:[params];return String(rows[0]?.name||'')+'\n'+rows.map(p=>p.seriesName+': '+value(series[p.seriesIndex||0]?.values[p.dataIndex]??p.value)+(p.percent!=null?' · '+p.percent+'%':'')).join('\n');}}};
   if(config.type==='donut'){
    option.series=[{name:config.title,type:'pie',radius:['66%','88%'],center:['50%','50%'],avoidLabelOverlap:true,label:{show:false},labelLine:{show:false},itemStyle:{borderColor:css.getPropertyValue('--pp-surface').trim()||(dark?'#182623':'#fff'),borderWidth:4,borderRadius:8},emphasis:{scaleSize:4},data:labels.map((name,i)=>({name,value:series[0].values[i]}))}];
   }else if(config.type==='comparison'){
    option.grid={left:8,right:68,top:24,bottom:8,containLabel:true};
    option.xAxis={type:'value',axisLabel:{color:muted,formatter:compact},axisLine:{show:false},axisTick:{show:false},splitLine:{lineStyle:{color:grid,type:'dashed'}}};
    option.yAxis={type:'category',inverse:true,data:series.map(row=>row.name),axisLabel:{color:muted,fontSize:12,width:100,overflow:'break'},axisLine:{show:false},axisTick:{show:false}};
    option.tooltip.trigger='item';option.tooltip.formatter=p=>p.name+'\n'+value(series[p.dataIndex].values[0]);
    option.series=[{type:'bar',barWidth:16,showBackground:true,backgroundStyle:{color:dark?'#253e35':'#f0f5f2',borderRadius:8},label:{show:true,position:'right',color:text,fontSize:13,formatter:p=>compact(p.value)},data:series.map((row,i)=>({name:row.name,value:Number(row.values[0]),itemStyle:{borderRadius:8,color:{type:'linear',x:0,y:0,x2:1,y2:0,colorStops:[{offset:0,color:colors[i]},{offset:1,color:i===0?(dark?'#a1ead0':'#42c9a1'):(dark?'#f8dea0':'#f0c460')}]}}})),emphasis:{focus:'self'}}];
   }else{
    option.grid={left:8,right:12,top:18,bottom:8,containLabel:true};
    option.xAxis={type:'category',data:labels,boundaryGap:config.type==='bar',axisLine:{show:false},axisTick:{show:false},axisLabel:{color:muted,fontSize:12,hideOverlap:true,margin:12,formatter:name=>config.type==='line'&&/^\d{4}-\d{2}-\d{2}$/.test(name)?name.slice(5):name}};
    option.yAxis={type:'value',min:config.nonNegative?0:undefined,axisLine:{show:false},axisTick:{show:false},axisLabel:{color:muted,fontSize:12,formatter:compact},splitLine:{lineStyle:{color:grid,type:'dashed'}}};
    option.series=series.map((row,i)=>({name:row.name,type:config.type,data:row.values.map(Number),...(config.type==='line'?{smooth:0.2,smoothMonotone:'x',showSymbol:true,symbol:'circle',symbolSize:labels.length<=12?7:3,itemStyle:{borderWidth:2,borderColor:dark?'#182e25':'#fff'},lineStyle:{width:3,cap:'round',shadowBlur:6,shadowColor:dark?'#53d5b120':'#087f6515'},areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:i===0?(dark?'#53d5b16b':'#087f6545'):(dark?'#f1bd5055':'#b67b1238')},{offset:1,color:i===0?'#087f6502':'#b67b1202'}]}}}:{barMaxWidth:28,barGap:'25%',itemStyle:{borderRadius:[4,4,0,0]}}),emphasis:{focus:'series'},color:colors[i%colors.length]}));
   }
   chart.setOption(option,{notMerge:true});host.dataset.chartTheme=dark?'dark':'light';plot.setAttribute('role','img');plot.setAttribute('aria-label',description);plot.setAttribute('aria-description',__('Left and Right arrows explore values. Home and End jump to the first and last values. Escape closes the tooltip.'));
  };
  plot.onkeydown=event=>{
   if(!['ArrowLeft','ArrowRight','Home','End','Escape'].includes(event.key)||!points)return;
   event.preventDefault();event.stopPropagation();if(event.key==='Escape'){chart.dispatchAction({type:'hideTip'});chart.dispatchAction({type:'downplay'});speech.textContent='';return;}
   index=event.key==='Home'?0:event.key==='End'?points-1:(index+(event.key==='ArrowLeft'?-1:1)+points)%points;
   chart.dispatchAction({type:'downplay'});chart.dispatchAction({type:'highlight',seriesIndex:0,dataIndex:index});chart.dispatchAction({type:'showTip',seriesIndex:0,dataIndex:index});speech.textContent=read(index);
  };
  try{refresh();}catch(error){chart.dispose();throw error;}stats.created++;stats.active++;
  const api={instance:chart,refresh,resize(){if(disposed||!host.isConnected)return;const width=plot.clientWidth,height=plot.clientHeight;if(width>0&&height>0&&(width!==lastWidth||height!==lastHeight)){lastWidth=width;lastHeight=height;chart.resize({animation:{duration:0}});}},destroy(){if(disposed)return;disposed=true;plot.onkeydown=null;chart.dispose();mounted.delete(host);stats.destroyed++;stats.active--;host.removeAttribute('data-chart-engine');}};mounted.set(host,api);return api;
 }};
})();
