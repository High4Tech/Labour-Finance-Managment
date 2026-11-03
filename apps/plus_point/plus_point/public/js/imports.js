/* One React owner for all product template/upload/review/approval flows.
 * Native Data Import and the original transactional import engine are retained. */
(()=>{
 const pp=window.plus_point;
 pp.open_import=async(company,onClose,kind='employees',returnLabel='Return to records',options={})=>{
  await pp.load_feature('react_ui');
  return pp.react_import_open({company,kind,returnLabel,onClose,...options});
 };
})();
