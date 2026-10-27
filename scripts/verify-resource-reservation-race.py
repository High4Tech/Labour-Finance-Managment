"""Two independent MariaDB sessions contend for one disposable QA Bin.

This isolates reservation locking; the rollback suite separately verifies real
stock reconciliation, stock ledger and valuation. No customer data is touched.
"""
import json,subprocess,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def run(action,run_id,index=0):
    result=subprocess.run(['docker','compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.reservation_testing.race','--kwargs',json.dumps(dict(action=action,run_id=run_id,index=index))],cwd=ROOT,capture_output=True,text=True,check=True)
    return json.loads(result.stdout)


if __name__=='__main__':
    run_id=uuid.uuid4().hex[:12];evidence={}
    try:
        run('begin',run_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda i:run('attempt',run_id,i),[0,1]))
        evidence=dict(attempts=results,successes=sum(r['saved'] for r in results))
        assert evidence['successes']==1,results
        print('PASS two simultaneous quantity-8 requests against quantity-12 stock: one saved, one rejected')
    finally:
        evidence['cleanup']=run('end',run_id)
        (ROOT/'.local/qa/reservation-race.json').write_text(json.dumps(evidence,indent=2))
        assert evidence['cleanup']['restored']
        print('PASS exact reservation race fixture restored')
