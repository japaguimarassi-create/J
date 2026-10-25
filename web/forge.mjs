export const DEFAULT_SOURCE = 'scene "Orbit Study" fps=24 width=960 height=540\nbackground color=#0b1020\n\ncircle orb x=120 y=270 radius=28 color=#65e8d4\nrect ground x=0 y=442 width=960 height=98 color=#17233a\ntext heading x=42 y=64 value="MOTIONFORGE" size=28 color=#eaf2ff\n\nkey orb at=0 x=120 y=270 scale=1\nkey orb at=24 x=480 y=154 scale=1.35\nkey orb at=48 x=820 y=270 scale=1\n\ncube core x=0 y=0 z=0 size=1.2 color=#65e8d4\nkey3 core at=0 rotationY=0 rotationX=0\nkey3 core at=48 rotationY=6.28 rotationX=1.0\n';
const NUMERIC = new Set(["x","y","z","radius","width","height","size","scale","rotation","rotationX","rotationY","rotationZ","opacity","at","fps"]);
const IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_-]{0,63}$/;
function tokenize(line) {
 return (line.match(/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\S+/g)||[]).map(function(part){
  if((part[0]==='"'&&part[part.length-1]==='"')||(part[0]==="'"&&part[part.length-1]==="'"))return part.slice(1,-1).replace(/\\(["'\\])/g,"$1");
  return part;
 });
}
function attrsFrom(tokens,line,errors){
 const attrs={};
 for(const token of tokens){const split=token.indexOf("=");if(split<1){errors.push({line:line,message:'Parâmetro inválido "'+token+'". Use chave=valor.'});continue;}
  const key=token.slice(0,split),raw=token.slice(split+1);
  if(!/^[A-Za-z][A-Za-z0-9_-]*$/.test(key)||raw===""){errors.push({line:line,message:'Atributo inválido "'+token+'".'});continue;}
  if(Object.prototype.hasOwnProperty.call(attrs,key)){errors.push({line:line,message:'Atributo duplicado "'+key+'".'});continue;}
  const value=NUMERIC.has(key)?Number(raw):raw;if(NUMERIC.has(key)&&!Number.isFinite(value)){errors.push({line:line,message:'"'+key+'" precisa ser número válido.'});continue;}attrs[key]=value;
 }return attrs;
}
function validColor(value){return typeof value==="string"&&(/^#[0-9a-fA-F]{3}$/.test(value)||/^#[0-9a-fA-F]{6}$/.test(value));}
export function parseForge(source){
 const project={name:"Nova cena",fps:24,width:960,height:540,background:"#0b1020",objects:[],errors:[],source:String(source||"")},byName=new Map(),lines=project.source.split(/\r?\n/);
 for(let i=0;i<lines.length;i++){
  const trimmed=lines[i].trim();if(!trimmed||trimmed.startsWith("//"))continue;const tokens=tokenize(trimmed),command=(tokens.shift()||"").toLowerCase(),line=i+1;
  if(command==="scene"){if(!tokens.length){project.errors.push({line:line,message:'Uso: scene "Nome" fps=24 width=960 height=540'});continue;}project.name=tokens.shift();const attrs=attrsFrom(tokens,line,project.errors);for(const key of ["fps","width","height"])if(attrs[key]!==undefined)project[key]=attrs[key];continue;}
  if(command==="background"){const parsed=attrsFrom(tokens,line,project.errors),color=parsed.color||tokens[0];if(!validColor(color))project.errors.push({line:line,message:"Fundo inválido; use background color=#112233."});else project.background=color;continue;}
  if(["circle","rect","text","cube"].includes(command)){
   const name=tokens.shift();if(!IDENTIFIER.test(name||"")){project.errors.push({line:line,message:"Nome de objeto inválido."});continue;}if(byName.has(name)){project.errors.push({line:line,message:'O objeto "'+name+'" já existe.'});continue;}
   const props=attrsFrom(tokens,line,project.errors);props.color=props.color||"#65e8d4";if(!validColor(props.color))project.errors.push({line:line,message:'Cor inválida no objeto "'+name+'".'});
   if(command==="circle"&&!(props.radius>0))project.errors.push({line:line,message:'O círculo "'+name+'" precisa de radius > 0.'});
   if(command==="rect"&&(!(props.width>0)||!(props.height>0)))project.errors.push({line:line,message:'O retângulo "'+name+'" precisa de width e height > 0.'});
   if(command==="cube"&&!(props.size>0))project.errors.push({line:line,message:'O cubo "'+name+'" precisa de size > 0.'});
   const object={name:name,type:command,props:props,keyframes:[]};project.objects.push(object);byName.set(name,object);continue;
  }
  if(command==="key"||command==="key3"){
   const name=tokens.shift(),object=byName.get(name);if(!object){project.errors.push({line:line,message:'Objeto "'+name+'" não declarado antes do keyframe.'});continue;}
   if(command==="key3"&&object.type!=="cube"){project.errors.push({line:line,message:"key3 só pode animar cube."});continue;}
   const parsed=attrsFrom(tokens,line,project.errors),at=parsed.at;delete parsed.at;if(!Number.isFinite(at)||at<0){project.errors.push({line:line,message:"Keyframe precisa de at=N, com N >= 0."});continue;}
   const allowed=new Set(["x","y","z","scale","rotation","rotationX","rotationY","rotationZ","opacity","color"]);for(const key of Object.keys(parsed))if(!allowed.has(key))project.errors.push({line:line,message:'Propriedade animável não suportada "'+key+'".'});
   if(parsed.color!==undefined&&!validColor(parsed.color))project.errors.push({line:line,message:"Cor de keyframe inválida."});object.keyframes.push({at:at,props:parsed,line:line});continue;
  }
  project.errors.push({line:line,message:'Comando desconhecido "'+command+'".'});
 }
 project.fps=Math.max(1,Math.min(120,Number.isFinite(project.fps)?project.fps:24));project.width=Math.max(64,Math.min(4096,Number.isFinite(project.width)?project.width:960));project.height=Math.max(64,Math.min(4096,Number.isFinite(project.height)?project.height:540));
 for(const object of project.objects)object.keyframes.sort(function(a,b){return a.at-b.at;});if(!project.objects.length)project.errors.push({line:1,message:"A cena precisa ter pelo menos um objeto."});return project;
}
export function sampleObject(object,frame){
 const base=Object.assign({},object.props),keys=object.keyframes||[];if(!keys.length)return base;if(frame<=keys[0].at)return Object.assign(base,keys[0].props);if(frame>=keys[keys.length-1].at)return Object.assign(base,keys[keys.length-1].props);
 let left=keys[0],right=keys[keys.length-1];for(let i=0;i<keys.length-1;i++){if(frame>=keys[i].at&&frame<=keys[i+1].at){left=keys[i];right=keys[i+1];break;}}
 const amount=(frame-left.at)/Math.max(1,right.at-left.at),result=Object.assign(base,left.props),names=new Set(Object.keys(left.props).concat(Object.keys(right.props)));
 for(const name of names){const start=left.props[name]===undefined?base[name]:left.props[name],end=right.props[name]===undefined?start:right.props[name];if(typeof start==="number"&&typeof end==="number")result[name]=start+(end-start)*amount;else result[name]=amount<1?(start===undefined?end:start):end;}return result;
}
export function findSceneDuration(project,minimum=48){let maximum=minimum;for(const object of project.objects||[])for(const key of object.keyframes||[])maximum=Math.max(maximum,key.at);return Math.max(1,Math.min(10000,maximum));}
export function upsertKeyframe(source,command,name,frame,props){
 const lines=source.split(/\r?\n/),expression=new RegExp("^\\s*"+command+"\\s+"+name+"\\s+at="+frame+"(?:\\s|$)"),attrs=Object.entries(props).map(function(entry){return entry[0]+"="+String(entry[1]);}),replacement=command+" "+name+" at="+frame+" "+attrs.join(" ");
 const index=lines.findIndex(function(line){return expression.test(line);});if(index>=0)lines[index]=replacement;else lines.push(replacement);return lines.join("\n");
}