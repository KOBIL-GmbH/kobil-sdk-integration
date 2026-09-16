'use strict';
const vscode=require('vscode');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const crypto=require('node:crypto');
const {execFile}=require('node:child_process');
const {promisify}=require('node:util');
const exec=promisify(execFile);
const {RELEASE,escapeHtml,connectionInfo,skillText,agentText}=require('./core');

function activate(context){
 const root=path.join(context.globalStorageUri.fsPath,'releases',RELEASE.tag);
 const event=new vscode.EventEmitter();
 let panel,side,busy=false,message='Install the integration, then build with Copilot.';
 const status=()=>context.globalState.get('setup',{});
 const config=()=>vscode.workspace.getConfiguration('kobilSdk');
 const executable=()=>path.join(root,'.venv',process.platform==='win32'?'Scripts':'bin',process.platform==='win32'?'kobil-sdk-mcp.exe':'kobil-sdk-mcp');
 const python=()=>path.join(root,'.venv',process.platform==='win32'?'Scripts':'bin',process.platform==='win32'?'python.exe':'python');
 const run=async(cmd,args,options={})=>{try{return await exec(cmd,args,{timeout:180000,maxBuffer:2*1024*1024,...options});}catch(e){throw Error(`${path.basename(cmd)} failed (${e.code || 'timeout'}). Check that it is installed and GitHub access is configured; no credentials should be placed in the URL.`);}};
 async function exists(p){try{await fs.access(p);return true;}catch{return false;}}
 async function verified(){
  if(!await exists(executable()))return false;
  const {stdout}=await run(config().get('gitPath'),['-C',root,'rev-parse','HEAD']);
  if(stdout.trim()!==RELEASE.commit)throw Error('The installed commit differs from the pinned release. Installation was not activated.');
  const dirty=await run(config().get('gitPath'),['-C',root,'status','--porcelain']);
  if(dirty.stdout.trim())throw Error('The release checkout has local modifications. Restore it before running.');
  return true;
 }
 async function save(values){await context.globalState.update('setup',{...status(),...values});event.fire();render();}
 async function env(){
  const c=status().connection;if(!c)return {};
  const info=connectionInfo(JSON.parse(await fs.readFile(c,'utf8')));
  const value=await context.secrets.get('backendCredential');
  if(!value)throw Error('Backend credential is missing. Choose Connect backend to store it securely.');
  return {KOBIL_SDK_CONNECTION:c,[info.secretName]:value};
 }
 context.subscriptions.push(event,vscode.lm.registerMcpServerDefinitionProvider('kobilSdk.release',{
  onDidChangeMcpServerDefinitions:event.event,
  provideMcpServerDefinitions:()=>status().installed?[new vscode.McpStdioServerDefinition('KOBIL SDK Release',executable(),[],{},RELEASE.version)]:[],
  resolveMcpServerDefinition:async definition=>{if(!await verified())throw Error('Install the pinned release first.');definition.env=await env();return definition;}
 }));
 async function install(){
  await run(config().get('gitPath'),['--version']);await run(config().get('uvPath'),['--version']);
  await fs.mkdir(path.dirname(root),{recursive:true});
  if(!await exists(root))await run(config().get('gitPath'),['clone','--branch',RELEASE.tag,'--depth','1',RELEASE.repository,root],{env:{...process.env,GIT_TERMINAL_PROMPT:'0'}});
  const commit=await run(config().get('gitPath'),['-C',root,'rev-parse','HEAD']);
  if(commit.stdout.trim()!==RELEASE.commit)throw Error('Release verification failed: commit does not match.');
  await run(config().get('uvPath'),['sync','--frozen','--python','3.11','--directory',root]);
  if(!await verified())throw Error('Release executable is missing after installation.');
  await save({installed:true,checked:false});
  await installSkills();message=`Release ${RELEASE.tag} installed. MCP and Copilot recipes use the same verified commit.`;
 }
 async function installSkills(){
  if(!await verified())throw Error('Install the release first.');
  const home=path.join(os.homedir(),'.copilot');
  const entries=[[path.join(home,'skills','kobil-sdk-release','SKILL.md'),skillText(root)],[path.join(home,'agents','kobil-release-builder.agent.md'),agentText(root)]];
  for(const [file,content] of entries){
   if(await exists(file)){
    const previous=await fs.readFile(file,'utf8');
    if(previous!==content && !previous.includes('<!-- Managed by KOBIL SDK extension -->'))throw Error('A custom skill or agent already exists at '+file+'. Rename it before installing this integration.');
   }
  }
  for(const [file,content] of entries){await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,content+'\n<!-- Managed by KOBIL SDK extension -->\n',{mode:0o600});}
  await save({skills:true});
 }
 async function connect(){
  const selected=await vscode.window.showOpenDialog({title:'Select your backend connection JSON',canSelectMany:false,filters:{'Connection JSON':['json']}});if(!selected)return;
  let info;try{info=connectionInfo(JSON.parse(await fs.readFile(selected[0].fsPath,'utf8')));}catch(e){throw Error('Invalid connection: '+(e instanceof SyntaxError?'The file is not valid JSON.':e.message));}
  const secret=await vscode.window.showInputBox({title:'Backend credential',prompt:`Enter the value for ${info.secretName}. Stored in VS Code SecretStorage, never in your project.`,password:true,ignoreFocusOut:true});if(secret===undefined)return;if(!secret)throw Error('The credential cannot be empty.');
  await fs.mkdir(context.globalStorageUri.fsPath,{recursive:true,mode:0o700});
  const file=path.join(context.globalStorageUri.fsPath,'connection.json');
  await fs.writeFile(file,JSON.stringify(info.config,null,2)+'\n',{mode:0o600});
  await context.secrets.store('backendCredential',secret);
  await save({connection:file,checked:false});message='Connection saved securely. Run Check setup to validate local configuration. Backend authentication is tested by the agent when you request an operation.';
 }
 async function check(){
  if(!await verified())throw Error('Install the release before checking setup.');
  const script=`import asyncio,json,os\nfrom mcp import ClientSession,StdioServerParameters\nfrom mcp.client.stdio import stdio_client\nasync def main():\n async with stdio_client(StdioServerParameters(command=${JSON.stringify(executable())},env=dict(os.environ))) as (r,w):\n  async with ClientSession(r,w) as s:\n   await s.initialize()\n   t=await s.list_tools()\n   assert len(t.tools)==13\n   for n in ${JSON.stringify(status().connection?['sdk_targets','sdk_backend_status']:['sdk_targets'])}:\n    result=await s.call_tool(n,{})\n    assert not result.isError,n\n   print('READY')\nasyncio.run(main())`;
  const result=await run(python(),['-c',script],{env:{...process.env,...await env()},timeout:30000});
  if(!result.stdout.includes('READY'))throw Error('MCP discovery did not complete.');
  await save({checked:true});message=status().connection?'MCP ready: 13 tools discovered. Local connection configuration checked; backend authentication and device behavior are separate checks.':'MCP ready: 13 tools discovered. Planning and artifact tools are ready. Connect a backend when you need provisioning.';
 }
 async function action(name){
  if(busy)return;busy=true;render();
  try{
   if(name==='install')await install();
   else if(name==='connect')await connect();
   else if(name==='check')await check();
   else if(name==='skills'){await installSkills();message='Copilot skill and KOBIL Release Builder agent installed.';}
   else if(name==='copilot'){
    if(!status().skills)throw Error('Install the integration first.');
    const choice=await vscode.window.showQuickPick(['Swift · iOS','Kotlin · Android','Flutter · Android and iOS'],{title:'Choose your app platform'});
    if(choice){await vscode.commands.executeCommand('workbench.action.chat.open',{query:`/kobil-sdk-release Build a fresh ${choice} app. Help me choose the features, project folder and app identifier, then implement and test it.`,isPartialQuery:true});message='Choose KOBIL Release Builder in the Copilot agent picker, then send your request.';}
   }
   else if(name==='notes')await vscode.env.openExternal(vscode.Uri.parse(RELEASE.repository.replace('.git','')+'/releases/tag/'+RELEASE.tag));
   else if(name==='settings')await vscode.commands.executeCommand('workbench.action.openSettings','@ext:kobil.kobil-sdk-integration');
   else if(name==='example'){
    const doc=await vscode.workspace.openTextDocument({language:'json',content:JSON.stringify({environment:'your-development',tenant:'your-tenant',ast_url:'https://ast.example',services:[{name:'astCa',url:'https://ast.example'},{name:'astLogin',url:'https://ast.example'}],oauth:{token_url:'https://identity.example/realms/your-realm/protocol/openid-connect/token',client_id:'your-service-client',client_secret_env:'KOBIL_SDK_CLIENT_SECRET'}},null,2)});await vscode.window.showTextDocument(doc);message='Replace the example endpoints and complete the services map with your deployment values, save privately, then choose Connect backend.';
   }
  }catch(e){message=e.message;vscode.window.showErrorMessage('KOBIL SDK: '+message);}finally{busy=false;render();}
 }
 function bind(webview){webview.options={enableScripts:true,localResourceRoots:[]};context.subscriptions.push(webview.onDidReceiveMessage(m=>{if(m && typeof m.action==='string')void action(m.action);}));}
 function render(){for(const w of [panel?.webview,side?.webview])if(w)w.html=html();}
 function html(){const s=status(),nonce=crypto.randomBytes(18).toString('base64');const esc=escapeHtml;
 return `<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';"><style nonce="${nonce}">
 :root{color-scheme:light dark}*{box-sizing:border-box}body{margin:0;background:var(--vscode-editor-background);color:var(--vscode-editor-foreground);font:14px/1.55 var(--vscode-font-family)}main{max-width:1000px;margin:auto;padding:36px 28px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--vscode-widget-border);padding-bottom:20px}.brand{font-weight:800;letter-spacing:3px;font-size:19px}.badge{font-size:11px;border:1px solid var(--vscode-widget-border);padding:5px 10px;border-radius:30px}.eyebrow{color:var(--vscode-textLink-foreground);font-size:11px;font-weight:700;letter-spacing:2px;margin-top:38px}h1{font-size:clamp(29px,5vw,48px);line-height:1.12;letter-spacing:-1.5px;margin:12px 0 18px;max-width:660px}.lead{color:var(--vscode-descriptionForeground);max-width:620px;font-size:16px}.platforms{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0 32px}.pill{border:1px solid var(--vscode-widget-border);border-radius:5px;padding:5px 10px;font-size:12px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}.card{border:1px solid var(--vscode-widget-border);border-radius:12px;padding:22px;background:var(--vscode-sideBar-background)}.number{font:12px var(--vscode-editor-font-family);color:var(--vscode-descriptionForeground)}h2{font-size:18px;margin:12px 0 8px}.card p{min-height:66px;color:var(--vscode-descriptionForeground)}button{cursor:pointer;border:1px solid transparent;border-radius:6px;padding:10px 14px;font:inherit;background:var(--vscode-button-background);color:var(--vscode-button-foreground)}button:hover{background:var(--vscode-button-hoverBackground)}button:focus-visible{outline:2px solid var(--vscode-focusBorder);outline-offset:3px}button:disabled{opacity:.5;cursor:wait}.secondary{background:transparent;color:var(--vscode-textLink-foreground);padding:8px 0;margin-right:18px}.status{margin:24px 0;padding:17px 20px;border-left:3px solid var(--vscode-textLink-foreground);background:var(--vscode-textBlockQuote-background);border-radius:4px}.foot{color:var(--vscode-descriptionForeground);font-size:12px;margin-top:25px}.ready{color:var(--vscode-testing-iconPassed)}@media(max-width:450px){main{padding:20px 16px}.eyebrow{margin-top:25px}h1{font-size:31px}.card p{min-height:0}}
 </style></head><body><main><header><span class="brand">KOBIL <span style="font-weight:400;letter-spacing:0">/ SDK</span></span><span class="badge">COPILOT EDITION · PREVIEW</span></header><div class="eyebrow">FROM IDEA TO RUNNING APP</div><h1>Your app.<br>Connected with KOBIL.</h1><p class="lead">Set up once. Describe what you want to build in GitHub Copilot, with the SDK tools and integration guidance ready to use.</p><div class="platforms"><span class="pill">Swift / iOS</span><span class="pill">Kotlin / Android</span><span class="pill">Flutter / Android + iOS</span></div><section class="grid"><article class="card"><span class="number">01 / INTEGRATION</span><h2>One fixed release</h2><span class="${s.installed?'ready':''}">${s.installed?'Installed':'Not installed'} · ${RELEASE.tag}</span><p>MCP and skill, installed together from a verified GitHub commit.</p><button data-action="install" ${busy?'disabled':''}>${s.installed?'Verify / repair setup':'Install integration'}</button><br><button class="secondary" data-action="notes">Release notes ↗</button></article><article class="card"><span class="number">02 / YOUR BACKEND</span><h2>Connect your services</h2><span>${s.connection?'Connection saved':'Optional for planning'}</span><p>Import your deployment configuration. Credentials stay in VS Code secure storage.</p><button data-action="connect" ${busy?'disabled':''}>Connect backend</button><br><button class="secondary" data-action="example">Create config template</button></article><article class="card"><span class="number">03 / BUILD WITH COPILOT</span><h2>Make it your app</h2><span>${s.skills?'Agent and skill installed':'Setup required'}</span><p>Choose a platform, describe your features, then build and test with the release agent.</p><button data-action="copilot" ${busy||!s.skills?'disabled':''}>Open Copilot →</button><br><button class="secondary" data-action="skills">Refresh agent & skill</button></article></section><div class="status" role="status" aria-live="polite">${busy?'Working… Keep this window open while setup completes.':esc(message)}</div><button data-action="check" ${busy||!s.installed?'disabled':''}>${s.checked?'✓ Check setup again':'Check setup'}</button> <button class="secondary" data-action="settings">Tool paths & settings</button><p class="foot">Requires Git and uv; uv can provision Python 3.11. Private repository access must already be configured in Git. SDK binaries are delivered separately. Native app builds need the platform toolchain. ${s.checked?'MCP discovery verified. Backend authentication and device flows are not certified by this check.':''}</p></main><script nonce="${nonce}">const api=acquireVsCodeApi();document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>api.postMessage({action:b.dataset.action})));</script></body></html>`;
 }
 context.subscriptions.push(vscode.window.registerWebviewViewProvider('kobilSdk.welcome',{resolveWebviewView(view){side=view;bind(view.webview);render();}}));
 context.subscriptions.push(vscode.commands.registerCommand('kobilSdk.open',()=>{if(panel){panel.reveal();return;}panel=vscode.window.createWebviewPanel('kobilSdk.setup','KOBIL SDK · App Builder',vscode.ViewColumn.One,{enableScripts:true});bind(panel.webview);panel.onDidDispose(()=>panel=undefined);render();}));
 if(!context.globalState.get('welcomed')){void context.globalState.update('welcomed',true);void vscode.commands.executeCommand('kobilSdk.open');}
}
module.exports={activate};
