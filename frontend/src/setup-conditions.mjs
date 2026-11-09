// Parse the small declarative visibility language used by saved setup schemas.
// Never execute schema text or accept JavaScript/property access beyond doc.key.
export function condition(expression,values={}){
 if(!expression)return true;
 const input=expression.replace(/^eval:/,''),tokens=[];
 const pattern=/\s*(===|&&|\|\||!|\(|\)|doc\.\w+|"[^"]*"|'[^']*'|true|false|0|1)\s*/gy;
 let at=0,match;while(at<input.length){pattern.lastIndex=at;match=pattern.exec(input);if(!match)return false;tokens.push(match[1]);at=pattern.lastIndex;}
 let index=0;
 const atom=()=>{const token=tokens[index++];if(token==='!')return !atom();if(token==='('){const result=or();if(tokens[index++]!==')')throw Error();return result;}if(token?.startsWith('doc.'))return values[token.slice(4)];if(token?.startsWith('"')||token?.startsWith("'"))return token.slice(1,-1);if(['true','false','0','1'].includes(token))return token==='true'||token==='1';throw Error();};
 const compare=()=>{const left=atom();if(tokens[index]==='==='){index++;return left===atom();}return !!left&&left!=='0';};
 const and=()=>{let result=compare();while(tokens[index]==='&&'){index++;const next=compare();result=result&&next;}return result;};
 const or=()=>{let result=and();while(tokens[index]==='||'){index++;const next=and();result=result||next;}return result;};
 try{const result=or();return index===tokens.length&&!!result;}catch{return false;}
}
