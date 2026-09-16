const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
test('registers a stdio MCP with the VS Code constructor contract, without credentials during discovery',()=>{
 let provider;const registered={};const vscode={
  EventEmitter:class{event=()=>{};fire(){}dispose(){}},
  McpStdioServerDefinition:class{constructor(label,command,args,env,version){assert.equal(typeof label,'string');Object.assign(this,{label,command,args,env,version});}},
  lm:{registerMcpServerDefinitionProvider(id,p){assert.equal(id,'kobilSdk.release');provider=p;return {dispose(){}};}},
  workspace:{getConfiguration:()=>({get:()=>null})},
  window:{registerWebviewViewProvider:()=>({dispose(){}})},
  commands:{registerCommand:(n,f)=>{registered[n]=f;return {dispose(){}};}}
 };
 const sandbox={require:n=>n==='vscode'?vscode:n==='./core'?require('../src/core'):require(n),module:{exports:{}},process,URL};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/extension.js'),'utf8'),sandbox);
 sandbox.module.exports.activate({globalStorageUri:{fsPath:'/private/extension'},globalState:{get:k=>k==='setup'?{installed:true}:true},subscriptions:[],secrets:{get(){throw Error('Secret must not be read during discovery');}}});
 const [server]=provider.provideMcpServerDefinitions();assert.equal(server.label,'KOBIL SDK Release');assert.equal(server.version,'0.3.3');assert.equal(Object.keys(server.env).length,0);assert(server.command.includes('v0.3.3'));assert(registered['kobilSdk.open']);
});
